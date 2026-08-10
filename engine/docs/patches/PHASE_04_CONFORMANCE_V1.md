# PHASE_04_CONFORMANCE_V1

Status: **ruling document, T-04 spec conformance audit.** Governs Phase 4 (Explanations & Trap Feedback). Produced by reading `docs/tasks/PHASE_04_EXPLANATIONS_TRAP_FEEDBACK.md` and its controlling specs (Spec 02 §10/§13, Spec 03 §7.3/§9.4, Spec 04 §14, Spec 10) against the repo at v25. **This document rules; it changes no code.**

Citation convention: repo artifacts `file:line`; `.docx` specs by section and table row.

---

## 1. Defects found

**D4-1 — The naive trap-feedback join silently drops every credited explanation.** *(master-audit F-3, verified)*
`content_explanations.trap_family` is `not null` (`db/migrations/0001_mvp_schema.sql:69`) and carries the sentinel `'N/A_correct'` on the credited choice — **200 of the 1000 explanation rows** in the V1 bank (counted from `data/runs/AR_V1_FULL200_20260708T014500Z_c7d41a2b/consolidated/output/generated_items_all200.csv`: one credited choice per item × 200 items). `trap_taxonomy` has exactly the 20 seeded families and **no `N/A_correct` row** (`db/seeds/0001_trap_taxonomy_seed.sql:4` — "excluding N/A_correct"; `TRAP_GRAIN_V1` ruling 5: the sentinel "is **not** a `trap_taxonomy` row and must never be seeded as one"). Therefore `content_explanations INNER JOIN trap_taxonomy ON trap_family` returns nothing for any credited choice: the correct-answer explanation — the row a student who just got it right most wants — vanishes.

**D4-2 — The Phase 4 task packet points at the wrong schema for trap data.**
`docs/tasks/PHASE_04_EXPLANATIONS_TRAP_FEEDBACK.md` (Inputs) describes `schemas/content_choice_schema.json` as carrying a "per-choice trap label." It does not: its properties are `canonical_id, content_version, choice_letter, choice_text, is_correct, display_order, created_from_shuffle` — no trap fields. Trap fields live on `schemas/content_explanation_schema.json` (`trap_label`, `trap_family`, both required), per `CONTENT_DDL_CONFORMANCE_V1` D-2/ruling 3, which corrected exactly this misplacement. The packet's wording is stale relative to that correction; `tests/test_ts_schema_alignment.py:79–82` even asserts that a trap label on a choice **fails** validation.

**D4-3 — "Trap label in student-friendly language" has no lookup to be friendly with.**
The Phase 4 packet and Spec 02 §13 require the trap label and family "in student-readable language." Only `trap_family` has a pedagogy row (`trap_taxonomy.student_name`, `db/migrations/0003_spec03_tables.sql:19–26`). `trap_label` is free text with no controlled vocabulary and no FK (`TRAP_GRAIN_V1` ruling 3) — there is nothing to translate it *through*.

**D4-4 — `user_events.event_type` is declared in Spec 03 and constrained nowhere.** *(audit-discovered; extends master-audit F-4's list)*
Spec 03 §9.4 declares six event types (`item_viewed, explanation_opened, trap_lesson_opened, review_added, session_abandoned, dashboard_viewed`), two of which are Phase 4 surfaces. `user_events.event_type` (`db/migrations/0003_spec03_tables.sql:59–67`) is unconstrained text with no TS constant and no JSON schema. Note these are **product/UX events, distinct from** the 18-name analytics dictionary (`packages/shared/src/analytics.ts`, constrained by `0005`) — a Phase 4 implementer could plausibly write `explanation_viewed` (analytics name) into `user_events` (whose spec name is `explanation_opened`) and no layer would object.

## 2. Rulings

1. **D4-1 — The correct-answer path never consults `trap_taxonomy`.** Per Spec 04 §14 (feedback routing: correct answers get confirmation + recipe reinforcement, not trap diagnosis) and Spec 02 §10, the correct-answer render is: the item's `content_explanations` row with `explanation_role = 'correct'` (`0001_mvp_schema.sql:67`), plus recipe pedagogy from `recipes` via `content_items.normalized_recipe_id`. Trap pedagogy joins happen **only** on the wrong-answer path, keyed by the *selected* choice's `trap_family`, filtered to `explanation_role = 'wrong'`. Any query that must span both roles uses a LEFT JOIN to `trap_taxonomy` and treats null pedagogy as "credited choice," never as an error. **RESOLVED.**

2. **D4-2 — `content_explanation_schema.json` is the trap-data contract for Phase 4.** The packet's reference to the choice schema is corrected by this ruling (the packet file itself is left untouched; this document supersedes its Inputs wording per the T-04 convention that rulings correct packets). Choices supply text and `is_correct` only. **RESOLVED.**

3. **D4-3 — Family renders through the taxonomy; label renders as itself.** `trap_family` is displayed via `trap_taxonomy.student_name` (+ `definition`/`why_tempting`/`repair_prompt` as the Spec 02 §13 components). `trap_label` is displayed verbatim from the explanation row: per `TRAP_GRAIN_V1` ruling 3 it is "a descriptor used to render the explanation" — it was authored as student-facing copy and needs no lookup. If a label reads as internal jargon, that is a content defect for the T-08 content-V2 backlog, not a schema problem. **RESOLVED.**

4. **D4-4 — Spec 03 §9.4's six-value list is authoritative for `user_events.event_type`.** Phase 4's surface events are `explanation_opened` and `trap_lesson_opened` in `user_events`; `explanation_viewed`/`trap_feedback_viewed` remain **analytics** events per `ANALYTICS_EVENT_DICTIONARY_V1` (emitted contract-only in Phase 4, wired in Phase 8, per the packet). The two namespaces must not be cross-written. The value list and its declaration surface go to the backlog for `0006`. **RESOLVED.**

5. **Source-safety pin (no defect).** The explanation surface renders nothing from staging and no factory-internal columns; `tests/test_schema_loader_readiness.py` (FORBIDDEN_IN_APP_TABLES) already guarantees the app tables cannot even store `source_question_number` etc. The Phase 4 privacy constraint is structurally satisfied; the implementer's only obligation is not to query staging.

## 3. Accepted deviations

| Authority | Says | Repo does | Why |
|---|---|---|---|
| Phase 4 task packet (Inputs) | choice schema carries per-choice trap label | trap fields live on `content_explanation_schema.json` | `CONTENT_DDL_CONFORMANCE_V1` D-2 corrected the placement; packet wording is stale |
| Spec 02 §13 ("student-readable" trap label) | implies a translation layer for labels | label renders verbatim; only family translates via `trap_taxonomy.student_name` | `TRAP_GRAIN_V1` ruling 3: labels are free-text render descriptors, 666 values / 575 singletons |

## 4. Conformance checks (for the Phase 4 implementer)

1. Answer an item correctly; assert the explanation screen shows the `explanation_role = 'correct'` row's text. This is the F-3 regression check — it fails under an inner join.
2. Assert no SQL path inner-joins `content_explanations` to `trap_taxonomy` without an `explanation_role = 'wrong'` filter (grep the Phase 4 queries; or run one credited-choice render through each).
3. Answer wrongly; assert the feedback shows `trap_taxonomy.student_name` for the *selected* choice's family, plus that explanation row's `why tempting / why fails` text (Spec 02 §10.1 layout).
4. Assert the rendered surface contains no `source_bank`, `run_id`, or any FORBIDDEN_IN_APP_TABLES column value.
5. Assert Phase 4 writes `user_events.event_type = 'explanation_opened'` / `'trap_lesson_opened'` (Spec 03 §9.4), and does **not** write analytics dictionary names into `user_events`.
