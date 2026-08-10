# MASTERY_CONTRACT_V1

Status: canonical, operator-approved. Resolves the Spec 03 §12.3 / Spec 04 conflict: Spec 03 controls storage shape and MVP constants; Spec 04 controls band boundaries (normalized to 0–1) and review-stage intervals. algorithm_version: mvp_rule_v1.

## The approved contract

- Scale: mastery_score is a number 0.0–1.0. New dimensions start at 0.50.
- Update rule: correct answer +0.06 (applied to the relevant recipe and question-type dimensions); wrong answer −0.08 to the recipe dimension and −0.10 to the selected trap dimension, keyed on **`trap_family`** (the `trap_family` of the selected distractor; `attempts.selected_trap_label` is still logged per Spec 04 §121 but is not a mastery dimension — TRAP_GRAIN_V1 §2.2/§2.4). Clamp to [0.0, 1.0].
- Bands from score: weak < 0.40; developing 0.40–0.699…; stable 0.70–0.849…; mastered ≥ 0.85 — but mastered additionally requires attempt_count >= 5 AND recent_accuracy >= 0.80; if score ≥ 0.85 without both conditions, the band is stable.
- Status enum (storage): new, weak, developing, stable, mastered, decayed. new = zero attempts. decayed is reserved — no MVP rule assigns it; it exists for future decay logic. Do not invent decay behavior.
- Dimension types: recipe, trap_family, question_type, difficulty.
  - **Narrowing note (2026-07-09):** `trap_label` was originally listed here and has been removed, per the operator-approved ruling in TRAP_GRAIN_V1 §2.2: per-label mastery cannot converge (666 labels, 575 singletons in V1), so `trap_family` is the trap mastery grain. This propagates the narrowing already enforced by the `db/migrations/0001` CHECK on `mastery_states.dimension_type` to this contract, `packages/shared/src/mastery.ts`, `schemas/mastery_contract_constants.json`, and `schemas/mastery_state_schema.json` (master-audit B-1). `attempts.selected_trap_label` remains logged; it simply is not a mastery dimension.
- Review intervals (replaces the doubling logic): stage schedule 1 → 3 → 7 → 21 days. Correct answer advances to the next stage (21 stays at 21). Incorrect answer resets to 1 day.

## Machine-readable constants

`schemas/mastery_contract_constants.json` mirrors these values for validation tripwires. Code constants live in `packages/shared/src/mastery.ts`.
