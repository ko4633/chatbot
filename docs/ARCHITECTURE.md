# OMNIS — Architecture

## 1. Style: Modular Monolith

Phase 1 is a modular monolith, not microservices. Kafka, Kubernetes, Neo4j,
ClickHouse, Temporal, and multi-agent swarms are explicitly out of scope until
there is a measured reason to add them (§42/§44 of the product brief). What we
do instead: draw hard module boundaries now so any of those can replace an
internal piece later without a rewrite.

```
apps/
  api/      FastAPI HTTP surface. No business logic lives here.
  worker/   Runs collectors + the analysis pipeline as jobs. Same codebase as api,
            different entrypoint, so business logic is never duplicated.
  web/      Next.js (TypeScript) frontend. Talks to apps/api only, never to the DB
            or to AI providers directly.

packages/
  core/           settings, structured logging, ids, error types, time utils
  db/             SQLAlchemy 2.x models + Alembic migrations (the only place
                  that knows the schema)
  ai/             AIProvider interface + adapters (Anthropic, Null/disabled).
                  The only place allowed to import an AI vendor SDK.
  collectors/     Collector interface + per-source adapters (fixture-based in
                  Phase 1). The only place allowed to know about a specific
                  marketplace's HTML/JSON shape.
  entities/       Entity resolution engine (identifier → attributes → string →
                  fuzzy → embedding → vision(future) → LLM judge)
  scoring/        Deterministic margin calculator + opportunity scoring +
                  confidence scoring. No AI calls permitted in this package.
  intelligence/   Event detection, Insight assembly, Opportunity assembly —
                  orchestrates entities/scoring/ai but contains no scoring math
                  itself
  observability/  structured logging helpers, run/request id propagation
  fx/             (Phase 2) FXProvider interface + adapters (Manual, Frankfurter/
                  Null-equivalent). Mirrors packages/ai's adapter shape — the
                  only place that decides where an FX rate comes from.
  telegram/       (Phase 2) TelegramAdapter interface + adapters (HTTP, Null).
                  Outbound-only: formats/sends messages and answers personal-bot
                  commands by querying the same tables apps/api queries — never
                  a second business-logic path. See ADR-0010.
```

Rule: `packages/core` and `packages/db` may be imported by anything. Every
other package may be imported by `apps/*` but must not import from another
sibling package's internals except through its public `__init__.py` — e.g.
`collectors` must not reach into `scoring`, and `scoring` must never import
`ai`. This is enforced by convention + code review today; if it becomes a
real problem, `import-linter` is the natural next step (not added
speculatively).

## 2. Data flow (Phase 1)

```
Fixture JP/KR data
      │
      ▼
Collector.collect() → RawObject (content-hashed, stored in MinIO)
      │
      ▼
Collector.parse() → structured dict
      │
      ▼
Collector.normalize() → Observation rows (Price/Inventory/Review/Demand)
      │  (Source + SourceSnapshot provenance attached to every row)
      │  Source.data_quality_status reassessed after each collector run
      │  (packages/collectors/quality.py) — FAILED/QUARANTINED sources are
      │  excluded from the Opportunity calculation below (Phase 2)
      ▼
FX ingest (packages/fx) → FXObservation rows, then FX_MOVE event detection
      ▼
Entity Resolution (packages/entities)
      │  produces EntityMatch rows, may create/merge Product
      ▼
Intelligence pipeline (packages/intelligence), one AnalysisRun per invocation
      │
      ├─ Event detection (compare current vs prior observation → Event)
      ├─ Margin + Opportunity scoring (packages/scoring, deterministic,
      │  FX rate flows in explicitly — never a static config value)
      ├─ Confidence scoring (packages/scoring, deterministic; penalizes stale FX)
      ├─ Forecast direction classification (packages/scoring, deterministic;
      │  never a fabricated probability — ADR-0009)
      └─ Insight/Opportunity narrative (packages/ai, optional, labeled AI-generated)
      ▼
Opportunity + Insight + Event + Forecast rows persisted
      │
      ├─ Telegram broadcast of new high-score Opportunities (packages/telegram,
      │  opt-in, disabled by default — ADR-0010)
      ▼
apps/api serves them to apps/web
      │
      ▼
User records UserDecision (or queries the Telegram personal bot, same data)
```

Every arrow above is inspectable: every row created carries either a direct
FK to a `Source`/`SourceSnapshot`/`AnalysisRun`/`AIRun`, or is a pure function
of rows that do.

## 3. AI Provider Architecture

Business logic never imports `anthropic` or `openai` directly. Everything
goes through `packages/ai.AIProvider`:

```python
class AIProvider(Protocol):
    async def generate(self, request: GenerateRequest) -> GenerateResult: ...
    async def extract(self, request: ExtractRequest) -> ExtractResult: ...
    async def classify(self, request: ClassifyRequest) -> ClassifyResult: ...
    async def reason(self, request: ReasonRequest) -> ReasonResult: ...
    async def embed(self, request: EmbedRequest) -> EmbedResult: ...
```

Every call, regardless of provider, is wrapped so it produces an `AIRun` row
(provider, model, tokens, cost, latency, status, prompt_version) before the
result reaches the caller — cost tracking cannot be bypassed by calling the
adapter differently.

`NullAIProvider` is the default when no API key is configured
(`AI_ENABLED=false` or missing key). It never fabricates content: `generate`/
`reason` return an explicit `AI_DISABLED` deterministic placeholder,
`classify`/`extract` return `UNKNOWN`/empty with `ai_dependency=False` in the
result, and `embed` raises `EmbeddingUnavailable`, which callers (the entity
matching engine) must catch and treat as "stage skipped", not as a match
failure. The backend and worker must start and serve traffic with
`NullAIProvider` — no code path may require an AI key to boot.

## 4. Entity Resolution

Implemented as an ordered pipeline of stages (`packages/entities/stages/`).
Each stage either returns a decision (`EXACT`, `LIKELY`, `REJECTED`) which
stops the pipeline, or `INCONCLUSIVE` which falls through to the next stage.
AI (Stage 7, LLM Judge) only ever runs if stages 1-6 were inconclusive, and
its output is capped at `LIKELY` at best (never auto-promoted to `EXACT`,
since `EXACT` is reserved for deterministic identifier matches) — see
`docs/AI_POLICY.md` and ADR-0002.

Stages implemented in Phase 1: 1 (exact identifier), 2 (deterministic
attributes), 3 (normalized string), 4 (fuzzy match), 5 (embedding similarity,
skipped gracefully if AI is disabled), 7 (LLM judge, skipped if AI is
disabled). Stage 6 (vision similarity) is a documented interface stub only —
no image pipeline exists yet; calling it raises `NotImplementedError` and it
is never silently skipped in a way that looks like a real check happened.

## 5. Repository layout

```
omnis (repo root)
├── apps/{api,worker,web}
├── packages/{core,db,ai,collectors,entities,scoring,intelligence,observability,fx,telegram}
├── infra/                  docker init scripts (postgres init sql, minio bucket setup)
├── tests/{unit,integration,contract,fixtures,evals}
├── docs/ (+ ADR/)
├── scripts/                bash + PowerShell wrappers
├── legacy/                 pre-existing unrelated demo, preserved as-is
├── CLAUDE.md, AGENTS.md, README.md, .env.example, docker-compose.yml
```

Deviation from the originally sketched layout: Alembic migrations live at
`packages/db/migrations/` (next to the models they migrate) rather than a
top-level `migrations/` folder, because Alembic's `env.py` needs direct
import access to the `Base` metadata and co-locating avoids a fragile
cross-package import path. See ADR-0001. `tests/` stays top-level as
originally specified since tests intentionally cross package boundaries.

## 6. Adversarial Architecture Review

Self-review performed before implementation, per the product brief's
required checklist. Each item: the risk, and the concrete mitigation chosen.

**Over-engineering risk**: A 7-stage entity resolution pipeline, an AI
provider abstraction, and a full provenance chain for a single-user Phase 1
demo is a lot of structure. Mitigation: every one of these is *narrow* — no
new infra (no Kafka, no multi-agent orchestration framework, no Kubernetes),
just extra columns and a stage pipeline that is pure Python. The cost is
schema complexity, not operational complexity, and schema complexity is
exactly what an entity-resolution/provenance system is supposed to spend its
complexity budget on.

**Under-engineering risk**: Phase 1 has exactly one Opportunity type
(`IMPORT_RESALE`) and one Multi-Agent flow (Researcher/Skeptic/Verifier/Judge)
is *not* implemented — only documented as the Phase 5 shape. This is
deliberate: building a 4-agent verification pipeline before there is a single
working deterministic scoring path would hide bugs in the deterministic core
behind AI narrative confidence. Confidence scoring is real and load-bearing
today; multi-agent debate is future work.

**Data corruption risk**: Collectors write `RawObject` once (content-hash
addressed, immutable) and Observations are append-only (never UPDATEd in
place — a new observation with a new `observed_at` is inserted, and "current
value" is a query, not a mutation). This means a bad parse run creates bad
*new* rows, never corrupts history. Backfills are corrected by inserting a
superseding observation with a note, never by rewriting old rows.

**AI hallucination entering Fact tables**: Structurally prevented — the
`Insight`/`Opportunity` tables have an `ai_run_id` (nullable) and
`is_ai_generated`/`ai_assisted_fields` columns, and the observation/fact
tables (`PriceObservation` etc.) have no such column and no code path writes
to them from `packages/ai`. `packages/scoring` never imports `packages/ai` —
enforced by module boundary convention above, checked in code review.

**Entity mismatch risk**: The single highest-blast-radius bug class (merging
two different products destroys every downstream number). Mitigated by (a)
only `EXACT`/`LIKELY` above a configured threshold auto-merge into a
canonical `Product`; `POSSIBLE` is surfaced for human review and never
merges silently; (b) `EntityMatch` rows are never deleted, only superseded,
so a bad merge is auditable and reversible; (c) the golden dataset
(`docs/EVALUATION.md`) tracks false-positive rate specifically because a
false match is more dangerous than a false negative here.

**Time-series breakage risk**: Every Observation carries `observed_at` +
`retrieved_at` (distinct — a page can be re-fetched without the underlying
fact having changed) and is append-only with a DB-level unique constraint on
`(source_snapshot_id)` per row to make collector re-runs idempotent (see
§Idempotency below) rather than relying on application logic alone.

**Source disappearance**: `Source.is_active` flag + `SourceSnapshot.status`
(`SUCCESS`/`FAILED`/`PARTIAL`) let a dead source stop producing new
observations without deleting any historical row referencing it. Historical
Observations/Opportunities keep their FK and remain fully explainable even
after a source goes dark.

**Collector failure isolation**: Each collector run is wrapped with retry +
exponential backoff + a max attempt count (`packages/collectors/retry.py`);
a failed collector writes a `SourceSnapshot(status=FAILED)` row and the
worker's job loop continues to the next collector. One marketplace's fixture
breaking never stops JP or KR ingestion for the other market.

**Duplicate job execution**: All collector writes and observation inserts use
natural keys / content hashes with DB unique constraints and `ON CONFLICT DO
NOTHING`/upsert semantics (see Idempotency section, DATA_MODEL.md §5) — running
the same fixture ingestion job twice produces the same row count, not double.

**Secret exposure paths**: `apps/web` never receives an AI or marketplace
API key — no `NEXT_PUBLIC_*` secret variables exist by construction (there is
nothing to leak because the Next.js app has no server actions that embed a
key; all calls needing a key go through `apps/api`). `.env` is gitignored;
`.env.example` documents variable names with placeholder values only.
Structured logging redacts any field named `*key*`/`*token*`/`*secret*`
before it reaches a log sink (`packages/observability/redact.py`).

**Marketplace HTML structure changes**: N/A for Phase 1 — there are no live
scrapers, only fixture collectors, precisely because no real Marketplace API
or scraping terms have been confirmed (§19/§51 of the brief). The
`Collector` interface and `JapanMarketplaceProvider`/`KoreaMarketplaceProvider`
Protocol exist so a real adapter is a new file, not a core change, when a
real, ToS-compliant integration is actually scoped as its own task.

**Schema blocking future domains**: `Source`, `Event`, `Insight`,
`Opportunity`, `Watchlist`, `AnalysisRun`, `AIRun` are all modeled with
generic/polymorphic entity references (`entity_type` + `entity_id`) rather
than hard FKs to `Product` alone, specifically so Phase 3+ domains (news,
regulation, companies) can produce Events/Insights/Opportunities about
non-product entities without a schema migration that touches Phase 1 tables.
See DATA_MODEL.md §7.

**Opportunity Score explainability**: `Opportunity.sub_scores` (JSONB) stores
every named sub-score and the weight applied to it at compute time (not just
the final number), plus `AnalysisRun` links back to the exact code version
(`algorithm_version` string) that produced it. The UI's "Why Now" and
"Evidence" panels render directly from this JSON, not from a re-computation.

**Confidence conflated with Opportunity**: See DATA_MODEL.md and
`docs/AI_POLICY.md` — Confidence is a separate column with its own
deterministic formula and its own inputs (source count, reliability,
freshness, identifier tier, missing/conflicting data, AI dependency, market
coverage). It is never a weighted component *inside* the Opportunity Score
formula. This directly resolves an internal inconsistency in the original
product brief, where §14's example YAML listed `confidence` as one of the
Opportunity weight keys while §15 requires the two scores to be
independent axes — §15 is the harder, more specific requirement (an example
YAML is explicitly marked as illustrative only), so §14's example is
implemented *without* a confidence weight. Recorded as ADR-0003.

**Mock vs live confusion**: `Source.is_mock: bool` is a required column (not
nullable, no default) — every Source must declare itself. The frontend reads
this and renders a persistent "MOCK DATA" badge on every screen that shows
data from a mock source; `apps/api` also sets a response header
(`X-Omnis-Data-Mode: mock|live|mixed`) computed from the sources actually
touched by that response, so this can never be missed by only checking one
code path. Phase 2 adds the explicit `data_mode` enum (MOCK/LIVE/MANUAL,
ADR-0007) alongside `is_mock` — `packages/intelligence/system_status.py`
computes the rollup once, shared by `/opportunities` and
`/health/dashboard` rather than duplicated per router.

## 7. FX and Telegram Adapters (Phase 2)

Both mirror §3's `AIProvider` pattern exactly — one interface, a Null/Manual
default that requires no external key, and a real adapter that is opt-in:

```python
class FXProvider(Protocol):
    def get_latest(self, base: str, quote: str) -> FXRateResult: ...
    def get_historical(self, base: str, quote: str, as_of: date) -> FXRateResult: ...

class TelegramAdapter(Protocol):
    def send_message(self, chat_id: str, text: str) -> TelegramSendResult: ...
    def get_updates(self, offset: int | None, timeout_seconds: int) -> list[dict]: ...
```

`ManualFXProvider` (default) reads `config/fx_rates.yaml` — zero external
dependency, same "must boot without a key" guarantee as `NullAIProvider`.
`FrankfurterFXProvider` (opt-in via `FX_PROVIDER=frankfurter`) calls the
real, long-documented `api.frankfurter.dev` — its exact current response
shape could not be network-verified from the development sandbox (outbound
policy blocked it, same as it blocked Docker Hub during Phase 1), so it is
implemented against training-data knowledge of a stable public contract but
deliberately not the default; see ADR-0006 and
`docs/LIVE_SOURCE_RESEARCH.md`.

`NullTelegramAdapter` (default) logs what would have been sent instead of
calling the network. `HTTPTelegramAdapter` (opt-in, requires
`TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID`) calls the real, stable, official
Telegram Bot API — same "network access could not be verified from this
sandbox" caveat as Frankfurter applies here too (see ADR-0010). The
`packages/telegram/commands.py` personal-bot handlers query the exact same
tables/filters `apps/api`'s routers use, by design: there is exactly one
place "top opportunities" or "why was this recommended" is computed, so the
bot and the website can never disagree.

**Data Quality Monitor (Phase 2)**: `Source.data_quality_status`
(HEALTHY/DEGRADED/STALE/QUARANTINED/FAILED) is recomputed after every
collector run by comparing this run's yield against the same collector's
previous run (`packages/collectors/quality.py`) — catching a collector that
returns 200 OK but degraded data, not just an outright fetch failure.
FAILED/QUARANTINED sources are excluded from `build_opportunities`, so one
degraded marketplace connector cannot silently corrupt every Opportunity
that happens to reference it. Content-level anomaly detection (e.g. "this
run's average price is wildly different from history") is **not**
implemented yet — yield-drop detection only; see the Phase 2 BUILD STATUS
report's Known Risks for what this does not yet catch.

**Health Dashboard (Phase 2)**: `GET /health/dashboard` performs a live
probe of every dependency (DB, Redis, raw object store, FX freshness,
per-collector data quality, AI/Telegram configuration, Live-vs-Mock
rollup) rather than reporting a cached or assumed status — each check
either succeeds or reports its own error string, so the dashboard itself
never crashes because one dependency is down.

**Telegram token exposure risk**: `TELEGRAM_BOT_TOKEN` is read only by
`packages/core/settings.py` server-side, same as `ANTHROPIC_API_KEY` — it
never reaches `apps/web`, and `packages/observability/redact.py`'s existing
`*token*` pattern match already redacts it from structured logs with no
code change needed. `tests/unit/test_no_secret_exposed_to_frontend.py`
statically greps `apps/web` for secret-shaped `NEXT_PUBLIC_*` variables and
for the literal token/key env var names, as a regression guard.

**Forecast fabrication risk**: The single most tempting shortcut in a
"forecast" feature is inventing a probability number because it looks more
impressive than a qualitative label. `packages/scoring/forecast.py` has no
code path that can produce `predicted_probability` — the field is
hardcoded `None` at the call site in `opportunity_builder.py`, and
`is_calibrated` is hardcoded `False`. See ADR-0009.
