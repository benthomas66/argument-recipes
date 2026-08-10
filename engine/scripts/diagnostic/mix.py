"""AR_DIAG_V1_15_ITEM — the diagnostic mix, as code.

Authority: docs/patches/DIAGNOSTIC_MIX_V1.md §3 (operator-approved, resolves
PHASE_03_CONFORMANCE_V1 D3-7). The constants below transcribe that artifact;
parse_mix_artifact() re-reads the doc's §3 block so tests can assert the two
never drift (the declared-vs-enforced guard pattern, applied to a document).
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MIX_DOC = ROOT / 'docs' / 'patches' / 'DIAGNOSTIC_MIX_V1.md'

DIAGNOSTIC_VERSION = 'AR_DIAG_V1_15_ITEM'
DIAGNOSTIC_LENGTH = 15
SELECTION_REASON = 'diagnostic_mix'

# The eight Spec 02 §8 categories and the question_type codes they cover.
# PR / PI / RP / EV (Principle, Point-at-Issue, Resolve, Evaluate — 18 items)
# are outside the diagnostic pool by design (DIAGNOSTIC_MIX_V1 §1).
CATEGORY_QUESTION_TYPES: dict[str, tuple[str, ...]] = {
    'Flaw': ('FL',),
    'Strengthen': ('ST',),
    'Weaken': ('WK',),
    'Necessary Assumption': ('NA',),
    'Sufficient Assumption': ('SA',),
    'Main Conclusion/Role': ('MC', 'MR', 'RC'),
    'MBT/MSS': ('MBT', 'MSS'),
    'Parallel/Parallel Flaw': ('PA', 'PF'),
}

EXCLUDED_QUESTION_TYPES = ('PR', 'PI', 'RP', 'EV')

# category -> per-item difficulties (one selected item per listed difficulty).
MIX: dict[str, tuple[int, ...]] = {
    'Flaw': (2, 3, 4),
    'Strengthen': (3, 4),
    'Weaken': (2, 3),
    'Necessary Assumption': (3, 4),
    'Sufficient Assumption': (3,),
    'Main Conclusion/Role': (2, 3),
    'MBT/MSS': (3, 4),
    'Parallel/Parallel Flaw': (3,),
}

# Single-observation categories: the asymmetric reading rule applies
# (DIAGNOSTIC_MIX_V1 §2/§3 — a miss flags for repair; a hit certifies nothing).
SINGLE_ITEM_CATEGORIES = tuple(c for c, ds in MIX.items() if len(ds) == 1)

# Ordering rules (DIAGNOSTIC_MIX_V1 §3): first item is difficulty 2;
# Parallel is never first.
FIRST_ITEM_DIFFICULTY = 2
NEVER_FIRST_CATEGORY = 'Parallel/Parallel Flaw'


def cells() -> list[tuple[str, int]]:
    """The fifteen (category, difficulty) cells, in artifact order."""
    out = [(cat, d) for cat, ds in MIX.items() for d in ds]
    assert len(out) == DIAGNOSTIC_LENGTH
    return out


def category_for_question_type(question_type: str) -> str | None:
    for cat, qts in CATEGORY_QUESTION_TYPES.items():
        if question_type in qts:
            return cat
    return None


_ARTIFACT_LINE = re.compile(
    r'^\s{2}(?P<cat>[A-Za-z/ ]+?)\s{2,}(?P<n>\d+)\s+difficulties \[(?P<ds>[\d, ]+)\]\s*$'
)


def parse_mix_artifact(path: Path = MIX_DOC) -> dict[str, tuple[int, ...]]:
    """Re-read DIAGNOSTIC_MIX_V1.md §3's fenced block. Tests assert this equals
    MIX, so an edit to the artifact that is not mirrored here fails the suite."""
    parsed: dict[str, tuple[int, ...]] = {}
    for raw in path.read_text(encoding='utf-8').splitlines():
        m = _ARTIFACT_LINE.match(raw)
        if not m:
            continue
        cat = m.group('cat').strip()
        difficulties = tuple(int(x) for x in m.group('ds').replace(' ', '').split(','))
        assert int(m.group('n')) == len(difficulties), (cat, raw)
        parsed[cat] = difficulties
    return parsed
