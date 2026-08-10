# DIFFICULTY_EVIDENCE_RULINGS_V1 — controlling rulings (operator-recorded)

Status: **CONTROLLING.** Recorded by operator instruction at v42 → v43.
Extends `docs/patches/TAXONOMY_SUPPLEMENT_RULINGS_V1.md` (which remains in
force); where this record speaks, it governs.

**Authority note.** Memorializes operator rulings issued in the governor
conversation upon acceptance of v42. Binding on blueprint ratification,
difficulty evidence, the legacy-label quarantine, and the authoring
continuation.

---

## R1. v42 canonical; A1 approvals

v42 is accepted as canonical. **A1 is approved** for the seven drafted
blueprints: `AR_TAX_BP_0001`, `0002`, `0005`, `0006`, `0007`, `0008`, `0009`.

## R2. T9 formal core

The T9 formal core is **accepted** as verified at v42. It **must be re-run
after final predicate/prose instantiation** — a passing
`scripts/content/verify_mss_formal_core.py` transcript against the final
predicate assignment, plus a recorded 1:1 mapping from the prose's quantified
statements to P1–P3 / C / D1–D4, are conditions of T9's content-quality
review (A6).

## R3. Two-axis bracket method — RATIFIED for T1, T2, T6, T7, T9

The bracket method proposed at v42 is ratified with these elements, all
required:

1. Clean same-type anchors one difficulty level away (per the v42 census
   criterion of "clean");
2. Clean cross-type anchors at the target level;
3. Minimum **three** blinded solve records;
4. Named human adjudication (Spec 07 §10.2 qualification);
5. An explicit **"not one level easier"** finding recorded by the
   adjudicator — the judgment must affirmatively rule out the adjacent lower
   difficulty, not merely assert the target;
6. Later empirical confirmation or revision once response data exists.

`difficulty_status = prepublication_expert_calibrated` for these five items.

## R4. T3 / T4 — UNBLOCKED via strengthened one-sided bracket

Parallel / Parallel-Flaw @ d3 **stays in the diagnostic mix**. The v42 halt
on `AR_TAX_0003` / `AR_TAX_0004` is lifted under this method, all elements
required:

1. Held `AR_V1_B5_0019` is **not used** in any anchoring role;
2. Upper anchors: clean PA/PF @ d4 (`AR_V1_B1_0017`, `AR_V1_B2_0017`,
   `AR_V1_B2_0018`, `AR_V1_B6_0019`, `AR_V1_B10_0017`);
3. Clean cross-type d3 anchors;
4. A recorded **first-principles d3-versus-d4 analysis** for the
   Parallel family (what structurally separates the levels, applied to the
   item);
5. Minimum **five** blinded solve records;
6. Named human adjudication;
7. Recorded status: `difficulty_status =
   prepublication_expert_calibrated_one_sided`;
8. Later empirical confirmation or revision.

`AR_TAX_BP_0003` and `AR_TAX_BP_0004` are created under this method.

## R5. The 25 legacy over-labeled items — quarantined, not held

The 25 items labeled above their keyed-source difficulty (v42 packet Annex B)
are **not** placed on B4 hold automatically. Ruling:

1. Each is marked **`legacy_harder_than_source_unverified`**.
2. Until retrospective calibration, they are **excluded from**: anchor use,
   diagnostic-mix cell counts, beta-pool feasibility, and any other
   difficulty-sensitive use.
3. Each is confirmed or corrected through **blinded, anchored human
   review**; the present label is **not assumed valid**.
4. Student visibility is unchanged by this ruling (none is published; none
   becomes publishable by it).

The 25 (type, label, keyed source): AR_V1_B4_0009 (WK 3/2), AR_V1_B4_0015
(MC 3/2), AR_V1_B4_0017 (MBT 3/2), AR_V1_B5_0002 (FL 3/2), AR_V1_B5_0003
(FL 4/3), AR_V1_B5_0004 (FL 4/3), AR_V1_B5_0008 (WK 4/3), AR_V1_B5_0011
(NA 3/2), AR_V1_B5_0017 (MSS 3/2), AR_V1_B5_0018 (MBT 4/3), AR_V1_B6_0002
(FL 4/3), AR_V1_B6_0003 (FL 4/3), AR_V1_B6_0004 (FL 4/3), AR_V1_B7_0009
(WK 3/2), AR_V1_B7_0020 (RP 4/3), AR_V1_B8_0005 (ST 3/2), AR_V1_B8_0009
(WK 4/3), AR_V1_B8_0012 (NA 3/2), AR_V1_B9_0010 (NA 4/3), AR_V1_B9_0015
(MC 4/2), AR_V1_B9_0016 (MSS 3/2), AR_V1_B9_0017 (MBT 5/3), AR_V1_B10_0015
(MSS 4/3), AR_V1_B10_0016 (MBT 3/2), AR_V1_B10_0019 (PR 4/3).

**Consequences applied at v43:** the marker and exclusions are recorded in
`data/supplemental_taxonomy/anchor_census.json`.
**Deliberately not done:** `data/provenance/beta_pool_feasibility.json` is
not regenerated — it is a byte-reproducible Workstream-A artifact; the
quarantine applies at consumption, and any recomputation is a separate
operator instruction. Note the already-recorded verdict (INSUFFICIENT) only
worsens under exclusion.

**T8 anchor note.** `AR_V1_B9_0010` (NA 4/3) is quarantined; `AR_TAX_BP_0008`
already anchors on `AR_V1_B1_0006` alone, which is unaffected.

## R6. Taxonomy-only blueprint schema — mandated before prose

Before prose authoring: add and validate a dedicated taxonomy-only blueprint
JSON Schema. Constraints: it must **not** include a fabricated
`source_question_number` (Spec 07 §6.6), and
`schemas/normalized_blueprints_schema.json` (source-derived) is **not
weakened or modified**. Implemented at v43 as
`schemas/taxonomy_blueprint_schema.json` +
`tests/test_taxonomy_blueprint_schema.py` (validates every
`data/supplemental_taxonomy/AR_TAX_BP_*.json` on every pytest run).

**Enum-registration note.** `difficulty_status` values
(`prepublication_expert_calibrated`,
`prepublication_expert_calibrated_one_sided`) and the quarantine marker exist
in supplement artifacts only. No code/DB enum is touched (standing
prohibition); registration happens at the import phase as its own
operator-authorized change.

## R7. Run-SPI difficulty field — non-authoritative (ruled)

The v42 evidentiary finding is ratified as a ruling: the
`difficulty_estimate_1_to_5` column of
`intermediate/source_pattern_inventory_B*.json` and
`consolidated/reports/source_pattern_inventory_all200.json` is
**non-authoritative** for source difficulty and must not be consumed for it.
Authoritative chain: `resolved_source_uid`
(`data/provenance/source_mapping_reconciliation.json`) → `uid` →
`difficulty` in `intermediate/source_inventory_keyed.json`.

## R8. Handoff correction

The next governor handoff corrects the trap-family shorthand to the seeded
canonical strings — in particular **`Misdescription`** (there is no
"Principle Doesn't Apply" family). Canon: `db/seeds/0001_trap_taxonomy_seed.sql`.

## R9. Continuation authorization and standing prohibitions

After the R3–R6 deliverables pass validation, work proceeds to **final prose
authoring and blind-solve review** under
`TAXONOMY_SUPPLEMENT_RULINGS_V1` §§3–8 (source isolation, AI disclosure,
human acceptance, D2/D3 evidence). Blinded solve records may include
automated solver records only as **supplementary** evidence, clearly labeled
(D2: automated solvers are not sufficient); human acceptance (A5) and named
human adjudication (A7) remain with the operator.

It remains prohibited to: approve Spec 07, publish, seed, or mark Phase 8
complete. All v41/v42 standing prohibitions continue.

## What this record does NOT do

- It does not hold, relabel, or publish any item.
- It does not regenerate provenance or feasibility ledgers.
- It does not register new enum values in code or DB.
- It does not approve Spec 07 or advance Phase 8.
