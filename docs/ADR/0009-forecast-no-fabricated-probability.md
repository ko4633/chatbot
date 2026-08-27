# ADR-0009: Forecast direction is qualitative until real calibration data exists; probability is never LLM-invented

## Status
Accepted

## Context
Product brief §22-23 is explicit and non-negotiable: an LLM must never emit
a number like "73% success probability" when there is no historical sample
to calibrate against — a confident-looking number with no statistical basis
is worse than no number (exactly CLAUDE.md's "do not hide uncertainty" and
"a missing value is UNKNOWN, never a plausible-looking guess"). Phase 1 has
zero historical Opportunity outcomes to calibrate against (no
`UserDecision` has had time to play out).

## Decision
- New `forecast` table: `forecast_created_at`, `forecast_horizon_days`,
  `predicted_direction` (enum `BULLISH`/`NEUTRAL`/`BEARISH`),
  `predicted_probability` (nullable numeric — **NULL for every Phase 2
  forecast**, reserved for a future calibrated model), `confidence_tier`
  (enum `LOW`/`MEDIUM`/`HIGH`), `is_calibrated` (boolean, hardcoded `False`
  in Phase 2), `model` (`"deterministic.v1"` — not an LLM in Phase 2, see
  below), `evidence` (jsonb), `product_id`, `analysis_run_id`,
  `actual_outcome`/`evaluated_at` (nullable, populated by a future Phase 2+
  evaluation job once enough time has passed).
- `predicted_direction` and `confidence_tier` in Phase 2 are computed by a
  **deterministic** function (`packages/scoring/forecast.py`) over existing
  signals already in `Opportunity.sub_scores` (trend, margin, competition) —
  not by calling `packages/ai`. This keeps forecasting inside the same
  "deterministic where possible" boundary as margin/opportunity scoring
  (docs/AI_POLICY.md §3), and sidesteps the exact failure mode this ADR
  exists to prevent: there is no path by which an LLM could emit a fake
  probability, because no LLM is in the direction-classification loop at
  all in Phase 2.
- The API/UI must render `is_calibrated=False` forecasts with the literal
  string **"Not statistically calibrated"** next to them (brief §22) —
  enforced as a required field in the response schema, not an optional
  caveat that's easy to omit.

## Consequences
- Positive: structurally impossible to regress into "LLM invents a
  probability" — Phase 2's forecast path has no AI call in it.
- Positive: the schema (`predicted_probability`, `actual_outcome`,
  `evaluated_at`) is ready for Phase 3+ to compute real Brier
  score/calibration error once enough `UserDecision` + outcome history
  exists, without a schema migration at that point.
- Negative: Phase 2's "forecast" is a simple heuristic (BULLISH/NEUTRAL/
  BEARISH from existing sub-scores), not a real predictive model — this is
  intentional and disclosed, not a hidden limitation.
