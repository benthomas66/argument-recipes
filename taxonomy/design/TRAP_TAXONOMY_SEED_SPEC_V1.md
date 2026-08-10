# TRAP_TAXONOMY_SEED_SPEC_V1

Authoring spec for seeding `trap_taxonomy`. This is **content/pedagogy authoring**, not engineering. The text authored here is what a student reads the moment they fall for a trap, so it must be written deliberately rather than generated as filler.

Governing authority: `docs/patches/TRAP_GRAIN_V1.md`.

---

## 1. Target table

```sql
create table if not exists trap_taxonomy (
  trap_family text primary key,
  student_name text not null,
  definition text not null,
  why_tempting text not null,
  repair_prompt text not null,
  default_review_interval_days integer not null
);
```

Exactly **20 rows**, one per `trap_family` present in the V1 bank. No more, no fewer.

`trap_label` is **not** in this table. It is free-text per-choice metadata on `content_explanations` with no foreign key. Do not attempt to enumerate the 666 labels.

## 2. Field semantics

| Field | What it is | Constraints |
|---|---|---|
| `trap_family` | The exact family string as it appears in the bank | Verbatim, case-sensitive, e.g. `Scope Failure` |
| `student_name` | The name a student sees. Plain English, no jargon. | 2–5 words. Not the raw family string. |
| `definition` | What the trap *is*, structurally. | 1–2 sentences. Describes the wrong answer's relationship to the argument, not the topic. |
| `why_tempting` | Why a competent solver seriously considers it. | 1–2 sentences. Must name the *specific pull* — half-right, right-answer-to-wrong-question, too-strong version of a real point, etc. If a family isn't tempting, the definition is wrong. |
| `repair_prompt` | The question a student asks themselves next time to avoid it. | One imperative sentence, second person, actionable at read time. |
| `default_review_interval_days` | Spaced-repetition base interval after a miss. | Integer 1–14. Shorter for high-frequency, structurally central families; longer for rare ones. Be internally consistent and state the scheme. |

## 3. The 20 families (from the V1 bank — verbatim strings)

| trap_family | distractors | distinct labels | dominant question types |
|---|--:|--:|---|
| Scope Failure | 386 | 340 | NA, ST, WK |
| Direction Failure | 62 | 54 | ST, WK, SA |
| Inference Failure | 56 | 38 | MSS, MBT |
| Role Failure | 48 | 46 | RC, MC, MR |
| Conclusion Failure | 40 | 26 | MC |
| Form Failure | 36 | 32 | PF, PA |
| Conditional Failure | 30 | 22 | SA, FL, NA |
| Misdescription | 24 | 22 | FL |
| Resolve Failure | 24 | 24 | RP |
| Structure Failure | 22 | 20 | FL |
| Parallel Failure | 20 | 20 | PA |
| Principle Failure | 12 | 12 | PR |
| Relevance Failure | 11 | 11 | FL |
| Causal Failure | 8 | 6 | FL, NA |
| Dispute Failure | 8 | 6 | PI |
| Analogy Failure | 4 | 4 | MSS |
| Method Failure | 4 | 4 | MR |
| Comparison Failure | 3 | 3 | WK, ST |
| Evidence Failure | 1 | 1 | MR |
| Language Failure | 1 | 1 | FL |

Derive this list from the data, not from this table — the table is a cross-check. Source of truth: `data/runs/AR_V1_FULL200_.../consolidated/output/generated_items_all200.csv`, columns `trap_family_a..e`, excluding `N/A_correct`.

## 4. Grounding requirement

Every `definition` and `why_tempting` must be written **from the actual distractors** carrying that family, not from the family's name. Use `trap_family_evidence_pack.json`, which provides per family: distractor count, distinct label count, dominant question types, up to 8 representative `trap_label`s, and up to 3 full examples (choice text + explanation).

Before writing a family's row, read its examples and state in one line what those distractors actually have in common. If the examples do **not** cohere, say so rather than papering over it.

## 5. Known issue to handle honestly

**Scope Failure is 48% of all distractors (386/800) across 340 distinct labels.** It is a catch-all. Its leading-token clusters do not separate (`irrelevant*` is the largest at 25 of 386), so there is no clean sub-structure to extract without hand-relabeling validated content.

For V1: **keep it as one family.** Write its definition to be genuinely teachable rather than a residual category — the honest core is roughly *"the choice concerns something the argument never commits to."* Do not silently split it.

Flag explicitly in the completion notes that mastery on `Scope Failure` will be diagnostically coarse: telling a student they are "weak at scope" carries little information when half of all wrong answers are scope. A future sub-family pass should be driven by real student-response data, not by hand-sorting labels.

`Evidence Failure` and `Language Failure` have exactly one distractor each. Seed them anyway. Do not fold or drop them. Note their thinness as a content-coverage observation.

## 6. Required outputs

1. `db/seeds/0001_trap_taxonomy_seed.sql` — idempotent seed:
   ```sql
   insert into trap_taxonomy (trap_family, student_name, definition, why_tempting, repair_prompt, default_review_interval_days)
   values (...)
   on conflict (trap_family) do update set
     student_name = excluded.student_name,
     definition = excluded.definition,
     why_tempting = excluded.why_tempting,
     repair_prompt = excluded.repair_prompt,
     default_review_interval_days = excluded.default_review_interval_days;
   ```
   Escape apostrophes correctly. Do not use `psql` meta-commands.
2. `data/seeds/trap_taxonomy.csv` — the same 20 rows, for human review and diffing. Header row, exact column names.
3. A short report: the interval scheme used; the one-line cohesion statement per family; any family whose examples did not cohere; the Scope Failure note.

## 7. Constraints

- Read-only on everything else. Add only the two seed files.
- Do not modify the 200 items, any migration, any validator, or any ledger.
- Do not invent trap families. Twenty, derived from the data.
- Do not write pedagogy that presumes a specific item — families are item-independent.
- Verify before asserting: the row count is 20; the family strings match the CSV byte-for-byte.
