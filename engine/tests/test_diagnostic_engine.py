"""Phase 3a diagnostic engine tests — pure core, no database.

Covers: mix constants equal the DIAGNOSTIC_MIX_V1 artifact; the eight-category
question-type map; deterministic seeded selection (identical for one user,
varying across users, exact mix histogram every time); ordering rules;
loud empty-cell failure; the visibility predicate built from the matrix as
SQL; the D3-4 sentinel; mastery deltas equal the contract constants; the
4-vs-5 dimension-list split; the asymmetric reading rule; the attempt payload
validating against student_attempt_schema.json; and the backlog-#5 pin that
session_items.selection_reason remains unconstrained.

The database-side proofs (trap_label rejected by mastery_events, accepted by
diagnostic_results_by_dimension; staging never selectable) run against live
Postgres in the verification script — same split as Phases 1 and 2.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts' / 'diagnostic'))

import mix  # noqa: E402
import selection  # noqa: E402
import mastery_engine as me  # noqa: E402


# ---------------------------------------------------------------------------
# The mix artifact


def test_mix_constants_equal_the_artifact():
    """DIAGNOSTIC_MIX_V1.md §3 is the controlling artifact; the code constant
    must transcribe it exactly. Drift in either direction fails here."""
    assert mix.parse_mix_artifact() == mix.MIX


def test_mix_is_fifteen_cells_with_the_documented_shape():
    cs = mix.cells()
    assert len(cs) == 15
    assert Counter(d for _, d in cs) == {2: 3, 3: 8, 4: 4}
    assert all(d not in (1, 5) for _, d in cs)


def test_category_map_covers_exactly_the_twelve_pool_types():
    covered = [qt for qts in mix.CATEGORY_QUESTION_TYPES.values() for qt in qts]
    assert len(covered) == len(set(covered)) == 12
    assert set(mix.EXCLUDED_QUESTION_TYPES) == {'PR', 'PI', 'RP', 'EV'}
    assert not set(covered) & set(mix.EXCLUDED_QUESTION_TYPES)
    for qt in mix.EXCLUDED_QUESTION_TYPES:
        assert mix.category_for_question_type(qt) is None


def test_single_item_categories_are_sa_and_parallel():
    assert set(mix.SINGLE_ITEM_CATEGORIES) == {
        'Sufficient Assumption', 'Parallel/Parallel Flaw'}


# ---------------------------------------------------------------------------
# Selection


def synthetic_candidates(per_cell: int = 3) -> list[dict]:
    out, i = [], 0
    for cat, difficulties in mix.MIX.items():
        qts = mix.CATEGORY_QUESTION_TYPES[cat]
        for d in difficulties:
            for k in range(per_cell):
                i += 1
                out.append({'canonical_id': f'SYN_{i:04d}',
                            'content_version': 1,
                            'question_type': qts[k % len(qts)],
                            'difficulty': d})
    return out


def test_selection_100_users_exact_histogram_every_time():
    cands = synthetic_candidates()
    expected = Counter(mix.cells())
    for i in range(100):
        items = selection.select_diagnostic(f'user_{i}', cands)
        assert len(items) == 15
        assert Counter((it['category'], it['difficulty']) for it in items) == expected


def test_selection_is_deterministic_per_user_and_varies_across_users():
    cands = synthetic_candidates()
    draws = {}
    for i in range(100):
        uid = f'user_{i}'
        a = [it['canonical_id'] for it in selection.select_diagnostic(uid, cands)]
        b = [it['canonical_id'] for it in selection.select_diagnostic(uid, cands)]
        assert a == b, 'same user must always receive the identical diagnostic'
        draws[uid] = tuple(a)
    assert len(set(draws.values())) > 1, 'selection must not be a constant'


def test_ordering_first_is_difficulty_two_and_never_parallel():
    cands = synthetic_candidates()
    for i in range(100):
        items = selection.select_diagnostic(f'user_{i}', cands)
        assert items[0]['position'] == 1
        assert items[0]['difficulty'] == 2
        assert items[0]['category'] != 'Parallel/Parallel Flaw'
        assert [it['position'] for it in items] == list(range(1, 16))


def test_empty_cell_fails_loudly_naming_the_cell():
    cands = [c for c in synthetic_candidates()
             if not (c['question_type'] == 'SA' and c['difficulty'] == 3)]
    with pytest.raises(selection.EmptyCellError) as e:
        selection.select_diagnostic('user_x', cands)
    assert e.value.category == 'Sufficient Assumption'
    assert e.value.difficulty == 3
    assert 'Sufficient Assumption' in str(e.value)


def test_excluded_types_never_enter_a_cell():
    cands = synthetic_candidates()
    cands.append({'canonical_id': 'SYN_EV', 'content_version': 1,
                  'question_type': 'EV', 'difficulty': 3})
    for i in range(20):
        items = selection.select_diagnostic(f'user_{i}', cands)
        assert all(it['canonical_id'] != 'SYN_EV' for it in items)


def test_no_duplicate_items_within_a_draw():
    cands = synthetic_candidates()
    for i in range(20):
        ids = [it['canonical_id']
               for it in selection.select_diagnostic(f'user_{i}', cands)]
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# Visibility predicate


def test_visibility_predicate_is_sql_built_from_the_matrix():
    sql, params = selection.visibility_predicate('internal_beta')
    assert 'content_state = any(' in sql
    assert 'publication_state = any(' in sql
    assert 'diagnostic_eligible = true' in sql
    assert params['visible_content_states'] == ['validated']
    assert set(params['visible_publication_states']) == {'published', 'unpublished'}
    assert 'staging' not in sql


def test_default_visibility_mode_is_most_restrictive():
    assert selection.DEFAULT_VISIBILITY_MODE == 'production_student'
    _, params = selection.visibility_predicate('production_student')
    assert params['visible_publication_states'] == ['published']


def test_unknown_visibility_mode_refuses():
    with pytest.raises(ValueError):
        selection.visibility_predicate('factory_import_typo')


# ---------------------------------------------------------------------------
# Mastery math (MASTERY_CONTRACT_V1 via mastery_contract_constants.json)


def _attempt(is_correct, qt='FL', recipe='FLAW_CLASSIC',
             family='Scope Failure', label='artest_label'):
    return {'is_correct': is_correct, 'question_type': qt,
            'normalized_recipe_id': recipe,
            'selected_trap_family': 'N/A_correct' if is_correct else family,
            'selected_trap_label': 'N/A_correct' if is_correct else label}


def test_deltas_match_the_contract_constants_exactly():
    constants = json.loads(
        (ROOT / 'schemas' / 'mastery_contract_constants.json').read_text())
    ups = me.mastery_updates_for_attempt(_attempt(True))
    assert {(u['dimension_type'], u['delta']) for u in ups} == {
        ('recipe', constants['correct_delta']),
        ('question_type', constants['correct_delta'])}
    downs = me.mastery_updates_for_attempt(_attempt(False))
    assert {(u['dimension_type'], u['delta']) for u in downs} == {
        ('recipe', constants['wrong_recipe_delta']),
        ('trap_family', constants['wrong_trap_delta'])}


def test_updates_use_only_the_four_mastery_dimensions_and_never_decay():
    for correct in (True, False):
        for u in me.mastery_updates_for_attempt(_attempt(correct)):
            assert u['dimension_type'] in me.MASTERY_DIMENSIONS
            assert u['dimension_type'] != 'trap_label'
            assert u['change_reason'] in ('correct', 'missed_trap')


def test_scores_start_at_initial_and_clamp():
    states, _ = me.apply_updates([_attempt(False)] * 20)
    trap = states[('trap_family', 'Scope Failure')]
    assert trap['score'] == 0.0  # clamped
    states, _ = me.apply_updates([_attempt(True)] * 20)
    recipe = states[('recipe', 'FLAW_CLASSIC')]
    assert recipe['score'] == 1.0  # clamped
    one, _ = me.apply_updates([_attempt(True)])
    assert one[('recipe', 'FLAW_CLASSIC')]['score'] == pytest.approx(0.56)


def test_mastered_is_unreachable_in_a_fifteen_item_diagnostic():
    """Contract gate: mastered needs score >= 0.85; from 0.50 at +0.06 that is
    six correct on ONE dimension — but a diagnostic serves each recipe at most
    a handful of times and each question_type at most 3. Simulate the most
    favorable case: all 15 correct, all same recipe (impossible in the real
    mix, still must not reach mastered per-question_type)."""
    attempts = [_attempt(True, qt=q) for q in
                ['FL'] * 3 + ['ST'] * 2 + ['WK'] * 2 + ['NA'] * 2 +
                ['SA'] + ['MC'] * 2 + ['MBT'] * 2 + ['PA']]
    states, _ = me.apply_updates(attempts)
    for (dt, di), st in states.items():
        if dt == 'question_type':
            assert st['status'] != 'mastered'


def test_one_event_per_update_with_before_after():
    _, events = me.apply_updates([_attempt(True), _attempt(False)])
    assert len(events) == 4
    for ev in events:
        assert ev['change_reason'] != 'decay'
        assert 0.0 <= ev['after_score'] <= 1.0


def test_wrong_attempt_with_sentinel_family_is_a_programming_error():
    bad = _attempt(False)
    bad['selected_trap_family'] = 'N/A_correct'
    with pytest.raises(AssertionError):
        me.mastery_updates_for_attempt(bad)


# ---------------------------------------------------------------------------
# Diagnostic dimension rows + asymmetry


CATEGORY_BY_QT = {qt: cat for cat, qts in mix.CATEGORY_QUESTION_TYPES.items()
                  for qt in qts}


def test_dimension_rows_may_carry_trap_label_but_mastery_never_does():
    attempts = [_attempt(False)]
    rows = me.diagnostic_dimension_rows(attempts)
    assert any(r['dimension_type'] == 'trap_label' for r in rows)
    states, events = me.apply_updates(attempts)
    assert all(dt != 'trap_label' for dt, _ in states)
    assert all(ev['dimension_type'] != 'trap_label' for ev in events)


def test_asymmetry_missed_single_item_category_is_ranked():
    attempts = [_attempt(False, qt='SA', recipe='SA_RECIPE')]
    rows = me.diagnostic_dimension_rows(attempts)
    me.apply_priority_ranks(rows, CATEGORY_BY_QT)
    sa = next(r for r in rows if r['dimension_type'] == 'question_type'
              and r['dimension_id'] == 'SA')
    assert sa['priority_rank'] is not None
    assert 'flagged for repair' in sa['interpretation_text']


def test_asymmetry_hit_single_item_category_is_unranked():
    attempts = [_attempt(True, qt='SA', recipe='SA_RECIPE'),
                _attempt(False, qt='FL')]
    rows = me.diagnostic_dimension_rows(attempts)
    me.apply_priority_ranks(rows, CATEGORY_BY_QT)
    sa = next(r for r in rows if r['dimension_type'] == 'question_type'
              and r['dimension_id'] == 'SA')
    assert sa['priority_rank'] is None
    assert 'certifies nothing' in sa['interpretation_text']
    fl = next(r for r in rows if r['dimension_type'] == 'question_type'
              and r['dimension_id'] == 'FL')
    assert fl['priority_rank'] is not None


def test_multi_item_hit_categories_are_simply_unranked_without_commentary():
    rows = me.diagnostic_dimension_rows([_attempt(True, qt='FL')])
    me.apply_priority_ranks(rows, CATEGORY_BY_QT)
    fl = next(r for r in rows if r['dimension_id'] == 'FL')
    assert fl['priority_rank'] is None and fl['interpretation_text'] is None


# ---------------------------------------------------------------------------
# Attempt payload (D3-4 sentinel + schema)


def test_correct_attempt_payload_carries_the_sentinel_and_validates():
    schema = json.loads(
        (ROOT / 'schemas' / 'student_attempt_schema.json').read_text())
    attempt = {
        'attempt_id': 'att_x', 'user_id': 'u1', 'canonical_id': 'AR_V1_B1_0001',
        'content_version': 1, 'session_id': 's1', 'session_type': 'diagnostic',
        'selected_answer': 'C', 'correct_answer_at_attempt': 'C',
        'is_correct': True,
        'selected_trap_label': 'N/A_correct',      # D3-4: sentinel, not null
        'selected_trap_family': 'N/A_correct',
        'response_time_ms': 41000, 'confidence_self_report': 'not_collected',
        'submitted_at': '2026-07-10T00:00:00Z', 'scoring_context': {},
    }
    errors = list(Draft202012Validator(schema).iter_errors(attempt))
    assert not errors, [e.message for e in errors]
    assert attempt['selected_trap_label'] is not None
    assert attempt['selected_trap_family'] is not None


# ---------------------------------------------------------------------------
# Backlog-#5 pin


def test_selection_reason_remains_unconstrained_in_every_migration():
    """Hard rule: session_items.selection_reason stays unconstrained (Spec 03
    §9.2 is open-ended; closing it is a Phase 3b+ product decision). This
    task, and any future one, fails here if it adds a CHECK."""
    ddl = '\n'.join(p.read_text(encoding='utf-8')
                    for p in sorted((ROOT / 'db' / 'migrations').glob('*.sql')))
    assert not re.search(r'check \(selection_reason in', ddl, re.I)
    assert not re.search(
        r'add constraint \S*selection_reason', ddl, re.I)


# ---------------------------------------------------------------------------
# Patch A: build_attempt_payload — the D3-4 sentinel, enforced by a test that
# touches the REAL builder (not a hand-built dict)


def _payload(selected, correct='C', label='too_strong', family='Scope Failure'):
    import run_diagnostic as rd
    return rd.build_attempt_payload(
        attempt_id='att_t', user_id='u1', canonical_id='AR_V1_B1_0001',
        content_version=1, session_id='s1', position=1, selected=selected,
        correct_answer=correct, choice_trap_label=label,
        choice_trap_family=family, response_time_ms=1000, confidence=None,
        submitted_at='2026-07-10T00:00:00Z')


def test_builder_correct_attempt_writes_the_sentinel_in_both_fields():
    p = _payload(selected='C')
    assert p['is_correct'] is True
    assert p['selected_trap_label'] == 'N/A_correct'
    assert p['selected_trap_family'] == 'N/A_correct'
    assert p['selected_trap_label'] is not None
    assert p['selected_trap_family'] is not None


def test_builder_wrong_attempt_carries_the_distractors_real_values():
    p = _payload(selected='B')
    assert p['is_correct'] is False
    assert p['selected_trap_label'] == 'too_strong'
    assert p['selected_trap_family'] == 'Scope Failure'


def test_builder_can_never_emit_none_in_either_trap_field():
    import run_diagnostic as rd
    with pytest.raises(rd.DiagnosticError) as e:
        _payload(selected='B', label=None, family=None)
    assert e.value.code == 'TRAP_FIELDS_NULL'
    with pytest.raises(rd.DiagnosticError):
        _payload(selected='B', family=None)


def test_builder_output_validates_against_the_tightened_schema():
    schema = json.loads(
        (ROOT / 'schemas' / 'student_attempt_schema.json').read_text())
    for selected in ('C', 'B'):
        errors = list(Draft202012Validator(schema).iter_errors(_payload(selected)))
        assert not errors, [e.message for e in errors]


def test_schema_rejects_null_trap_fields():
    schema = json.loads(
        (ROOT / 'schemas' / 'student_attempt_schema.json').read_text())
    p = _payload(selected='C')
    for field in ('selected_trap_label', 'selected_trap_family'):
        assert list(Draft202012Validator(schema).iter_errors({**p, field: None}))
