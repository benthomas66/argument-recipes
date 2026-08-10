"""Steps D/E — the four hard rules, tiering, determinism, and log shape,
tested against the PURE pipeline (no database). Rule 1 (the publication/
eligibility pre-filter) is a DB-layer concern verified in
tests/test_adaptive_conformance.py.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts' / 'diagnostic'))

import adaptive_selection as asel  # noqa: E402


def item(cid, *, qt='FL', recipe='R1', diff=3, scenario='s', families=('Scope Failure',),
         flags=5):
    return {'canonical_id': cid, 'content_version': 1, 'question_type': qt,
            'normalized_recipe_id': recipe, 'difficulty': diff,
            'scenario': scenario, 'trap_families': list(families),
            'elig_flags': flags}


TARGET = {'dimension': ('trap_family', 'Scope Failure'), 'trap_family': 'Scope Failure'}
# mid mastery with evidence -> NOT foundational; mastery_need computable
MASTERY_MID = {('trap_family', 'Scope Failure'): {'mastery_score': 0.5, 'attempt_count': 5}}


# ---------------------------------------------------------------------------
# Rule 2 — exact tier beats fallback tier even at lower total score


def test_rule2_exact_tier_beats_higher_scoring_fallback():
    exact = item('EXACT', families=['Scope Failure'], diff=1, flags=1)   # weak extras
    fallback = item('FALLB', families=['Other'], recipe='R9', qt='WK',   # no target grain
                    diff=4, flags=5)
    out = asel.select_slots(
        [exact, fallback], targets=[TARGET], slot_count=1,
        mastery_by_dim=MASTERY_MID,
        recent_by_cid={'EXACT': 0.0},          # exact recently seen (low freshness)
        review_by_cid={'FALLB': 10.0},          # fallback overdue (high due_review)
        seed='s1')
    assert out[0]['canonical_id'] == 'EXACT'
    assert out[0]['fallback_used'] is False
    # sanity: the fallback item's raw total is actually higher, proving tiering
    # is categorical, not additive
    from scoring import adaptive_item_score
    fb_comps = asel._components_for(
        fallback, TARGET, MASTERY_MID, {}, {'FALLB': 10.0}, {}, {}, 'normal')
    ex_comps = asel._components_for(
        exact, TARGET, MASTERY_MID, {'EXACT': 0.0}, {}, {}, {}, 'normal')
    assert adaptive_item_score(fb_comps) > adaptive_item_score(ex_comps)


def test_rule2_fallback_used_flag_when_no_exact_candidate():
    fallback = item('FALLB', families=['Other'], recipe='R9', qt='WK')
    out = asel.select_slots(
        [fallback], targets=[TARGET], slot_count=1, mastery_by_dim=MASTERY_MID,
        recent_by_cid={}, review_by_cid={}, seed='s1')
    assert out[0]['canonical_id'] == 'FALLB'
    assert out[0]['fallback_used'] is True


# ---------------------------------------------------------------------------
# Rule 3 — no same-session duplicates unless redo


def test_rule3_no_duplicates_across_slots():
    cands = [item(f'C{i}', families=['Scope Failure']) for i in range(5)]
    out = asel.select_slots(
        cands, targets=[TARGET], slot_count=3, mastery_by_dim=MASTERY_MID,
        recent_by_cid={}, review_by_cid={}, seed='s1')
    picked = [s['canonical_id'] for s in out]
    assert len(picked) == 3 and len(set(picked)) == 3


def test_rule3_redo_mode_allows_repeat_when_pool_is_one():
    only = item('ONLY', families=['Scope Failure'])
    out = asel.select_slots(
        [only], targets=[TARGET], slot_count=2, mastery_by_dim=MASTERY_MID,
        recent_by_cid={}, review_by_cid={}, seed='s1', mode='redo')
    assert [s['canonical_id'] for s in out] == ['ONLY', 'ONLY']


# ---------------------------------------------------------------------------
# Rule 4 — very-low-mastery target routes to foundational (lowest difficulty)


def test_rule4_routes_very_low_mastery_to_foundational():
    low = {('trap_family', 'Scope Failure'): {'mastery_score': 0.10, 'attempt_count': 3}}
    hard = item('HARD', families=['Scope Failure'], diff=5, flags=5)
    easy = item('EASY', families=['Scope Failure'], diff=2, flags=1)  # lowest diff
    other = item('OTHER', families=['Other'], recipe='R9', qt='WK', diff=1)
    out = asel.select_slots(
        [hard, easy, other], targets=[{'dimension': ('trap_family', 'Scope Failure'),
                                       'trap_family': 'Scope Failure'}],
        slot_count=1, mastery_by_dim=low, recent_by_cid={}, review_by_cid={},
        seed='s1')
    assert out[0]['selection_reason'] == 'foundational_instruction'
    assert out[0]['fallback_used'] is False
    # lowest-difficulty item that MATCHES the target grain (EASY diff 2),
    # not OTHER (diff 1 but wrong grain), not by adaptive score
    assert out[0]['canonical_id'] == 'EASY'


def test_rule4_not_triggered_below_evidence_gate():
    # mastery < 0.20 but only 1 attempt -> NOT foundational (evidence gate)
    thin = {('trap_family', 'Scope Failure'): {'mastery_score': 0.10, 'attempt_count': 1}}
    c = item('C1', families=['Scope Failure'])
    out = asel.select_slots(
        [c], targets=[TARGET], slot_count=1, mastery_by_dim=thin,
        recent_by_cid={}, review_by_cid={}, seed='s1')
    assert out[0]['selection_reason'] == 'adaptive_selection'


# ---------------------------------------------------------------------------
# Determinism (Spec 04 §19)


def test_determinism_identical_inputs_and_seed():
    cands = [item(f'C{i}', families=['Scope Failure'], diff=(i % 5) + 1) for i in range(12)]
    kw = dict(targets=[TARGET], slot_count=6, mastery_by_dim=MASTERY_MID,
              recent_by_cid={}, review_by_cid={}, seed='fixed-seed')
    a = asel.select_slots(list(cands), **kw)
    b = asel.select_slots(list(cands), **kw)
    assert [s['canonical_id'] for s in a] == [s['canonical_id'] for s in b]
    assert [s['component_scores'] for s in a] == [s['component_scores'] for s in b]
    assert [s['adaptive_item_score'] for s in a] == [s['adaptive_item_score'] for s in b]


def test_seed_changes_tie_break_order():
    # all-identical candidates except id -> only the seeded tie-break decides
    cands = [item(f'C{i}', families=['Scope Failure'], diff=3, scenario=f'sc{i}')
             for i in range(8)]
    kw = dict(targets=[TARGET], slot_count=1, mastery_by_dim=MASTERY_MID,
              recent_by_cid={}, review_by_cid={})
    p1 = asel.select_slots(list(cands), seed='seed-A', **kw)[0]['canonical_id']
    p2 = asel.select_slots(list(cands), seed='seed-B', **kw)[0]['canonical_id']
    # not guaranteed different for every pair, but these two seeds differ here
    assert p1 != p2


def test_tie_break_prefers_least_recently_seen():
    a = item('A', families=['Scope Failure'], scenario='sa')
    b = item('B', families=['Scope Failure'], scenario='sb')
    # identical scoring except freshness: A seen 1 day ago, B seen 30 days ago.
    # B is less recently seen AND has higher freshness -> B wins on score; to
    # isolate the tie-break we instead make freshness equal via mode='review'
    # (freshness=1 for both) and differ only recent history.
    out = asel.select_slots(
        [a, b], targets=[TARGET], slot_count=1, mastery_by_dim=MASTERY_MID,
        recent_by_cid={'A': 1.0, 'B': 30.0}, review_by_cid={}, seed='s',
        mode='review')
    assert out[0]['canonical_id'] == 'B'  # least recently seen


# ---------------------------------------------------------------------------
# Log shape


def test_every_selection_has_all_eight_components():
    cands = [item(f'C{i}', families=['Scope Failure']) for i in range(4)]
    out = asel.select_slots(
        cands, targets=[TARGET], slot_count=3, mastery_by_dim=MASTERY_MID,
        recent_by_cid={}, review_by_cid={}, seed='s')
    for s in out:
        assert set(s['component_scores']) == set(asel.sc.COMPONENT_ORDER)
        assert s['item_order'] in (1, 2, 3)
