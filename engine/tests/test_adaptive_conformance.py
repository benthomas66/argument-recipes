"""Phase 7 conformance — PHASE_07_CONFORMANCE_V1 §4 + ADAPTIVE_SCORING_V1 §11.

DB-FREE, in the repo's established split: pure/static/schema proofs run in
pytest (CI has no Postgres); the live-Postgres end-to-end (assemble against the
real 199, determinism, Rule 1/2 on real content) is
scripts/diagnostic/verify_adaptive_live.py, run by the operator/auditor. Each
test names the check it satisfies.
"""
import inspect
import re
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts' / 'diagnostic'))

import adaptive_selection as asel  # noqa: E402
import scoring as sc  # noqa: E402
import mastery_engine as me  # noqa: E402


def _item(cid, **kw):
    base = {'canonical_id': cid, 'content_version': 1, 'question_type': 'FL',
            'normalized_recipe_id': 'R1', 'difficulty': 3, 'scenario': 's',
            'trap_families': ['Scope Failure'], 'elig_flags': 5}
    base.update(kw)
    return base


# --- §11 check 1 (Rule 1): pool is filtered BEFORE the scorer ---------------

def test_rule1_pool_query_filters_publication_and_eligibility_before_scoring():
    """The candidate query hard-filters published + validated + the mode flag;
    select_slots trusts that pre-filtered pool (never re-admits ineligible
    content). Static assertion on the query, mirroring how
    test_diagnostic_engine asserts the visibility predicate SQL."""
    src = inspect.getsource(asel.fetch_adaptive_candidates)
    assert "publication_state = 'published'" in src
    assert "content_state = 'validated'" in src
    assert '{flag}' in src and 'MODE_ELIGIBILITY_FLAG' in inspect.getsource(asel)
    # select_slots takes candidates as given — no publication/eligibility column
    # is even referenced inside it (the filter cannot live in the scorer).
    slots_src = inspect.getsource(asel.select_slots)
    for banned in ('publication_state', 'content_state', 'diagnostic_eligible',
                   'daily_repair_eligible'):
        assert banned not in slots_src


def test_mode_eligibility_flag_map_is_complete():
    # The five SESSION_TYPES (packages/shared/src/sessions.ts) each map to their
    # own eligibility flag; no mode falls through to another mode's pool.
    expected = {'diagnostic', 'daily_repair', 'targeted_drill',
                'missed_trap_review', 'timed_practice'}
    assert set(asel.MODE_ELIGIBILITY_FLAG) == expected
    assert asel.MODE_ELIGIBILITY_FLAG['daily_repair'] == 'daily_repair_eligible'
    assert asel.MODE_ELIGIBILITY_FLAG['missed_trap_review'] == 'review_eligible'


# --- §11 check 6/7 & §4 check 5/6: log shape, schema, weight vector ---------

def test_persisted_item_selected_event_validates_against_schema():
    """Every selection's wire payload (the 7 Spec 04 §18 fields) validates
    against schemas/item_selected_schema.json, including all 8 component_scores."""
    target = {'dimension': ('trap_family', 'Scope Failure'), 'trap_family': 'Scope Failure'}
    out = asel.select_slots(
        [_item(f'C{i}') for i in range(4)], targets=[target], slot_count=3,
        mastery_by_dim={('trap_family', 'Scope Failure'): {'mastery_score': 0.5, 'attempt_count': 5}},
        recent_by_cid={}, review_by_cid={}, seed='s')
    import json as _json
    schema = _json.loads(
        (ROOT / 'schemas' / 'item_selected_schema.json').read_text(encoding='utf-8'))
    validator = Draft202012Validator(schema)
    for s in out:
        event = {
            'session_id': 'adpt_test', 'canonical_id': s['canonical_id'],
            'item_order': s['item_order'],
            'adaptive_item_score': s['adaptive_item_score'],
            'component_scores': s['component_scores'],
            'selection_reason': s['selection_reason'],
            'fallback_used': s['fallback_used'],
        }
        errors = list(validator.iter_errors(event))
        assert not errors, '; '.join(e.message for e in errors)
        assert set(s['component_scores']) == set(sc.COMPONENT_ORDER)


def test_weight_vector_and_algorithm_version_registered():
    assert sc.ALGORITHM_VERSION == 'adaptive_scoring_v1'
    assert sc.WEIGHT_VECTOR == (30, 20, 15, 10, 10, 5, 5, 5)
    # the same version tags the assembled/selection rows the engine writes
    assert asel.ALGORITHM_VERSION == 'adaptive_scoring_v1'


# --- §4 check 5/6 & §11 check 6: batch schema is off-limits to app code -----

def test_no_app_code_imports_batch_selection_log_schema():
    """PHASE_07_CONFORMANCE_V1 D7-4: batch_selection_log_schema.json carries
    source_question_number (FORBIDDEN_IN_APP_TABLES). No app surface may load
    it. App surfaces = the API, the runtime engine, and shipped TS packages —
    NOT the content factory or tests."""
    app_dirs = [
        ROOT / 'scripts' / 'api',
        ROOT / 'scripts' / 'diagnostic',
        ROOT / 'packages' / 'shared' / 'src',
        ROOT / 'packages' / 'adaptive-engine' / 'src',
        ROOT / 'apps' / 'web' / 'src',
    ]
    # Target the SCHEMA the ban is about: loading it requires naming the file
    # (batch_selection_log_schema.json) or a symbol carrying that identifier.
    # Prose explaining WHY the factory log is off-limits (e.g. "the factory's
    # batch_selection_log carries source_question_number") is not a load and is
    # deliberately not matched.
    offenders = []
    for d in app_dirs:
        for p in d.rglob('*'):
            if p.suffix in ('.py', '.ts', '.tsx') and p.is_file():
                if 'batch_selection_log_schema' in p.read_text(encoding='utf-8'):
                    offenders.append(str(p.relative_to(ROOT)))
    assert not offenders, f'batch_selection_log_schema loaded by app code: {offenders}'


# --- §4 check 1: mastery_states recomputable from attempts + events ----------

def test_mastery_states_recomputable_from_attempts_and_events():
    """Spec 04 §4 recomputability: the stored score is reconstructable from the
    event log, and replaying the same attempts is deterministic (also validates
    the D7-1 mapping's 'auditable from events' claim)."""
    attempts = [
        {'is_correct': True, 'question_type': 'FL', 'normalized_recipe_id': 'R1',
         'selected_trap_family': 'N/A_correct', 'selected_trap_label': 'N/A_correct'},
        {'is_correct': False, 'question_type': 'FL', 'normalized_recipe_id': 'R1',
         'selected_trap_family': 'Scope Failure', 'selected_trap_label': 'x'},
        {'is_correct': False, 'question_type': 'FL', 'normalized_recipe_id': 'R1',
         'selected_trap_family': 'Scope Failure', 'selected_trap_label': 'y'},
    ]
    states, events = me.apply_updates(attempts)
    # replay is deterministic
    states2, _ = me.apply_updates(attempts)
    assert {k: v['score'] for k, v in states.items()} == \
           {k: v['score'] for k, v in states2.items()}
    # the recipe dimension's stored score == initial + chained event deltas
    key = ('recipe', 'R1')
    recipe_events = [e for e in events
                     if (e['dimension_type'], e['dimension_id']) == key]
    reconstructed = me.INITIAL
    for e in recipe_events:
        assert e['before_score'] == round(reconstructed, 10)
        reconstructed = e['after_score']
    assert round(reconstructed, 10) == round(states[key]['score'], 10)


def test_mastery_events_change_reason_never_decay():
    """§4 check 3: every mastery write's change_reason is in the five-value
    list and is never 'decay' (reserved)."""
    attempts = [
        {'is_correct': False, 'question_type': 'FL', 'normalized_recipe_id': 'R1',
         'selected_trap_family': 'Role Failure', 'selected_trap_label': 'z'},
    ]
    _states, events = me.apply_updates(attempts)
    allowed = {'correct', 'missed_trap', 'repeated_miss', 'review_success', 'decay'}
    for e in events:
        assert e['change_reason'] in allowed
        assert e['change_reason'] != 'decay'


# --- backlog #5 pin: selection_reason enum stays OPEN -----------------------

def test_selection_reason_enum_left_open():
    """The engine emits 'adaptive_selection' and 'foundational_instruction'.
    session_items.selection_reason must remain unconstrained (ENUM_CONSTRAINT_
    BACKLOG_V1 #5) — closing it here would conflict with Phase 3's
    'diagnostic_mix'. Assert no migration adds a CHECK on that column."""
    migrations = '\n'.join(
        p.read_text(encoding='utf-8')
        for p in sorted((ROOT / 'db' / 'migrations').glob('*.sql')))
    assert not re.search(
        r'session_items[\s\S]{0,200}?selection_reason[^\n,]*check', migrations, re.I), \
        'a CHECK was added to session_items.selection_reason (backlog #5 must stay open)'
    assert asel.REASON_ADAPTIVE == 'adaptive_selection'
    assert asel.REASON_FOUNDATIONAL == 'foundational_instruction'
