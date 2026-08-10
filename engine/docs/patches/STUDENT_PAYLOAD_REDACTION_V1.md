# STUDENT_PAYLOAD_REDACTION_V1 — what the API may serve a student, and when

**Status:** ruling, binding on every student-facing endpoint from Phase 3b-1
onward. Companion to `VISIBILITY_CONTRACT_V1` (which governs *which items* a
student may see; this governs *which fields of a visible item*).

## The defect this prevents

`packages/shared/src/api.ts` declared `PracticeItemPayload = { item:
ContentItem; choices }`. `ContentItem` carries `correct_answer` and
`correct_answer_job`. Serializing it to a browser puts the credited answer in
the network response **before the student answers** — readable by anyone with
devtools open, defeating the product's core measurement.

## Rulings

1. **The API never serializes `ContentItem` to a student.** The only
   pre-answer item shape is `StudentItemPayload` (`api.ts`):
   `canonical_id, content_version, position, question_type, stimulus,
   question_stem, choices[{letter, text}]`.
2. **Withheld before an answer is submitted:** `correct_answer`,
   `correct_answer_job`, `recipe_title` (it names the argument's move — a
   hint), `normalized_recipe_id`, `normalized_pattern_id`, `is_correct` on
   any choice, every explanation, every trap label and trap family.
3. **Reveal happens only inside the submit-answer response**, after the
   attempt row exists: `correct`, `correct_answer`, the selected choice's
   explanation, the credited answer's explanation. Trap labels/families and
   recipe identifiers remain withheld from students even post-answer in MVP
   (they surface through admin/analytics views, not the student wire format;
   relaxing this is a future product decision, not a default).
4. **Enforcement is layered and whitelist-shaped:**
   - the engine loader (`fetch_student_item`) selects only student-safe
     columns — forbidden fields never enter the row;
   - the API serializer (`student_item_payload`) is a strict whitelist
     **projection** — any key outside it, however it entered the row, never
     reaches the wire;
   - `tests/test_diagnostic_api.py` scans the **serialized JSON body** of
     every item-returning endpoint for the forbidden field names — asserting
     on the wire format, not the DTO type.
5. `PracticeItemPayload` is retained as a type alias of `StudentItemPayload`
   so the pre-existing `apps/web` contract stubs compile unchanged; the
   ContentItem-carrying shape is gone.

## Non-rulings

Admin and internal-QA surfaces may serve full `ContentItem` rows; they are
not student endpoints. Nothing here changes `VISIBILITY_CONTRACT_V1`.
