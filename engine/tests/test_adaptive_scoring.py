"""Step C — shape tests for the eight ADAPTIVE_SCORING_V1 component functions.

Each assertion pins a shape property the doc fixes (peak location, saturation,
asymmetry, gating), not just a point value — a wrong shape fails even if a
single point happens to match.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts' / 'diagnostic'))

import scoring as s  # noqa: E402


# ---------------------------------------------------------------------------
# §1 target_match — graded ladder


def _item(**kw):
    base = {'question_type': 'FL', 'normalized_recipe_id': 'R1',
            'difficulty': 3, 'trap_families': ['Scope Failure'],
            'canonical_id': 'AR_1'}
    base.update(kw)
    return base


def test_target_match_grades_descend_by_grain():
    assert s.target_match(_item(), {'trap_family': 'Scope Failure'}) == 1.00
    assert s.target_match(_item(), {'recipe_id': 'R1'}) == 0.85
    assert s.target_match(_item(), {'question_type': 'FL'}) == 0.55
    assert s.target_match(_item(), {'difficulty': 3}) == 0.25
    assert s.target_match(_item(), {'trap_family': 'Other'}) == 0.00


def test_target_match_takes_the_max_applicable_grain():
    # same recipe AND same qtype -> recipe (0.85) dominates
    assert s.target_match(_item(), {'recipe_id': 'R1', 'question_type': 'FL'}) == 0.85


def test_review_target_matches_on_canonical_or_family_at_1():
    assert s.target_match(_item(), {'is_review': True, 'canonical_id': 'AR_1'}) == 1.00
    assert s.target_match(
        _item(trap_families=['Role Failure']),
        {'is_review': True, 'trap_family': 'Role Failure'}) == 1.00


# ---------------------------------------------------------------------------
# §2 mastery_need — Gaussian peaking at PEAK=0.45, evidence-gated


def test_mastery_need_peaks_near_0_45():
    peak = s.mastery_need(0.45, 10)
    assert peak == pytest.approx(1.0, abs=1e-9)
    assert s.mastery_need(0.10, 10) < peak
    assert s.mastery_need(0.90, 10) < peak


def test_mastery_need_evidence_gate_suppresses_one_attempt():
    # one attempt is gated to 1/3 of the raw need
    assert s.mastery_need(0.45, 1) == pytest.approx(1 / 3, abs=1e-9)
    assert s.mastery_need(0.45, 3) == pytest.approx(1.0, abs=1e-9)


# ---------------------------------------------------------------------------
# §3 due_review — zero before due, floor at due, saturates overdue


def test_due_review_zero_before_due():
    assert s.due_review(-1) == 0.0
    assert s.due_review(None) == 0.0


def test_due_review_floor_at_due_and_saturates():
    assert s.due_review(0) == pytest.approx(0.60, abs=1e-9)   # OVERDUE_FLOOR
    assert s.due_review(7) == pytest.approx(1.0, abs=1e-9)    # OVERDUE_SAT
    assert s.due_review(100) == 1.0                            # saturated


# ---------------------------------------------------------------------------
# §4 difficulty_fit — asymmetric: harder tolerated more than easier


def test_difficulty_fit_asymmetry():
    # lvl at mastery 0.5 = 3.0; target center = 3.5
    center_hi = s.difficulty_fit(4.5, 0.5)  # +1.0 over center
    center_lo = s.difficulty_fit(2.5, 0.5)  # -1.0 under center
    assert center_hi > center_lo  # too-hard less penalized than too-easy


def test_difficulty_fit_peaks_at_center():
    at_center = s.difficulty_fit(3.5, 0.5)  # delta 0
    assert at_center == pytest.approx(1.0, abs=1e-9)


# ---------------------------------------------------------------------------
# §5 freshness — 1 when never seen / redo / review; dips then recovers


def test_freshness_full_when_never_seen_or_special_mode():
    assert s.freshness(None) == 1.0
    assert s.freshness(0.0, mode='redo') == 1.0
    assert s.freshness(0.0, mode='review') == 1.0


def test_freshness_dips_just_after_seen_and_recovers():
    just = s.freshness(0.0)   # ~0.1
    later = s.freshness(20.0)  # recovered toward 1
    assert just == pytest.approx(0.1, abs=1e-9)
    assert later > just


# ---------------------------------------------------------------------------
# §6 / §7 saturating session-context signals


def test_coverage_and_variety_saturate_with_repetition():
    assert s.coverage_balance(0) == 1.0
    assert s.coverage_balance(1) < 1.0
    assert s.coverage_balance(3) < s.coverage_balance(1)
    # variety is stronger than coverage at the same seen count (VAR>COV)
    assert s.surface_variety(1) < s.coverage_balance(1)


# ---------------------------------------------------------------------------
# §8 eligibility_quality — breadth reward above a base


def test_eligibility_quality_breadth():
    assert s.eligibility_quality(0) == pytest.approx(0.85, abs=1e-9)
    assert s.eligibility_quality(5) == pytest.approx(1.0, abs=1e-9)
    assert s.eligibility_quality(2) < s.eligibility_quality(5)


# ---------------------------------------------------------------------------
# weighted sum


def test_adaptive_item_score_uses_the_fixed_weight_vector():
    assert s.WEIGHT_VECTOR == (30, 20, 15, 10, 10, 5, 5, 5)
    ones = {c: 1.0 for c in s.COMPONENT_ORDER}
    assert s.adaptive_item_score(ones) == 100.0
    zeros = {c: 0.0 for c in s.COMPONENT_ORDER}
    assert s.adaptive_item_score(zeros) == 0.0


def test_adaptive_item_score_rejects_missing_components():
    with pytest.raises(ValueError):
        s.adaptive_item_score({'target_match': 1.0})
