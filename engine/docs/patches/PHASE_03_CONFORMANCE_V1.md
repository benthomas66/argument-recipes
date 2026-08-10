# PHASE_03_CONFORMANCE_V1

Status: **ruling document, T-04 spec conformance audit.** Governs Phase 3 (Student Diagnostic MVP). Produced by reading `docs/tasks/PHASE_03_STUDENT_DIAGNOSTIC_MVP.md` and its controlling specs (Spec 02 §§6–9, Spec 03 §§9–10, Spec 04, Spec 10) against the repo at v25 (`db/migrations/0001`–`0005`, `schemas/*.json`, `packages/shared/src/*.ts`). **This document rules; it changes no code.** DDL/schema changes it proposes are collected in `ENUM_CONSTRAINT_BACKLOG_V1.md` for a single later migration.

Citation convention: repo artifacts are cited `file:line`. The specs are `.docx` and have no line numbers; they are cited by section and table row.

---

## 1. Defects found

**D3-1 — `sessions` is missing three columns Spec 03 requires.**
Spec 03 §9.1 requires `planned_item_count` (integer, **yes**), `actual_item_count` (integer, no), and `selection_policy` (string, **yes**). The table at `db/migrations/0001_mvp_schema.sql:75–82` has only `session_id, user_id, session_type, status, started_at, completed_at`; `schemas/session_schema.json` mirrors the same six fields. Phase 3's acceptance test "answer all 15 items" has nowhere to record that 15 was planned, and "Policy or rule used to assemble the session" (§9.1) has no home.

**D3-2 — The fifth `session_type` value disagrees across spec and repo.**
Spec 03 §9.1: `diagnostic, daily_repair, targeted_drill, missed_trap_review,` **`free_practice`**. The repo — `schemas/session_schema.json` (`session_type` enum), `schemas/student_attempt_schema.json` (`session_type` enum), and `packages/shared/src/attempts.ts:3` (`SessionType` union) — all say **`timed_practice`**. Spec 02 §6 defines only four loops (Diagnostic, Daily Repair, Targeted Drill, Missed-Trap Review) and names neither.

**D3-3 — `session_status` value lists disagree, and the column is unconstrained.**
Spec 03 §9.1: `created, in_progress, completed, abandoned` (4). `schemas/session_schema.json` `status` enum: `active, completed, abandoned` (3). `db/migrations/0001_mvp_schema.sql:79` is unconstrained `text`.

**D3-4 — Correct-attempt trap fields: sentinel per the specs, null per the repo.**
Spec 03 §9.3 marks `selected_trap_label` / `selected_trap_family` required **yes**, "N/A_correct if correct"; Spec 04 §5 (Attempt Evaluation and Signal Extraction, signal table) says "Correct attempts record N/A_correct" for both, and Spec 04 Appendix B's pseudocode assigns `selected_trap = "N/A_correct"` on a correct answer; `TRAP_GRAIN_V1` ruling 4 says both fields are "retained and both populated." The repo allows null: `db/migrations/0001_mvp_schema.sql:95–96` (nullable columns), `schemas/student_attempt_schema.json` (`["string","null"]`), and the Phase 3 task packet's own wording "trap if wrong" implies null-when-correct.

**D3-5 — `confidence_self_report`: two value vocabularies and a type clash.**
Spec 03 §9.3: `low, medium, high, skipped`. `schemas/student_attempt_schema.json` and `packages/shared/src/attempts.ts:18`: `low, medium, high,` **`not_collected`**. And `packages/shared/src/api.ts:22` declares `confidence_self_report?: number` on `SubmitAnswerRequest` — a **TypeScript-internal contradiction** with `attempts.ts:18`'s string union. `tsc --noEmit` passes because the two interfaces are never assigned to each other; the first handler that copies the request field onto a `StudentAttempt` will not typecheck. The DDL column (`0001_mvp_schema.sql:98`) is unconstrained text.

**D3-6 — `StudentAttempt` (TS) is missing `scoring_context`.**
`schemas/student_attempt_schema.json` lists `scoring_context` in `required`; `db/migrations/0001_mvp_schema.sql:91` is `scoring_context jsonb not null`; `packages/shared/src/attempts.ts:5–20` has no such field. `tests/test_ts_schema_alignment.py` validates fixtures against the JSON schemas, not the TS interfaces, so it cannot see this. This is the §1-of-the-master-audit bug class in its TS-vs-schema form.

**D3-7 — The 15-item diagnostic mix has categories but no counts, anywhere.**
Spec 02 §8 fixes length (15) and names the mix categories ("Main Conclusion/Role, Flaw, Strengthen, Weaken, Necessary Assumption, Sufficient Assumption, MBT/MSS, Parallel/Parallel Flaw") but defers the composition to "the diagnostic mix defined by the content system," which does not exist. Spec 03 §10.1's `diagnostic_version` example is `AR_DIAG_V1_15_ITEM`; no artifact defines per-type counts summing to 15. The Phase 3 task packet's own `TODO(needs-decision)` records this; verified — nothing in the repo resolves it.

**D3-8 — `diagnostic_results_by_dimension.dimension_type` legitimately differs from the mastery dimension list.**
Spec 03 §10.2 declares `question_type, recipe, trap_family, trap_label, difficulty` (5, including `trap_label`). `mastery_states.dimension_type` is constrained to exclude `trap_label` (`0001_mvp_schema.sql:108–109`, per `TRAP_GRAIN_V1` §2.2). The diagnostic column (`0003_spec03_tables.sql:84`) is unconstrained. These are two same-named columns with two *correct but different* value lists — exactly the trap that produced master-audit B-1.

## 2. Rulings

1. **D3-1 — Adopt Spec 03 §9.1's three columns.** `sessions` gains `planned_item_count integer not null`, `actual_item_count integer`, `selection_policy text not null` in the later `0006` migration; `session_schema.json` gains the same fields when that migration lands. Until then Phase 3 may not start (it cannot record its own 15-item plan). Recorded in the backlog. **RESOLVED.**

2. **D3-2 — `timed_practice` stands; `free_practice` is rejected.** Three shipped repo artifacts agree on `timed_practice`; the content contract carries a paired `timed_eligible` flag (`packages/shared/src/content.ts`; `0001_mvp_schema.sql`, eligibility flags per `CONTENT_DDL_CONFORMANCE_V1` ruling 4); Spec 02 §6 defines no free-practice loop, and Spec 02 §7's "Timing preference" (untimed / relaxed timed / strict timed) motivates a timed mode, not a free one. Accepted deviation from Spec 03 §9.1. **RESOLVED.**

3. **D3-3 — The repo's three-state `session_status` stands.** In the MVP flow a session is created at the moment it starts, so Spec 03's `created` and `in_progress` collapse into `active`. Accepted deviation from Spec 03 §9.1; the 3-value list (`active, completed, abandoned`) is the authoritative list for the `0006` CHECK. If a deferred-start session ever ships, that is a contract revision, not a silent enum addition. **RESOLVED.**

4. **D3-4 — The sentinel is authoritative.** On a correct attempt, `selected_trap_label` and `selected_trap_family` are written as `'N/A_correct'`, per the three agreeing authorities (Spec 03 §9.3, Spec 04 §5/Appendix B, `TRAP_GRAIN_V1` ruling 4/5). Null is reserved for "not captured" anomalies only and must not be the normal correct-answer value. The JSON schema's null-ability is retained as tolerance, not as license; the Phase 3 packet's "trap if wrong" wording is superseded by this ruling. **RESOLVED.**

5. **D3-5 — `not_collected` stands; `api.ts` must be corrected at Phase 3 build.** `not_collected` subsumes Spec 03 §9.3's `skipped` for an MVP in which the confidence prompt may not be shown at all (accepted deviation; if an explicit skip UX ships later, adding `skipped` is a contract revision). `api.ts:22`'s `number` type is a defect: the field must become the `'low' | 'medium' | 'high' | 'not_collected'` union when Phase 3 code is written (recorded here; no code changes in this task). **RESOLVED**, with a build-time fix pinned.

6. **D3-6 — Schema and DDL are authoritative; the TS interface is incomplete.** `StudentAttempt` gains `scoring_context: Record<string, unknown>` at Phase 3 build time. Recorded in the backlog so the fix is not lost. **RESOLVED.**

7. **D3-7 — OPERATOR DECISION REQUIRED.** The per-type counts of the 15-item diagnostic (over Spec 02 §8's eight categories, against the bank's actual distribution — FL 32, ST 24, WK 24, NA 24, SA 16, MSS 16, MC 13, MBT 8, PA 8, PR 8, RC 7, RP 6, PF 6, MR 4, PI 3, EV 1 per `generated_items_all200.csv`) is a product decision no engineering rule can derive. It blocks Phase 3 item selection and therefore Phase 3 itself. Once decided, the mix must be recorded as a versioned artifact named by `diagnostic_version` (Spec 03 §10.1, e.g. `AR_DIAG_V1_15_ITEM`).

8. **D3-8 — Two dimension lists, both authoritative, constrained separately.** `diagnostic_results_by_dimension.dimension_type` = the 5-value list of Spec 03 §10.2 **including** `trap_label` (diagnostics may report on labels, `TRAP_GRAIN_V1` ruling 4). `mastery_states.dimension_type` and `mastery_events.dimension_type` = the 4-value list **excluding** it (`TRAP_GRAIN_V1` §2.2; see `PHASE_07_CONFORMANCE_V1` D7-2). Both lists go to the backlog with their columns explicitly paired so `0006` cannot conflate them. **RESOLVED.**

9. **Selection gate (no defect; pinned for the implementer).** Production diagnostic selection is `publication_state = 'published'` AND `content_state = 'validated'` AND `diagnostic_eligible = true` (`VISIBILITY_CONTRACT_V1`, `production_student` row; Spec 02 §8 Eligibility; Spec 03 §6.3). No staging table is ever read (`IMPORT_ARCHITECTURE_V1`).

## 3. Accepted deviations

| Authority | Says | Repo does / will do | Why |
|---|---|---|---|
| Spec 03 §9.1 | `session_type` includes `free_practice` | `timed_practice` | pairs with the shipped `timed_eligible` flag; Spec 02 §6 defines no free-practice loop |
| Spec 03 §9.1 | `session_status` = `created, in_progress, completed, abandoned` | `active, completed, abandoned` | MVP sessions are created at start; `created`/`in_progress` collapse |
| Spec 03 §9.3 | `confidence_self_report` includes `skipped` | `not_collected` | no explicit-skip UX in MVP; `not_collected` covers both |
| Phase 3 task packet | "trap if wrong" (null when correct) | `'N/A_correct'` sentinel when correct | Spec 03 §9.3 + Spec 04 §5/Appendix B + TRAP_GRAIN_V1 ruling 4 agree on the sentinel |

## 4. Conformance checks (for the Phase 3 implementer)

1. Create a diagnostic session; assert the `sessions` row records `planned_item_count = 15` and a non-empty `selection_policy` (requires `0006`).
2. Submit a correct answer; assert the attempt row carries `selected_trap_label = 'N/A_correct'` and `selected_trap_family = 'N/A_correct'`, not null.
3. Submit a wrong answer; assert `selected_trap_label`/`selected_trap_family` equal the selected choice's values from `content_explanations` (Spec 04 §20 test 1).
4. Assert every attempt insert supplies `scoring_context` (the DDL's `not null` enforces this; the TS interface must not make it unrepresentable).
5. Assert the selection query filters `publication_state = 'published' and content_state = 'validated' and diagnostic_eligible` and never touches `content_items_staging`.
6. Attempt to write `session_type = 'free_practice'`; after `0006`, the database must reject it.
7. Assert the served mix matches the operator-decided `AR_DIAG_V1_15_ITEM` artifact exactly (blocked on D3-7).
