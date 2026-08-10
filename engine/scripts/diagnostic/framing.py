"""Server-side mastery framing — the Python mirror of
packages/shared/src/dashboardFraming.ts (Phase 7 Step F).

The Daily Repair completion summary is built server-side (Python), so the
raw→framed and evidence→confidence mappings must exist here too, exactly as the
scorer exists in both Python and TS. Same guarantee: a student-facing payload
carries the FRAMED label + confidence and NEVER a raw band or mastery_score.
tests/test_daily_repair.py asserts the label/confidence strings match the TS
file (drift tripwire).
"""
from __future__ import annotations

# raw MasteryStatus -> student-facing label (mirrors FRAMED_LABELS in the TS).
FRAMED_LABELS = {
    'weak': 'Focus area',
    'developing': 'Improving',
    'stable': 'Solid',
    'mastered': 'Strong',
    'new': 'Not yet assessed',
    'decayed': 'Focus area',  # reserved; frames conservatively, never leaks the word
}


def frame_mastery_band(status: str) -> str:
    return FRAMED_LABELS[status]


def mastery_confidence(attempt_count: int) -> str:
    if attempt_count < 3:
        return 'limited evidence'
    if attempt_count < 5:
        return 'some evidence'
    return 'well-established'


def to_student_mastery_view(dimension_type: str, dimension_id: str,
                            status: str, attempt_count: int,
                            direction: str | None = None) -> dict:
    """The only shape a student-facing surface should carry for a dimension:
    framed label + confidence (+ optional movement direction). By construction
    it omits the raw band and mastery_score."""
    view = {
        'dimension_type': dimension_type,
        'dimension_id': dimension_id,
        'label': frame_mastery_band(status),
        'confidence': mastery_confidence(attempt_count),
        'attempt_count': attempt_count,
    }
    if direction is not None:
        view['direction'] = direction
    return view
