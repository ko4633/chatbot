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
      ▼
Entity Resolution (packages/entities)
      │  produces EntityMatch rows, may create/merge Product
      ▼
Intelligence pipeline (packages/intelligence), one AnalysisRun per invocation
      │
      ├─ Event detection (compare current vs prior observation → Event)
      ├─ Margin + Opportunity scoring (packages/scoring, deterministic)
      ├─ Confidence scoring (packages/scoring, deterministic)
      └─ Insight/Opportunity narrative (packages/ai, optional, labeled AI-generated)
      ▼
Opportunity + Insight + Event rows persisted
      │
      ▼
apps/api serves them to apps/web
      │
      ▼
User records UserDecision
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
├── packages/{core,db,ai,collectors,entities,scoring,intelligence,observability}
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
code path.
