// Adaptive selection-log contracts — TS mirror of schemas/item_selected_schema.json
// and schemas/session_assembled_schema.json (Spec 04 §18). Authored per
// PHASE_07_CONFORMANCE_V1 D7-4: the factory's batch_selection_log carries
// source_question_number (a FORBIDDEN_IN_APP_TABLES field) and must never be
// used as the runtime selection-log contract. These are the runtime contracts.

// The eight scored components, in Spec 04 §13 weight order. This ordered
// vocabulary is the single source for the component_scores keys; the Python
// runtime and scoringConstants.ts are drift-checked against it and the doc.
export const ADAPTIVE_COMPONENTS = [
  'target_match',
  'mastery_need',
  'due_review',
  'difficulty_fit',
  'freshness',
  'coverage_balance',
  'surface_variety',
  'eligibility_quality',
] as const;

export type AdaptiveComponent = typeof ADAPTIVE_COMPONENTS[number];

export type ComponentScores = Record<AdaptiveComponent, number>;

// Mirrors schemas/item_selected_schema.json field-for-field.
export interface ItemSelectedEvent {
  session_id: string;
  canonical_id: string;
  item_order: number; // 1-based
  adaptive_item_score: number;
  component_scores: ComponentScores;
  selection_reason: string;
  fallback_used: boolean;
}

// Mirrors schemas/session_assembled_schema.json field-for-field.
export interface SessionAssembledEvent {
  session_id: string;
  session_type: string;
  algorithm_version: string;
  seed: string | null;
  slot_count: number;
  fallback_used: boolean;
  assembled_at: string;
}
