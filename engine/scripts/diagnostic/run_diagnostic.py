#!/usr/bin/env python3
"""Phase 3a diagnostic engine — server-side CLI. No UI.

Authorities: DIAGNOSTIC_MIX_V1 (controlling), PHASE_03_CONFORMANCE_V1,
VISIBILITY_CONTRACT_V1 + visibility_mode_matrix.json, MASTERY_CONTRACT_V1,
TRAP_GRAIN_V1.

Contract:
  * Selection reads content_items ONLY, filtered by the visibility predicate
    built from visibility_mode_matrix.json as a real SQL WHERE fragment.
    content_items_staging is never queried from any code path in this module.
    Default mode is production_student (most restrictive); internal beta runs
    pass --mode internal_beta explicitly (or set DIAGNOSTIC_VISIBILITY_MODE).
  * This module never writes content_state, publication_state, or
    validation_status. It never promotes, publishes, or touches ledgers.
  * Correct attempts write the 'N/A_correct' sentinel in BOTH trap fields
    (PHASE_03_CONFORMANCE_V1 D3-4) — never null.
  * mastery_states / mastery_events use the 4-value dimension list (no
    trap_label; the 0001/0006 CHECKs enforce it).
    diagnostic_results_by_dimension uses the 5-value list and may carry
    trap_label (TRAP_GRAIN_V1 ruling 4). These differ on purpose.
  * change_reason 'decay' is never written (reserved).

Usage:
    python scripts/diagnostic/run_diagnostic.py create --user-id u1 --mode internal_beta
    python scripts/diagnostic/run_diagnostic.py answer --session-id <id> \
        --canonical-id AR_V1_B1_0001 --selected C [--response-time-ms 42000] \
        [--confidence low|medium|high]
    python scripts/diagnostic/run_diagnostic.py finalize --session-id <id>

Exit codes: 0 ok; 1 refused/blocked (nothing written); 2 usage error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts' / 'db'))
sys.path.insert(0, str(ROOT / 'scripts' / 'diagnostic'))
from config import assert_not_production, database_url  # noqa: E402
from mix import (  # noqa: E402
    CATEGORY_QUESTION_TYPES, DIAGNOSTIC_LENGTH, DIAGNOSTIC_VERSION,
    SELECTION_REASON, category_for_question_type,
)
from selection import (  # noqa: E402
    DEFAULT_VISIBILITY_MODE, EmptyCellError, select_diagnostic,
    student_visibility_predicate, visibility_predicate,
)
import mastery_engine as me  # noqa: E402

ATTEMPT_SCHEMA = json.loads(
    (ROOT / 'schemas' / 'student_attempt_schema.json').read_text(encoding='utf-8'))
TRAP_SENTINEL = 'N/A_correct'


class DiagnosticError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(f'{code}: {message}')
        self.code = code
        self.message = message


def _connect(url: str):
    try:
        import psycopg  # type: ignore
    except ImportError:  # pragma: no cover
        sys.exit('psycopg is not installed. Install it with:\n'
                 '    pip install "psycopg[binary]" --break-system-packages\n')
    return psycopg.connect(url)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# create


def fetch_candidates(conn, mode: str) -> list[dict]:
    """The ONLY selection query. FROM content_items; visibility as SQL."""
    predicate, params = visibility_predicate(mode)
    sql = ('select canonical_id, content_version, question_type, difficulty '
           f'from content_items where {predicate}')
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return [
            {'canonical_id': r[0], 'content_version': r[1],
             'question_type': r[2], 'difficulty': r[3]}
            for r in cur.fetchall()
        ]


def create_session(conn, user_id: str, mode: str) -> dict:
    items = select_diagnostic(user_id, fetch_candidates(conn, mode))
    session_id = f'diag_{uuid.uuid4()}'
    started = now_iso()
    with conn.transaction():
        with conn.cursor() as cur:
            cur.execute(
                'insert into sessions (session_id, user_id, session_type, status, '
                'started_at, planned_item_count, selection_policy) '
                'values (%s, %s, %s, %s, %s, %s, %s)',
                (session_id, user_id, 'diagnostic', 'active', started,
                 DIAGNOSTIC_LENGTH, DIAGNOSTIC_VERSION))
            for it in items:
                cur.execute(
                    'insert into session_items (session_id, position, canonical_id, '
                    'content_version, selection_reason, target_recipe_id, '
                    'target_trap_family) values (%s, %s, %s, %s, %s, null, null)',
                    (session_id, it['position'], it['canonical_id'],
                     it['content_version'], SELECTION_REASON))
    return {'session_id': session_id, 'user_id': user_id, 'mode': mode,
            'items': [{k: it[k] for k in
                       ('position', 'canonical_id', 'content_version',
                        'question_type', 'difficulty', 'category')}
                      for it in items]}


# ---------------------------------------------------------------------------
# answer


def build_attempt_payload(*, attempt_id: str, user_id: str, canonical_id: str,
                          content_version: int, session_id: str, position: int,
                          selected: str, correct_answer: str,
                          choice_trap_label: str | None,
                          choice_trap_family: str | None,
                          response_time_ms: int | None,
                          confidence: str | None,
                          submitted_at: str) -> dict:
    """Construct the attempts row — pure, no I/O. THE single place the D3-4
    sentinel rule lives (PHASE_03_CONFORMANCE_V1: on a correct attempt both
    trap fields carry 'N/A_correct', never null; on a wrong attempt both carry
    the selected distractor's real values). Raises DiagnosticError rather than
    ever emitting None in either field."""
    is_correct = selected == correct_answer
    if is_correct:
        selected_trap_label = TRAP_SENTINEL
        selected_trap_family = TRAP_SENTINEL
    else:
        selected_trap_label = choice_trap_label
        selected_trap_family = choice_trap_family
    if selected_trap_label is None or selected_trap_family is None:
        raise DiagnosticError(
            'TRAP_FIELDS_NULL',
            f'attempt would carry null trap fields (is_correct={is_correct}); '
            f'D3-4 forbids null — a wrong attempt needs the distractor\'s real '
            f'trap_label/trap_family from content_explanations, a correct one '
            f'the sentinel')
    return {
        'attempt_id': attempt_id,
        'user_id': user_id,
        'canonical_id': canonical_id,
        'content_version': content_version,
        'session_id': session_id,
        'session_type': 'diagnostic',
        'selected_answer': selected,
        'correct_answer_at_attempt': correct_answer,
        'is_correct': is_correct,
        'selected_trap_label': selected_trap_label,
        'selected_trap_family': selected_trap_family,
        'response_time_ms': response_time_ms,
        'confidence_self_report': confidence or 'not_collected',
        'submitted_at': submitted_at,
        'scoring_context': {
            'algorithm_version': me.ALGORITHM_VERSION,
            'diagnostic_version': DIAGNOSTIC_VERSION,
            'position': position,
        },
    }


def record_attempt(conn, session_id: str, canonical_id: str, selected: str,
                   response_time_ms: int | None,
                   confidence: str | None) -> dict:
    selected = selected.strip().upper()
    if selected not in ('A', 'B', 'C', 'D', 'E'):
        raise DiagnosticError('SELECTED_ANSWER_INVALID', f'{selected!r} not in A..E')
    with conn.cursor() as cur:
        cur.execute(
            'select s.user_id, s.status, si.content_version, si.position '
            'from sessions s join session_items si on si.session_id = s.session_id '
            'where s.session_id = %s and si.canonical_id = %s',
            (session_id, canonical_id))
        row = cur.fetchone()
        if row is None:
            raise DiagnosticError(
                'ITEM_NOT_IN_SESSION',
                f'{canonical_id} is not part of session {session_id}')
        user_id, status, content_version, position = row
        if status != 'active':
            raise DiagnosticError('SESSION_NOT_ACTIVE', f'session status={status!r}')
        cur.execute(
            'select 1 from attempts where session_id = %s and canonical_id = %s',
            (session_id, canonical_id))
        if cur.fetchone():
            raise DiagnosticError(
                'ALREADY_ANSWERED', f'{canonical_id} already answered in this session')
        cur.execute(
            'select correct_answer from content_items '
            'where canonical_id = %s and content_version = %s',
            (canonical_id, content_version))
        (correct_answer,) = cur.fetchone()
        cur.execute(
            'select trap_label, trap_family from content_explanations '
            'where canonical_id = %s and content_version = %s and choice_letter = %s',
            (canonical_id, content_version, selected))
        trap_label, trap_family = cur.fetchone()

    attempt = build_attempt_payload(
        attempt_id=f'att_{uuid.uuid4()}', user_id=user_id,
        canonical_id=canonical_id, content_version=content_version,
        session_id=session_id, position=position, selected=selected,
        correct_answer=correct_answer, choice_trap_label=trap_label,
        choice_trap_family=trap_family, response_time_ms=response_time_ms,
        confidence=confidence, submitted_at=now_iso())
    is_correct = attempt['is_correct']
    errors = [e.message for e in
              Draft202012Validator(ATTEMPT_SCHEMA).iter_errors(attempt)]
    if errors:
        raise DiagnosticError('ATTEMPT_SCHEMA_INVALID', '; '.join(errors))

    with conn.transaction():
        with conn.cursor() as cur:
            cur.execute(
                'insert into attempts (attempt_id, user_id, canonical_id, '
                'content_version, session_id, session_type, scoring_context, '
                'selected_answer, correct_answer_at_attempt, is_correct, '
                'selected_trap_label, selected_trap_family, response_time_ms, '
                'confidence_self_report, submitted_at) values '
                '(%(attempt_id)s, %(user_id)s, %(canonical_id)s, %(content_version)s, '
                '%(session_id)s, %(session_type)s, %(scoring_context)s, '
                '%(selected_answer)s, %(correct_answer_at_attempt)s, %(is_correct)s, '
                '%(selected_trap_label)s, %(selected_trap_family)s, '
                '%(response_time_ms)s, %(confidence_self_report)s, %(submitted_at)s)',
                {**attempt, 'scoring_context': json.dumps(attempt['scoring_context'])})
    return {'is_correct': is_correct, 'position': position,
            'attempt_id': attempt['attempt_id']}


# ---------------------------------------------------------------------------
# item loaders (Phase 3b-1: the API delegates here; logic lives in the engine)


def _removal_reason(cur, canonical_id: str, content_version: int) -> str:
    """Classify WHY an in-flight item is being removed (D3 operator ruling).

    source_safety_rollback is keyed off an AUTHORITATIVE ACTIVE rollback-review
    state -- admin_reviews.review_queue_state = 'rollback_review_queue' -- and
    NOT off the mere fact that the item is unpublished. An item pulled for
    ordinary reasons (retired, superseded, withdrawn) is routine_retirement.

    Both remove the item from the slot identically; only the challenged one is
    RECORDED as a rollback, which keeps Spec 07 §12.4 incidents countable and
    stops routine churn inflating them.

    The record is HISTORICAL (operator ruling): a substitution recorded as
    source_safety_rollback stays source_safety_rollback even if the item is
    later cleared and re-published. It was one at the time. That is why this is
    evaluated once, at removal, and never recomputed.
    """
    cur.execute(
        "select 1 from admin_reviews "
        "where canonical_id = %s and content_version = %s "
        "  and review_queue_state = 'rollback_review_queue' "
        'limit 1',
        (canonical_id, content_version))
    return 'source_safety_rollback' if cur.fetchone() else 'routine_retirement'


def _find_replacement(cur, session_id: str, position: int,
                      removed_canonical_id: str, removed_content_version: int,
                      mode: str) -> tuple[str, int] | None:
    """Deterministic same-slot replacement from currently eligible content.

    Like-for-like: the replacement matches the removed item's question_type and
    difficulty, so the session's mix cell (DIAGNOSTIC_MIX_V1) survives the
    substitution. It must be currently visible under the SAME predicate the
    fetch re-check applies, and must not duplicate a canonical_id already in
    this session (Rule 3 spans the session).

    Deterministic: candidates are ordered by canonical_id and the choice is a
    seeded hash of (session, position, removed item), so identical inputs give
    an identical replacement on every call and on every machine. No RNG.

    Returns (canonical_id, content_version) or None when no candidate exists.
    """
    vis_sql, vis_params = student_visibility_predicate(mode, alias='ci')
    params = dict(vis_params)
    params.update({'session_id': session_id,
                   'removed_id': removed_canonical_id,
                   'removed_ver': removed_content_version})
    cur.execute(
        'select ci.canonical_id, ci.content_version from content_items ci '
        'join content_items src on src.canonical_id = %(removed_id)s '
        '  and src.content_version = %(removed_ver)s '
        f'where {vis_sql} '
        '  and ci.question_type = src.question_type '
        '  and ci.difficulty = src.difficulty '
        '  and ci.canonical_id not in ('
        '    select canonical_id from session_items where session_id = %(session_id)s) '
        'order by ci.canonical_id',
        params)
    candidates = cur.fetchall()
    if not candidates:
        return None
    seed = f'{session_id}|{position}|{removed_canonical_id}|{removed_content_version}'
    idx = int(hashlib.sha256(seed.encode()).hexdigest(), 16) % len(candidates)
    return candidates[idx][0], candidates[idx][1]


def _unavailable_payload(position: int) -> dict:
    """A slot the student cannot be served. Carries NO content -- no stimulus,
    no stem, no choices, and no canonical_id (the id stays in session_items for
    audit, but naming a pulled item to a student is exactly what §12.4 is for).
    """
    return {'position': position, 'slot_state': 'unavailable',
            'canonical_id': None, 'content_version': None,
            'question_type': None, 'stimulus': None, 'question_stem': None,
            'choices': []}


def fetch_student_item(conn, session_id: str, position: int,
                       mode: str = DEFAULT_VISIBILITY_MODE) -> dict:
    """Source data for a StudentItemPayload: ONLY student-safe columns are
    selected. correct_answer, recipe fields, and explanations are not in the
    query, so no caller of this function can leak them by accident. The API
    additionally whitelists on serialization (defense in depth).

    D3 (operator ruling): the item's CURRENT publication_state/content_state are
    re-checked HERE, at fetch time -- the session_items row is not trusted. An
    item unpublished because of an originality challenge or source-safety
    rollback becomes unavailable on every student surface immediately,
    including an already-created session. Selection pools were always gated;
    this closes the in-flight read, which is what Spec 07 §12.4's
    unpublish-first remedy actually depends on.

    If the scheduled item is no longer visible: its content is NOT returned. A
    deterministic same-slot replacement is attempted from currently eligible
    content and the substitution recorded; if no valid replacement exists the
    slot is marked unavailable and the student continues with a shortened
    session (and is never scored or penalised for it -- an unavailable slot
    writes no attempt, and every denominator here is attempt-driven).

    Concurrency: the session_items row is locked FOR UPDATE and slot_state is
    re-read under the lock, so two concurrent fetches of the same slot cannot
    both substitute. The loser observes the winner's result and serves it.
    """
    with conn.transaction():
        with conn.cursor() as cur:
            # Lock the slot for the duration of the transaction. Concurrent
            # fetches of this slot serialise here; the second re-reads below and
            # sees the first's outcome instead of substituting again.
            cur.execute(
                'select canonical_id, content_version, slot_state '
                'from session_items where session_id = %s and position = %s '
                'for update',
                (session_id, position))
            row = cur.fetchone()
            if row is None:
                raise DiagnosticError(
                    'ITEM_NOT_FOUND', f'session {session_id} has no item at '
                    f'position {position}')
            canonical_id, content_version, slot_state = row

            # Already resolved by an earlier fetch (or a concurrent winner).
            if slot_state == 'unavailable':
                return _unavailable_payload(position)

            # The re-check. Deliberately the visibility CORE only: whether this
            # item is still published + validated. Not diagnostic_eligible --
            # that flag is session-type-specific and would wrongly pull items
            # from a session that legitimately selected them.
            vis_sql, vis_params = student_visibility_predicate(
                mode, alias='ci')
            params = dict(vis_params)
            params.update({'cid': canonical_id, 'ver': content_version})
            cur.execute(
                'select ci.question_type, ci.stimulus, ci.question_stem '
                'from content_items ci '
                'where ci.canonical_id = %(cid)s and ci.content_version = %(ver)s '
                f'  and {vis_sql}',
                params)
            visible = cur.fetchone()

            if visible is None:
                # Not visible any more. Do not return its content.
                reason = _removal_reason(cur, canonical_id, content_version)
                replacement = _find_replacement(
                    cur, session_id, position, canonical_id, content_version, mode)
                cur.execute(
                    'insert into session_item_substitutions ('
                    'substitution_id, session_id, position, removed_canonical_id, '
                    'removed_content_version, replacement_canonical_id, '
                    'replacement_content_version, reason, created_at) '
                    'values (%s, %s, %s, %s, %s, %s, %s, %s, %s)',
                    (f'sub_{uuid.uuid4()}', session_id, position, canonical_id,
                     content_version,
                     replacement[0] if replacement else None,
                     replacement[1] if replacement else None,
                     reason, now_iso()))
                if replacement is None:
                    # No valid replacement: shortened session. canonical_id is
                    # RETAINED on the row for audit; the payload carries none.
                    cur.execute(
                        "update session_items set slot_state = 'unavailable' "
                        'where session_id = %s and position = %s',
                        (session_id, position))
                    return _unavailable_payload(position)
                canonical_id, content_version = replacement
                cur.execute(
                    'update session_items set canonical_id = %s, '
                    "content_version = %s, slot_state = 'substituted' "
                    'where session_id = %s and position = %s',
                    (canonical_id, content_version, session_id, position))
                # NOTE: item_selected is deliberately NOT touched. It is the
                # selection log -- the record of what the selector chose at
                # assembly time. That record remains true and must not be
                # rewritten; the substitution is a separate, later fact with its
                # own table.
                cur.execute(
                    'select question_type, stimulus, question_stem '
                    'from content_items '
                    'where canonical_id = %s and content_version = %s',
                    (canonical_id, content_version))
                visible = cur.fetchone()

            question_type, stimulus, stem = visible
            cur.execute(
                'select choice_letter, choice_text from content_choices '
                'where canonical_id = %s and content_version = %s '
                'order by display_order',
                (canonical_id, content_version))
            choices = [{'letter': r[0], 'text': r[1]} for r in cur.fetchall()]

    return {
        'canonical_id': canonical_id, 'content_version': content_version,
        'position': position, 'question_type': question_type,
        'stimulus': stimulus, 'question_stem': stem, 'choices': choices,
        'slot_state': 'scheduled',
    }


def next_unanswered_position(conn, session_id: str) -> int | None:
    """Lowest session position without an attempt; None when all answered."""
    with conn.cursor() as cur:
        cur.execute(
            'select min(si.position) from session_items si '
            'left join attempts a on a.session_id = si.session_id '
            '  and a.canonical_id = si.canonical_id '
            'where si.session_id = %s and a.attempt_id is null',
            (session_id,))
        (pos,) = cur.fetchone()
    return pos


def fetch_reveal(conn, canonical_id: str, content_version: int,
                 selected: str) -> dict:
    """Post-answer reveal: the selected choice's explanation plus the credited
    answer's explanation. Only lawful AFTER an attempt is recorded — the API
    returns this exclusively inside the submit-answer response."""
    with conn.cursor() as cur:
        cur.execute(
            'select correct_answer from content_items '
            'where canonical_id = %s and content_version = %s',
            (canonical_id, content_version))
        (correct_answer,) = cur.fetchone()
        cur.execute(
            'select choice_letter, explanation_text from content_explanations '
            'where canonical_id = %s and content_version = %s '
            'and choice_letter in (%s, %s)',
            (canonical_id, content_version, selected, correct_answer))
        by_letter = {r[0]: r[1] for r in cur.fetchall()}
    return {
        'correct_answer': correct_answer,
        'selected_explanation': by_letter.get(selected),
        'correct_explanation': by_letter.get(correct_answer),
    }


# ---------------------------------------------------------------------------
# finalize


def load_session_attempts(conn, session_id: str) -> tuple[str, list[dict]]:
    """Load a session's attempts, refusing a PARTIAL session.

    D3: completeness is measured against the ANSWERABLE slots, not the planned
    ones. A slot whose item was pulled mid-session with no valid replacement is
    marked unavailable and can never receive an attempt, so comparing against
    planned_item_count would make a shortened session impossible to finalize --
    the student would answer everything they could and stay stuck forever. That
    would defeat the D3 ruling ("allow the student to continue with a shortened
    session") at the last step.

    The guard's ORIGINAL intent is preserved exactly: you must answer every slot
    you CAN answer. A student who abandons a 15-item diagnostic after 5 is still
    refused. planned_item_count is NOT mutated -- the session record keeps
    saying 3 were planned and 2 were answerable, which is the honest history.

    Shared by the diagnostic and adaptive (Daily Repair) finalize paths, so this
    one guard covers both.
    """
    with conn.cursor() as cur:
        cur.execute('select user_id, status, planned_item_count from sessions '
                    'where session_id = %s', (session_id,))
        row = cur.fetchone()
        if row is None:
            raise DiagnosticError('SESSION_NOT_FOUND', session_id)
        user_id, status, planned = row
        if status != 'active':
            raise DiagnosticError('SESSION_NOT_ACTIVE', f'session status={status!r}')
        cur.execute(
            'select count(*) from session_items '
            "where session_id = %s and slot_state <> 'unavailable'", (session_id,))
        (answerable,) = cur.fetchone()
        cur.execute(
            'select a.canonical_id, a.content_version, a.is_correct, '
            '  a.selected_trap_label, a.selected_trap_family, '
            '  ci.question_type, ci.normalized_recipe_id, si.position, '
            '  a.attempt_id '
            'from attempts a '
            'join content_items ci on ci.canonical_id = a.canonical_id '
            '  and ci.content_version = a.content_version '
            'join session_items si on si.session_id = a.session_id '
            '  and si.canonical_id = a.canonical_id '
            'where a.session_id = %s order by si.position', (session_id,))
        attempts = [
            {'canonical_id': r[0], 'content_version': r[1], 'is_correct': r[2],
             'selected_trap_label': r[3], 'selected_trap_family': r[4],
             'question_type': r[5], 'normalized_recipe_id': r[6], 'position': r[7],
             'attempt_id': r[8]}
            for r in cur.fetchall()
        ]
    if len(attempts) != answerable:
        raise DiagnosticError(
            'SESSION_INCOMPLETE',
            f'{len(attempts)} of {answerable} answerable items answered '
            f'({planned} planned, {planned - answerable} unavailable); finalize '
            f'refuses a partial diagnostic')
    return user_id, attempts


def persist_mastery(cur, user_id: str, states: dict, events: list, when: str) -> None:
    """Upsert mastery_states and insert mastery_events for one finalize.
    Factored out of finalize_session so Phase 5's adaptive finalize reuses the
    IDENTICAL mastery-write path (extend, don't fork); the shared mastery LOGIC
    is mastery_engine.apply_updates, called by both callers."""
    for (dt, di), st in states.items():
        cur.execute(
            'insert into mastery_states (user_id, dimension_type, '
            'dimension_id, mastery_score, attempt_count, recent_accuracy, '
            'status, last_attempt_at, last_updated_at) '
            'values (%s, %s, %s, %s, %s, %s, %s, %s, %s) '
            'on conflict (user_id, dimension_type, dimension_id) do update '
            'set mastery_score = excluded.mastery_score, '
            '    attempt_count = mastery_states.attempt_count + excluded.attempt_count, '
            '    recent_accuracy = excluded.recent_accuracy, '
            '    status = excluded.status, '
            '    last_attempt_at = excluded.last_attempt_at, '
            '    last_updated_at = excluded.last_updated_at',
            (user_id, dt, di, st['score'], st['attempt_count'],
             st['recent_accuracy'], st['status'], when, when))
    for ev in events:
        cur.execute(
            'insert into mastery_events (event_id, user_id, dimension_type, '
            'dimension_id, trigger_attempt_id, before_score, after_score, '
            'change_reason, created_at) values (%s, %s, %s, %s, null, '
            '%s, %s, %s, %s)',
            (f'mev_{uuid.uuid4()}', user_id, ev['dimension_type'],
             ev['dimension_id'], ev['before_score'], ev['after_score'],
             ev['change_reason'], when))


def finalize_session(conn, session_id: str) -> dict:
    user_id, attempts = load_session_attempts(conn, session_id)
    states, events = me.apply_updates(attempts)
    dim_rows = me.diagnostic_dimension_rows(attempts)
    category_by_qt = {qt: cat for cat, qts in CATEGORY_QUESTION_TYPES.items()
                      for qt in qts}
    me.apply_priority_ranks(dim_rows, category_by_qt)

    raw_score = sum(1 for a in attempts if a['is_correct'])
    ranked = sorted((r for r in dim_rows if r['priority_rank'] is not None),
                    key=lambda r: r['priority_rank'])
    primary_weaknesses = [
        {'dimension_type': r['dimension_type'], 'dimension_id': r['dimension_id'],
         'accuracy': r['accuracy'], 'priority_rank': r['priority_rank']}
        for r in ranked[:3]]
    worst_qt = next((r['dimension_id'] for r in ranked
                     if r['dimension_type'] == 'question_type'), None)
    recommended = (f'daily_repair:{worst_qt}' if worst_qt
                   else 'daily_repair:balanced')

    diagnostic_id = f'diagr_{uuid.uuid4()}'
    finished = now_iso()
    with conn.transaction():
        with conn.cursor() as cur:
            persist_mastery(cur, user_id, states, events, finished)
            cur.execute(
                'insert into diagnostic_runs (diagnostic_id, user_id, session_id, '
                'diagnostic_version, started_at, completed_at, raw_score, '
                'item_count, primary_weaknesses, recommended_start_path) '
                'select %s, %s, %s, %s, started_at, %s, %s, %s, %s, %s '
                'from sessions where session_id = %s',
                (diagnostic_id, user_id, session_id, DIAGNOSTIC_VERSION, finished,
                 raw_score, len(attempts), json.dumps(primary_weaknesses),
                 recommended, session_id))
            for r in dim_rows:
                cur.execute(
                    'insert into diagnostic_results_by_dimension (diagnostic_id, '
                    'dimension_type, dimension_id, correct_count, attempt_count, '
                    'accuracy, priority_rank, interpretation_text) '
                    'values (%s, %s, %s, %s, %s, %s, %s, %s)',
                    (diagnostic_id, r['dimension_type'], r['dimension_id'],
                     r['correct_count'], r['attempt_count'], r['accuracy'],
                     r['priority_rank'], r['interpretation_text']))
            cur.execute(
                "update sessions set status = 'completed', completed_at = %s, "
                'actual_item_count = %s where session_id = %s',
                (finished, len(attempts), session_id))
    return {'diagnostic_id': diagnostic_id, 'raw_score': raw_score,
            'item_count': len(attempts), 'primary_weaknesses': primary_weaknesses,
            'recommended_start_path': recommended,
            'mastery_dimensions_touched': len(states)}


# ---------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser(description='Diagnostic engine (server-side, no UI).')
    sub = ap.add_subparsers(dest='cmd', required=True)

    c = sub.add_parser('create', help='Select 15 items and open a session.')
    c.add_argument('--user-id', required=True)
    c.add_argument('--mode', default=os.environ.get(
        'DIAGNOSTIC_VISIBILITY_MODE', DEFAULT_VISIBILITY_MODE))

    a = sub.add_parser('answer', help='Record one attempt.')
    a.add_argument('--session-id', required=True)
    a.add_argument('--canonical-id', required=True)
    a.add_argument('--selected', required=True)
    a.add_argument('--response-time-ms', type=int, default=None)
    a.add_argument('--confidence', choices=['low', 'medium', 'high'], default=None)

    f = sub.add_parser('finalize', help='Compute mastery profile + summary.')
    f.add_argument('--session-id', required=True)

    args = ap.parse_args()
    url = assert_not_production(database_url())
    try:
        with _connect(url) as conn:
            if args.cmd == 'create':
                out = create_session(conn, args.user_id.strip(), args.mode)
            elif args.cmd == 'answer':
                out = record_attempt(conn, args.session_id, args.canonical_id,
                                     args.selected, args.response_time_ms,
                                     args.confidence)
            else:
                out = finalize_session(conn, args.session_id)
        print(json.dumps(out, indent=2))
        return 0
    except (DiagnosticError, EmptyCellError, ValueError) as e:
        print(f'BLOCKED: {e}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
