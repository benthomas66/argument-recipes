// ADAPTIVE_SCORING_V1 §10 constant registry — TS mirror of
// schemas/adaptive_scoring_constants.json (the machine-readable canonical the
// Python runtime reads). Values are tunable ONLY under a new algorithm_version;
// the shapes and the §0.5 hard rules are fixed. tests/test_adaptive_scoring_contract.py
// asserts JSON == this file == the literals in ADAPTIVE_SCORING_V1.md §10 — the
// same drift-tripwire pattern as MASTERY_CONTRACT_V1 / test_mastery_contract.py.

import { ADAPTIVE_COMPONENTS } from '@argument-recipes/shared';
import type { AdaptiveComponent } from '@argument-recipes/shared';

export const ADAPTIVE_ALGORITHM_VERSION = 'adaptive_scoring_v1';

// Spec 04 §13 weight vector (FIXED, not tunable), in component order.
export const ADAPTIVE_WEIGHTS: Record<AdaptiveComponent, number> = {
  target_match: 30,
  mastery_need: 20,
  due_review: 15,
  difficulty_fit: 10,
  freshness: 10,
  coverage_balance: 5,
  surface_variety: 5,
  eligibility_quality: 5,
};

// Ordered weight vector, guaranteed aligned to ADAPTIVE_COMPONENTS.
export const ADAPTIVE_WEIGHT_VECTOR = ADAPTIVE_COMPONENTS.map(
  (c) => ADAPTIVE_WEIGHTS[c],
) as readonly number[];

// Rule 2 / Rule 4 gates (§0.5).
export const TIER_EXACT_MIN = 0.85;
export const FOUNDATIONAL_THRESHOLD = 0.2;
export const FOUNDATIONAL_MIN_EVID = 2;

// §1 target_match grades.
export const TM_TRAP = 1.0;
export const TM_RECIPE = 0.85;
export const TM_QTYPE = 0.55;
export const TM_BAND = 0.25;

// §2 mastery_need Gaussian + evidence gate.
export const PEAK = 0.45;
export const WIDTH = 0.22;
export const MIN_EVID = 3;

// §3 due_review saturation.
export const OVERDUE_FLOOR = 0.6;
export const OVERDUE_SAT = 7;

// §4 difficulty_fit asymmetric window.
export const STRETCH = 0.5;
export const HARD_TOL = 1.1;
export const EASY_TOL = 0.7;

// §5 freshness recovery curve.
export const FRESH_DEPTH = 0.9;
export const FRESH_RECOVER = 5;

// §6 / §7 session-context saturations.
export const COV_SATURATION = 0.8;
export const VAR_SATURATION = 1.0;

// §8 eligibility breadth.
export const ELIG_BASE = 0.85;
export const ELIG_BREADTH = 0.15;

// §9 dep 1 level map: lvl = 1 + 4·mastery_score.
export const LEVEL_MAP_INTERCEPT = 1;
export const LEVEL_MAP_SLOPE = 4;

export function levelFromMastery(masteryScore: number): number {
  return LEVEL_MAP_INTERCEPT + LEVEL_MAP_SLOPE * masteryScore;
}
