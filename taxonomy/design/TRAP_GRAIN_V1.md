# TRAP_GRAIN_V1

Status: **canonical, operator-approved.** Governing authority for the trap dimension across the data model, the adaptive engine, and the content loader. Cite this document rather than re-deriving the decision.

Resolves: the conflict between the factory's emitted trap vocabulary and the taxonomy/mastery grain assumed by Spec 03 §5 and Spec 04.

---

## 1. The conflict

The V1 content bank (`AR_V1_FULL200`, 200 items / 800 distractors) emits:

- **666 distinct `trap_label` values**, of which **575 occur exactly once**. These are *descriptive, per-item* labels (e.g. `wrong_benefit_shelf_space`, `rival_explanation_ease_when_wet`). They are deliberately specific — that specificity is what makes per-choice explanations good.
- **Exactly 20 distinct `trap_family` values**, well distributed:

```
Scope Failure 386 · Direction Failure 62 · Inference Failure 56 · Role Failure 48
Conclusion Failure 40 · Form Failure 36 · Conditional Failure 30 · Misdescription 24
Resolve Failure 24 · Structure Failure 22 · Parallel Failure 20 · Principle Failure 12
Relevance Failure 11 · Causal Failure 8 · Dispute Failure 8 · Analogy Failure 4
Method Failure 4 · Comparison Failure 3 · Evidence Failure 1 · Language Failure 1
```

`trap_taxonomy` (0003) had PK `trap_label` and required `student_name`, `definition`, `why_tempting`, `repair_prompt`, `default_review_interval_days` per row. Populating that faithfully means hand-authoring 666 pedagogy rows, 575 of which apply to exactly one distractor in the entire bank. That is infeasible and pedagogically meaningless.

The deeper problem is learning, not authoring: `mastery_states` keys on `(dimension_type, dimension_id)`. Keyed on 666 singleton labels, **a student never encounters the same trap twice and mastery cannot converge.** Keyed on 20 families, it converges.

## 2. Ruling

1. **`trap_family` is the taxonomy grain.** `trap_taxonomy` is re-grained to PK `trap_family` (20 rows). Pedagogy content (`student_name`, `definition`, `why_tempting`, `repair_prompt`, `default_review_interval_days`) is authored per family.
2. **`trap_family` is the mastery grain.** The trap dimension of `mastery_states` is `dimension_type = 'trap_family'`. `mastery_states.dimension_type` is constrained to `('question_type','recipe','trap_family','difficulty')`.
3. **`trap_label` remains free-text metadata.** It is stored per-choice on `content_explanations` (see `CONTENT_DDL_CONFORMANCE_V1.md`) as a descriptor used to render the explanation. It carries **no foreign key** to `trap_taxonomy` and is not a controlled vocabulary.
4. **Attempt logging is unchanged.** `attempts.selected_trap_label` and `attempts.selected_trap_family` are both retained and both populated, per Spec 04 §121–122. Diagnostics may report on labels; *mastery updates and review scheduling key on `trap_family` only.*
5. `N/A_correct` remains the sentinel value for both fields on the credited choice.

## 3. Deviations from spec (accepted, deliberate)

| Authority | Says | We do | Why |
|---|---|---|---|
| Spec 03 §5 | `trap_taxonomy` keyed on `trap_label` | keyed on `trap_family` | 666 labels, 575 singletons — not a controlled vocabulary |
| Spec 03 §9 | `dimension_type` enum includes `trap_label` | enum excludes `trap_label` | per-label mastery cannot converge; `trap_family` is already a legal enum member |
| Spec 04 §101 | `student_trap_mastery` carries `trap_label` + `trap_family` | mastery keyed on `trap_family`; `trap_label` retained on the attempt row | preserves label-level diagnostics without label-level mastery |

Spec 03 already lists `trap_family` as a legal `dimension_type`, so ruling (2) is a *narrowing*, not a contradiction.

## 4. Consequences for implementers

- Seed `trap_taxonomy` from the 20 families observed in the consolidated bank. **Derive the list from the data** (`data/runs/AR_V1_FULL200_.../consolidated/output/generated_items_all200.csv`), never from memory.
- Two families (`Evidence Failure`, `Language Failure`) appear once each in V1. Seed them; do not fold or drop them. Their thinness is a content-coverage observation, not a schema problem.
- The loader must not attempt to insert `trap_label` into `trap_taxonomy`, and must not fail an item because its `trap_label` is unknown.

## 5. Contract-layer alignment (added after the pre-handoff audit)

`packages/shared/src/TRAP_FAMILIES` originally declared **10** families — nine real plus the
`N/A_correct` sentinel — including `'Job Failure'`, which appears nowhere in the content bank. The bank
and the seed carry **20**. Twelve families were therefore absent from the TypeScript contract.

The constant was never referenced by any schema, test, or module, so nothing broke — but app code
written against it (Phase 4 trap feedback, Phase 6 missed-trap review) would have rejected the
explanations of roughly 60% of items.

Resolved:

- `TRAP_FAMILIES` now declares the 20 seeded families in descending bank frequency, plus `N/A_correct`.
- `'Job Failure'` is removed: unattested in the bank.
- A paired `TrapFamily` type is exported, matching the pattern of every other enum in the file.
- `N/A_correct` is the sentinel carried by the credited choice. It is **not** a `trap_taxonomy` row and
  must never be seeded as one.
- `tests/test_schema_loader_readiness.py` now guards this: `status.ts` must equal
  `data/seeds/trap_taxonomy.csv`, which must equal the families attested in the bank. Drift in any of
  the three fails the suite.

