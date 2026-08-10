"""Mastery updates and diagnostic summary — pure core, no database.

Authorities: MASTERY_CONTRACT_V1 (deltas, bands, mastered gate;
algorithm_version mvp_rule_v1); TRAP_GRAIN_V1 (trap_family is the mastery
grain; trap_label may appear ONLY in diagnostic reporting);
PHASE_03_CONFORMANCE_V1 D3-8 (the two dimension lists); DIAGNOSTIC_MIX_V1 §3
(the asymmetric reading rule for single-item categories).

Constants are loaded from schemas/mastery_contract_constants.json — the
machine-readable contract — never re-typed. Stated assumptions (report §3):
  A1. On a wrong answer only the recipe (−0.08) and selected trap_family
      (−0.10) dimensions update; question_type updates on correct answers
      only. This is the contract's literal text.
  A2. change_reason is 'correct' for positive updates and 'missed_trap' for
      both negative updates (the miss is the cause; the 5-value list has no
      recipe-specific decrement reason). 'decay' is never written.
  A3. recent_accuracy is the mean correctness of the last 10 attempts
      touching that dimension (the contract names a moving window without a
      width; 10 is the MVP width, recorded here).
  A4. Trap-family/trap-label diagnostic rows report selections: attempt_count
      = times that trap was chosen, correct_count = 0 (choosing a trap is by
      definition a miss). question_type/recipe rows report attempts on items
      of that type/recipe.
"""
from __future__ import annotations

import json
from pathlib import Path

from mix import SINGLE_ITEM_CATEGORIES

ROOT = Path(__file__).resolve().parents[2]
CONSTANTS = json.loads(
    (ROOT / 'schemas' / 'mastery_contract_constants.json').read_text(encoding='utf-8'))

ALGORITHM_VERSION = CONSTANTS['algorithm_version']
INITIAL = CONSTANTS['initial_score']
CORRECT_DELTA = CONSTANTS['correct_delta']
WRONG_RECIPE_DELTA = CONSTANTS['wrong_recipe_delta']
WRONG_TRAP_DELTA = CONSTANTS['wrong_trap_delta']
RECENT_WINDOW = 10  # A3

MASTERY_DIMENSIONS = tuple(CONSTANTS['dimension_types'])  # 4 values, no trap_label
assert 'trap_label' not in MASTERY_DIMENSIONS


def clamp(x: float) -> float:
    return min(1.0, max(0.0, x))


def band(score: float, attempt_count: int, recent_accuracy: float) -> str:
    """MASTERY_CONTRACT_V1 bands. 'new' is assigned only at zero attempts by
    the caller; this function bands a post-attempt state."""
    if score < CONSTANTS['band_weak_below']:
        return 'weak'
    if score < CONSTANTS['band_developing_below']:
        return 'developing'
    if score < CONSTANTS['band_stable_below']:
        return 'stable'
    if (attempt_count >= CONSTANTS['mastered_min_attempts']
            and recent_accuracy >= CONSTANTS['mastered_min_recent_accuracy']):
        return 'mastered'
    return 'stable'


def mastery_updates_for_attempt(attempt: dict) -> list[dict]:
    """The dimension updates one attempt produces (contract §update rule).

    attempt needs: is_correct, question_type, normalized_recipe_id,
    selected_trap_family (real family on a miss; sentinel on a hit).
    Returns [{dimension_type, dimension_id, delta, change_reason}, ...] —
    dimension_type always within the 4-value mastery list.
    """
    if attempt['is_correct']:
        return [
            {'dimension_type': 'recipe', 'dimension_id': attempt['normalized_recipe_id'],
             'delta': CORRECT_DELTA, 'change_reason': 'correct', 'is_correct': True},
            {'dimension_type': 'question_type', 'dimension_id': attempt['question_type'],
             'delta': CORRECT_DELTA, 'change_reason': 'correct', 'is_correct': True},
        ]
    family = attempt['selected_trap_family']
    assert family and family != 'N/A_correct', \
        'a wrong attempt must carry the selected distractor\'s real trap_family'
    return [
        {'dimension_type': 'recipe', 'dimension_id': attempt['normalized_recipe_id'],
         'delta': WRONG_RECIPE_DELTA, 'change_reason': 'missed_trap', 'is_correct': False},
        {'dimension_type': 'trap_family', 'dimension_id': family,
         'delta': WRONG_TRAP_DELTA, 'change_reason': 'missed_trap', 'is_correct': False},
    ]


def apply_updates(attempts: list[dict], initial_states: dict | None = None) -> tuple[dict, list[dict]]:
    """Replay attempts in order into an in-memory mastery profile.

    Returns (states, events): states keyed by (dimension_type, dimension_id)
    with score/attempt_count/recent (list)/status; events one per update with
    before/after. The engine persists both verbatim.

    initial_states (Phase 5, cross-session continuation): optional
    {(dimension_type, dimension_id): {'score','attempt_count','recent','status'}}
    to SEED starting state. The diagnostic calls this with no seed (every
    dimension starts at INITIAL). Daily Repair seeds the prior SCORE (so a
    returning student's mastery continues rather than restarting) while leaving
    attempt_count at 0 so the caller's additive upsert accumulates the true
    total. Default None reproduces the pre-Phase-5 behavior exactly.
    """
    states: dict[tuple[str, str], dict] = {}
    if initial_states:
        for key, seed in initial_states.items():
            states[key] = {
                'score': seed['score'],
                'attempt_count': seed.get('attempt_count', 0),
                'recent': list(seed.get('recent', [])),
                'status': seed.get('status', 'new'),
            }
    events: list[dict] = []
    for attempt in attempts:
        for upd in mastery_updates_for_attempt(attempt):
            key = (upd['dimension_type'], upd['dimension_id'])
            st = states.setdefault(key, {
                'score': INITIAL, 'attempt_count': 0, 'recent': [], 'status': 'new'})
            before = st['score']
            st['score'] = clamp(round(st['score'] + upd['delta'], 10))
            st['attempt_count'] += 1
            st['recent'] = (st['recent'] + [1 if upd['is_correct'] else 0])[-RECENT_WINDOW:]
            recent_accuracy = sum(st['recent']) / len(st['recent'])
            st['recent_accuracy'] = recent_accuracy
            st['status'] = band(st['score'], st['attempt_count'], recent_accuracy)
            events.append({
                'dimension_type': upd['dimension_type'],
                'dimension_id': upd['dimension_id'],
                'before_score': before,
                'after_score': st['score'],
                'change_reason': upd['change_reason'],
            })
    return states, events


def diagnostic_dimension_rows(attempts: list[dict]) -> list[dict]:
    """diagnostic_results_by_dimension rows (the 5-value list; trap_label
    PERMITTED here and only here — TRAP_GRAIN_V1 ruling 4, D3-8)."""
    agg: dict[tuple[str, str], dict] = {}

    def touch(dt: str, di: str, correct: bool):
        a = agg.setdefault((dt, di), {'correct': 0, 'attempts': 0})
        a['attempts'] += 1
        a['correct'] += 1 if correct else 0

    for at in attempts:
        touch('question_type', at['question_type'], at['is_correct'])
        touch('recipe', at['normalized_recipe_id'], at['is_correct'])
        if not at['is_correct']:  # A4: trap rows report selections (misses)
            touch('trap_family', at['selected_trap_family'], False)
            if at.get('selected_trap_label'):
                touch('trap_label', at['selected_trap_label'], False)

    rows = []
    for (dt, di), a in agg.items():
        rows.append({
            'dimension_type': dt, 'dimension_id': di,
            'correct_count': a['correct'], 'attempt_count': a['attempts'],
            'accuracy': round(a['correct'] / a['attempts'], 6),
        })
    return rows


def apply_priority_ranks(rows: list[dict], category_by_qt: dict[str, str]) -> None:
    """Rank repair priorities in place; encode the asymmetric reading rule.

    Ranked: every dimension with at least one miss, by (accuracy asc,
    attempt_count desc, dimension_id). Single-item categories
    (DIAGNOSTIC_MIX_V1 §3): a MISSED single-observation question_type is
    ranked like any miss and its interpretation says so; a HIT one gets
    priority_rank None — one observation certifies nothing and must not
    outrank (i.e. must not carry a rank at all against) unmeasured categories.
    """
    def is_single_item_qt(row) -> bool:
        return (row['dimension_type'] == 'question_type'
                and category_by_qt.get(row['dimension_id']) in SINGLE_ITEM_CATEGORIES)

    for row in rows:
        row['priority_rank'] = None
        if is_single_item_qt(row):
            if row['correct_count'] == row['attempt_count']:
                row['interpretation_text'] = (
                    'Single observation: a hit certifies nothing '
                    '(asymmetric reading rule, DIAGNOSTIC_MIX_V1 §3). Unranked.')
            else:
                row['interpretation_text'] = (
                    'Single observation missed: flagged for repair '
                    '(asymmetric reading rule, DIAGNOSTIC_MIX_V1 §3).')
        else:
            row['interpretation_text'] = None

    missed = [r for r in rows if r['correct_count'] < r['attempt_count']]
    missed.sort(key=lambda r: (r['accuracy'], -r['attempt_count'], r['dimension_id']))
    for rank, row in enumerate(missed, start=1):
        row['priority_rank'] = rank
