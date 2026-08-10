"""ADAPTIVE_SCORING_V1 §0.5 — the four hard rules, the tiering, and the
end-to-end assembly pipeline. This is the Phase 7 replacement for the
sessionBuilder MVP placeholder, generalizing scripts/diagnostic/selection.py's
visibility filtering and following mastery_engine.py's I/O patterns rather than
inventing a parallel path.

Layering (mirrors the diagnostic):
  * select_slots(...)   — PURE. Rules 1-pool-in/2/3/4 + score + tie-break, no I/O.
  * DB loaders + assemble_session(...) — the ONLY database code; reads
    content_items (never staging) through the Rule 1 publication/eligibility
    filter, loads mastery/recent-history/review context, runs select_slots,
    and persists sessions / session_items / item_selected / session_assembled.

Determinism (Spec 04 §19): identical (state, pool, algorithm_version, seed) →
byte-identical selection and logs. Tie-break: adaptive_item_score desc →
least-recently-seen (never-seen first) → seeded order (sha256 of
algorithm_version|seed|canonical_id).
"""
from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path

import scoring as sc

ROOT = Path(__file__).resolve().parents[2]

ALGORITHM_VERSION = sc.ALGORITHM_VERSION
TIER_EXACT_MIN = sc.C['tier_exact_min']
FOUNDATIONAL_THRESHOLD = sc.C['foundational_threshold']
FOUNDATIONAL_MIN_EVID = sc.C['foundational_min_evid']

_INF = float('inf')

# selection_reason strings this engine emits (session_items.selection_reason is
# an OPEN enum — ENUM_CONSTRAINT_BACKLOG_V1 #5 — so no CHECK constrains these;
# we deliberately do NOT close it, see the completion report).
REASON_ADAPTIVE = 'adaptive_selection'
REASON_FOUNDATIONAL = 'foundational_instruction'

MODE_ELIGIBILITY_FLAG = {
    'diagnostic': 'diagnostic_eligible',
    'daily_repair': 'daily_repair_eligible',
    'targeted_drill': 'targeted_drill_eligible',
    'missed_trap_review': 'review_eligible',
    'timed_practice': 'timed_eligible',
}


def _seed_key(seed: str | None, canonical_id: str) -> str:
    return hashlib.sha256(
        f'{ALGORITHM_VERSION}|{seed or ""}|{canonical_id}'.encode()).hexdigest()


def _target_mastery(target: dict, mastery_by_dim: dict) -> tuple[float, int]:
    """Mastery of the session TARGET dimension (session-target reading of §2/§4).
    Defaults to a mid, zero-evidence state when the slot has no dimension
    (generic/brand-new student): mastery_need then gates to 0."""
    dim = target.get('dimension')
    if dim is not None and dim in mastery_by_dim:
        m = mastery_by_dim[dim]
        return float(m['mastery_score']), int(m['attempt_count'])
    return 0.5, 0


def _components_for(item: dict, target: dict, mastery_by_dim: dict,
                    recent_by_cid: dict, review_by_cid: dict,
                    seen_qtype: dict, seen_scenario: dict, mode: str) -> dict:
    m_score, m_attempts = _target_mastery(target, mastery_by_dim)
    return {
        'target_match': sc.target_match(item, target),
        'mastery_need': sc.mastery_need(m_score, m_attempts),
        'due_review': sc.due_review(review_by_cid.get(item['canonical_id'])),
        'difficulty_fit': sc.difficulty_fit(item['difficulty'], m_score),
        'freshness': sc.freshness(recent_by_cid.get(item['canonical_id']), mode),
        'coverage_balance': sc.coverage_balance(seen_qtype.get(item['question_type'], 0)),
        'surface_variety': sc.surface_variety(seen_scenario.get(item.get('scenario'), 0)),
        'eligibility_quality': sc.eligibility_quality(item.get('elig_flags', 0)),
    }


def _matches_target_grain(item: dict, target: dict) -> bool:
    """Does the item exercise the target dimension (for Rule 4 scaffolding)?"""
    tf = target.get('trap_family')
    if tf and tf in set(item.get('trap_families') or ()):
        return True
    if target.get('recipe_id') and item.get('normalized_recipe_id') == target['recipe_id']:
        return True
    return False


def select_slots(candidates: list[dict], *, targets: list[dict], slot_count: int,
                 mastery_by_dim: dict, recent_by_cid: dict, review_by_cid: dict,
                 seed: str | None = None, mode: str = 'normal') -> list[dict]:
    """Fill slot_count slots. candidates are ALREADY Rule 1-filtered by the
    caller (published + validated + mode-eligible). Returns a list of
    selections, each: canonical_id, content_version, item_order,
    adaptive_item_score, component_scores, selection_reason, fallback_used,
    and _target (the slot's target, for session_items columns)."""
    if not targets:
        targets = [{}]
    selections: list[dict] = []
    chosen: set[str] = set()
    seen_qtype: dict[str, int] = {}
    seen_scenario: dict[str, int] = {}

    for slot in range(slot_count):
        target = targets[slot % len(targets)]

        # Rule 3: within-session dedupe (hard), unless redo.
        pool = [c for c in candidates
                if mode == 'redo' or c['canonical_id'] not in chosen]
        if not pool:
            break  # genuine exhaustion; caller logs a short session

        # Rule 4: very-low-mastery TARGET dimension routes to foundational,
        # removed from the ordinary scored pool for this slot.
        m_score, m_attempts = _target_mastery(target, mastery_by_dim)
        foundational = (target.get('dimension') is not None
                        and m_score < FOUNDATIONAL_THRESHOLD
                        and m_attempts >= FOUNDATIONAL_MIN_EVID)

        if foundational:
            # Scaffolded item: lowest-difficulty eligible item for the target
            # dimension; tie-break seeded. Fall back to lowest-difficulty in
            # pool if nothing matches the grain (slot still filled, routing
            # still recorded).
            matching = [c for c in pool if _matches_target_grain(c, target)]
            scaffolding = matching or pool
            pick = sorted(
                scaffolding,
                key=lambda c: (c['difficulty'], _seed_key(seed, c['canonical_id'])))[0]
            reason, fallback_used = REASON_FOUNDATIONAL, False
        else:
            # Score survivors (§1–§8).
            scored = []
            for c in pool:
                comps = _components_for(
                    c, target, mastery_by_dim, recent_by_cid, review_by_cid,
                    seen_qtype, seen_scenario, mode)
                scored.append((c, comps, sc.adaptive_item_score(comps),
                               comps['target_match']))
            # Rule 2: exact tier (target_match >= 0.85) before fallback tier.
            exact = [x for x in scored if x[3] >= TIER_EXACT_MIN]
            fallback = [x for x in scored if x[3] < TIER_EXACT_MIN]
            tier = exact if exact else fallback
            fallback_used = not exact  # a fallback-tier item was chosen
            # Tie-break: score desc -> least-recently-seen -> seeded order.
            tier.sort(key=lambda x: (
                -x[2],
                -(recent_by_cid.get(x[0]['canonical_id']) or _INF),
                _seed_key(seed, x[0]['canonical_id'])))
            pick = tier[0][0]
            reason = REASON_ADAPTIVE

        comps = _components_for(
            pick, target, mastery_by_dim, recent_by_cid, review_by_cid,
            seen_qtype, seen_scenario, mode)
        selections.append({
            'canonical_id': pick['canonical_id'],
            'content_version': pick['content_version'],
            'item_order': len(selections) + 1,
            'adaptive_item_score': sc.adaptive_item_score(comps),
            'component_scores': comps,
            'selection_reason': reason,
            'fallback_used': fallback_used,
            '_target': target,
        })
        chosen.add(pick['canonical_id'])
        seen_qtype[pick['question_type']] = seen_qtype.get(pick['question_type'], 0) + 1
        sk = pick.get('scenario')
        seen_scenario[sk] = seen_scenario.get(sk, 0) + 1

    return selections


# ---------------------------------------------------------------------------
# Database layer — the ONLY I/O. content_items only; never staging.


def fetch_adaptive_candidates(conn, session_type: str) -> list[dict]:
    """Rule 1 pool: published + validated + this mode's eligibility flag.
    Generalizes selection.fetch_candidates to any session mode; does not
    weaken the publication gate (VISIBILITY_CONTRACT_V1)."""
    flag = MODE_ELIGIBILITY_FLAG[session_type]
    with conn.cursor() as cur:
        cur.execute(
            'select canonical_id, content_version, question_type, '
            '  normalized_recipe_id, difficulty, scenario, '
            '  (diagnostic_eligible::int + daily_repair_eligible::int + '
            '   targeted_drill_eligible::int + review_eligible::int + '
            '   timed_eligible::int) as elig_flags '
            'from content_items '
            "where publication_state = 'published' and content_state = 'validated' "
            f'and {flag} = true',
            ())
        rows = [{'canonical_id': r[0], 'content_version': r[1],
                 'question_type': r[2], 'normalized_recipe_id': r[3],
                 'difficulty': r[4], 'scenario': r[5], 'elig_flags': r[6]}
                for r in cur.fetchall()]
        # trap_families exercised by each item's wrong-choice explanations.
        cur.execute(
            'select canonical_id, content_version, trap_family '
            'from content_explanations '
            "where explanation_role = 'wrong' and trap_family <> 'N/A_correct'",
            ())
        fams: dict[tuple, set] = {}
        for cid, ver, fam in cur.fetchall():
            fams.setdefault((cid, ver), set()).add(fam)
    for row in rows:
        row['trap_families'] = sorted(
            fams.get((row['canonical_id'], row['content_version']), set()))
    return rows


def load_mastery(conn, user_id: str) -> dict:
    with conn.cursor() as cur:
        cur.execute(
            'select dimension_type, dimension_id, mastery_score, attempt_count '
            'from mastery_states where user_id = %s', (user_id,))
        return {(dt, di): {'mastery_score': float(ms), 'attempt_count': int(ac)}
                for dt, di, ms, ac in cur.fetchall()}


def load_recent_history(conn, user_id: str) -> dict:
    """days_since_seen per canonical_id from prior attempts (cross-session)."""
    with conn.cursor() as cur:
        cur.execute(
            'select canonical_id, '
            '  extract(epoch from (now() - max(submitted_at))) / 86400.0 '
            'from attempts where user_id = %s group by canonical_id', (user_id,))
        return {cid: float(days) for cid, days in cur.fetchall()}


def load_due_reviews(conn, user_id: str) -> dict:
    """days_since_due per canonical_id from queued review obligations."""
    with conn.cursor() as cur:
        cur.execute(
            'select canonical_id, '
            '  extract(epoch from (now() - due_at)) / 86400.0 '
            'from learning_queues '
            "where user_id = %s and status = 'queued'", (user_id,))
        return {cid: float(days) for cid, days in cur.fetchall()}


def derive_targets(mastery_by_dim: dict) -> list[dict]:
    """MVP target policy: the student's ranked weaknesses (lowest mastery
    first) among trap_family and recipe dimensions with any evidence. Empty ->
    a single generic target (scoring runs on the non-target components)."""
    weak = sorted(
        ((dim, m) for dim, m in mastery_by_dim.items()
         if dim[0] in ('trap_family', 'recipe') and m['attempt_count'] >= 1),
        key=lambda kv: (kv[1]['mastery_score'], kv[0][0], kv[0][1]))
    targets = []
    for (dt, di), _m in weak:
        if dt == 'trap_family':
            targets.append({'dimension': (dt, di), 'trap_family': di})
        else:
            targets.append({'dimension': (dt, di), 'recipe_id': di})
    return targets or [{}]


def assemble_session(conn, user_id: str, session_type: str = 'daily_repair', *,
                     slot_count: int = 10, seed: str | None = None,
                     mode: str = 'normal') -> dict:
    """Assemble and persist an adaptive session. Writes sessions,
    session_items, item_selected (one per selection), and session_assembled.
    Returns {session_id, planned_item_count, selections, fallback_used}."""
    candidates = fetch_adaptive_candidates(conn, session_type)
    mastery_by_dim = load_mastery(conn, user_id)
    recent = load_recent_history(conn, user_id)
    reviews = load_due_reviews(conn, user_id)

    if session_type == 'daily_repair':
        # Phase 5 slot-plan LAYER: Spec 04 §9's structured mix, each segment
        # with its own rule, reusing select_slots per segment.
        import daily_repair as dr
        selections = dr.plan_daily_repair(
            candidates, mastery_by_dim=mastery_by_dim, recent_by_cid=recent,
            review_by_cid=reviews, seed=seed, mode=mode)
        planned = dr.MIX_TOTAL
    else:
        targets = derive_targets(mastery_by_dim)
        selections = select_slots(
            candidates, targets=targets, slot_count=slot_count,
            mastery_by_dim=mastery_by_dim, recent_by_cid=recent,
            review_by_cid=reviews, seed=seed, mode=mode)
        planned = slot_count

    session_id = f'adpt_{uuid.uuid4()}'
    now = _now_iso()
    any_fallback = any(s['fallback_used'] for s in selections)

    schema = _load_schema('item_selected_schema.json')
    sess_schema = _load_schema('session_assembled_schema.json')

    with conn.transaction():
        with conn.cursor() as cur:
            cur.execute(
                'insert into sessions (session_id, user_id, session_type, '
                'status, started_at, planned_item_count, selection_policy) '
                'values (%s, %s, %s, %s, %s, %s, %s)',
                (session_id, user_id, session_type, 'active', now,
                 planned, ALGORITHM_VERSION))
            for s in selections:
                target = s['_target']
                target_recipe = target.get('recipe_id')
                target_family = target.get('trap_family')
                cur.execute(
                    'insert into session_items (session_id, position, '
                    'canonical_id, content_version, selection_reason, '
                    'target_recipe_id, target_trap_family) '
                    'values (%s, %s, %s, %s, %s, %s, %s)',
                    (session_id, s['item_order'], s['canonical_id'],
                     s['content_version'], s['selection_reason'],
                     target_recipe, target_family))
                # Validate the Spec 04 §18 event payload (exactly the 7 wire
                # fields) BEFORE persisting; extra DB columns are separate.
                event = {
                    'session_id': session_id,
                    'canonical_id': s['canonical_id'],
                    'item_order': s['item_order'],
                    'adaptive_item_score': s['adaptive_item_score'],
                    'component_scores': s['component_scores'],
                    'selection_reason': s['selection_reason'],
                    'fallback_used': s['fallback_used'],
                }
                _validate(schema, event, 'item_selected')
                cur.execute(
                    'insert into item_selected (session_id, canonical_id, '
                    'content_version, item_order, adaptive_item_score, '
                    'component_scores, selection_reason, fallback_used, '
                    'created_at) values (%s, %s, %s, %s, %s, %s, %s, %s, %s)',
                    (session_id, s['canonical_id'], s['content_version'],
                     s['item_order'], s['adaptive_item_score'],
                     json.dumps(s['component_scores']), s['selection_reason'],
                     s['fallback_used'], now))
            assembled = {
                'session_id': session_id, 'session_type': session_type,
                'algorithm_version': ALGORITHM_VERSION, 'seed': seed,
                'slot_count': len(selections), 'fallback_used': any_fallback,
                'assembled_at': now,
            }
            _validate(sess_schema, assembled, 'session_assembled')
            cur.execute(
                'insert into session_assembled (session_id, session_type, '
                'algorithm_version, seed, slot_count, fallback_used, '
                'assembled_at) values (%s, %s, %s, %s, %s, %s, %s)',
                (session_id, session_type, ALGORITHM_VERSION, seed,
                 len(selections), any_fallback, now))

    return {'session_id': session_id, 'planned_item_count': planned,
            'selections': selections, 'fallback_used': any_fallback}


# ---------------------------------------------------------------------------
# small helpers (kept local; the diagnostic uses equivalents)


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _iso_plus_days(when: str, days: int) -> str:
    """ISO timestamp `days` after `when` (an ISO string). Used to set due_at at
    enqueue so the value validated against learning_queue_schema.json is exactly
    the value inserted."""
    from datetime import datetime, timedelta
    return (datetime.fromisoformat(when) + timedelta(days=int(days))).isoformat()


_SCHEMA_CACHE: dict = {}


def _load_schema(name: str) -> dict:
    if name not in _SCHEMA_CACHE:
        _SCHEMA_CACHE[name] = json.loads(
            (ROOT / 'schemas' / name).read_text(encoding='utf-8'))
    return _SCHEMA_CACHE[name]


def _validate(schema: dict, payload: dict, label: str) -> None:
    from jsonschema import Draft202012Validator
    errors = list(Draft202012Validator(schema).iter_errors(payload))
    if errors:
        raise ValueError(
            f'{label} payload failed schema: '
            + '; '.join(e.message for e in errors))


# ---------------------------------------------------------------------------
# Phase 5 — session completion for adaptive (non-diagnostic) sessions.
# Reuses the diagnostic's mastery path (run_diagnostic.persist_mastery +
# mastery_engine.apply_updates) and adds review-obligation scheduling.

_REVIEW_INTERVALS = json.loads(
    (ROOT / 'schemas' / 'mastery_contract_constants.json').read_text(
        encoding='utf-8'))['review_intervals_days']  # [1, 3, 7, 21]
_REVIEW_TOP_STAGE = len(_REVIEW_INTERVALS) - 1  # 3 (the 21-day interval)

# Correct answers carry this sentinel in both trap fields (run_diagnostic
# writes it; the 0007 NOT NULL + CHECKs enforce it). Enqueue skips it.
TRAP_SENTINEL = 'N/A_correct'

# Phase 6 — missed-trap review priority weights (tunable; documented).
_RP = json.loads(
    (ROOT / 'schemas' / 'review_priority_constants.json').read_text(
        encoding='utf-8'))
W_MASTERY = _RP['w_mastery']          # weight on (1 - trap_family_mastery)
W_RECENCY = _RP['w_recency']          # weight on the recent-miss signal
RECENT_MISS_CAP = _RP['recent_miss_cap']  # normalizer for the recent-miss count


def _advance_reviews(cur, user_id: str, attempts: list[dict], when: str) -> int:
    """Advance/reset queued review obligations for the attempted items
    (reviewScheduler logic: stage 1→3→7→21, correct advances one stage capped
    at the top, incorrect resets to stage 0). Returns the count updated.
    Enqueuing NEW obligations on fresh misses is Phase 6's job (out of scope)."""
    correct_by_cid = {a['canonical_id']: bool(a['is_correct']) for a in attempts}
    if not correct_by_cid:
        return 0
    cur.execute(
        'select queue_id, canonical_id, review_stage from learning_queues '
        "where user_id = %s and status = 'queued' and canonical_id = any(%s)",
        (user_id, list(correct_by_cid)))
    rows = cur.fetchall()
    top = len(_REVIEW_INTERVALS) - 1
    updated = 0
    for queue_id, cid, stage in rows:
        new_stage = min(int(stage) + 1, top) if correct_by_cid[cid] else 0
        cur.execute(
            'update learning_queues set review_stage = %s, '
            "due_at = %s::timestamptz + (%s || ' days')::interval "
            'where queue_id = %s',
            (new_stage, when, _REVIEW_INTERVALS[new_stage], queue_id))
        updated += 1
    return updated


def missed_trap_priority(trap_family_mastery: float, recent_miss_count: int) -> float:
    """Pure priority score for a missed-trap obligation (Spec 04 §11 / Step B):
    higher for lower trap-family mastery and higher recent-miss frequency.
        priority = W_MASTERY·(1 − mastery) + W_RECENCY·min(recent/CAP, 1)
    clamped to [0, 1]. Tunable via schemas/review_priority_constants.json."""
    signal = min(max(recent_miss_count, 0) / RECENT_MISS_CAP, 1.0)
    raw = W_MASTERY * (1.0 - trap_family_mastery) + W_RECENCY * signal
    return round(max(0.0, min(1.0, raw)), 10)


def _missed_trap_priority_db(cur, user_id: str, trap_family: str) -> float:
    """Resolve the inputs to missed_trap_priority from the DB: the current
    trap_family mastery (default 0.5 when unseen) and a recent-miss signal =
    the number of currently-queued missed_trap_review obligations for this
    family (a deterministic proxy for recent miss frequency)."""
    cur.execute(
        'select mastery_score from mastery_states where user_id = %s '
        "and dimension_type = 'trap_family' and dimension_id = %s",
        (user_id, trap_family))
    row = cur.fetchone()
    mastery = float(row[0]) if row else 0.5
    cur.execute(
        'select count(*) from learning_queues where user_id = %s '
        "and queue_type = 'missed_trap_review' and status = 'queued' "
        'and trap_family = %s', (user_id, trap_family))
    recent = int(cur.fetchone()[0])
    return missed_trap_priority(mastery, recent)


def _enqueue_missed_trap_reviews(cur, user_id: str, attempts: list[dict],
                                 when: str) -> int:
    """Spec 04 §90/§225: every genuine wrong answer creates OR updates a review
    obligation. For each wrong attempt with a real trap (not the N/A_correct
    sentinel): if a queued missed_trap_review already exists for
    (user, canonical_id, trap_label) reset it to stage 0 (cooldown — never stack
    a duplicate); otherwise INSERT a new obligation at stage 0 (due +1 day) with
    the full A1 contract + trap linkage (§204). Returns the count inserted.

    Runs AFTER _advance_reviews (which reset any existing obligation for a missed
    item to stage 0); the dedup below therefore refreshes rather than duplicates,
    so the two never double-handle a row. Idempotent per (user, cid, trap_label)."""
    schema = _load_schema('learning_queue_schema.json')
    due = _iso_plus_days(when, _REVIEW_INTERVALS[0])  # stage 0 == +1 day
    inserted = 0
    for a in attempts:
        if a['is_correct']:
            continue
        label, family = a['selected_trap_label'], a['selected_trap_family']
        if not label or not family or label == TRAP_SENTINEL or family == TRAP_SENTINEL:
            continue
        cid, cver = a['canonical_id'], int(a['content_version'])
        priority = _missed_trap_priority_db(cur, user_id, family)
        cur.execute(
            'select queue_id from learning_queues where user_id = %s '
            'and canonical_id = %s and trap_label = %s '
            "and queue_type = 'missed_trap_review' and status = 'queued'",
            (user_id, cid, label))
        existing = cur.fetchone()
        if existing:  # cooldown: refresh the existing obligation, do not stack
            cur.execute(
                'update learning_queues set review_stage = 0, due_at = %s, '
                'priority_score = %s where queue_id = %s',
                (due, priority, existing[0]))
            continue
        row = {
            'queue_id': f'rvw_{uuid.uuid4()}', 'user_id': user_id,
            'queue_type': 'missed_trap_review', 'canonical_id': cid,
            'content_version': cver, 'priority_score': priority, 'due_at': due,
            'reason_code': 'missed_trap', 'status': 'queued',
            'created_by_policy': ALGORITHM_VERSION,
        }
        _validate(schema, row, 'learning_queue')  # A1 contract before insert
        cur.execute(
            'insert into learning_queues (queue_id, user_id, queue_type, '
            'canonical_id, content_version, priority_score, due_at, reason_code, '
            'status, created_by_policy, review_stage, trap_label, trap_family, '
            'source_attempt_id, recipe_id) values '
            '(%(queue_id)s, %(user_id)s, %(queue_type)s, %(canonical_id)s, '
            '%(content_version)s, %(priority_score)s, %(due_at)s, %(reason_code)s, '
            '%(status)s, %(created_by_policy)s, 0, %(trap_label)s, %(trap_family)s, '
            '%(source_attempt_id)s, %(recipe_id)s)',
            {**row, 'trap_label': label, 'trap_family': family,
             'source_attempt_id': a.get('attempt_id'),
             'recipe_id': a.get('normalized_recipe_id')})
        inserted += 1
    return inserted


def _stabilize_reviews(cur, user_id: str, attempts: list[dict], when: str,
                       pre_stages: dict) -> int:
    """Terminal transition (Step D): an obligation that was ALREADY at the top
    (21-day) stage and is answered correctly has passed the longest interval —
    mark it status='completed' (stabilized) so it stops recurring. Uses the
    stage captured BEFORE _advance_reviews ran, so _advance_reviews' update logic
    is untouched. Returns the count stabilized."""
    correct_by_cid = {a['canonical_id']: bool(a['is_correct']) for a in attempts}
    stabilized = 0
    for queue_id, (cid, pre_stage) in pre_stages.items():
        if pre_stage == _REVIEW_TOP_STAGE and correct_by_cid.get(cid):
            cur.execute(
                "update learning_queues set status = 'completed', due_at = %s "
                'where queue_id = %s', (when, queue_id))
            stabilized += 1
    return stabilized


def _queued_stages_for_attempts(cur, user_id: str, attempts: list[dict]) -> dict:
    """Snapshot {queue_id: (canonical_id, review_stage)} for queued obligations
    on the attempted items, taken BEFORE advance/stabilize run."""
    cids = list({a['canonical_id'] for a in attempts})
    if not cids:
        return {}
    cur.execute(
        'select queue_id, canonical_id, review_stage from learning_queues '
        "where user_id = %s and status = 'queued' and canonical_id = any(%s)",
        (user_id, cids))
    return {qid: (cid, int(stage)) for qid, cid, stage in cur.fetchall()}


def mastery_profile(conn, user_id: str) -> dict:
    """Dashboard read — the student's framed mastery profile, split by the two
    dimensions a student can act on: trap_family and recipe.

    THIN BY CONTRACT: it SELECTs persisted mastery_states and maps each row
    through the existing framing (label + confidence). It performs no mastery
    calculation, no write, no selection, and adds no schema. The raw band and
    mastery_score are never projected (framing.to_student_mastery_view omits
    them by construction). Scoped to one user by the caller's identity.
    """
    import framing
    with conn.cursor() as cur:
        cur.execute(
            'select dimension_type, dimension_id, status, attempt_count '
            'from mastery_states '
            "where user_id = %s and dimension_type in ('trap_family', 'recipe') "
            'order by dimension_type, dimension_id', (user_id,))
        rows = cur.fetchall()
    views = [framing.to_student_mastery_view(dt, di, st, int(ac))
             for dt, di, st, ac in rows]
    return {
        'user_id': user_id,
        'trap_families': [v for v in views if v['dimension_type'] == 'trap_family'],
        'recipes': [v for v in views if v['dimension_type'] == 'recipe'],
    }


def missed_trap_profile(conn, user_id: str) -> dict:
    """Step C — redacted profile view of standing missed-trap obligations. Per
    trap_family: the count of OPEN (queued) obligations plus a FRAMED status +
    confidence (reuses framing; never a raw band or mastery_score)."""
    import framing
    with conn.cursor() as cur:
        cur.execute(
            'select lq.trap_family, count(*), '
            '  coalesce(ms.status, %s), coalesce(ms.attempt_count, 0) '
            'from learning_queues lq '
            'left join mastery_states ms on ms.user_id = lq.user_id '
            "  and ms.dimension_type = 'trap_family' "
            '  and ms.dimension_id = lq.trap_family '
            "where lq.user_id = %s and lq.queue_type = 'missed_trap_review' "
            "  and lq.status = 'queued' and lq.trap_family is not null "
            'group by lq.trap_family, ms.status, ms.attempt_count '
            'order by count(*) desc, lq.trap_family', ('new', user_id))
        rows = cur.fetchall()
    traps = [
        {'trap_family': fam, 'open_obligations': int(n),
         **framing.to_student_mastery_view('trap_family', fam, status, int(ac))}
        for fam, n, status, ac in rows]
    return {'user_id': user_id, 'missed_traps': traps}


def finalize_adaptive_session(conn, session_id: str) -> dict:
    """Complete a non-diagnostic session: update mastery (continuing from the
    student's current scores), advance review obligations, mark the session
    completed, and return a REDACTED completion summary (framed labels only).
    Refuses a partial session (load_session_attempts enforces completeness)."""
    import run_diagnostic as rd
    import mastery_engine as me
    import framing

    user_id, attempts = rd.load_session_attempts(conn, session_id)

    # Continuation seed: prior SCORE per dimension, attempt_count 0 (so the
    # additive upsert accumulates the true total). New dimensions start at
    # INITIAL by falling through to apply_updates' default.
    current = load_mastery(conn, user_id)
    initial = {dim: {'score': m['mastery_score'], 'attempt_count': 0,
                     'recent': [], 'status': 'new'}
               for dim, m in current.items()}
    states, events = me.apply_updates(attempts, initial_states=initial)
    # Seeded-but-untouched dimensions carry no update this session; persist only
    # the ones actually exercised (apply_updates stamps recent_accuracy on those).
    states = {k: v for k, v in states.items() if 'recent_accuracy' in v}

    # Net movement direction per dimension (sign only — no score exposed).
    net: dict[tuple, float] = {}
    for ev in events:
        key = (ev['dimension_type'], ev['dimension_id'])
        net[key] = net.get(key, 0.0) + (ev['after_score'] - ev['before_score'])

    finished = rd.now_iso()
    with conn.transaction():
        with conn.cursor() as cur:
            rd.persist_mastery(cur, user_id, states, events, finished)
            # Snapshot stages BEFORE advancing so the stabilize check reads the
            # pre-attempt stage without touching _advance_reviews' logic.
            pre_stages = _queued_stages_for_attempts(cur, user_id, attempts)
            reviews_updated = _advance_reviews(cur, user_id, attempts, finished)
            reviews_stabilized = _stabilize_reviews(
                cur, user_id, attempts, finished, pre_stages)
            reviews_enqueued = _enqueue_missed_trap_reviews(
                cur, user_id, attempts, finished)
            cur.execute(
                "update sessions set status = 'completed', completed_at = %s, "
                'actual_item_count = %s where session_id = %s',
                (finished, len(attempts), session_id))

    return _build_summary(conn, session_id, attempts, states, net,
                          reviews_updated, framing,
                          reviews_enqueued=reviews_enqueued,
                          reviews_stabilized=reviews_stabilized)


def _build_summary(conn, session_id, attempts, states, net, reviews_updated,
                   framing, reviews_enqueued=0, reviews_stabilized=0) -> dict:
    """Redacted completion summary: counts, per-slot breakdown, and mastery
    movement as FRAMED labels + confidence + direction. No raw band or
    mastery_score appears (same guarantee as the dashboard)."""
    correct = sum(1 for a in attempts if a['is_correct'])
    with conn.cursor() as cur:
        cur.execute(
            'select selection_reason, count(*) from session_items '
            'where session_id = %s group by selection_reason', (session_id,))
        per_slot = {r[0]: int(r[1]) for r in cur.fetchall()}
        # accumulated status + attempt_count per touched dimension (post-persist)
        touched = set(states.keys())
        acc: dict[tuple, dict] = {}
        if touched:
            cur.execute(
                'select dimension_type, dimension_id, status, attempt_count '
                'from mastery_states where user_id = ('
                '  select user_id from sessions where session_id = %s)',
                (session_id,))
            for dt, di, status, ac in cur.fetchall():
                if (dt, di) in touched:
                    acc[(dt, di)] = {'status': status, 'attempt_count': int(ac)}

    movement = []
    for key in touched:
        a = acc.get(key)
        if a is None:
            continue
        delta = net.get(key, 0.0)
        direction = ('improved' if delta > 0 else
                     'declined' if delta < 0 else 'unchanged')
        movement.append(framing.to_student_mastery_view(
            key[0], key[1], a['status'], a['attempt_count'], direction))

    return {
        'session_id': session_id,
        'session_type': 'daily_repair',
        'items_attempted': len(attempts),
        'correct': correct,
        'incorrect': len(attempts) - correct,
        'per_slot': per_slot,
        'reviews_updated': reviews_updated,
        'reviews_enqueued': reviews_enqueued,
        'reviews_stabilized': reviews_stabilized,
        'mastery_movement': movement,
    }
