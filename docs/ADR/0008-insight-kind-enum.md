# ADR-0008: Insight rows get a typed `kind` enum instead of a free-text `title`-based distinction

## Status
Accepted

## Context
Phase 1's `Insight.title` distinguished "Why Now" from "Counter-Argument" as
plain strings — functional, but not queryable/type-safe, and product brief
§19-20 (Phase 2) explicitly wants THESIS/COUNTERTHESIS/missing-data/
recommendation content distinguishable at the schema level, not just by
string-matching a display label.

## Decision
Add `InsightKind` enum (`WHY_NOW`, `COUNTER_ARGUMENT`, `THESIS`,
`COUNTERTHESIS`, `MISSING_DATA`, `RECOMMENDATION`) as a new required column
`insight.kind`. `title` is kept as the human-readable display label (so the
UI doesn't need an enum-to-Korean/English label map baked into two places),
but every query that needs to fetch "the counterthesis for this product"
filters on `kind`, not on `title == "Counter-Argument"`. Existing Phase 1
rows are backfilled by mapping their known titles
(`"Why Now" -> WHY_NOW`, `"Counter-Argument" -> COUNTER_ARGUMENT`) in the
migration.

This does **not** create separate tables per the brief's illustrative list
(`AI_HYPOTHESIS`, `AI_ANALYSIS`, `AI_FORECAST`, `AI_COUNTERARGUMENT`,
`AI_RECOMMENDATION`) — `insight.kind` plus the pre-existing
`is_ai_generated`/`ai_assisted_fields`/`ai_run_id` columns (ADR predates
this one — see DATA_MODEL.md §3) already give exactly this separation
without a proliferation of near-identical tables. `AI_FORECAST` gets its own
dedicated `forecast` table (ADR-0009) because a forecast has structurally
different fields (horizon, predicted_direction, calibration bookkeeping)
that don't fit the Insight shape.

## Consequences
- Positive: "does this product have a Thesis yet?" is a `WHERE kind =
  'THESIS'` query, not string matching against a display label that could
  be renamed.
- Positive: no schema explosion — one enum column reused across the
  Insight-shaped content types, a dedicated table only where the shape
  actually differs (Forecast).
- Negative: `title` and `kind` can theoretically drift (a THESIS insight
  titled something odd) — mitigated by `insight_builder.py` always setting
  both together from one lookup table, never independently.
