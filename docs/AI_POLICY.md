# OMNIS — AI Usage Policy

## 1. The rule

AI is a tool for language and judgment-assist tasks. AI never decides what is
true in the database, and AI never does arithmetic that code can do
deterministically.

## 2. Allowed uses

- Japanese/Korean product name interpretation and normalization
- Product attribute extraction from unstructured text
- Category classification
- Relationship analysis between candidate entities (Stage 7 match assist only)
- Article/review summarization
- Unstructured-data structuring
- Opportunity narrative ("Why Now") generation
- Counter-argument generation ("why this might be a bad idea")
- Multi-source research synthesis (Phase 5)
- Uncertainty analysis / explaining what's missing

## 3. Forbidden or minimized uses

Never delegate to AI, because these are deterministic and an LLM is strictly
worse at them than code, with no offsetting benefit:

- FX conversion, price/fee/margin calculation, ratios, score arithmetic,
  date/time arithmetic, deterministic-identifier comparison, sorting/ranking
  by a numeric field.
- **Forecast probability (Phase 2)**: an LLM must never generate a number
  like "73% success probability" — there is no sample size or calibration
  behind such a number, and a fabricated one is worse than no forecast at
  all. `packages/scoring/forecast.py::classify_forecast_direction` produces
  only a qualitative `BULLISH`/`NEUTRAL`/`BEARISH` label plus a
  `LOW`/`MEDIUM`/`HIGH` confidence tier, from a measured score/margin delta
  between two real opportunity recomputes — never an LLM call.
  `Forecast.predicted_probability` is hardcoded `None` and
  `Forecast.is_calibrated` is hardcoded `False` at every call site; the UI
  must display "Not statistically calibrated" alongside the label. The
  schema (`forecast_horizon_days`, `predicted_probability`, `evidence`,
  `actual_outcome`, `evaluated_at`) is deliberately shaped so a real
  calibration pass (Brier score, hit rate) can be added later without a
  migration — see ADR-0009 and DATA_MODEL.md `forecast`.

`packages/scoring` has no dependency on `packages/ai` — this is enforced by
not importing it, checked in code review, and would show up immediately as a
layering violation if attempted.

## 4. Where AI output is allowed to live

Only tables/columns explicitly designed to hold it:

- `entity_match` when `match_stage = LLM_JUDGE` (capped at `LIKELY`, never `EXACT`)
- `insight.narrative` (`is_ai_generated=true`, `ai_assisted_fields` lists which fields)
- `opportunity`'s narrative fields only (never `opportunity_score`,
  `confidence_score`, or `sub_scores` values themselves)
- `product_variant.embedding` (a vector is not a "claim", it's a coordinate;
  still recorded via `ai_run_id` on the write that produced it)

`price_observation`, `inventory_observation`, `review_observation`,
`demand_observation` structurally cannot carry AI provenance fields (see
DATA_MODEL.md §3) — there is no column to put an `ai_run_id` even if someone
tried, by construction, not just convention.

## 5. Entity resolution and AI (detail)

Stage 7 (LLM Judge) only runs when Stages 1-6 returned `INCONCLUSIVE`. Its
maximum possible output is `LIKELY`, never `EXACT` — `EXACT` is reserved for
a deterministic identifier match (JAN/EAN/UPC/GTIN/ISBN/MPN/model number
equality), because an LLM asserting certainty about product identity is
exactly the failure mode this system is built to avoid (false-positive merges
are the highest-blast-radius bug in the whole system — see
`docs/EVALUATION.md` §Golden Dataset). A `LIKELY` from Stage 7 still merges
into a canonical `Product` (the product brief permits `LIKELY` to merge), but
`entity_match.evidence` records that the deciding stage was `LLM_JUDGE` so
this is filterable/auditable/reversible separately from deterministic merges.

## 6. AI provider architecture

See ARCHITECTURE.md §3. One interface (`AIProvider`), swappable adapters
(`AnthropicProvider`, `NullAIProvider`). No call site outside `packages/ai`
imports a vendor SDK.

`NullAIProvider` (used whenever `AI_ENABLED=false` or no API key is
configured) is not a stub that returns empty strings silently — every result
it returns is explicitly tagged so downstream code and the UI can show
"AI unavailable" rather than mistaking silence for "nothing found":

- `generate`/`reason` → result text is the literal marker
  `AI_DISABLED: <deterministic fallback text>` when a deterministic fallback
  exists (e.g. a templated Insight narrative built from the same facts a
  human would read), or raises `AIDisabledError` when no safe fallback exists.
- `classify`/`extract` → returns `UNKNOWN`/empty structure with
  `ai_dependency=False`.
- `embed` → raises `EmbeddingUnavailable`; callers must treat this as "stage
  skipped", never as "no match".

The backend and worker must boot and serve all non-AI functionality with no
key configured (§52 of the product brief). This is verified by an integration
test that boots the app with `AI_ENABLED=false` and runs the full ingest →
match → score pipeline end to end.

## 7. Cost tracking

Every `AIProvider` call, through every adapter including `NullAIProvider`
(which records `status=DISABLED`, zero cost), produces exactly one `ai_run`
row before the result is returned to the caller. This happens in the base
adapter wrapper, not in each adapter implementation, so it cannot be
forgotten by a new provider. See DATA_MODEL.md `ai_run`.

Model selection is task-scoped, not "always the best model available":
`config/ai_models.yaml` maps each `AIRunPurpose` to a model tier
(`cheap`/`standard`/`premium`), so e.g. `NAME_NORMALIZATION` defaults to a
cheaper model than `ENTITY_MATCH_JUDGE`. Actual model IDs are configurable —
this file does not hardcode a model name a user might not have access to.

## 8. Multi-agent usage

Not implemented in Phase 1 (see ARCHITECTURE.md §6, Adversarial Review). The
`docs/ROADMAP.md` Phase 5 shape (Researcher → Skeptic → Verifier → Judge) is
reserved for validating top-scoring Opportunities once there is real
Opportunity volume to justify the added cost and latency; it is not used to
re-summarize the same data multiple times.
