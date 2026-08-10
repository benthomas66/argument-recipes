"""Deterministic, seeded diagnostic selection — pure core, no database.

Authorities: DIAGNOSTIC_MIX_V1 §3 (mix, ordering, seeding);
PHASE_03_CONFORMANCE_V1 (rulings); VISIBILITY_CONTRACT_V1 +
visibility_mode_matrix.json (who may see what — realized here as a SQL
predicate builder, not a comment).

Candidates arrive as dicts with at least: canonical_id, content_version,
question_type, difficulty. The caller (engine.py) supplies them from a query
already filtered by the visibility predicate; select_diagnostic() re-groups
and re-checks so a mis-filtered caller still cannot produce an off-mix draw.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from mix import (
    DIAGNOSTIC_LENGTH,
    DIAGNOSTIC_VERSION,
    FIRST_ITEM_DIFFICULTY,
    NEVER_FIRST_CATEGORY,
    category_for_question_type,
    cells,
)

ROOT = Path(__file__).resolve().parents[2]
VISIBILITY_MATRIX = ROOT / 'docs' / 'patches' / 'visibility_mode_matrix.json'

# Most restrictive first; the engine defaults to production_student.
DEFAULT_VISIBILITY_MODE = 'production_student'


class EmptyCellError(Exception):
    """A (category, difficulty) mix cell has zero eligible candidates.

    DIAGNOSTIC_MIX_V1 forbids substitution and short sessions: fail loudly,
    name the cell, write nothing."""

    def __init__(self, category: str, difficulty: int):
        self.category = category
        self.difficulty = difficulty
        super().__init__(
            f'diagnostic mix cell has no eligible candidates: '
            f'(category={category!r}, difficulty={difficulty}). '
            f'Refusing to substitute or ship a short session '
            f'(DIAGNOSTIC_MIX_V1 / AGENT_PACKET_PHASE_3A).')


def student_visibility_predicate(mode: str = DEFAULT_VISIBILITY_MODE,
                                 alias: str = '') -> tuple[str, dict]:
    """The visibility CORE: content_state + publication_state, nothing else.

    This is the single source of truth for "which states may this mode see",
    read from docs/patches/visibility_mode_matrix.json (the encoded form of
    VISIBILITY_CONTRACT_V1) — never from memory.

    Two callers, one predicate:
      * visibility_predicate() composes this with the diagnostic eligibility
        flag for SELECTION POOLS.
      * run_diagnostic.fetch_student_item applies this alone for the FETCH-TIME
        RE-CHECK (D3). The re-check must not import diagnostic_eligible: that
        flag is session-type-specific, and the D3 ruling asks exactly whether
        the scheduled item is still published + validated — not whether it
        would be selected again today.

    `alias` qualifies the columns for a joined query (e.g. alias='ci').
    """
    matrix = json.loads(VISIBILITY_MATRIX.read_text(encoding='utf-8'))
    entry = next((m for m in matrix if m['mode'] == mode), None)
    if entry is None:
        raise ValueError(
            f'unknown visibility mode {mode!r}; known: {[m["mode"] for m in matrix]}')
    p = f'{alias}.' if alias else ''
    sql = (f'{p}content_state = any(%(visible_content_states)s) '
           f'and {p}publication_state = any(%(visible_publication_states)s)')
    params = {
        'visible_content_states': list(entry['visible_content_states']),
        'visible_publication_states': list(entry['visible_publication_states']),
    }
    return sql, params


def visibility_predicate(mode: str = DEFAULT_VISIBILITY_MODE) -> tuple[str, dict]:
    """Build the WHERE fragment for a visibility mode as a real SQL predicate.

    Values come from docs/patches/visibility_mode_matrix.json — the encoded
    form of VISIBILITY_CONTRACT_V1 — never from memory. Returns
    (sql_fragment, params) for psycopg named parameters. The fragment ANDs
    content_state, publication_state, and diagnostic_eligible; it references
    content_items only (no staging table can satisfy it because it is applied
    to a FROM content_items query and staging is never queried).

    Composed from student_visibility_predicate() so the selection pools and the
    D3 fetch-time re-check cannot drift apart. The composed string is
    byte-identical to the pre-D3 predicate (pinned by test).
    """
    sql, params = student_visibility_predicate(mode)
    return sql + ' and diagnostic_eligible = true', params


def _pick_index(user_id: str, salt: str, n: int) -> int:
    digest = hashlib.sha256(f'{DIAGNOSTIC_VERSION}|{user_id}|{salt}'.encode()).hexdigest()
    return int(digest, 16) % n


def _order_key(user_id: str, canonical_id: str) -> str:
    return hashlib.sha256(
        f'{DIAGNOSTIC_VERSION}|{user_id}|order|{canonical_id}'.encode()).hexdigest()


def select_diagnostic(user_id: str, candidates: list[dict]) -> list[dict]:
    """Fill the 15 mix cells deterministically for user_id.

    Returns the ordered 15 items (each the input dict plus 'category' and
    'position'). Same user -> identical draw; different users -> independent
    per-cell picks. Raises EmptyCellError on any unfillable cell BEFORE any
    pick is returned.
    """
    if not user_id or not user_id.strip():
        raise ValueError('user_id must be non-empty')

    by_cell: dict[tuple[str, int], list[dict]] = {}
    for c in candidates:
        cat = category_for_question_type(c['question_type'])
        if cat is None:
            continue  # PR/PI/RP/EV: outside the pool by design
        by_cell.setdefault((cat, int(c['difficulty'])), []).append(c)

    # Whole-draw validation first: every cell fillable or nothing returned.
    missing = [(cat, d) for (cat, d) in cells() if not by_cell.get((cat, d))]
    if missing:
        raise EmptyCellError(*missing[0])

    picked: list[dict] = []
    seen: set[tuple[str, int]] = set()
    for cat, d in cells():
        pool = sorted(
            (c for c in by_cell[(cat, d)]
             if (c['canonical_id'], c['content_version']) not in seen),
            key=lambda c: (c['canonical_id'], c['content_version']))
        if not pool:
            raise EmptyCellError(cat, d)
        choice = pool[_pick_index(user_id, f'{cat}|{d}', len(pool))]
        seen.add((choice['canonical_id'], choice['content_version']))
        picked.append({**choice, 'category': cat, 'difficulty': int(choice['difficulty'])})

    # Ordering (DIAGNOSTIC_MIX_V1 §3): first item is difficulty 2 and never
    # Parallel; the remainder is a deterministic seeded shuffle.
    d2 = sorted(
        (p for p in picked
         if p['difficulty'] == FIRST_ITEM_DIFFICULTY and p['category'] != NEVER_FIRST_CATEGORY),
        key=lambda p: p['canonical_id'])
    assert d2, 'mix guarantees three difficulty-2 items; none found'
    first = d2[_pick_index(user_id, 'first', len(d2))]
    rest = sorted(
        (p for p in picked if p is not first),
        key=lambda p: _order_key(user_id, p['canonical_id']))
    ordered = [first] + rest
    for pos, item in enumerate(ordered, start=1):
        item['position'] = pos
    assert len(ordered) == DIAGNOSTIC_LENGTH
    return ordered
