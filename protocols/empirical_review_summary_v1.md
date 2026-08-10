# EMPIRICAL REVIEW SUMMARY v1 — blinded solve records, nine supplemental items

Source: `blinded_solve_records_v1.json` (operator-run artifact export, received
2026-07-16). 31 records, all `fresh_model_context` (claude-sonnet-4-6), zero
parse errors, minimums met (3× items 1,2,5–9; 5× items 3–4). Human records: 0.
Machine layer: `empirical_review_compilation_v1.json`.

## Results

| Item | Key | Convergence | Uniform 2nd | Watch-flag | Perceived d̄ (target) |
|---|---|---|---|---|---|
| 0001 | B | 3/3 | D | — · survivor mismatch (predicted A,C) | 2.67 (4) |
| 0002 | D | 3/3 | A | T2-A confirmed, resolved | 2.0 (4) |
| 0003 | C | 5/5 | B | matches design | 2.0 (3) |
| 0004 | E | 5/5 | A | T4-A confirmed, resolved for the right reason | 2.0 (3) |
| 0005 | A | 3/3 | C | survivor mismatch (predicted B) | 2.0 (2) |
| 0006 | D | 3/3 | A | matches | 2.0 (2) |
| 0007 | B | 3/3 | A | matches | 2.0 (2) |
| 0008 | E | 3/3 | A | T8-A confirmed, resolved | 2.0 (4) |
| 0009 | C | 3/3 | B | matches · formal proof stands | 2.0 (4) |

## What this evidence establishes

1. **Answer uniqueness: STRONG for all nine.** 31/31 selections landed on the
   keyed answer at high confidence. Every alternate-answer concern named the
   runner-up and subordinated it to the key for the designed reason. The
   three analytic watch-flags (T2-A, T4-A, T8-A) all fired and all resolved
   toward the key — the designed near-misses attract without displacing.
2. **Key correctness corroborated**, including T9's machine-verified core
   (solver reasoning reproduces the P1–P3 chain).

## What this evidence does NOT establish

1. **Target difficulty.** Model perceived-difficulty was non-discriminating:
   d2-target and d4-target items alike rated ~2 by a solver that answers
   everything correctly in 4–8 s. It carries approximately zero weight for
   A7. The R3 "not one level easier" findings and the R4 d3-not-d4 findings
   rest on anchor comparison and human judgment, not on these records.
2. **The d3+ two-survivor floor.** One model produced one uniform runner-up
   per item; that neither confirms nor refutes a second surviving
   distractor. UNVERIFIED for items 1, 2, 3, 4, 8, 9.

## Findings for the record (not defects)

- **T1**: empirically strongest distractor is D (Causal/timing), not the
  predicted A/C. — **T5**: empirically strongest is C (Structure), not the
  predicted magnet B (Misdescription). Keys and uniqueness unaffected;
  drafter survivor predictions corrected by data.

## Proposed dispositions (all nine): ACCEPT, conditional

Conditions per item: (a) A5 named-human acceptance; (b) A7 named-human
anchored adjudication with the required finding — R3 "not one level easier"
for 0001/0002/0006/0007/0009; R4 "d3 rather than d4" for 0003/0004 with the
drafted first-principles analysis adopted, amended, or replaced; (c) for the
d3+ items, **recommended**: one or two key-naive human solve records to give
A7 a discriminating difficulty signal and to test the two-survivor floor.
Any solver must be key-naive; records from anyone who has read the item
files' keys are not blind and must be labeled accordingly.

No REVISE / HOLD / REJECT candidates: nothing in the records indicates a
content defect. Worksheets: `adjudication_worksheets.md`.
