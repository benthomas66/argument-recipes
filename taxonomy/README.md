# Taxonomy

The human-designed core of the project: the argument patterns and answer-choice
traps that everything else is built and scored against.

## Files

- **`recipes.csv`** — 22 argument "recipes," one per Logical Reasoning reasoning
  pattern. Columns: recipe id, title, question types, plain-English pattern, what
  to notice, prediction rule, common traps, repair lesson, mastery threshold.
- **`trap_taxonomy.csv`** — 20 "trap families," one per wrong-answer failure
  mode. Columns: trap family, student-facing name, definition, why it tempts,
  repair prompt, default review interval.
- **`recipe_id_canonical_map.csv`** — maps recipe identifiers to their canonical
  ids.
- **`supplemental/`** — 9 worked-example items (`items/`) authored directly from
  the taxonomy, each with its blueprint (`blueprints/`).
- **`design/`** — the design notes behind the seeds: how recipes and traps were
  specified, how trap grain was decided, and how recipe ids were canonicalized.

The schemes' design is the author's; entry prose was drafted with AI assistance
and revised against the design. This taxonomy is the reference that the question
bank is generated against and that the diagnostic engine scores toward.
