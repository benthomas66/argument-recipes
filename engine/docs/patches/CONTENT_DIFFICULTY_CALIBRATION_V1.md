# CONTENT_DIFFICULTY_CALIBRATION_V1

Status: canonical. Governs Argument Recipes content generation (the Batch-1 recalibration re-run and the full 200-item run). Suggested repo home: `docs/patches/`.

## Core principle

A generated item must reproduce the **structural difficulty of its source question**, not merely its difficulty *label* and *recipe type*. The Source Pattern Inventory (SPI) already records the source's structural properties per question; generation must honor them. The source questions are the difficulty benchmark — calibration is measured against the source, never against an arbitrary external target.

## What Batch 1 got wrong (measured, from this pilot's own artifacts)

The Batch-1 items tracked their sources' difficulty *labels* (mean gen−src delta = +0.15, i.e. neutral) but failed to reproduce two source properties the SPI explicitly recorded:

1. **Distractor profile.** Every one of the 101 SPI source rows carries `answer_choice_difficulty_profile = "one credited choice with attractive same-family distractors."` The generated items did not realize this: **~54% of the 80 distractors were eliminable-on-sight, and `background_detail` (irrelevant, cross-family filler) alone was 26% of all distractors.** Several items had 3–4 of 4 wrong answers eliminable at a glance. Filler distractors directly violate the source's own profile.
2. **Density / moving parts.** Most sources carry `moving_parts_count` 4–5 and `stimulus_length_band` medium; several 4-moving-part sources were compressed into 35–49-word analogs that dropped premises, qualifiers, or competing considerations.

Net effect: items that carry a difficulty-3/4 label but *play* like a 2 — thin stimulus, easy elimination. A bank built this way tops out around real-LSAT easy-medium and under-prepares students for genuine back-half items.

## Hard calibration requirements (per item)

For each generated item, read its source's SPI row and match, do not merely reference:

1. **Moving-parts parity.** The analog stimulus must contain the **same number of reasoning moving parts** as the source's `moving_parts_count` (premises, conditions, competing considerations, sub-claims). No compression below the source count.
2. **Density-band parity.** Match the source's `stimulus_length_band` and `reasoning_density`. Operational floor: a `medium` band source → analog stimulus **≥ ~60 words** with at least one embedded qualifier or competing consideration; a `short` band source may be tighter but must still carry every source moving part; `high` reasoning_density sources must carry a multi-step chain, not a single inference.
3. **Distractor-profile parity — highest leverage.** Realize `answer_choice_difficulty_profile` literally: **one credited choice with attractive, same-family distractors.** Concretely:
   - **≥3 of 4 distractors must be same-family attractive traps** — the kind a trained solver seriously weighs (half-right-then-wrong, right-answer-to-the-wrong-question, too-strong version of a real point, the tempting reversal/scope/causal error native to the recipe).
   - **≤1 distractor may be an eliminable-on-sight filler** (`background_detail`, `restates_premise`, `too_weak`). The sources use ~0 of these; treat 0 as the target and 1 as the ceiling.
   - Mirror the source's `trap_architecture` and `wrong_answer_trap_1..4` families rather than substituting weaker traps.
4. **Difficulty is earned by confusability, not asserted.** The item's `difficulty` must be validated by a blind solve: for any item labeled **d3+, at least 2 distractors must survive a first-pass read** (a competent solver would genuinely consider them). Inherit the source's `difficulty_estimate_1_to_5` as the floor — an analog may not play easier than its source.

## Post-generation calibration check (automated; reject/repair)

After authoring, compute per item and fail-and-repair any item that misses:
- `elim_distractor_count` (count of `background_detail` / `restates_premise` / `too_weak` traps) — **must be ≤1**.
- `same_family_attractive_count` — **must be ≥3**.
- `moving_parts_generated` vs source `moving_parts_count` — **must be ≥ source**.
- stimulus word count vs the source band floor — **must meet the floor**.
- blind-solve confusability for d3+ — **≥2 tempting distractors**.

Emit a `calibration_report.json` with these five metrics per item and a batch summary (mean elimination rate, % items meeting all five gates). A batch passes only when **100% of items meet all five gates.**

## Difficulty labeling rule

`difficulty` is set by the source-anchored blind-solve standard above, not by recipe type. Re-grade honestly: if an item plays easier than its source, either raise its density/distractors to match or relabel it down — do not ship a hollow label. Accurate labels matter downstream: `difficulty` feeds adaptive session selection and the mastery engine, so inflated labels corrupt item selection.

## Scope

This standard applies to (a) the Batch-1 recalibration re-run (same 20 blueprints, regenerated to this bar) and (b) every batch of the full 200-item run. It changes generation quality only; it does not alter schemas, status semantics, source-safety rules, or the validators. Items still ship `validated_candidate` / `unpublished` pending human validation.
