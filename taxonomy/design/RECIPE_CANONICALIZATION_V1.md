# RECIPE_CANONICALIZATION_V1

Status: **canonical, operator-approved.** Governing authority for how `normalized_recipe_id` in the content bank maps to `recipes.recipe_id` in the app tables. Cite this document rather than re-deriving.

---

## 1. The defect

The V1 factory wrote **descriptive labels where a controlled vocabulary was required** — the same failure mode as the 666 free-text trap labels, one layer up. Two consequences:

**D-1 — `recipe_title` is not a function of `recipe_id`.** 7 of 29 ids carry multiple titles; `WEAKEN_ATTACK_KEY_LINK` alone carries 15, `STRENGTHEN_SUPPORT_CAUSE` 13. The strings are per-item flavor text, not recipe names.

**D-2 — `recipe_id` contains synonym duplicates.** Seven pairs name the same reasoning job under two id strings, verified by comparing `correct_answer_job` and `recipe_tags` across their items. Left unmerged, `mastery_states` (which keys its recipe dimension on `recipe_id`) would split a single skill's mastery across two rows.

## 2. Rulings

1. **22 canonical recipes.** The 29 factory ids collapse to 22 via the merges in `data/seeds/recipe_id_canonical_map.csv`. `db/seeds/0002_recipes_seed.sql` seeds exactly those 22.
2. **One canonical `recipe_title` per recipe**, authored in the seed. Per-item title strings in the bank are not authoritative and are not imported.
3. **The 200 items are frozen.** `normalized_recipe_id` stays exactly as authored in `generated_items_all200.csv`. Canonicalization is *not* a content edit.
4. **The loader applies the map.** When landing rows into `content_items_staging`, the loader resolves `normalized_recipe_id` → `canonical_recipe_id` via `data/seeds/recipe_id_canonical_map.csv` and writes the canonical value. The map contains **all 29** factory ids (22 self-mapping, 7 merged); there are no chained or dangling targets. A factory id absent from the map is a **blocking error** — fail the import, do not pass the raw value through.
5. **`recipes` must be seeded before content import**, since `content_items.normalized_recipe_id` is expected to resolve to a seeded `recipe_id`. Seed order: `0001_trap_taxonomy_seed.sql`, then `0002_recipes_seed.sql`, then import.

## 3. The merges

| canonical | absorbs |
|---|---|
| `NA_REQUIRED` | `NECESSARY_ASSUMPTION_BRIDGE` |
| `SA_BRIDGE` | `SUFFICIENT_ASSUMPTION_CONDITIONAL_BRIDGE` |
| `MSS_SUPPORTED` | `MOST_STRONGLY_SUPPORTED` |
| `MBT_DEDUCE` | `MUST_BE_TRUE_CHAIN` |
| `MAIN_CONCLUSION` | `MAIN_CONCLUSION_ID` |
| `PARALLEL_REASONING_FORM` | `PARALLEL_REASONING` |
| `ROLE_IN_ARGUMENT` | `ROLE_OF_CITED_CLAIM` |

Post-merge item counts sum to 200 and match the seed exactly.

## 4. Accepted deviations

**`common_traps` may contain a single entry.** The authoring spec set a 2–5 floor. Four recipes attest exactly one `trap_family` across every distractor in the bank:

| recipe | distractors | families attested |
|---|--:|---|
| `RESOLVE_EXPLAIN` | 24 | Resolve Failure only |
| `PARALLEL_FLAW` | 24 | Form Failure only |
| `EVALUATE_KEY_UNCERTAINTY` | 4 | Scope Failure only |
| `PRINCIPLE_CONFORM` | 4 | Principle Failure only |

A second entry would assert a trap the bank contradicts. **One entry is correct; the floor is relaxed to 1.** Do not pad `common_traps` to satisfy a schema.

Root cause is content-side, not pedagogical: for RP and PF items the factory assigned `trap_family` largely *by question type*. `RESOLVE_EXPLAIN`'s 24 distractors carry 24 distinct sub-labels (`deepens_puzzle`, `partial_scope`, `bare_number`, `composition`, …) all flattened into `Resolve Failure`. The fix is a distractor re-labelling pass on RP/PF content, not a relaxed schema.

## 5. Known defects (NON-BLOCKING — record, do not fix mid-Phase-1)

- **`AR_V1_B6_0020` is mis-tagged.** It sits in `PRINCIPLE_JUSTIFY`, but its stem places the principle in the *stimulus* and arguments in the *choices* ("The principle stated above… justifies the reasoning in which one of the following arguments?"), and its `correct_answer_job` selects a **case**, not a principle. That is `PRINCIPLE_CONFORM`'s job. A content-side re-tag is warranted. `PRINCIPLE_JUSTIFY`'s seeded pedagogy is written to the dominant 4-of-5 direction.
  Note `normalized_pattern_id` does **not** reliably discriminate here: `AR_V1_B10_0019` also carries `PAT_APPLY_PRINCIPLE` while being a correct `PRINCIPLE_JUSTIFY` item. The stem and the credited answer's object are the reliable signals.
- **Five recipes have exactly one item** (`STRENGTHEN_RULE_OUT_RIVAL`, `EVALUATE_KEY_UNCERTAINTY`, `PRINCIPLE_ILLUSTRATE`, `PRINCIPLE_APPLY`, `PRINCIPLE_CONFORM`). Their pedagogy is generalized from a single example and carries more authorial inference. Re-read once the bank grows. `EVALUATE_KEY_UNCERTAINTY` is the only recipe covering question type `EV` — one item for an entire LR type.
- **`Language Failure` is referenced by no recipe's `common_traps`.** Its single distractor ranks 7th within `FLAW_DESCRIBE`, below the 5-entry cap. Expected, not a defect.
- **Every `question_types` array has exactly one element.** `PA` and `PF` are cleanly separate recipes; no recipe spans two LR types in V1.

## 6. Conformance checks

- `data/seeds/recipe_id_canonical_map.csv` covers all 29 factory ids; every target is one of the 22 seeded `recipe_id`s; no chained or dangling mappings.
- Every `common_traps` value matches a `trap_family` in `data/seeds/trap_taxonomy.csv` byte-for-byte.
- `mastery_threshold` ∈ [0.60, 0.90], assigned by a stated frequency × difficulty scheme.
