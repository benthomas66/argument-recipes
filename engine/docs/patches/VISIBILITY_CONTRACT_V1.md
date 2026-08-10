# VISIBILITY_CONTRACT_V1

Status: canonical, from Spec 03 §14.1. Defines the four app visibility modes and the content each exposes. This contract defines visibility; enforcement (the query/filter that applies it) is built in Phase 3 per the Phase 3 task packet, not here.

## Spec 03 §14.1 visibility modes (verbatim)

| Mode | Visible content states | Typical users |
|---|---|---|
| `production_student` | published only | Paid or public students. |
| `internal_beta` | published + validated | Internal beta testers, trusted reviewers. |
| `admin_qa` | published + validated + validated_candidate + holds | Operator, content QA, engineering. |
| `factory_import` | new imports before approval | Import process only. |

## Modeling note (read before using this contract)

In this repo's status model, `published` is a **publication_state**, NOT a `content_state`. The `content_state` enum is `blueprint`, `playable_draft`, `playable_draft_hold`, `validated_candidate`, `validated` (see `packages/shared/src/status.ts`). Therefore a visibility mode is **not** a pure `content_state` filter — it is a rule over the `(content_state, publication_state)` pair. There is no `published` content_state; do not invent one.

The §14.1 shorthand is encoded into explicit `(visible_publication_states, visible_content_states, includes_holds)` tuples as follows:

| Mode | visible_publication_states | visible_content_states | includes_holds |
|---|---|---|---|
| `production_student` | `["published"]` | `["validated"]` | `false` |
| `internal_beta` | `["published", "unpublished"]` | `["validated"]` | `false` |
| `admin_qa` | `["published", "unpublished", "retired", "superseded"]` | `["validated", "validated_candidate", "playable_draft_hold"]` | `true` |
| `factory_import` | `["unpublished"]` | `["validated_candidate", "playable_draft", "playable_draft_hold"]` | `false` |

- `production_student`: an item is student-visible only when it is `content_state` `validated` AND `publication_state` `published` — the intersection Spec 03 intends by "published only".
- `internal_beta`: sees `validated` content whether or not it is published ("published + validated").
- `admin_qa`: sees every publication state plus validated, validated_candidate, and hold content; the only mode with `includes_holds: true`.
- `factory_import`: sees pre-publication factory states only (new imports before approval).

## Machine-readable files

- Enum of mode names: `VISIBILITY_MODES` in `packages/shared/src/status.ts`.
- Rule-object schema: `schemas/visibility_mode_schema.json` (Draft 2020-12).
- The four-mode rule data: `docs/patches/visibility_mode_matrix.json`. This is plain **data** (a JSON array), not a JSON Schema, so it lives in `docs/patches/` rather than `schemas/` — the schema-validation gate treats every file under `schemas/` as a Draft 2020-12 schema and would reject an array. Each entry conforms to `schemas/visibility_mode_schema.json`.

## Scope

Contract only. No filtering, query, or enforcement code is defined here. The enforcement layer that applies these visible sets to content queries is built in Phase 3 per the Phase 3 task packet.
