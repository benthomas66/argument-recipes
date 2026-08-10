# ADAPTIVE_SCORING_V1

**Status:** canonical, operator-approved (shapes + four hard rules). Resolves `PHASE_07_CONFORMANCE_V1` D7-5 — the eight component scoring functions and the selection architecture around them. Constants are tunable against beta attempt data; the **shapes and the §0.5 hard rules are fixed** and change only under a new `algorithm_version`.

Selection runs under `algorithm_version = adaptive_scoring_v1`. All scoring is deterministic; `component_scores` in the `item_selected` log (Spec 04 §18) fully explains every selection.

---

## 0. What Spec 04 fixes vs what this document fixes

**Fixed by Spec 04 §13 (not re-decided) — the weight vector:**
```
adaptive_item_score =
   30·target_match  + 20·mastery_need + 15·due_review + 10·difficulty_fit
 + 10·freshness     +  5·coverage_balance + 5·surface_variety + 5·eligibility_quality
```
Each component ∈ 0.0–1.0. Ties break by score → least-recently-seen → seeded order (Spec 04 §19).

**Fixed by this document:** (a) the four **hard rules / routing branches** that run *around* the scorer (§0.5), and (b) the eight component **shapes** (§1–§8). Design stance: sophistication lives in the shapes (non-linear where the pedagogy is non-linear; saturating where more evidence should stop mattering; asymmetric where over/undershoot differ) and in the hard gates — not in constants. Every literal is a named tunable.

---

## 0.5 HARD RULES AND ROUTING (operator-mandated; run before/around scoring)

These four rules are **not** components and are **not** weighted. They are gates, tiers, and routing branches that constrain the candidate pool and the selection procedure. They take precedence over any component score. This is the correct place for eligibility, duplication, and remediation logic — encoding them as soft weights (as an earlier draft did) is wrong, because a hard constraint must never be overcome by scoring margin.

### Rule 1 — Eligibility and publication are hard pre-filters, never scored preferences.
The candidate pool is built **before** scoring by filtering to items that satisfy ALL of:
- `publication_state = 'published'` AND `content_state = 'validated'`, AND
- the current session mode's eligibility flag is true (`diagnostic_eligible` / `daily_repair_eligible` / `targeted_drill_eligible` / `review_eligible` / `timed_eligible`).

Nothing failing these ever reaches the scorer. This physically enforces the A5 visibility contract (`VISIBILITY_CONTRACT_V1`) — the adaptive engine cannot surface non-published or mode-ineligible content by any scoring path. Consequently `eligibility_quality_score` (§8) only rewards *breadth* among already-eligible survivors; its "ineligible" branch is unreachable by construction.

### Rule 2 — Exact-target candidates are selected before fallback candidates (tiered, not merely higher-scored).
Selection is **tiered**, implementing Spec 04 §9's ordered fallback ladder as tiers rather than as a weighted nudge:
- **Exact tier** = candidates matching the session target at trap-family grain OR same-recipe grain (`target_match_score ≥ TIER_EXACT_MIN`, i.e. the 1.00 and 0.85 bands of §1).
- **Fallback tier** = everything below (same question-type, same difficulty band, general).

The engine fills a slot from the **exact tier first**, ranked by full `adaptive_item_score`. It descends to the fallback tier only when the exact tier is empty or cannot fill the slot. `fallback_used = true` is logged in `item_selected` **exactly when** a fallback-tier item is chosen. This is strictly stronger than scoring order: a high-need overdue fallback item cannot preempt an available exact-target item.
- `TIER_EXACT_MIN = 0.85`.

### Rule 3 — Same-session duplicates are hard-excluded (unless explicit redo mode).
Any item already selected earlier in the **current session** is removed from the candidate pool for all remaining slots, regardless of score — unless the session is in explicit `redo` mode. This is a hard within-session exclusion, distinct from the cross-session `freshness_score` (§5), which remains a soft recovery curve. (Cross-session, a recently-seen item is penalized but selectable at the 0.1 floor when the pool is genuinely exhausted; within-session, it is simply gone.)

### Rule 4 — Very low mastery routes to foundational instruction / scaffolded practice, not a low adaptive score.
When a dimension the session targets is at very low mastery **with enough evidence to trust it** —
`mastery_score < FOUNDATIONAL_THRESHOLD` AND `attempt_count ≥ FOUNDATIONAL_MIN_EVID` —
the correct response is not to down-weight that dimension's items (which would leave a genuinely-lost student with nothing on their biggest weakness). Instead the dimension is **routed to a foundational path**:
- serve the recipe's `repair_lesson` (foundational instruction — the field exists in `recipes`), and/or
- fill the slot with a **scaffolded item**: the lowest-difficulty eligible item for that dimension, preferentially in a warmup slot (Daily Repair already reserves 2 warmup slots per Spec 04 §9 / Phase 5).

Above the threshold, the §2 `mastery_need` Gaussian governs normally. Below it, the dimension does not compete in the ordinary adaptive pool for that slot; it is served instructionally/scaffolded and flagged with `selection_reason = 'foundational_instruction'`.
- `FOUNDATIONAL_THRESHOLD = 0.20`, `FOUNDATIONAL_MIN_EVID = 2`.

**Build dependencies for Rule 4 (flagged, not invented here):**
- `session_items.selection_reason` must gain the value `foundational_instruction`. That column's enum is deliberately open until Phase 3/5 build (`ENUM_CONSTRAINT_BACKLOG_V1` #5); this value is added when that list is closed. Until then the engine may set the reason string but no CHECK enforces it.
- Whether the foundational slot renders the `repair_lesson` (instructional card) vs a scaffolded item is a Phase 5 session-assembly / Phase 4 explanation-surface decision; this document fixes the *routing trigger and target selection*, not the render.

### Rule precedence
Pool construction order: **Rule 1** (eligibility/publication filter) → **Rule 3** (drop same-session dupes) → **Rule 4** (route very-low-mastery dimensions to the foundational path, removing them from the ordinary pool for that slot) → **Rule 2** (tier the remaining candidates exact-before-fallback) → score survivors by §1–§8 → tie-break (Spec 04 §19).

---

## 1. `target_match_score` — weight 30

*Spec §277: how directly the item matches the session target (trap, recipe, question type, or review obligation).*

Graded match over the target's grain hierarchy (not binary — the grades ARE the §9 fallback ladder, made auditable in the log and used to draw the Rule 2 tier boundary):
```
target_match_score = max over the target's applicable grains of:
    exact_trap_family_match   → TM_TRAP  = 1.00
    same_recipe               → TM_RECIPE= 0.85
    same_question_type        → TM_QTYPE = 0.55
    same_difficulty_band_only → TM_BAND  = 0.25
    no relation               → 0.00
(a review-obligation target matches on its (canonical_id | trap_family) at 1.00)
```
The exact tier (Rule 2) is `≥ 0.85` — i.e. trap-family or same-recipe. Wide gaps ensure an exact match dominates when one exists.

## 2. `mastery_need_score` — weight 20  (the key pedagogical shape)

*Spec §278: higher when the student is weak/developing in the relevant trap or recipe.*

Desirable-difficulty curve — need **peaks in the developing band** and tapers at both extremes. (A `1 − mastery_score` ramp is wrong at both ends: it wastes drills near 0 and never stops near 1. Note the very-low end is handled by Rule 4, not by this curve.)
```
m = mastery_score (0–1)
raw_need = exp( −((m − PEAK)²) / (2·WIDTH²) )          # Gaussian, peaks at m = PEAK
mastery_need_score = raw_need · min(1, attempt_count / MIN_EVID)
```
- `PEAK = 0.45`, `WIDTH = 0.22`, `MIN_EVID = 3` (evidence gate — one attempt shouldn't scream "drill this"; this is Spec 04 §7's low-evidence uncertainty idea applied to selection).

## 3. `due_review_score` — weight 15

*Spec §279: higher when a review obligation is due or overdue.*

Reads `learning_queues.review_stage` (index into `REVIEW_INTERVALS_DAYS = [1,3,7,21]`) and `due_at`. Zero before due; steps above zero at due; climbs while overdue; **saturates** so ancient obligations can't infinitely dominate.
```
d = now − due_at, in days      (negative = not yet due)
if d < 0:  due_review_score = 0
else:      due_review_score = min(1, OVERDUE_FLOOR + (1−OVERDUE_FLOOR)·(d / OVERDUE_SAT))
```
- `OVERDUE_FLOOR = 0.60`, `OVERDUE_SAT = 7` days.

## 4. `difficulty_fit_score` — weight 10  (Spec 04 §12 safety rails live here)

*Spec §280: higher when item difficulty matches the student's current band.*

Asymmetric window centered slightly **above** current ability (desirable difficulty); tolerant of "a bit too hard," less tolerant of "too easy." The §12 rail against reactive difficulty swings is enforced in how `lvl` updates (slow, multi-attempt — see §9 dep 1), not here.
```
lvl = student difficulty band for this dimension on the 1–5 scale (see §9 dep 1)
delta = item_difficulty − (lvl + STRETCH)             # positive = harder than target
if delta >= 0:  difficulty_fit_score = exp( −(delta²)/(2·HARD_TOL²) )
else:           difficulty_fit_score = exp( −(delta²)/(2·EASY_TOL²) )
```
- `STRETCH = 0.5`, `HARD_TOL = 1.1`, `EASY_TOL = 0.7`.

## 5. `freshness_score` — weight 10

*Spec §281: penalizes recently seen items unless in explicit redo/review mode.* (Cross-session only; same-session duplication is Rule 3's hard exclusion.)

Recovery curve — 1 for never-seen/redo/review, dropping sharply after exposure, recovering with time; floor keeps a repeat selectable only under genuine pool exhaustion.
```
if mode ∈ {redo, review} or never seen:  freshness_score = 1
else:
    g = now − last_seen_at, in days
    freshness_score = 1 − FRESH_DEPTH · exp( −g / FRESH_RECOVER )
```
- `FRESH_DEPTH = 0.9` (just-seen ≈ 0.1), `FRESH_RECOVER = 5` days.

## 6. `coverage_balance_score` — weight 5

*Spec §282: healthy variety across question types and recipes.* Session-context signal.
```
seen = count in current session of this item's question_type
coverage_balance_score = 1 / (1 + COV_SATURATION · seen)
```
- `COV_SATURATION = 0.8`.

## 7. `surface_variety_score` — weight 5

*Spec §283: avoids same scenario/domain clustering.* Reads the item's **`scenario`** field (confirmed present in `generated_items` and the FULL200 bank — ships live).
```
seen_domain = count in current session sharing this item's scenario
surface_variety_score = 1 / (1 + VAR_SATURATION · seen_domain)
```
- `VAR_SATURATION = 1.0` (stronger than coverage — domain repetition is more salient to a student than type repetition).

## 8. `eligibility_quality_score` — weight 5

*Spec §284: rewards eligibility flags.* Per Rule 1 the pool is already all-eligible, so this rewards **breadth** only (broad eligibility ≈ content that cleared more QA gates — a mild quality proxy).
```
breadth = (number of eligibility flags set) / 5
eligibility_quality_score = clamp_0_1( ELIG_BASE + ELIG_BREADTH·breadth )
```
- `ELIG_BASE = 0.85`, `ELIG_BREADTH = 0.15`. (Set `ELIG_BREADTH = 0` to make it a pure constant if preferred.)

---

## 9. Dependencies (verified against the repo)

1. **`difficulty_fit` needs a per-dimension band `lvl` (1–5).** MVP mapping: `lvl = 1 + 4·mastery_score` (linear), defined in the constants block. The §12 "gradual" rail is satisfied because `lvl` moves only as `mastery_score` moves (already multi-attempt-smoothed). **[operator-approved: linear map]**
2. **`surface_variety` needs a scenario tag — VERIFIED PRESENT** (`generated_items.scenario`, and column 15 of the FULL200 bank). Ships live; no degradation path needed.
3. **Rule 4 foundational target — VERIFIED PRESENT** (`recipes.repair_lesson` seeded; Daily Repair reserves 2 warmup slots). Build dependency: `session_items.selection_reason` gains `foundational_instruction` when its open enum is closed at Phase 3/5 build (`ENUM_CONSTRAINT_BACKLOG_V1` #5).
4. **Session context** (already-selected set, per-student recent-item history) must be passed into the scorer/pool-builder. Function-signature requirement for the Phase 7 implementer; no data-model change.

---

## 10. Constant registry (tunable under `algorithm_version = adaptive_scoring_v1`)

| Constant | Value | Component / rule |
|---|---|---|
| `TIER_EXACT_MIN` | 0.85 | Rule 2 tier boundary |
| `FOUNDATIONAL_THRESHOLD` | 0.20 | Rule 4 trigger |
| `FOUNDATIONAL_MIN_EVID` | 2 | Rule 4 evidence gate |
| `TM_TRAP / TM_RECIPE / TM_QTYPE / TM_BAND` | 1.00 / 0.85 / 0.55 / 0.25 | §1 |
| `PEAK / WIDTH / MIN_EVID` | 0.45 / 0.22 / 3 | §2 |
| `OVERDUE_FLOOR / OVERDUE_SAT` | 0.60 / 7d | §3 |
| `STRETCH / HARD_TOL / EASY_TOL` | 0.5 / 1.1 / 0.7 | §4 |
| `FRESH_DEPTH / FRESH_RECOVER` | 0.9 / 5d | §5 |
| `COV_SATURATION` | 0.8 | §6 |
| `VAR_SATURATION` | 1.0 | §7 |
| `ELIG_BASE / ELIG_BREADTH` | 0.85 / 0.15 | §8 |
| `LEVEL_MAP` | `1 + 4·mastery_score` | §9 dep 1 |
| weight vector | 30/20/15/10/10/5/5/5 | Spec 04 §13 (fixed, not tunable) |

**Tuning stance:** these are principled first estimates, calibrated against real attempt data during beta. Shapes + the §0.5 hard rules are fixed under this `algorithm_version`; constants move. Changing a shape or a hard rule requires a new algorithm_version and a conformance re-check per `PHASE_07_CONFORMANCE_V1` §4.

---

## 11. Conformance checks (Phase 7 implementer must satisfy)

Extends `PHASE_07_CONFORMANCE_V1` §4 with the §0.5 rules:
1. No item with `publication_state ≠ 'published'` or `content_state ≠ 'validated'` or a false mode-eligibility flag is ever scored (Rule 1). Assert the pool-builder filters before the scorer runs.
2. Given an available exact-tier candidate, the engine never selects a fallback-tier item for that slot, even when the fallback item's `adaptive_item_score` is higher (Rule 2). `fallback_used` is true iff a fallback-tier item is chosen.
3. No item appears twice in one session unless `mode = redo` (Rule 3).
4. A dimension at `mastery_score < 0.20` with `attempt_count ≥ 2` is served via the foundational path (`selection_reason = 'foundational_instruction'`), not the ordinary scored pool, for its slot (Rule 4).
5. Selection is byte-identical across two runs with identical state, pool, `algorithm_version`, and seed (Spec 04 §19).
6. Every selection writes `item_selected` with all eight `component_scores` and the correct `selection_reason`/`fallback_used`; no app code imports `batch_selection_log_schema.json`.
7. The implemented weight vector equals Spec 04 §13's (30,20,15,10,10,5,5,5) and is registered under `algorithm_version = adaptive_scoring_v1`.
