"""Phase 7 constant-drift tripwire — the same discipline as
test_mastery_contract.py, applied to ADAPTIVE_SCORING_V1.

Three layers must agree: the machine-readable JSON the Python runtime reads,
the TS mirror the contract/frontend layer reads, and the literals written in
ADAPTIVE_SCORING_V1.md §10. Drift in any one fails here. If this fails, fix
the layers to agree — do not weaken the test.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONSTANTS_JSON = ROOT / 'schemas' / 'adaptive_scoring_constants.json'
CONSTANTS_TS = ROOT / 'packages' / 'adaptive-engine' / 'src' / 'scoringConstants.ts'
DOC = ROOT / 'docs' / 'patches' / 'ADAPTIVE_SCORING_V1.md'
SELECTION_TS = ROOT / 'packages' / 'shared' / 'src' / 'selection.ts'

EXPECTED = {
    'algorithm_version': 'adaptive_scoring_v1',
    'weights': {
        'target_match': 30, 'mastery_need': 20, 'due_review': 15,
        'difficulty_fit': 10, 'freshness': 10, 'coverage_balance': 5,
        'surface_variety': 5, 'eligibility_quality': 5,
    },
    'tier_exact_min': 0.85,
    'foundational_threshold': 0.20,
    'foundational_min_evid': 2,
    'tm_trap': 1.00, 'tm_recipe': 0.85, 'tm_qtype': 0.55, 'tm_band': 0.25,
    'peak': 0.45, 'width': 0.22, 'min_evid': 3,
    'overdue_floor': 0.60, 'overdue_sat': 7,
    'stretch': 0.5, 'hard_tol': 1.1, 'easy_tol': 0.7,
    'fresh_depth': 0.9, 'fresh_recover': 5,
    'cov_saturation': 0.8, 'var_saturation': 1.0,
    'elig_base': 0.85, 'elig_breadth': 0.15,
    'level_map_intercept': 1, 'level_map_slope': 4,
}

# The eight components in Spec 04 §13 weight order (the canonical ordering).
COMPONENT_ORDER = [
    'target_match', 'mastery_need', 'due_review', 'difficulty_fit',
    'freshness', 'coverage_balance', 'surface_variety', 'eligibility_quality',
]
WEIGHT_VECTOR = [30, 20, 15, 10, 10, 5, 5, 5]


def test_constants_json_matches_contract():
    constants = json.loads(CONSTANTS_JSON.read_text(encoding='utf-8'))
    assert constants == EXPECTED


def test_ts_mirror_contains_every_constant_literal():
    ts = CONSTANTS_TS.read_text(encoding='utf-8')
    assert "ADAPTIVE_ALGORITHM_VERSION = 'adaptive_scoring_v1'" in ts
    # weight vector present in order
    for comp, w in zip(COMPONENT_ORDER, WEIGHT_VECTOR):
        assert re.search(rf'{comp}:\s*{w}\b', ts), f'weight {comp}:{w} missing from TS'
    for token, literal in [
        ('TIER_EXACT_MIN', '0.85'), ('FOUNDATIONAL_THRESHOLD', '0.2'),
        ('FOUNDATIONAL_MIN_EVID', '2'), ('TM_TRAP', '1.0'), ('TM_RECIPE', '0.85'),
        ('TM_QTYPE', '0.55'), ('TM_BAND', '0.25'), ('PEAK', '0.45'),
        ('WIDTH', '0.22'), ('MIN_EVID', '3'), ('OVERDUE_FLOOR', '0.6'),
        ('OVERDUE_SAT', '7'), ('STRETCH', '0.5'), ('HARD_TOL', '1.1'),
        ('EASY_TOL', '0.7'), ('FRESH_DEPTH', '0.9'), ('FRESH_RECOVER', '5'),
        ('COV_SATURATION', '0.8'), ('VAR_SATURATION', '1.0'),
        ('ELIG_BASE', '0.85'), ('ELIG_BREADTH', '0.15'),
        ('LEVEL_MAP_INTERCEPT', '1'), ('LEVEL_MAP_SLOPE', '4'),
    ]:
        assert re.search(rf'{token}\s*=\s*{re.escape(literal)}\b', ts), \
            f'{token} = {literal} missing from scoringConstants.ts'


def test_doc_declares_the_same_literals():
    doc = DOC.read_text(encoding='utf-8')
    for literal in [
        'TIER_EXACT_MIN', 'FOUNDATIONAL_THRESHOLD', 'FOUNDATIONAL_MIN_EVID',
        'PEAK', 'WIDTH', 'MIN_EVID', 'OVERDUE_FLOOR', 'OVERDUE_SAT',
        'STRETCH', 'HARD_TOL', 'EASY_TOL', 'FRESH_DEPTH', 'FRESH_RECOVER',
        'COV_SATURATION', 'VAR_SATURATION', 'ELIG_BASE', 'ELIG_BREADTH',
    ]:
        assert literal in doc, f'{literal} missing from ADAPTIVE_SCORING_V1.md'
    assert 'adaptive_scoring_v1' in doc
    # the fixed weight vector appears in the doc
    assert '30·target_match' in doc and '20·mastery_need' in doc


def test_component_vocabulary_single_sourced_in_selection_ts():
    ts = SELECTION_TS.read_text(encoding='utf-8')
    block = ts.split('ADAPTIVE_COMPONENTS')[1].split(']')[0]
    for comp in COMPONENT_ORDER:
        assert f"'{comp}'" in block, f'{comp} missing from ADAPTIVE_COMPONENTS'
