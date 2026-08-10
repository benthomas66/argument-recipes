# BLINDED_REVIEW_ADJUDICATION_V1 — operator adjudication record (controlling)

Status: **CONTROLLING.** Recorded by operator instruction, 2026-07-16 (UTC).
Extends `TAXONOMY_SUPPLEMENT_RULINGS_V1.md` and
`DIFFICULTY_EVIDENCE_RULINGS_V1.md`; where this record speaks for the
blinded-review stage, it governs.

**Authority note.** Memorializes the operator's adjudication of the nine
supplemental items (`AR_TAX_0001…0009`) on the evidence compiled at v45
(`empirical_review_compilation_v1.json`; 31 fresh-model-context solve
records, 0 human records). Per-item machine-readable records:
`data/supplemental_taxonomy/items/adjudication_records_v1.json`.

---

## AD-1. Waiver — key-naive human solve records (beta stage)

The recommended key-naive human solve records are **waived for this beta
stage** by operator ruling. The waiver covers additional human *solve*
evidence only; the named-human judgment requirements of D2/R3/R4 are
discharged by the operator's own adjudication recorded here.

## AD-2. Evidentiary scope of the v45 record set

The 31 model records are accepted as sufficient **for answer uniqueness
only** (31/31 keyed-answer convergence; all alternate-answer concerns
resolved toward the key; watch-flags T2-A, T4-A, T8-A fired and resolved).
They are accepted for nothing else.

## AD-3. Stage decisions

- **A5 — draft acceptance: ACCEPT, all nine items.** Responsible human:
  the operator (Ben), this ruling.
- **A6 — content-quality review: PASS, all nine items.** Basis: v45
  empirical uniqueness (AD-2) + structural floors (calibration self-report,
  v43) + T9 formal-core verification (PASS at v42 and v43).
- **A7 — difficulty adjudication:** the existing provisional labels are
  **retained on blueprint and anchor analysis**:
  - `AR_TAX_0001` d4, `0002` d4, `0005` d2, `0006` d2, `0007` d2, `0008` d4,
    `0009` d4 — `difficulty_status = prepublication_expert_calibrated`;
  - `AR_TAX_0003` d3, `0004` d3 —
    `difficulty_status = prepublication_expert_calibrated_one_sided`.

## AD-4. R4 finding — items 0003 / 0004

The drafted first-principles d3-versus-d4 analysis
(`adjudication_worksheets.md`) is **ADOPTED by the operator**. The R4
"d3 rather than d4" finding is thereby explicitly made for both items, under
the one-sided method (upper d4 anchors; no lower Parallel anchor exists).

## AD-5. R3 findings — items 0001, 0002, 0006, 0007, 0009 — NOT AFFIRMED

The R3 element "an explicit 'not one level easier' finding" is **not
affirmed at this stage**. No discriminating evidence supports it (AD-6), and
the operator has not made the affirmation. For this beta stage it is waived
by operator ruling and **folded into the empirical-confirmation obligation
(AD-6.3)**: the affirmative finding, or a label revision, is owed when
response data exists. Until then these five labels rest on blueprint design
and bracket-anchor analysis alone.

## AD-6. Recorded limitations (operator-directed; carried on every label)

1. **No key-naive human difficulty evidence was collected** for any of the
   nine items.
2. **The model solve data was non-discriminating for difficulty**
   (d2-targets and d4-targets rated alike by a solver at ceiling); it
   contributes no support to any d3/d4 label.
3. **All d3/d4 labels require empirical confirmation after beta usage.**
   The labels are prepublication expert calibrations and must not be
   described as psychometrically validated, measured, or empirically
   confirmed anywhere in product, docs, or code comments until response
   data exists and the confirmation is recorded.
4. The d3+ two-survivor floor remains UNVERIFIED (single-model uniform
   runner-up); it rides with the same empirical-confirmation obligation.

## AD-7. Dispositions

**ACCEPT — all nine items**, at state `human_accepted_prepublication`,
`publication_state = unpublished`. Remaining gates before any item can be
used or published, none satisfied and none authorized by this record:

- A8 — provenance recording at import (taxonomy rows carried into the
  system of record; reconciliation fold as `taxonomy_only`,
  `resolved_source_uid: null`, `uid_resolution: not_applicable_no_source`).
  The committed reconciliation ledger is **not modified** by this record.
- A9 — Spec 07 §9 human attestation (no `source_reference`; §6.6
  affirmation).
- A10 — publication remains refused: Spec 07 approval, publication
  authorization, and the beta-assembly gates are all outstanding.

## AD-8. What this record does NOT do

It does not publish, seed, validate-for-publication, attest, approve
Spec 07, modify any committed ledger, register enum values in code or DB,
or mark Phase 8 complete. It does not describe any difficulty label as
psychometrically validated.
