# Diagnostic engine

Server-side Python that operates on the [question bank](../bank/) — no UI. It
selects diagnostic sessions, scores answers against the [taxonomy](../taxonomy/),
and estimates per-recipe and per-trap mastery.

~2,957 lines across 10 files.

## Layout

```
scripts/diagnostic/
  scoring.py            eight-component adaptive-scoring model (pure, no DB)
  adaptive_selection.py adaptive item selection over the scored pool
  selection.py          diagnostic selection under visibility constraints
  mix.py                session composition rules
  mastery_engine.py     per-recipe / per-trap mastery estimation (pure, no DB)
  daily_repair.py       builds the follow-up "repair" set
  framing.py            learner-facing framing of results
  run_diagnostic.py     CLI wiring (requires PostgreSQL — see below)
scripts/api/app.py      FastAPI wiring (requires PostgreSQL — see below)
schemas/                machine-readable constants and data contracts the code reads
docs/patches/           the design docs the scoring/mastery/selection logic implements
packages/               TypeScript mirror files, used by the cross-language contract tests
tests/                  core-logic tests (run without a database)
```

## Running the tests

The pure-logic core (scoring, mastery, selection, daily-repair) runs with no
database:

```bash
pip install jsonschema pandas openpyxl pytest
python -m pytest tests/      # 77 tests, all passing
```

## What is and isn't runnable here

- **Runnable:** the scoring / mastery / selection logic and its test suite.
- **Reference source only:** `run_diagnostic.py` and `scripts/api/app.py`. These
  read and write a PostgreSQL schema that is **not** included in this repository,
  so they will not run standalone from this repo. They are included to show how
  the core logic is wired into a CLI and an API.

Constants (scoring weights, mastery thresholds, review priorities) are never
hard-coded; they are loaded from `schemas/*.json`, and several tests assert the
Python logic and its TypeScript mirror stay in sync with those contracts.
