# ADJUDICATION WORKSHEETS — A5 / A6 / A7 (blinded-review stage)

Governing: `docs/patches/TAXONOMY_SUPPLEMENT_RULINGS_V1.md` §§5–7,
`docs/patches/DIFFICULTY_EVIDENCE_RULINGS_V1.md` R2–R4.

These worksheets are completed by named humans. Automated solve records
(fresh model contexts) are supplementary evidence only; no item is accepted
on them alone. The AI drafter has not produced and may not produce any solve
record for these items.

**Evidence minimums before A7:** three blinded solve records each for items
1, 2, 5, 6, 7, 8, 9; five each for items 3 and 4. Each record: selected
answer, confidence, perceived difficulty, second choice, brief reasoning,
alternate-answer concern, completion time where available.

---

## Per-item worksheet (complete one per item)

- Item: `AR_TAX_000_`   Reviewer name: ________  Date: ________
- **A5 acceptance** (human accepts the draft as an item): ACCEPT / REVISE / REJECT
- **A6 content-quality review:**
  - Blinded solve records attached: ____ (count; meets minimum? Y/N)
  - Solver convergence on keyed answer: ____ / ____
  - Alternate-answer concerns raised (list, or "none"): ________
  - Single defensible credited answer confirmed (consult
    `answer_uniqueness_report_draft.json` analytic layer + empirical
    records): Y / N — if N: disposition is REVISE or REJECT, not label
    adjustment.
  - Explanation–letter alignment checked: Y / N
- **A7 difficulty adjudication** (named human):
  - Anchor comparison performed against the item's blueprint anchor set
    (below): Y / N
  - Adjudicated difficulty label: ____
  - For items 1, 2, 6, 7, 9 — explicit finding required (R3):
    "The item is NOT one level easier than the target." AFFIRMED / NOT AFFIRMED
    Rationale: ________
  - For items 3, 4 — explicit finding required (R4): the item is **d3 rather
    than d4** under the one-sided method. AFFIRMED / NOT AFFIRMED
    (first-principles analysis below must be adopted, amended, or replaced —
    record which.)
  - `difficulty_status` recorded:
    `prepublication_expert_calibrated` (items 1, 2, 5, 6, 7, 8, 9) /
    `prepublication_expert_calibrated_one_sided` (items 3, 4)
- **Disposition:** ACCEPT / REVISE / HOLD / REJECT — rationale: ________
  - On REVISE: the item receives a new draft version; **all prior solve
    records for that item are reset** and the evidence minimum re-accrues
    against the revision. Item 9: any substantive revision requires an A3
    verifier re-run (R2) before new solves.

---

## Anchor sets (from the approved blueprints)

| Item | Same-cell / upper anchors | Bracket / contrast anchors |
|---|---|---|
| 0001 (ST@4) | — (bracket, R3) | ST@3: B4_0007, B5_0007, B6_0007 · d4 cross-type: B1_0006, B2_0017, B6_0019 |
| 0002 (ST@4) | — (bracket, R3) | ST@3: B4_0007, B5_0007, B6_0007, B2_0001 · d4 cross-type: B1_0006, B2_0017, B6_0019 |
| 0003 (PA@3) | upper d4: B1_0017, B2_0017, B2_0018, B6_0019, B10_0017 | cross-type d3: B3_0003, B1_0003, B4_0010, B4_0007 |
| 0004 (PF@3) | upper d4: same five | cross-type d3: same four |
| 0005 (FL@2) | same-cell: B3_0002, B4_0004 | — |
| 0006 (WK@2) | — (bracket, R3) | d2 cross-type: B3_0002, B4_0004 · WK@3: B1_0003, B2_0003, B5_0010 |
| 0007 (WK@2) | — (bracket, R3) | d2 cross-type: B3_0002, B4_0004 · WK@3: B1_0004, B6_0009, B6_0010 |
| 0008 (NA@4) | same-cell: B1_0006 (see disclosure in packet §2) | NA@3 contrast: B4_0010, B7_0012, B8_0011 |
| 0009 (MSS@4) | — (bracket, R3) | MSS@3: B3_0009, B3_0010, B4_0016 · d4 cross-type: B1_0006, B1_0017, B10_0017 |

Held items and `legacy_harder_than_source_unverified` items may not be used
as anchors (rulings §7; R5).

---

## DRAFTED first-principles d3-vs-d4 analysis — Parallel family (items 3, 4)

*Drafted by the AI drafter as analytic support (R4 element 4). The named
adjudicator must ADOPT, AMEND, or REPLACE it; it has no force until then.*

What separates d4 from d3 in the clean Parallel-family anchors: the d4
exemplars layer three or more inferential links, or mix operator types
(quantifier + conditional, modality shifts), and typically present several
near-valid competitors whose differences are abstract rather than surface.
Items 3 and 4 each hold exactly one operator type (universal conditionals);
item 3 runs a two-link chain closed by a single contrapositive, item 4 a
single canonical conditional flaw; content is concrete; each is designed
with exactly two serious competitors and uniform topic distance across
choices.

Above d2: each demands form abstraction across five structurally parallel
choices with two live competitors — more load than the single-link,
one-survivor texture of the clean d2 anchors (B3_0002, B4_0004). Below d4:
no layering, no operator mixing, no abstract content. Drafted conclusion:
**d3, not d4** — one-sided support consistent with R4; the affirmative
finding belongs to the adjudicator.

Adjudicator action on this analysis (item 3): ADOPT / AMEND / REPLACE — signature ________
Adjudicator action on this analysis (item 4): ADOPT / AMEND / REPLACE — signature ________

---

## Disposition summary (complete when all worksheets are done)

| Item | A5 | Solves (n / min) | Convergence | A7 label | Finding | Disposition |
|---|---|---|---|---|---|---|
| 0001 | | /3 | | | not-one-easier: | |
| 0002 | | /3 | | | not-one-easier: | |
| 0003 | | /5 | | | d3-not-d4: | |
| 0004 | | /5 | | | d3-not-d4: | |
| 0005 | | /3 | | | — | |
| 0006 | | /3 | | | not-one-easier: | |
| 0007 | | /3 | | | not-one-easier: | |
| 0008 | | /3 | | | — | |
| 0009 | | /3 | | | not-one-easier: | |
