# Argument Recipes

Argument Recipes is a project about diagnosing *why* a test-taker misses
LSAT-style Logical Reasoning questions. On that test, each question gives a short
argument and asks you to do one specific logical task with it — for example, find
the flaw in the reasoning, or name what the argument must be assuming. The wrong
answers are written to be tempting in recognizable ways. This project tries to
organize those reasoning tasks and those tempting-wrong-answer patterns into
categories, build a set of practice questions labeled with those categories, and
write software that summarizes, from a user's recorded answers, which kinds of
questions they tend to get wrong.

It is a content-and-methodology project, not a product. There is no website or
app here — the software is command-line / API code that operates on a file of
questions. Parts of it were built with AI assistance, and I've tried to be exact
below about which parts, and about what has and has not actually been checked.

## The question

When someone misses Logical Reasoning questions, are they missing them for
patterned reasons — a particular kind of logical task, a particular kind of
tempting wrong answer — and can those errors be sorted into categories that are
useful enough for software to summarize where a person tends to struggle?

## What I built

Three things:

1. **A taxonomy** — two category schemes I developed for organizing reasoning
   tasks and wrong-answer patterns, with AI assistance in parts of the
   development and drafting process.
2. **A 200-item question bank** — LSAT-style questions, generated with AI
   assistance, each labeled with categories from the taxonomy.
3. **A Python diagnostic engine** — software that reads a user's recorded
   answers plus the taxonomy labels on each question, calculates a per-category
   summary of where they appear to be having more trouble, and selects further
   practice questions aimed at those categories.

The sections below explain each part and are careful to separate what I built,
and how much of it was AI-assisted, from what has actually been tested.

## Taxonomy

The taxonomy is two lists of categories I developed, with AI assistance in parts
of the development and drafting process. I decided how the space should be
organized and what each category is meant to capture; AI assistance was used in
proposing and refining categories and in drafting the explanatory prose in the
entries.

- **22 reasoning-pattern categories** ("recipes," in `taxonomy/recipes.csv`).
  Each names a kind of logical task a question can ask. For example, one category
  is *Describe the Flaw* (the question asks you to identify what is wrong with an
  argument's reasoning); another is *What the Argument Must Assume* (the question
  asks for an unstated premise the argument depends on). Each entry includes a
  plain-English description of the pattern, what to look for, and a common way
  people go wrong.

- **20 wrong-answer trap categories** ("trap families," in
  `taxonomy/trap_taxonomy.csv`). Each names a structural reason a wrong answer
  can be tempting. For example, *Outside the Argument* describes a choice that
  raises something the argument never actually relied on, and *Pushes the Wrong
  Way* describes a choice that is on-topic but works in the opposite direction
  from what the question asked. Each entry includes a definition and a note on
  why the trap tends to attract people.

The taxonomy exists so that errors can be grouped. If the questions a person
misses are labeled by reasoning pattern and by the kind of wrong answer they
picked, the software can report *what type* of question tends to give them
trouble, rather than just a raw score.

Nine additional worked-example items authored directly from the taxonomy live in
`taxonomy/supplemental/`; these are the items used in the small pilot described
later.

## Question bank

The bank is 200 LSAT-style items in `bank/argument_recipes_200_items.csv` (also
provided as `.xlsx`). I confirmed the count by counting the rows: 200.

Each item contains:

- a **stimulus** (the short argument or passage),
- a **question stem** (what task to perform),
- **five answer choices** (A–E),
- the **intended correct answer**,
- a short **explanation** for each choice, and
- **taxonomy labels** (its reasoning-pattern category, and a trap category for
  each wrong choice).

Three full items with walkthroughs are in [`SAMPLES.md`](SAMPLES.md) if you want
to see the shape of the content.

**How the bank was made, and what that means.** The items were generated with AI
assistance, working from the taxonomy and from a set of human-written blueprints.
Each item was written to have its own original wording and scenario, as an analog
of an item in a private source compilation (see the source disclosure at the
bottom).

Important limitations, stated plainly:

- The items have **not** had a full human quality review. I have not
  hand-checked all 200 for accuracy, clarity, or whether exactly one answer is
  defensible.
- Each item carries a **difficulty rating (1–5)**, but these are **design-time
  estimates**, not measurements. Nothing in this repository calibrates them
  against how hard the items actually are for real solvers. (For reference, the
  labels are distributed as 1 at level 1, 28 at level 2, 106 at level 3, 61 at
  level 4, and 4 at level 5.)
- Answer uniqueness — the property that exactly one choice is correct — has not
  been established for the bank. Checking it is the point of the evaluation
  procedure below, which has not yet been run on these items.

Full human review is still needed. That is the honest status.

## Diagnostic engine

In plain terms: the engine looks at the questions a user has answered, the
reasoning-pattern category attached to each question, and — for wrong answers —
the trap category of the choice they picked. From those recorded answers it
calculates a per-category summary of where the user appears to be doing better or
worse, and it selects additional practice questions aimed at the categories where
they appear to be struggling.

A few things about how to read those outputs:

- The summary is produced by **fixed rules**, not by a fitted statistical model.
  On a missed question the code lowers a running estimate for the relevant
  reasoning-pattern and trap categories by set amounts; on a correct question it
  raises the estimate for that question type. The internal code calls these
  running values "mastery," but that is just a variable name. They are
  bookkeeping estimates computed from the answers a person has recorded — **not**
  a measurement of anyone's underlying reasoning ability, and nothing here has
  checked whether they track such an ability.

- The trap labels describe the **structure of the wrong answer** the person
  chose. They should not be read as verified explanations of *why* that person
  chose it. Recording that a wrong answer belongs to a certain trap category is
  not the same as showing that the test-taker was psychologically caught by that
  trap; this project has no evidence of the latter.

- Because the estimates are not validated, the software deliberately never shows
  a user a raw score or the word "mastery." It maps the internal values to plain
  labels like "Focus area" or "Solid" for display. I mention this because it
  reflects the intended caution about what the numbers do and don't mean.

The engine is implemented in Python and runs against the item bank; there is no
user interface. Implementation specifics (the scoring components, the
session-assembly rules, the follow-up "repair" set) are in the **Technical
details** section near the end, so this explanation doesn't depend on them.

## How I planned to evaluate it

`protocols/` contains a **designed blinded review procedure** for checking item
quality. The idea is that solvers answer each item *without* seeing the intended
answer key, recording their choice, confidence, and perceived difficulty; then a
separate adjudication step compares how the solvers converged against the
intended answer and difficulty. The point of solving blind is to test whether an
item really has a single defensible answer and whether its difficulty estimate is
plausible.

What has actually happened so far is a **small pilot on the 9 supplemental
items** — not the 200-item bank. In that pilot the solver was an **AI model, not
a human** (the records are in `protocols/blinded_solve_records_v1.json`). The
pilot's own write-up (`protocols/empirical_review_summary_v1.md`) reports that
the results are consistent with a single defensible answer for those 9 items but
carry essentially no weight on difficulty, and it recommends human solvers as the
next step.

So: the procedure is designed and has been exercised once, on 9 items, by an AI
solver. There are **zero human solve records**, and the 200-item bank has not
been through the procedure at all.

## What has and has not been validated

Because the words matter here, this section is deliberately blunt.

**Established in this repository:**

- The taxonomy exists and is internally consistent enough for the software to use
  its labels.
- The 200-item bank exists, is schema-valid, and each item is fully labeled.
- The engine's core logic runs and behaves as its rules specify (there is a
  passing test suite; see below).

**Not established:**

- That the questions are individually correct, clear, and have a unique answer —
  no full human review has been done.
- That the difficulty ratings reflect actual difficulty — they are not
  calibrated against any solver data.
- That the blinded procedure "passes" the bank — it has not been run on the bank,
  and never with human solvers.
- That the engine's per-category estimates correspond to any stable underlying
  reasoning ability in a person. There is no evidence for this, and showing it
  would require a study well beyond what a question bank and a rule-based summary
  can provide on their own.

## Repository structure

```
taxonomy/     the two category schemes (recipes, trap families), the 9
              supplemental items, and the design notes behind them
bank/         the 200-item question bank (CSV + XLSX) and machine-generated
              validation / source-safety / near-duplicate / difficulty reports
engine/       the Python diagnostic engine and its tests
protocols/    the designed blinded review procedure and the small AI-solver pilot
SAMPLES.md    three full items with taxonomy-annotated walkthroughs
LICENSE       licensing for code vs. content (see below)
```

## Running the code

The core logic runs without a database:

```bash
cd engine
pip install jsonschema pandas openpyxl pytest
python -m pytest tests/        # 77 tests, all passing
```

The command-line and API wrappers (`engine/scripts/diagnostic/run_diagnostic.py`
and `engine/scripts/api/app.py`) additionally expect a PostgreSQL schema that is
**not** included here, so they are provided as reference source and do not run
standalone from this repository.

## Status and next steps

**Done:**

- taxonomy developed (22 reasoning-pattern categories, 20 trap categories)
- 200-item AI-assisted question bank generated and labeled
- diagnostic engine implemented
- core-logic test suite passing (77 tests)
- blinded review procedure designed
- small pilot completed on 9 supplemental items, using an AI solver

**Not yet done:**

- full human review of the 200-item bank
- human blinded solving of the 200 items
- difficulty calibration against solver data
- any evidence that the engine's per-category estimates track a stable underlying
  reasoning ability

The clear next step is to run the blinded review procedure with human, key-naive
solvers on the full bank, and to do a careful human quality review of the items.

## Technical details

For readers who want the implementation specifics behind the plain-English
description above:

- **`engine/scripts/diagnostic/scoring.py`** — the per-item score used to pick
  practice questions is a weighted sum of eight components (how well an item
  matches the target categories, how much the user seems to need that category,
  whether an item is due for review, difficulty fit, freshness, category
  coverage, surface variety, and label completeness). The weights and constants
  are loaded from a JSON file rather than hard-coded.
- **`mastery_engine.py`** — applies the fixed per-category update rules described
  above and produces the per-category summary. The rule set is versioned
  (`mvp_rule_v1`).
- **`adaptive_selection.py`, `selection.py`, `mix.py`** — assemble a session by
  selecting items under coverage and eligibility rules, deterministically.
- **`daily_repair.py`, `framing.py`** — build a short follow-up practice set and
  map the internal per-category values to the plain display labels.

The engine has a TypeScript mirror of some constants; tests check that the two
stay in agreement.

## AI-use disclosure

To be explicit in one place:

- I **developed the taxonomy's category schemes**, with **AI assistance in parts
  of the development and in drafting the entry prose**, which I directed and
  revised.
- The **200-item question bank was generated with AI assistance** from the
  taxonomy and human-written blueprints. It has **not** been fully human-reviewed.
- The **only evaluation run so far used an AI solver**, on **9 items**, not the
  full bank. There are **no human solve records**.
- I directed the development of the diagnostic engine and used AI assistance
  substantially during implementation, debugging, testing, and documentation.
  The engine uses the taxonomy and rule set described above; it should not be
  read as approximately 3,000 lines of code written independently without AI
  assistance.

## License and source disclosure

The code in `engine/` is released under the MIT License. The taxonomy, question
bank, and protocol documents (`taxonomy/`, `bank/`, `protocols/`) are released
under [Creative Commons Attribution-NonCommercial 4.0](https://creativecommons.org/licenses/by-nc/4.0/).
See [`LICENSE`](LICENSE).

**Source disclosure.** The items were written as original-wording analogs of
items in a private LSAT-style source compilation. That source material is **not**
included in this repository and is excluded by `.gitignore`; only original
generated text and abstract category labels are published here. No third-party
LSAT source text is reproduced in this repository.
