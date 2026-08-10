"""Phase 5 — Daily Repair slot plan (pure) + framing.

Verifies Spec 04 §9's structured mix, per-slot targeting, Rule 3 spanning the
whole session, deterministic underfill fallback, determinism, log shape, and
the server-side framing/redaction. DB-side proofs (mastery + review update on
finalize) run in scripts/diagnostic/verify_daily_repair_live.py.
"""
import re
import sys
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts' / 'diagnostic'))

import daily_repair as dr  # noqa: E402
import scoring as sc  # noqa: E402
import framing  # noqa: E402


def item(cid, *, qt='FL', recipe='R1', diff=3, scenario='s', families=('Scope Failure',),
         flags=5):
    return {'canonical_id': cid, 'content_version': 1, 'question_type': qt,
            'normalized_recipe_id': recipe, 'difficulty': diff, 'scenario': scenario,
            'trap_families': list(families), 'elig_flags': flags}


# A mastery profile with stable/developing dims (warmup), weak recipe dims
# (targeted_recipe), and missed trap families (trap_repair).
MASTERY = {
    ('recipe', 'RA'): {'mastery_score': 0.78, 'attempt_count': 6},   # stable  -> warmup
    ('recipe', 'RB'): {'mastery_score': 0.60, 'attempt_count': 5},   # developing -> warmup
    ('recipe', 'RC'): {'mastery_score': 0.30, 'attempt_count': 4},   # weak -> targeted
    ('recipe', 'RD'): {'mastery_score': 0.25, 'attempt_count': 4},   # weak -> targeted
    ('recipe', 'RE'): {'mastery_score': 0.35, 'attempt_count': 4},   # weak -> targeted
    ('trap_family', 'Scope Failure'): {'mastery_score': 0.30, 'attempt_count': 4},
    ('trap_family', 'Role Failure'): {'mastery_score': 0.35, 'attempt_count': 4},
}


def big_pool():
    """A pool with exact-target items for every slot plus filler, so no slot
    underfills and each segment picks its intended targets."""
    items = []
    n = 0
    for recipe in ('RA', 'RB', 'RC', 'RD', 'RE'):
        for _k in range(4):
            n += 1
            items.append(item(f'C{n}', recipe=recipe, qt='FL', scenario=f'sc{n}',
                              families=['Scope Failure' if recipe in ('RC', 'RD') else 'Role Failure']))
    for fam in ('Scope Failure', 'Role Failure'):
        for _k in range(4):
            n += 1
            items.append(item(f'T{n}', recipe='RX', qt='WK', scenario=f'sd{n}', families=[fam]))
    return items


def slot_of_position(pos):
    # plan emits slots in order; item_order 1..10 maps to segments
    if pos <= 2:
        return 'warmup'
    if pos <= 7:
        return 'targeted_recipe'
    if pos <= 9:
        return 'trap_repair'
    return 'review'


# ---------------------------------------------------------------------------
# Acceptance 1 — exactly 10 items in the §9 mix (by position + reason)


def test_daily_repair_is_ten_items_in_the_section9_mix():
    due_cid = 'REVIEW_ITEM'
    cands = big_pool() + [item(due_cid, recipe='RZ', qt='SA', scenario='rz',
                               families=['Language Failure'])]
    out = dr.plan_daily_repair(
        cands, mastery_by_dim=MASTERY, recent_by_cid={},
        review_by_cid={due_cid: 3.0}, seed='s')
    assert len(out) == 10
    for s in out:
        pos = s['item_order']
        slot = slot_of_position(pos)
        reason = s['selection_reason']
        base = re.sub(r'_fallback$', '', reason)
        # each item's reason matches its slot (slot name, its *_fallback, or
        # foundational_instruction inside a repair slot)
        allowed = {slot, 'foundational_instruction'} if slot in (
            'targeted_recipe', 'trap_repair') else {slot}
        assert base in allowed or reason == f'{slot}_fallback', \
            f'position {pos} ({slot}) had reason {reason!r}'
    # the review slot found the due obligation (not a fallback)
    assert out[9]['selection_reason'] == 'review'
    assert out[9]['canonical_id'] == due_cid


# ---------------------------------------------------------------------------
# Acceptance 2 — warmup targets stable/developing; repair slots target weak


def test_slot_targets_differ_by_intent():
    warm = dr._warmup_targets(MASTERY)
    targeted = dr._targeted_recipe_targets(MASTERY)
    trap = dr._trap_repair_targets(MASTERY)
    warm_recipes = {t.get('recipe_id') for t in warm}
    targeted_recipes = [t.get('recipe_id') for t in targeted]
    trap_fams = [t.get('trap_family') for t in trap]
    # Per Spec 04 §9 the extremes are cleanly separated: the STABLE recipe is a
    # warmup target only; the WEAK recipes are targeted-only. (A DEVELOPING
    # recipe legitimately qualifies for both — consolidate vs drill.)
    assert 'RA' in warm_recipes and 'RA' not in targeted_recipes  # stable -> warmup only
    assert {'RC', 'RD', 'RE'} <= set(targeted_recipes)            # weak -> targeted
    assert not warm_recipes & {'RC', 'RD', 'RE'}                  # weak never warmup
    # weak/developing recipes, lowest mastery first (RD 0.25 leads)
    assert targeted_recipes[0] == 'RD'
    # trap_repair targets the missed families, lowest first (Scope 0.30 first)
    assert trap_fams[0] == 'Scope Failure'


# ---------------------------------------------------------------------------
# Acceptance 3 — Rule 3 spans the whole session


def test_no_duplicate_across_the_whole_session():
    cands = big_pool() + [item('REVIEW_ITEM', recipe='RZ', families=['Language Failure'])]
    out = dr.plan_daily_repair(
        cands, mastery_by_dim=MASTERY, recent_by_cid={},
        review_by_cid={'REVIEW_ITEM': 2.0}, seed='s')
    cids = [s['canonical_id'] for s in out]
    assert len(cids) == len(set(cids)) == 10


def test_redo_mode_allows_repeats_when_pool_small():
    only = [item('ONLY', recipe='RC', families=['Scope Failure'])]
    out = dr.plan_daily_repair(
        only, mastery_by_dim=MASTERY, recent_by_cid={}, review_by_cid={},
        seed='s', mode='redo')
    # redo lets the single item recur to fill the 10 slots
    assert len(out) == 10
    assert all(s['canonical_id'] == 'ONLY' for s in out)


# ---------------------------------------------------------------------------
# Acceptance 5 — deterministic fallback when a slot can't fill


def test_review_slot_falls_back_when_nothing_due():
    cands = big_pool()
    out = dr.plan_daily_repair(
        cands, mastery_by_dim=MASTERY, recent_by_cid={},
        review_by_cid={}, seed='s')  # no due obligation
    review = out[9]
    assert review['selection_reason'] == 'review_fallback'
    assert review['fallback_used'] is True
    assert len(out) == 10  # still a full session


# ---------------------------------------------------------------------------
# Acceptance 6 — determinism


def test_determinism_identical_seed_identical_queue():
    cands = big_pool() + [item('REVIEW_ITEM', recipe='RZ', families=['Language Failure'])]
    kw = dict(mastery_by_dim=MASTERY, recent_by_cid={},
              review_by_cid={'REVIEW_ITEM': 2.0}, seed='fixed')
    a = dr.plan_daily_repair(list(cands), **kw)
    b = dr.plan_daily_repair(list(cands), **kw)
    assert [(s['canonical_id'], s['selection_reason']) for s in a] == \
           [(s['canonical_id'], s['selection_reason']) for s in b]
    assert [s['component_scores'] for s in a] == [s['component_scores'] for s in b]


# ---------------------------------------------------------------------------
# Acceptance 9 — every selection carries all eight component scores


def test_every_selection_has_eight_components():
    cands = big_pool() + [item('REVIEW_ITEM', recipe='RZ', families=['Language Failure'])]
    out = dr.plan_daily_repair(
        cands, mastery_by_dim=MASTERY, recent_by_cid={},
        review_by_cid={'REVIEW_ITEM': 2.0}, seed='s')
    for s in out:
        assert set(s['component_scores']) == set(sc.COMPONENT_ORDER)
        assert isinstance(s['adaptive_item_score'], float)


# ---------------------------------------------------------------------------
# Rule 4 still fires inside a repair slot for a genuinely-lost dimension


def test_rule4_foundational_inside_targeted_slot():
    mastery = dict(MASTERY)
    mastery[('recipe', 'RD')] = {'mastery_score': 0.10, 'attempt_count': 3}  # very low
    cands = big_pool() + [item('REVIEW_ITEM', recipe='RZ', families=['Language Failure'])]
    out = dr.plan_daily_repair(
        cands, mastery_by_dim=mastery, recent_by_cid={},
        review_by_cid={'REVIEW_ITEM': 2.0}, seed='s')
    targeted = [s for s in out if 3 <= s['item_order'] <= 7]
    assert any(s['selection_reason'] == 'foundational_instruction' for s in targeted)


# ---------------------------------------------------------------------------
# Acceptance 8 building block — framing never leaks raw bands/scores


def test_framing_matches_ts_labels_and_confidence():
    ts = (ROOT / 'packages' / 'shared' / 'src' / 'dashboardFraming.ts').read_text(encoding='utf-8')
    # the Python labels must all appear in the TS mapping (drift tripwire)
    for label in ['Focus area', 'Improving', 'Solid', 'Strong', 'Not yet assessed']:
        assert f"'{label}'" in ts, f'label {label!r} missing from dashboardFraming.ts'
    assert framing.frame_mastery_band('weak') == 'Focus area'
    assert framing.frame_mastery_band('mastered') == 'Strong'
    assert framing.frame_mastery_band('decayed') == 'Focus area'  # never leaks the word
    for cnt, exp in [(0, 'limited evidence'), (2, 'limited evidence'),
                     (3, 'some evidence'), (4, 'some evidence'),
                     (5, 'well-established'), (12, 'well-established')]:
        assert framing.mastery_confidence(cnt) == exp
    # confidence thresholds mirror the TS (<3, <5)
    assert "attemptCount < 3" in ts and "attemptCount < 5" in ts


def test_student_mastery_view_omits_raw_band_and_score():
    RAW = ['weak', 'developing', 'stable', 'mastered', 'new', 'decayed']
    for raw in RAW:
        view = framing.to_student_mastery_view('trap_family', 'Scope Failure',
                                               raw, 5, direction='improved')
        blob = str(view)
        for band in RAW:
            assert band not in blob
        assert 'mastery_score' not in blob and '0.' not in blob
        assert view['label'] and view['confidence'] and view['direction'] == 'improved'
