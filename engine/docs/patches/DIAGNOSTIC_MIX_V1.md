# DIAGNOSTIC_MIX_V1 — decision memo + ruling artifact

Resolves **D3-7** (`PHASE_03_CONFORMANCE_V1`), which blocks Phase 3 entirely. Also resolves **D6-2** (review-stage storage), which blocks `0006`'s S-3.

Two decisions. Both are yours. My recommendation is below each, with the reasoning and the data. Edit the numbers if you disagree — but keep §3's structure, because the migration and Phase 3 build both read it.

---

## 1. The pool is smaller and cleaner than it looked

Spec 02 §8 names eight diagnostic categories: *Main Conclusion/Role, Flaw, Strengthen, Weaken, Necessary Assumption, Sufficient Assumption, MBT/MSS, Parallel/Parallel Flaw.*

Those eight **exclude** Principle / Resolve / Evaluate / Point-at-Issue — 18 items. So:

- The diagnostic pool is **182 items, not 200.**
- **`EV`'s single item is not in the pool at all.** The "one-item type" worry evaporates.
- All 182 in-pool items are `diagnostic_eligible = true`. There is no scarcity anywhere.

| Category | in pool | difficulty of eligible items |
|---|--:|---|
| Flaw | 32 | d2:2 · d3:17 · d4:12 · d5:1 |
| Strengthen | 24 | d2:4 · d3:13 · d4:7 |
| Weaken | 24 | d2:4 · d3:15 · d4:5 |
| Necessary Assumption | 24 | d3:15 · d4:8 · d5:1 |
| Sufficient Assumption | 16 | d3:11 · d4:5 |
| Main Conclusion/Role | 24 | d1:1 · d2:5 · d3:14 · d4:4 |
| MBT/MSS | 24 | d2:8 · d3:9 · d4:6 · d5:1 |
| Parallel/Parallel Flaw | 14 | d3:4 · d4:9 · d5:1 |

Two facts shape the mix: **Sufficient Assumption and Necessary Assumption have no d2 items**, and **Parallel is the hardest category** (9 of 14 at d4+).

---

## 2. Decision A — the 15-item mix

### The core tension

Fifteen items across eight categories means **at least one category gets a single item**, and a single item is a coin flip. You cannot estimate accuracy from one attempt. So be clear about what a diagnostic is *for*: Spec 02 §6 says its output is a "baseline weakness map and recommended repair plan" — a **directional signal**, not a mastery estimate.

There is an existing safeguard worth knowing: `MASTERY_CONTRACT_V1` requires `attempt_count >= 5` **and** `recent_accuracy >= 0.80` before any dimension reads as `mastered`. **A one-item category can never come out of the diagnostic looking mastered.** The contract already prevents the worst failure mode.

### Options

**Option A — proportional to the bank (recommended).** The bank's in-pool distribution already mirrors your §5 coverage targets, which were themselves set to real-LSAT frequency. So a proportional mix is *derived*, not invented:

```
Flaw 32/182 × 15 = 2.64 → 3      Sufficient Assumption 16/182 × 15 = 1.32 → 1
Strengthen 24/182 × 15 = 1.98 → 2      Main Conclusion/Role   = 1.98 → 2
Weaken                  = 1.98 → 2      MBT/MSS                = 1.98 → 2
Necessary Assumption    = 1.98 → 2      Parallel/Parallel Flaw = 1.15 → 1
```

**Option B — floor of 2 everywhere.** Needs 16 items. Requires changing Spec 02's fixed length of 15. Rejected: the length is specced, and 16 buys one noisy observation.

**Option C — drop Parallel, give SA 2.** `FL 3 · ST 2 · WK 2 · NA 2 · SA 2 · MC 2 · MBT 2 · PA 0`. Defensible — Parallel is the hardest category and a first-timer who misses both learns nothing. But you'd have **zero signal** on a distinct skill, and Parallel is where the trap-discipline story lives. Rejected, narrowly.

### Recommended: Option A, with an asymmetric reading rule

`SA` and `PA` carry one item each. Treat them **asymmetrically**: a miss flags the category for repair; a hit certifies nothing. This is honest about what one observation supports, and it costs nothing to implement — it's a `priority_rank` rule in `diagnostic_results_by_dimension`, not a schema change.

### Difficulty profile

The eligible pool skews d3 (98 of 182). Excluding d1 (1 item) and d5 (4 items, punishing on a first encounter), scale the remainder to 15: **3 × d2, 8 × d3, 4 × d4.**

Feasibility check — this instantiation exists in the bank:

| Category | count | difficulties |
|---|--:|---|
| Flaw | 3 | d2, d3, d4 |
| Strengthen | 2 | d3, d4 |
| Weaken | 2 | d2, d3 |
| Necessary Assumption | 2 | d3, d4 |
| Sufficient Assumption | 1 | d3 |
| Main Conclusion/Role | 2 | d2, d3 |
| MBT/MSS | 2 | d3, d4 |
| Parallel/Parallel Flaw | 1 | d3 |
| **total** | **15** | **d2 × 3 · d3 × 8 · d4 × 4** |

The three d2 items must come from Flaw / Strengthen / Weaken / MC / MBT — **NA, SA and Parallel have no d2 items.** Open on a d2 (Main Conclusion or MBT read well as a warmup); do not open on Parallel.

---

## 3. The ruling artifact — `AR_DIAG_V1_15_ITEM`

*(This is the versioned artifact Spec 03 §10.1 requires. On approval, land it at `docs/patches/DIAGNOSTIC_MIX_V1.md`.)*

```
diagnostic_version: AR_DIAG_V1_15_ITEM
length: 15
pool: diagnostic_eligible = true, question_type in the eight Spec 02 §8 categories (182 items)

mix:
  Flaw                      3    difficulties [2, 3, 4]
  Strengthen                2    difficulties [3, 4]
  Weaken                    2    difficulties [2, 3]
  Necessary Assumption      2    difficulties [3, 4]
  Sufficient Assumption     1    difficulties [3]
  Main Conclusion/Role      2    difficulties [2, 3]
  MBT/MSS                   2    difficulties [3, 4]
  Parallel/Parallel Flaw    1    difficulties [3]

ordering: first item must be difficulty 2. Parallel is never first.
excluded: difficulty 1 and difficulty 5; Principle/Resolve/Evaluate/Point-at-Issue.
selection: deterministic within (category, difficulty) cell over the eligible pool,
           seeded by user_id, logged to session_items.selection_reason = 'diagnostic_mix'.
reading rule: categories with a single item are asymmetric — a miss flags for repair;
           a hit certifies nothing. mastered is unreachable from a diagnostic anyway
           (MASTERY_CONTRACT_V1 requires attempt_count >= 5).
```

**Recipe coverage note, not a blocker:** 22 canonical recipes, 15 items — a diagnostic cannot cover recipes, only categories. `diagnostic_results_by_dimension` may still report a `recipe` dimension for the 15 recipes it happens to touch; do not present that as coverage.

---

## 4. Decision B — where the review stage lives (D6-2)

`MASTERY_CONTRACT_V1` sets review stages **1 → 3 → 7 → 21 days**. `learning_queues` stores `due_at` and `priority_score` and **has no stage column**. Phase 6 cannot advance a stage it does not store.

Deriving the stage from `due_at` fails: after a due date passes, the interval that produced it is unrecoverable, and a reset-to-1 is indistinguishable from a fresh stage-0 entry.

**Recommended:** add `learning_queues.review_stage integer not null default 0`, an index into `REVIEW_INTERVALS_DAYS = [1, 3, 7, 21]`. Correct answer advances (3 stays at 3); incorrect resets to 0. `due_at` becomes derived, not authoritative.

One column, no ambiguity, and it unblocks `0006`'s S-3.

---

## 5. Two decisions you can defer

- **D7-1a** (persist vs derive the learning plan) — blocks Phase 7 only. The audit recommends *derive for MVP*; I agree. A persisted plan buys explainability you have no UI for yet.
- **D7-5** (the eight scoring component functions) — blocks deterministic selection in Phase 7 only. Spec 04 §13's weight vector is authoritative; the component functions are genuinely undefined everywhere. That deserves its own task (`ADAPTIVE_SCORING_V1.md`), not a rushed answer inside a migration.

Neither blocks Phase 3, `0006`, or a student seeing a question.
