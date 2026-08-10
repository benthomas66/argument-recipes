"""ADAPTIVE_SCORING_V1 — the eight component functions and the weighted sum.

Pure core, no database (mirrors mastery_engine.py's stance). Constants are
loaded from schemas/adaptive_scoring_constants.json — the machine-readable
contract — never re-typed here. The TS mirror (packages/adaptive-engine/src/
scoringConstants.ts) and this module are drift-checked against the doc by
tests/test_adaptive_scoring_contract.py.

Every function returns a float in 0.0–1.0. Shapes are fixed by the doc
(§1–§8); only the named constants are tunable, and only under a new
algorithm_version. The four HARD RULES (§0.5) are NOT here — they are gates
and tiers that run around the scorer, implemented in adaptive_selection.py.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
C = json.loads(
    (ROOT / 'schemas' / 'adaptive_scoring_constants.json').read_text(encoding='utf-8'))

ALGORITHM_VERSION = C['algorithm_version']
WEIGHTS = C['weights']

# The eight components in Spec 04 §13 weight order — the canonical ordering,
# matching packages/shared/src/selection.ts ADAPTIVE_COMPONENTS.
COMPONENT_ORDER = (
    'target_match', 'mastery_need', 'due_review', 'difficulty_fit',
    'freshness', 'coverage_balance', 'surface_variety', 'eligibility_quality')
WEIGHT_VECTOR = tuple(WEIGHTS[c] for c in COMPONENT_ORDER)


def _clamp01(x: float) -> float:
    return min(1.0, max(0.0, x))


def level_from_mastery(mastery_score: float) -> float:
    """§9 dep 1: lvl = 1 + 4·mastery_score (the 1–5 per-dimension band)."""
    return C['level_map_intercept'] + C['level_map_slope'] * mastery_score


# ---------------------------------------------------------------------------
# §1 target_match — weight 30. Graded over the target's grain hierarchy; the
# grades ARE the §9 fallback ladder and draw the Rule 2 tier boundary (≥0.85).


def target_match(item: dict, target: dict) -> float:
    """item carries: question_type, normalized_recipe_id, difficulty,
    trap_families (iterable of the families its wrong choices exercise).
    target carries any of: trap_family, recipe_id, question_type, difficulty,
    and optionally canonical_id + is_review for a review-obligation target
    (which matches on canonical_id | trap_family at 1.00)."""
    if target.get('is_review'):
        if target.get('canonical_id') and item.get('canonical_id') == target['canonical_id']:
            return C['tm_trap']
        if target.get('trap_family') and target['trap_family'] in set(item.get('trap_families') or ()):
            return C['tm_trap']
    grades = [0.0]
    tf = target.get('trap_family')
    if tf and tf in set(item.get('trap_families') or ()):
        grades.append(C['tm_trap'])
    if target.get('recipe_id') and item.get('normalized_recipe_id') == target['recipe_id']:
        grades.append(C['tm_recipe'])
    if target.get('question_type') and item.get('question_type') == target['question_type']:
        grades.append(C['tm_qtype'])
    if (target.get('difficulty') is not None
            and item.get('difficulty') == target['difficulty']):
        grades.append(C['tm_band'])
    return max(grades)


# ---------------------------------------------------------------------------
# §2 mastery_need — weight 20. Desirable-difficulty Gaussian peaking in the
# developing band, gated by evidence. (Very-low mastery is Rule 4's job, not
# this curve's.)


def mastery_need(mastery_score: float, attempt_count: int) -> float:
    raw = math.exp(-((mastery_score - C['peak']) ** 2) / (2 * C['width'] ** 2))
    gate = min(1.0, attempt_count / C['min_evid']) if C['min_evid'] else 1.0
    return _clamp01(raw * gate)


# ---------------------------------------------------------------------------
# §3 due_review — weight 15. Zero before due; steps up at due; climbs while
# overdue; saturates.


def due_review(days_since_due: float | None) -> float:
    """days_since_due = now − due_at in days (negative = not yet due; None =
    no review obligation)."""
    if days_since_due is None or days_since_due < 0:
        return 0.0
    floor, sat = C['overdue_floor'], C['overdue_sat']
    return _clamp01(floor + (1 - floor) * (days_since_due / sat))


# ---------------------------------------------------------------------------
# §4 difficulty_fit — weight 10. Asymmetric window centered slightly above
# current ability; tolerant of "a bit too hard," less of "too easy."


def difficulty_fit(item_difficulty: float, mastery_score: float) -> float:
    lvl = level_from_mastery(mastery_score)
    delta = item_difficulty - (lvl + C['stretch'])
    tol = C['hard_tol'] if delta >= 0 else C['easy_tol']
    return _clamp01(math.exp(-(delta ** 2) / (2 * tol ** 2)))


# ---------------------------------------------------------------------------
# §5 freshness — weight 10. Cross-session recovery curve (same-session dup is
# Rule 3's hard exclusion, not here).


def freshness(days_since_seen: float | None, mode: str = 'normal') -> float:
    if mode in ('redo', 'review') or days_since_seen is None:
        return 1.0
    return _clamp01(1 - C['fresh_depth'] * math.exp(-days_since_seen / C['fresh_recover']))


# ---------------------------------------------------------------------------
# §6 coverage_balance — weight 5. Session-context; on question_type.


def coverage_balance(seen_question_type_count: int) -> float:
    return _clamp01(1 / (1 + C['cov_saturation'] * seen_question_type_count))


# ---------------------------------------------------------------------------
# §7 surface_variety — weight 5. Session-context; on the item's scenario.


def surface_variety(seen_scenario_count: int) -> float:
    return _clamp01(1 / (1 + C['var_saturation'] * seen_scenario_count))


# ---------------------------------------------------------------------------
# §8 eligibility_quality — weight 5. Pool is already all-eligible (Rule 1);
# rewards breadth only.


def eligibility_quality(eligibility_flags_set: int) -> float:
    breadth = eligibility_flags_set / 5
    return _clamp01(C['elig_base'] + C['elig_breadth'] * breadth)


# ---------------------------------------------------------------------------
# Weighted sum (Spec 04 §13). components is a dict over COMPONENT_ORDER.


def adaptive_item_score(components: dict) -> float:
    missing = set(COMPONENT_ORDER) - set(components)
    if missing:
        raise ValueError(f'component_scores missing keys: {sorted(missing)}')
    return sum(WEIGHTS[c] * components[c] for c in COMPONENT_ORDER)
