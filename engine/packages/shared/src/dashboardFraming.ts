// Dashboard mastery framing (Phase 7 Step F, OPERATOR-RULED).
//
// The persisted/internal contract keeps the canonical raw bands
// (weak/developing/stable/mastered/new/decayed) — see MASTERY_CONTRACT_V1 and
// mastery.ts; those are NOT changed. The STUDENT-FACING dashboard must never
// show a raw band. It shows a framed label plus an evidence/confidence
// descriptor derived from attempt_count, so a "Focus area" backed by 1 attempt
// is visibly distinct from one backed by 12 (DIAGNOSTIC_MIX_V1's asymmetric
// single-observation reading, honored at the UI layer). These functions are
// pure; apps/web unit-tests assert the raw→framed and evidence→confidence
// mappings and that no raw band string ever leaves toStudentMasteryView.

import type { MasteryState, MasteryStatus } from './mastery';

export type MasteryFramedLabel =
  | 'Focus area'
  | 'Improving'
  | 'Solid'
  | 'Strong'
  | 'Not yet assessed';

export type MasteryConfidence =
  | 'limited evidence'
  | 'some evidence'
  | 'well-established';

// Centralized raw→framed mapping. 'decayed' is a reserved raw status no MVP
// path writes; if it ever appears it frames conservatively as a focus area
// (never leaks the raw word).
const FRAMED_LABELS: Record<MasteryStatus, MasteryFramedLabel> = {
  weak: 'Focus area',
  developing: 'Improving',
  stable: 'Solid',
  mastered: 'Strong',
  new: 'Not yet assessed',
  decayed: 'Focus area',
};

export function frameMasteryBand(status: MasteryStatus): MasteryFramedLabel {
  return FRAMED_LABELS[status];
}

// Evidence descriptor from attempt_count (MIN_EVID = 3 in the scorer; the same
// low-evidence threshold governs the UI's confidence wording).
export function masteryConfidence(attemptCount: number): MasteryConfidence {
  if (attemptCount < 3) return 'limited evidence';
  if (attemptCount < 5) return 'some evidence';
  return 'well-established';
}

export interface StudentMasteryView {
  dimension_type: string;
  dimension_id: string;
  label: MasteryFramedLabel;
  confidence: MasteryConfidence;
  attempt_count: number;
}

// The ONLY shape a student dashboard should render for a mastery dimension.
// By construction it carries the framed label + confidence and NEVER the raw
// band/score — those keys are not projected.
export function toStudentMasteryView(state: MasteryState): StudentMasteryView {
  return {
    dimension_type: state.dimension_type,
    dimension_id: state.dimension_id,
    label: frameMasteryBand(state.status),
    confidence: masteryConfidence(state.attempt_count),
    attempt_count: state.attempt_count,
  };
}
