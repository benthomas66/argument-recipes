# Verification protocol

A **designed** protocol for checking that each item has a single defensible
answer and a defensible difficulty — by having solvers work the items *blind* to
the answer key, then adjudicating their convergence against the intended key.

> **Status: designed, and piloted once — not yet run on the 200-item bank, and
> not yet run with human solvers.**

## Files

- **`solver_packet_blinded.md`** — the blinded packet given to a solver: answer,
  confidence, perceived difficulty, second choice, and reasoning for each item,
  with no access to the key.
- **`blinded_solver_runner.jsx`** — the runner used to collect solve records.
- **`blinded_solve_records_v1.json`** — the proof-of-concept run: **31 records**
  in which an **AI model** (not a human) solved the **9 supplemental** taxonomy
  items. There are **zero human solve records**.
- **`empirical_review_summary_v1.md`** / **`empirical_review_compilation_v1.json`**
  — the analysis of that pilot. It supports answer-uniqueness for those 9 items,
  states that the model signal carries essentially no weight on difficulty, and
  recommends key-naive **human** solvers as the next step.
- **`adjudication_worksheets.md`**, **`adjudication_records_v1.json`**,
  **`answer_uniqueness_report_draft.json`** — the adjudication method and its
  working records.
- **`BLINDED_REVIEW_ADJUDICATION_V1.md`** — the adjudication design document.

## What this establishes, and what it does not

The pilot exercises the protocol end-to-end on a small sample and corroborates
answer uniqueness for the 9 supplemental items. It does **not** validate the
200-item bank, does **not** establish difficulty, and involves **no** human
review. Running the protocol with human, key-naive solvers on the full bank is
the project's next phase.
