# RECIPES_SEED_SPEC_V1

Authoring spec for seeding `recipes`. This is **the teaching layer of the product** — the content that makes it "Argument Recipes" rather than a question bank. None of it exists anywhere in the content bank; it must be written.

Two canonicalization defects must be resolved as part of this task. They are not optional cleanup: `recipes` is keyed on `recipe_id`, and the current id/title space cannot key a table.

Governing authority: `docs/patches/CONTENT_DDL_CONFORMANCE_V1.md`, Spec 03 §7.4, Spec 04 (mastery).

---

## 1. Target table

```sql
create table if not exists recipes (
  recipe_id text primary key,
  recipe_title text not null,
  question_types jsonb not null,
  plain_english_pattern text not null,
  what_to_notice text not null,
  prediction_rule text not null,
  common_traps jsonb not null,
  repair_lesson text not null,
  mastery_threshold numeric not null
);
```

## 2. Two defects to resolve first

**D-1 — `recipe_title` is not a function of `recipe_id`.** 7 of 29 ids carry multiple titles. `WEAKEN_ATTACK_KEY_LINK` alone has **15** ("Weaken by Severing a Chain Link," "Weaken by the Severity Tradeoff," …). `STRENGTHEN_SUPPORT_CAUSE` has 13. The factory was writing *per-item descriptive labels*, not recipe names — the same failure mode as the 666 trap labels, one layer up.

**Ruling: canonicalize.** Choose exactly one `recipe_title` per canonical recipe. The per-item title strings remain in the content bank as flavor text and are not authoritative.

**D-2 — `recipe_id` contains synonym duplicates.** Seven pairs name the *same reasoning job* under two id strings. Verified by comparing `correct_answer_job` across items:

| keep | merge in | why |
|---|---|---|
| `NA_REQUIRED` | `NECESSARY_ASSUMPTION_BRIDGE` | both: state what must hold for the support to work |
| `SA_BRIDGE` | `SUFFICIENT_ASSUMPTION_CONDITIONAL_BRIDGE` | both: supply the conditional that closes the gap |
| `MSS_SUPPORTED` | `MOST_STRONGLY_SUPPORTED` | both: draw the best-supported inference |
| `MBT_DEDUCE` | `MUST_BE_TRUE_CHAIN` | both: combine given facts to force a claim |
| `MAIN_CONCLUSION` | `MAIN_CONCLUSION_ID` | both: identify the claim the others support |
| `PARALLEL_REASONING_FORM` | `PARALLEL_REASONING` | both: match the abstract logical form |
| `ROLE_IN_ARGUMENT` | `ROLE_OF_CITED_CLAIM` | both: locate a claim's function in the argument |

**Ruling: merge. 29 → 22 canonical recipes.** This matters beyond tidiness: `mastery_states` keys the recipe dimension on `recipe_id`, so duplicate ids split a student's mastery signal across two rows for one skill.

Verify each merge yourself against `correct_answer_job` and `recipe_tags` in the evidence pack before accepting it. If a pair does **not** collapse on inspection, keep it separate and say why.

**Ruling: do not edit the 200 items.** The content bank is validated and frozen. Canonicalization is expressed as a **mapping file**, and the Phase 1 loader applies it when landing rows into staging. `normalized_recipe_id` in the CSV stays as authored.

## 3. The 22 canonical recipes (post-merge item counts)

```
FLAW_DESCRIBE 32 · NA_REQUIRED 24 · WEAKEN_ATTACK_KEY_LINK 21 · STRENGTHEN_SUPPORT_CAUSE 20
SA_BRIDGE 16 · MSS_SUPPORTED 16 · MAIN_CONCLUSION 13 · MBT_DEDUCE 8 · PARALLEL_REASONING_FORM 8
ROLE_IN_ARGUMENT 7 · RESOLVE_EXPLAIN 6 · PARALLEL_FLAW 6 · PRINCIPLE_JUSTIFY 5 · METHOD_OF_REASONING 4
STRENGTHEN_CLOSE_SUPPORT_GAP 3 · WEAKEN_ALTERNATIVE_CAUSE 3 · POINT_AT_ISSUE 3
STRENGTHEN_RULE_OUT_RIVAL 1 · EVALUATE_KEY_UNCERTAINTY 1 · PRINCIPLE_ILLUSTRATE 1
PRINCIPLE_APPLY 1 · PRINCIPLE_CONFORM 1
```

Derive this from the data, not from this list — the list is a cross-check.

**Five recipes have exactly one item** (`STRENGTHEN_RULE_OUT_RIVAL`, `EVALUATE_KEY_UNCERTAINTY`, `PRINCIPLE_ILLUSTRATE`, `PRINCIPLE_APPLY`, `PRINCIPLE_CONFORM`). Seed them; do not fold or drop them. Their pedagogy is generalized from a single example and carries more authorial inference — flag them, and note that the four `PRINCIPLE_*` recipes may be over-split (consider whether `PRINCIPLE_APPLY` / `PRINCIPLE_CONFORM` / `PRINCIPLE_ILLUSTRATE` are one recipe with three surface forms, and say so — but **do not merge them without evidence**, and if you do, justify from `correct_answer_job`).

## 4. Field semantics

| Field | What it is | Constraints |
|---|---|---|
| `recipe_id` | Canonical id | From the 22. Exact string, uppercase snake. |
| `recipe_title` | The one canonical name a student sees | 2–6 words. Plain English. Not a per-item label. |
| `question_types` | JSON array of LR types this recipe covers | e.g. `["NA"]`, `["PA","PF"]`. Derive from the bank. |
| `plain_english_pattern` | What the argument *does*, in the student's language | 1–2 sentences. Describes the argument's structure, not the question task. |
| `what_to_notice` | The read-time cue that this recipe is in play | 1–2 sentences. Concrete and spottable *before* looking at the choices. |
| `prediction_rule` | The prediction to form before reading the choices | One imperative sentence. This is the heart of the method — it must produce an actual prediction, not "consider the gap." |
| `common_traps` | JSON array of the `trap_family` strings that most often appear as distractors for this recipe | 2–5 entries, drawn from the evidence pack's `top_trap_families`. Must use the exact 20 family strings — they FK-match `trap_taxonomy`. |
| `repair_lesson` | What to re-learn after missing this recipe | 2–3 sentences. Diagnostic: names the likely misread, then the fix. |
| `mastery_threshold` | Accuracy required to count as mastered | Numeric 0.60–0.90. Pick a scheme (e.g. higher for foundational/high-frequency recipes, lower for rare/hard ones), apply it consistently, and state it. |

## 5. Grounding requirement

Every field must be written **from the items**, not from the recipe's name. The bank supplies unusually good raw material — use it:

| Bank field | Populated | Grounds |
|---|--:|---|
| `correct_answer_job` | 200/200 | `prediction_rule`, `plain_english_pattern` |
| `prediction_text` | 200/200 | `prediction_rule` |
| `conclusion` | 197/200 | `what_to_notice` |
| `support` | 180/200 | `what_to_notice` |
| `gap` | 174/200 | `plain_english_pattern`, `repair_lesson` |
| `recipe_tags` | 200/200 | recipe identity, merge checks |
| `inference_or_resolution` | 15/200 | MBT/MSS/RP recipes only |

`recipe_evidence_pack.json` provides, per recipe: item count, question types, difficulty spread, pattern ids, all titles with counts, top trap families, five sample `correct_answer_job` strings, and three full examples (stem, conclusion, support, gap, prediction, job, tags).

Before writing a recipe's row, read its examples and state in one line what those items actually have in common. If they do not cohere, say so rather than papering over it.

## 6. Required outputs

1. `db/seeds/0002_recipes_seed.sql` — 22 rows, idempotent:
   ```sql
   insert into recipes (recipe_id, recipe_title, question_types, plain_english_pattern,
                        what_to_notice, prediction_rule, common_traps, repair_lesson, mastery_threshold)
   values (...)
   on conflict (recipe_id) do update set
     recipe_title = excluded.recipe_title, question_types = excluded.question_types,
     plain_english_pattern = excluded.plain_english_pattern, what_to_notice = excluded.what_to_notice,
     prediction_rule = excluded.prediction_rule, common_traps = excluded.common_traps,
     repair_lesson = excluded.repair_lesson, mastery_threshold = excluded.mastery_threshold;
   ```
   `question_types` and `common_traps` cast to `jsonb` (e.g. `'["NA"]'::jsonb`). Escape apostrophes by doubling. No `psql` meta-commands.
2. `data/seeds/recipes.csv` — the same 22 rows for human review. Header row, exact column names; JSON columns as compact JSON strings.
3. `data/seeds/recipe_id_canonical_map.csv` — columns `factory_recipe_id,canonical_recipe_id`. **All 29** factory ids appear, including the 22 that map to themselves. This is what the loader applies.
4. A short report: the mastery-threshold scheme; the one-line cohesion statement per recipe; the canonical title chosen for each multi-title id and what was discarded; any pair that did **not** collapse on inspection; the five single-item recipes; your read on whether the four `PRINCIPLE_*` recipes are over-split.

## 7. Constraints

- Add only the three seed files. Read-only on everything else.
- **Do not modify the 200 items, any migration, any validator, or any ledger.**
- `common_traps` must use the exact 20 `trap_family` strings from `trap_taxonomy` (see `data/seeds/trap_taxonomy.csv`). Any other string is a defect.
- Do not invent recipes. Twenty-two, derived from the data via the documented merge.
- Pedagogy must be item-independent — never presume a specific question.
- Verify before asserting: row count is 22; the map covers all 29 factory ids; every `common_traps` entry matches a seeded family.
