# Question bank

**200 items**, generated against the [taxonomy](../taxonomy/) with AI assistance.

## Files

- **`argument_recipes_200_items.csv`** / **`.xlsx`** — the full bank. 200 rows,
  one per item.
- **`reports/`** — machine-generated reports produced during generation:
  - `consolidated_validation.json`, `generated_items_all200_ValidationReport.json`
    — schema/consistency validation.
  - `generated_items_all200_SourceSafety.json` — the source-safety / leakage scan.
  - `near_copy_all200.json` — near-duplicate check across items.
  - `calibration_summary.json` — the design-time difficulty calibration summary.

## What each item contains

Original scenario and stimulus, a question stem, five answer choices, the keyed
answer, a per-choice explanation, and per-choice trap tags that map back to the
trap taxonomy. Items also carry recipe/pattern ids linking them to the taxonomy.

## Honest limits

- Items are **AI-assisted generated** and have **not** been human-reviewed for
  quality, accuracy, or difficulty.
- The `difficulty` field (1–5) is a **design-time estimate**, not an empirical
  calibration.
- Items were authored as original-surface **analogs** of items in a private
  source compilation. That source material is **not** in this repo; only original
  generated text and abstract metadata are published. No LSAT source text is
  reproduced.

Empirical checking of these items is the job of the [verification
protocol](../protocols/), which has not yet been run on this bank.
