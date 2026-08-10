#!/usr/bin/env python3
"""Phase 3b-1 — the diagnostic HTTP API. Thin transport, no engine logic.

Architectural ruling (AGENT_PACKET_PATCH_A_AND_PHASE_3B1): the Python engine
in scripts/diagnostic/ is the single source of truth. Every endpoint here
delegates to it — create_session, record_attempt, finalize_session,
fetch_student_item, next_unanswered_position, fetch_reveal. This module
contains serialization, routing, and error mapping. Nothing else.

Redaction ruling (docs/patches/STUDENT_PAYLOAD_REDACTION_V1.md): a student
response NEVER carries correct_answer, correct_answer_job, recipe_title,
normalized_recipe_id, normalized_pattern_id, is_correct, trap_label,
trap_family, or any explanation BEFORE that item's answer is submitted.
Enforced twice: the engine loader selects only student-safe columns, and
student_item_payload() below serializes through a strict WHITELIST — an
unexpected key is an error, not a passenger.

Run:  DIAGNOSTIC_VISIBILITY_MODE=internal_beta \\
          uvicorn app:app --app-dir scripts/api --port 8300
"""
from __future__ import annotations

import contextlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Optional

import base64
import hashlib
import hmac
import time

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts' / 'db'))
sys.path.insert(0, str(ROOT / 'scripts' / 'diagnostic'))
sys.path.insert(0, str(ROOT / 'scripts' / 'analytics'))

from config import assert_not_production, database_url  # noqa: E402
from selection import DEFAULT_VISIBILITY_MODE, EmptyCellError  # noqa: E402
import run_diagnostic as engine  # noqa: E402
import adaptive_selection as adaptive  # noqa: E402
import emitter as analytics  # noqa: E402

# ---------------------------------------------------------------------------
# STUDENT_IDENTITY_V1 — identity plumbing (not authentication; Phase 8 swaps
# the cookie ISSUER, nothing else).

# Ruling 3: APP_SECRET is mandatory in every mode. No default, no fallback,
# no boot-time generation. The API refuses to start without it.
APP_SECRET = os.environ.get('APP_SECRET')
if not APP_SECRET:
    raise SystemExit(
        'APP_SECRET is required (STUDENT_IDENTITY_V1 ruling 3). Set it in the '
        'environment; see .env.example. The API refuses to start without it.')

APP_ENV = os.environ.get('APP_ENV', '')
COOKIE_NAME = 'ar_student'


def _sign(payload_b64: str) -> str:
    return hmac.new(APP_SECRET.encode(), payload_b64.encode(),
                    hashlib.sha256).hexdigest()


def issue_identity_cookie(user_id: str) -> str:
    # Signed cookie value: base64url({user_id, issued_at}) + '.' + hmac_sha256.
    body = json.dumps({'user_id': user_id, 'issued_at': int(time.time())},
                      separators=(',', ':'))
    payload_b64 = base64.urlsafe_b64encode(body.encode()).decode().rstrip('=')
    return f'{payload_b64}.{_sign(payload_b64)}'


def verify_identity_cookie(value: str) -> str | None:
    # Returns user_id, or None on any tampering or shape failure.
    try:
        payload_b64, signature = value.split('.', 1)
    except ValueError:
        return None
    if not hmac.compare_digest(signature, _sign(payload_b64)):
        return None
    try:
        padded = payload_b64 + '=' * (-len(payload_b64) % 4)
        body = json.loads(base64.urlsafe_b64decode(padded))
        user_id = body['user_id']
    except Exception:
        return None
    return user_id if isinstance(user_id, str) and user_id else None


def current_user(request: Request) -> str:
    # Ruling 2: identity comes ONLY from the signed cookie. Endpoints depend
    # on this function; they never read the cookie, and never a request body.
    value = request.cookies.get(COOKIE_NAME)
    user_id = verify_identity_cookie(value) if value else None
    if user_id is None:
        raise HTTPException(401, detail='not signed in')
    return user_id


def fetch_session_owner(conn, session_id: str) -> str | None:
    with conn.cursor() as cur:
        cur.execute('select user_id from sessions where session_id = %s',
                    (session_id,))
        row = cur.fetchone()
    return row[0] if row else None


def assert_session_owner(conn, session_id: str, user_id: str) -> None:
    # Ruling 5: ownership on every /sessions/{id}/* endpoint. Mismatch AND
    # missing both return 404 — never 403; never confirm the session exists.
    if fetch_session_owner(conn, session_id) != user_id:
        raise engine.DiagnosticError('SESSION_NOT_FOUND', session_id)

# The ONLY keys a pre-answer student payload may carry. Whitelist, not
# blacklist: a field added to content_items tomorrow stays unserved until
# someone adds it here deliberately.
STUDENT_ITEM_FIELDS = (
    'canonical_id', 'content_version', 'position', 'question_type',
    'stimulus', 'question_stem', 'choices',
    # D3: 'scheduled' | 'unavailable'. Added deliberately (this is a whitelist,
    # not a blacklist) so a client can render an unavailable slot honestly. An
    # unavailable slot carries no content: every other field is null/empty and
    # the item's identity is withheld -- naming a pulled item to a student is
    # exactly what Spec 07 §12.4 exists to prevent.
    'slot_state',
)
CHOICE_FIELDS = ('letter', 'text')


def student_item_payload(row: dict) -> dict:
    """Serialize an item for a student: a strict whitelist PROJECTION.
    Only STUDENT_ITEM_FIELDS / CHOICE_FIELDS reach the wire; any other key —
    however it got into the row — is dropped here. The test suite feeds this
    function rows deliberately poisoned with every forbidden field and scans
    the wire format, so bypassing this projection fails the suite."""
    payload = {k: row[k] for k in STUDENT_ITEM_FIELDS}
    payload['choices'] = [
        {k: c[k] for k in CHOICE_FIELDS} for c in row['choices']]
    return payload


def _connect():
    import psycopg
    return psycopg.connect(assert_not_production(database_url()))


@contextlib.contextmanager
def _analytics_never_breaks_flow():
    """Packet §2: 'a failed analytics write is logged, not raised into the
    session path.' analytics.emit() already swallows its own failures, but the
    property-GATHERING around it (extra reads, a second connection) must be
    equally contained — otherwise telemetry could still 500 a student request.
    Everything analytics-related in this module runs inside this guard."""
    try:
        yield
    except Exception as exc:  # noqa: BLE001 — deliberate: telemetry is best-effort
        analytics.log.warning('analytics: block failed, flow unaffected: %s', exc)


def _mode() -> str:
    return os.environ.get('DIAGNOSTIC_VISIBILITY_MODE', DEFAULT_VISIBILITY_MODE)


app = FastAPI(title='Argument Recipes — Diagnostic API', version='3b-1')


@app.exception_handler(engine.DiagnosticError)
def _diagnostic_error(_, exc: engine.DiagnosticError):
    status = {'SESSION_NOT_FOUND': 404, 'ITEM_NOT_FOUND': 404,
              'ITEM_NOT_IN_SESSION': 404, 'ALREADY_ANSWERED': 409,
              'SESSION_NOT_ACTIVE': 409, 'SESSION_INCOMPLETE': 409}.get(exc.code, 400)
    return JSONResponse(status_code=status,
                        content={'error': exc.code, 'detail': exc.message})


@app.exception_handler(EmptyCellError)
def _empty_cell(_, exc: EmptyCellError):
    return JSONResponse(status_code=409, content={
        'error': 'EMPTY_MIX_CELL', 'detail': str(exc),
        'category': exc.category, 'difficulty': exc.difficulty})


# STUDENT_IDENTITY_V1 ruling 1: no request model carries user_id. Session
# creation takes no body at all; identity is the cookie's job.

class SubmitAnswerRequest(BaseModel):
    canonical_id: str
    selected_answer: str
    response_time_ms: Optional[int] = None
    confidence_self_report: Optional[str] = None


@app.post('/diagnostic/sessions')
def create_session(user_id: str = Depends(current_user)) -> dict:
    with _connect() as conn:
        session = engine.create_session(conn, user_id, _mode())
        first = engine.fetch_student_item(conn, session['session_id'], 1)
        with _analytics_never_breaks_flow():
            analytics.emit(conn, 'diagnostic_started', user_id, {
                'session_id': session['session_id'],
                'planned_item_count': len(session['items']),
            })
    return {
        'session_id': session['session_id'],
        'planned_item_count': len(session['items']),
        'first': student_item_payload(first),
    }


@app.get('/sessions/{session_id}/items/{position}')
def get_item(session_id: str, position: int,
             user_id: str = Depends(current_user)) -> dict:
    with _connect() as conn:
        assert_session_owner(conn, session_id, user_id)
        row = engine.fetch_student_item(conn, session_id, position)
        with _analytics_never_breaks_flow():
            analytics.emit(conn, 'practice_item_viewed', user_id, {
                'session_id': session_id, 'position': position,
                'canonical_id': row.get('canonical_id'),
                'session_type': _session_type(conn, session_id),
            })
    return student_item_payload(row)


@app.post('/sessions/{session_id}/attempts')
def submit_answer(session_id: str, body: SubmitAnswerRequest,
                  user_id: str = Depends(current_user)) -> dict:
    confidence = body.confidence_self_report
    if confidence not in (None, 'low', 'medium', 'high'):
        raise HTTPException(422, detail='confidence must be low|medium|high')
    with _connect() as conn:
        assert_session_owner(conn, session_id, user_id)
        result = engine.record_attempt(
            conn, session_id, body.canonical_id, body.selected_answer,
            body.response_time_ms, confidence)
        reveal = engine.fetch_reveal(
            conn, body.canonical_id,
            _content_version_for(conn, session_id, body.canonical_id),
            body.selected_answer.strip().upper())
        nxt = engine.next_unanswered_position(conn, session_id)
        next_payload = (student_item_payload(
            engine.fetch_student_item(conn, session_id, nxt))
            if nxt is not None else None)
    out = {
        'correct': result['is_correct'],
        'correct_answer': reveal['correct_answer'],
        'explanation': reveal['selected_explanation'],
        'correct_explanation': reveal['correct_explanation'],
        'next': next_payload,
    }
    if not result['is_correct']:
        # Post-answer reveal of the selected distractor's trap (3b-2 packet;
        # supersedes STUDENT_PAYLOAD_REDACTION_V1 ruling 3's MVP withholding —
        # recorded in the completion report). Never present pre-answer. Read
        # from the attempt row the engine just wrote — scripts/diagnostic/ is
        # frozen this phase, so the transport reads rather than the engine
        # returning more.
        label, family = _attempt_trap_fields(conn, result['attempt_id'])
        out['selected_trap_label'] = label
        out['selected_trap_family'] = family

    # Analytics (Workstream B). Emitted after the attempt is durably recorded,
    # on its own connection so telemetry can never affect the answer path.
    with _analytics_never_breaks_flow():
        with _connect() as aconn:
            stype = _session_type(aconn, session_id)
            submitted = ('diagnostic_item_submitted' if stype == 'diagnostic'
                         else 'practice_item_submitted')
            base = {'session_id': session_id, 'canonical_id': body.canonical_id,
                    'session_type': stype, 'is_correct': bool(result['is_correct'])}
            analytics.emit(aconn, submitted, user_id, base)
            # The response body carries the explanation, so the reveal happened.
            analytics.emit(aconn, 'explanation_viewed', user_id, base)
            if not result['is_correct']:
                # The trap is revealed only on a wrong answer (above).
                analytics.emit(aconn, 'trap_feedback_viewed', user_id, {
                    **base,
                    'selected_trap_family': out.get('selected_trap_family')})
    return out


def _attempt_trap_fields(conn, attempt_id: str):
    with conn.cursor() as cur:
        cur.execute(
            'select selected_trap_label, selected_trap_family '
            'from attempts where attempt_id = %s', (attempt_id,))
        return cur.fetchone()


def _content_version_for(conn, session_id: str, canonical_id: str) -> int:
    with conn.cursor() as cur:
        cur.execute('select content_version from session_items '
                    'where session_id = %s and canonical_id = %s',
                    (session_id, canonical_id))
        row = cur.fetchone()
    if row is None:
        raise engine.DiagnosticError(
            'ITEM_NOT_IN_SESSION', f'{canonical_id} not in {session_id}')
    return row[0]


def _session_type(conn, session_id: str) -> str | None:
    with conn.cursor() as cur:
        cur.execute('select session_type from sessions where session_id = %s',
                    (session_id,))
        row = cur.fetchone()
    return row[0] if row else None


def _completed_review_rows(conn, user_id: str) -> set:
    """queue_ids of the user's review obligations currently marked completed.
    Read-only transport helper: the Phase 5/6 engines are frozen this phase, so
    the completed-review analytics event is derived by diffing this set around
    finalize rather than by emitting from inside the engine."""
    with conn.cursor() as cur:
        cur.execute("select queue_id, canonical_id from learning_queues "
                    "where user_id = %s and status = 'completed'", (user_id,))
        return {(r[0], r[1]) for r in cur.fetchall()}


@app.post('/sessions/{session_id}/finalize')
def finalize(session_id: str,
             user_id: str = Depends(current_user)) -> dict:
    with _connect() as conn:
        assert_session_owner(conn, session_id, user_id)
        # Diagnostic sessions compute a diagnostic profile; adaptive sessions
        # (daily_repair, etc.) update mastery + reviews and return a redacted
        # completion summary. Both go through the same mastery path.
        stype = _session_type(conn, session_id)
        if stype == 'diagnostic':
            summary = engine.finalize_session(conn, session_id)
            with _analytics_never_breaks_flow():
                analytics.emit(conn, 'diagnostic_completed', user_id,
                               {'session_id': session_id})
            return _decorate_finalize_summary(conn, summary)

        before = set()
        with _analytics_never_breaks_flow():
            before = _completed_review_rows(conn, user_id)
        summary = adaptive.finalize_adaptive_session(conn, session_id)
        with _analytics_never_breaks_flow():
            # A review obligation that reached status='completed' during this
            # finalize is a completed review-queue item.
            for _qid, cid in sorted(_completed_review_rows(conn, user_id) - before):
                analytics.emit(conn, 'review_queue_item_completed', user_id,
                               {'session_id': session_id, 'canonical_id': cid})
            if stype == 'daily_repair':
                analytics.emit(conn, 'daily_repair_completed', user_id, {
                    'session_id': session_id,
                    'items_attempted': summary.get('items_attempted'),
                    'correct': summary.get('correct'),
                    'reviews_enqueued': summary.get('reviews_enqueued'),
                    'reviews_stabilized': summary.get('reviews_stabilized'),
                })
        return _decorate_finalize_summary(conn, summary)


# ---------------------------------------------------------------------------
# AR-WEB-016 — authored display names for the dashboard.
#
# The dashboard was rendering internal machine identifiers as student copy:
# recipe ids (FLAW_DESCRIBE, NA_REQUIRED) and raw taxonomy keys ("Scope
# Failure"). The authored student-facing names already exist — recipes
# .recipe_title and trap_taxonomy.student_name — but the two engine reads that
# build these payloads (adaptive.mastery_profile / .missed_trap_profile) live in
# the FROZEN scripts/diagnostic/, so the transport reads rather than the engine
# returning more. Same precedent as _attempt_trap_fields and
# _completed_review_rows above.
#
# Deliberately a LOOKUP, not a join: the engine's queries (including the
# missed-trap GROUP BY) are untouched, so row cardinality cannot change. The
# maps are tiny (22 recipes, 20 trap families). Nothing here reads a content
# body — only an authored label — and nothing is written.


def _authored_names(conn, sql: str) -> dict:
    """{identifier: authored name} for the rows that actually HAVE one. A null,
    non-string, or whitespace-only name is dropped here so no caller can
    accidentally promote it to student copy."""
    with conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()
    return {key: name for key, name in rows
            if isinstance(key, str) and isinstance(name, str) and name.strip()}


def _recipe_display_names(conn) -> dict:
    return _authored_names(conn, 'select recipe_id, recipe_title from recipes')


def _trap_display_names(conn) -> dict:
    return _authored_names(
        conn, 'select trap_family, student_name from trap_taxonomy')


def _decorate_mastery_profile(conn, profile: dict) -> dict:
    """Add display_name to each framed view, ONLY where an authored name
    exists. Purely additive: no row is added, removed, reordered, or altered, so
    a dimension with no authored name (possible under taxonomy_only provenance)
    simply arrives as it always has and the client falls back to the id."""
    names_by_type = {
        'recipe': _recipe_display_names(conn),
        'trap_family': _trap_display_names(conn),
    }
    for views in (profile.get('trap_families'), profile.get('recipes')):
        for view in views or []:
            names = names_by_type.get(view.get('dimension_type'))
            name = names.get(view.get('dimension_id')) if names else None
            if name:
                view['display_name'] = name
    return profile


def _decorate_missed_traps(conn, profile: dict) -> dict:
    """Same rule for the "To revisit" rows, keyed on trap_family."""
    names = _trap_display_names(conn)
    for row in profile.get('missed_traps') or []:
        name = names.get(row.get('trap_family'))
        if name:
            row['display_name'] = name
    return profile


# ---------------------------------------------------------------------------
# AR-WEB-017 — the SAME authored names on the session Summary.
#
# Summary.tsx had the identical defect one screen over: the diagnostic weakness
# rows and the Daily Repair movement rows both rendered dimension_id as student
# copy. Same architecture as above and for the same reason — both finalize
# payloads are built by the FROZEN scripts/diagnostic/ engines, so the transport
# decorates rather than the engine returning more. Same lookup, same
# _authored_names choke point, same purely-additive rule: no join, no GROUP BY
# change, no migration, so row cardinality cannot change.
#
# question_type rows are deliberately NOT named. There is no authored-name
# source for a question type (recipes.question_types is an array of codes, not a
# display-name table), and inventing one would be fabrication — the identifier
# is the honest fallback.


def _display_names_for(conn, dimension_type, cache: dict) -> dict:
    """The authored-name map for one dimension_type, memoized in `cache`.

    `cache` is REQUEST-SCOPED: the caller creates a fresh dict per decoration
    and it never escapes that call, so there is no module-level or otherwise
    shared mutable state here and one request can never observe another's
    lookup. It exists only so a payload with several recipe rows issues one
    SELECT instead of one per row; a dimension_type with no authored-name source
    (question_type, difficulty, trap_label) memoizes an empty map and issues
    none at all."""
    if dimension_type not in cache:
        if dimension_type == 'recipe':
            cache[dimension_type] = _recipe_display_names(conn)
        elif dimension_type == 'trap_family':
            cache[dimension_type] = _trap_display_names(conn)
        else:
            cache[dimension_type] = {}
    return cache[dimension_type]


def _decorate_finalize_summary(conn, summary: dict) -> dict:
    """Add display_name to the dimension rows of EITHER finalize payload, ONLY
    where an authored name exists. The two payloads are structurally disjoint,
    so exactly one of these keys is ever present; the other is absent and
    iterates nothing. A summary with no rows performs no read at all."""
    cache: dict = {}
    for key in ('primary_weaknesses', 'mastery_movement'):
        for row in summary.get(key) or []:
            names = _display_names_for(conn, row.get('dimension_type'), cache)
            name = names.get(row.get('dimension_id'))
            if name:
                row['display_name'] = name
    return summary


@app.get('/profile/mastery')
def profile_mastery(user_id: str = Depends(current_user)) -> dict:
    # Dashboard read — the student's own framed mastery profile (trap families
    # + recipes), FRAMED label + confidence only, never a raw band or
    # mastery_score. Thin by contract: delegates to a read-only projection over
    # persisted mastery_states; no mastery calculation, write, or selection
    # happens here. Scoped to the authenticated user by the cookie.
    # The only thing added on top is the authored display name (AR-WEB-016).
    with _connect() as conn:
        return _decorate_mastery_profile(
            conn, adaptive.mastery_profile(conn, user_id))


@app.get('/profile/missed-traps')
def profile_missed_traps(user_id: str = Depends(current_user)) -> dict:
    # Phase 6 Step C — a student's own standing missed-trap obligations, per
    # trap_family, with FRAMED status only (no raw band/mastery_score). Scoped
    # to the authenticated user by the cookie; no cross-user read is possible.
    with _connect() as conn:
        return _decorate_missed_traps(
            conn, adaptive.missed_trap_profile(conn, user_id))


# ---------------------------------------------------------------------------
# Phase 7 — adaptive session assembly. Delegates entirely to
# scripts/diagnostic/adaptive_selection.py (the single-source-of-truth engine);
# this endpoint only carries identity and re-uses the SAME redacted student
# payload as the diagnostic. The subsequent per-item / attempt / finalize
# endpoints already work for any session_id, so no other transport is added.
# STUDENT_IDENTITY_V1 ruling 1: the body carries no user_id — identity is the
# cookie. Ownership on the returned session is guaranteed because we created it
# for current_user; the item/attempt/finalize routes re-check ownership.

# Adaptive modes only; 'diagnostic' has its own fixed-mix endpoint above.
ADAPTIVE_SESSION_TYPES = (
    'daily_repair', 'targeted_drill', 'missed_trap_review', 'timed_practice')


class AdaptiveSessionRequest(BaseModel):
    session_type: str = 'daily_repair'
    slot_count: int = Field(default=10, ge=1, le=50)


@app.post('/adaptive/sessions')
def create_adaptive_session(body: AdaptiveSessionRequest,
                            user_id: str = Depends(current_user)) -> dict:
    if body.session_type not in ADAPTIVE_SESSION_TYPES:
        raise HTTPException(
            422, detail=f'session_type must be one of {list(ADAPTIVE_SESSION_TYPES)}')
    with _connect() as conn:
        result = adaptive.assemble_session(
            conn, user_id, body.session_type, slot_count=body.slot_count)
        first = None
        if result['selections']:
            first = student_item_payload(
                engine.fetch_student_item(conn, result['session_id'], 1))
        # Only 'daily_repair' has a canonical start event. targeted_drill /
        # missed_trap_review / timed_practice have no name in
        # ANALYTICS_EVENT_DICTIONARY_V1; minting one requires a ruling, so
        # nothing is emitted for them.
        if body.session_type == 'daily_repair':
            with _analytics_never_breaks_flow():
                analytics.emit(conn, 'daily_repair_started', user_id, {
                    'session_id': result['session_id'],
                    'planned_item_count': len(result['selections']),
                    'fallback_used': result['fallback_used'],
                })
    return {
        'session_id': result['session_id'],
        'planned_item_count': len(result['selections']),
        'fallback_used': result['fallback_used'],
        'first': first,
    }


# ---------------------------------------------------------------------------
# STUDENT_IDENTITY_V1 ruling 4: /dev/login is REGISTERED only in development
# with a local database. In any other configuration it is absent from the
# router — not a 403, not a 404 handler; never added.

def _dev_login_permitted() -> bool:
    if APP_ENV != 'development':
        return False
    try:
        assert_not_production(database_url())
    except Exception:
        return False
    return True


class DevLoginRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=128)


if _dev_login_permitted():
    @app.post('/dev/login')
    def dev_login(body: DevLoginRequest, response: Response) -> dict:
        user_id = body.user_id.strip()
        with _connect() as conn, conn.transaction():
            with conn.cursor() as cur:
                cur.execute(
                    'insert into student_profiles '
                    '(user_id, onboarding_status, created_at, updated_at) '
                    "values (%s, 'not_started', now(), now()) "
                    'on conflict (user_id) do nothing', (user_id,))
        response.set_cookie(
            COOKIE_NAME, issue_identity_cookie(user_id),
            httponly=True, samesite='lax')
        return {'user_id': user_id}
