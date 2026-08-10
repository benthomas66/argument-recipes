"""Phase 5 — Daily Repair slot-plan assembler (Spec 04 §9).

Daily Repair is the repeatable 10-question treatment loop with a STRUCTURED
mix — 2 warmup · 5 targeted_recipe · 2 trap_repair · 1 review — where each
segment has its OWN selection rule. This module is the slot-plan LAYER above
the Phase 7 scorer: it derives slot-specific targets, constrains each segment,
and calls the frozen, reused `adaptive_selection.select_slots` per segment. It
adds NO scoring of its own.

`plan_daily_repair` is PURE (no I/O), like `select_slots`. The DB loaders and
persistence stay in adaptive_selection.py; assemble_session calls this when
session_type='daily_repair'.

Rule mapping (Spec 04 §9, verbatim):
  * warmup (2)          — accessible items near the student's stable/developing
                          level (consolidation, the opposite end from repair).
  * targeted_recipe (5) — items targeting top weak/developing RECIPE dims.
  * trap_repair (2)     — items pressuring top missed TRAP_FAMILY dims.
  * review (1)          — highest-priority due obligation (learning_queues via
                          load_due_reviews); deterministic fallback if none due.

Rule 3 (no duplicate item) spans the WHOLE session across slots — enforced by
excluding already-chosen canonical_ids from each subsequent segment's pool.
"""
from __future__ import annotations

import json
from pathlib import Path

import adaptive_selection as asel
import scoring as sc

ROOT = Path(__file__).resolve().parents[2]

_MIX = json.loads(
    (ROOT / 'schemas' / 'daily_repair_mix.json').read_text(encoding='utf-8'))
DAILY_REPAIR_MIX = _MIX['daily_repair_mix']            # [{slot,count}, ...]
WARMUP_TARGET_BANDS = tuple(_MIX['warmup_target_bands'])  # ('stable','developing')
MIX_TOTAL = sum(s['count'] for s in DAILY_REPAIR_MIX)     # 10

# Band thresholds from the mastery contract (never re-typed).
_MC = json.loads(
    (ROOT / 'schemas' / 'mastery_contract_constants.json').read_text(encoding='utf-8'))
BAND_WEAK_BELOW = _MC['band_weak_below']          # 0.40
BAND_DEVELOPING_BELOW = _MC['band_developing_below']  # 0.70
BAND_STABLE_BELOW = _MC['band_stable_below']      # 0.85

SLOT_WARMUP = 'warmup'
SLOT_TARGETED = 'targeted_recipe'
SLOT_TRAP = 'trap_repair'
SLOT_REVIEW = 'review'
SLOT_NAMES = (SLOT_WARMUP, SLOT_TARGETED, SLOT_TRAP, SLOT_REVIEW)


def _band(score: float) -> str:
    if score < BAND_WEAK_BELOW:
        return 'weak'
    if score < BAND_DEVELOPING_BELOW:
        return 'developing'
    if score < BAND_STABLE_BELOW:
        return 'stable'
    return 'mastered'


def _dims(mastery_by_dim: dict, dim_type: str) -> list[tuple]:
    """(dimension, mastery) for one dimension type, evidence-bearing only."""
    return [(dim, m) for dim, m in mastery_by_dim.items()
            if dim[0] == dim_type and m['attempt_count'] >= 1]


def _warmup_targets(mastery_by_dim: dict) -> list[dict]:
    """Stable/developing dims (consolidation). Recipe dims preferred, then
    question_type; most-consolidated (highest mastery) first. Generic if none."""
    pool = []
    for dt in ('recipe', 'question_type'):
        for dim, m in _dims(mastery_by_dim, dt):
            if _band(m['mastery_score']) in WARMUP_TARGET_BANDS:
                pool.append((dim, m))
    pool.sort(key=lambda kv: (-kv[1]['mastery_score'], kv[0][0], kv[0][1]))
    return [_target_for(dim) for dim, _m in pool] or [{}]


def _targeted_recipe_targets(mastery_by_dim: dict) -> list[dict]:
    """Top weak/developing recipe dims (mastery < developing threshold),
    lowest first. Generic if none."""
    weak = [(dim, m) for dim, m in _dims(mastery_by_dim, 'recipe')
            if m['mastery_score'] < BAND_DEVELOPING_BELOW]
    weak.sort(key=lambda kv: (kv[1]['mastery_score'], kv[0][1]))
    return [_target_for(dim) for dim, _m in weak] or [{}]


def _trap_repair_targets(mastery_by_dim: dict) -> list[dict]:
    """Top missed trap_family dims (lowest mastery first). Generic if none."""
    trap = _dims(mastery_by_dim, 'trap_family')
    trap.sort(key=lambda kv: (kv[1]['mastery_score'], kv[0][1]))
    return [_target_for(dim) for dim, _m in trap] or [{}]


def _target_for(dim: tuple) -> dict:
    dt, di = dim
    if dt == 'trap_family':
        return {'dimension': dim, 'trap_family': di}
    if dt == 'recipe':
        return {'dimension': dim, 'recipe_id': di}
    if dt == 'question_type':
        return {'dimension': dim, 'question_type': di}
    return {'dimension': dim, 'difficulty': None}


def _relabel(selections: list[dict], slot_name: str) -> None:
    """Tag primary picks with the slot name, but preserve foundational_instruction
    when Rule 4 fired inside a repair slot. Leaves the scorer's fallback_used
    (the Rule 2 tier flag) untouched — that is distinct from slot-underfill."""
    for s in selections:
        if s['selection_reason'] != asel.REASON_FOUNDATIONAL:
            s['selection_reason'] = slot_name


def _fallback_fill(slot_name: str, candidates: list[dict], chosen: set,
                   need: int, mastery_by_dim: dict, recent_by_cid: dict,
                   review_by_cid: dict, seed, mode: str = 'normal') -> list[dict]:
    """Deterministic underfill fallback: pick the best remaining items from the
    general pool (top-weak targets), tagged '<slot>_fallback' + fallback_used.
    In redo mode repeats are allowed, so the chosen set is not subtracted."""
    pool = (list(candidates) if mode == 'redo'
            else [c for c in candidates if c['canonical_id'] not in chosen])
    if not pool or need <= 0:
        return []
    targets = asel.derive_targets(mastery_by_dim)
    picked = asel.select_slots(
        pool, targets=targets, slot_count=need, mastery_by_dim=mastery_by_dim,
        recent_by_cid=recent_by_cid, review_by_cid=review_by_cid,
        seed=seed, mode=mode)
    for s in picked:
        s['selection_reason'] = f'{slot_name}_fallback'
        s['fallback_used'] = True
    return picked


def _review_targets_and_pool(candidates: list[dict], chosen: set,
                             review_by_cid: dict) -> tuple[list[dict], list[dict]]:
    """The single highest-priority DUE obligation (most overdue first, using the
    days-since-due the loader provides), constrained to eligible candidates.
    Empty when nothing is due — the caller then falls back."""
    by_cid = {c['canonical_id']: c for c in candidates}
    due = [(cid, days) for cid, days in review_by_cid.items()
           if days is not None and days >= 0
           and cid not in chosen and cid in by_cid]
    if not due:
        return [], []
    due.sort(key=lambda kv: (-kv[1], kv[0]))  # most overdue first, then id
    top_cid = due[0][0]
    item = by_cid[top_cid]
    fam = (item.get('trap_families') or [None])[0]
    target = {'is_review': True, 'canonical_id': top_cid}
    if fam:
        target['trap_family'] = fam
    return [target], [item]


def plan_daily_repair(candidates: list[dict], *, mastery_by_dim: dict,
                      recent_by_cid: dict, review_by_cid: dict,
                      seed: str | None = None, mode: str = 'normal') -> list[dict]:
    """Assemble the ordered 10-item Daily Repair queue per Spec 04 §9. Returns
    selections (each with the full item_selected shape from select_slots) tagged
    with slot-naming selection_reasons. Rule 3 spans the whole session. Returns
    fewer than MIX_TOTAL only under genuine global pool exhaustion."""
    chosen: set[str] = set()
    out: list[dict] = []

    slot_targets = {
        SLOT_WARMUP: _warmup_targets(mastery_by_dim),
        SLOT_TARGETED: _targeted_recipe_targets(mastery_by_dim),
        SLOT_TRAP: _trap_repair_targets(mastery_by_dim),
    }

    for slot in DAILY_REPAIR_MIX:
        name, count = slot['slot'], slot['count']
        avail = (candidates if mode == 'redo'
                 else [c for c in candidates if c['canonical_id'] not in chosen])

        if name == SLOT_REVIEW:
            targets, pool = _review_targets_and_pool(candidates, chosen, review_by_cid)
        else:
            targets, pool = slot_targets[name], avail

        picked = []
        if pool:
            picked = asel.select_slots(
                pool, targets=targets, slot_count=count,
                mastery_by_dim=mastery_by_dim, recent_by_cid=recent_by_cid,
                review_by_cid=review_by_cid, seed=seed, mode=mode)
            _relabel(picked, name)
            for s in picked:
                chosen.add(s['canonical_id'])

        if len(picked) < count:
            picked += _fallback_fill(
                name, candidates, chosen, count - len(picked),
                mastery_by_dim, recent_by_cid, review_by_cid, seed, mode)
            for s in picked:
                chosen.add(s['canonical_id'])

        out += picked

    for i, s in enumerate(out, start=1):
        s['item_order'] = i
    return out
