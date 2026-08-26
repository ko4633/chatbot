# OMNIS — Data Model

This document is the source of truth for schema intent. `packages/db/models`
must never diverge from it; if they do, this file is out of date and must be
fixed in the same PR as the code change (CLAUDE.md rule).

## 1. Conventions

- All primary keys are UUIDv4 (`id: uuid`), generated application-side, so
  IDs are stable before the first `flush()` and safe to reference from
  external systems (e.g. `raw_object_id` used by the storage layer).
- All tables have `created_at` (server default `now()`); mutable tables also
  have `updated_at`. Append-only tables (Observations, Events, EntityMatch,
  AIRun) do **not** have `updated_at` — they are never updated in place.
- Money fields are stored as integer minor units (e.g. JPY has no minor unit,
  stored as whole yen; KRW likewise whole won) plus an explicit currency
  code — never floats.
- Every enum is a Postgres `ENUM` type with an `UNKNOWN` or equivalent
  "we don't know" member wherever the domain allows one, because storing a
  guess as a false-precision value is worse than admitting we don't know.

## 2. Information-layer → table mapping

| Layer | Table(s) |
|---|---|
| Raw Data | `raw_object`, `source_snapshot` |
| Observation | `price_observation`, `inventory_observation`, `review_observation`, `demand_observation` |
| Fact | *(no table — a query over the latest Observation per key; see §6)* |
| Event | `event` |
| Insight | `insight` |
| Opportunity | `opportunity` |
| Decision | `user_decision` |

## 3. Provenance (applies to every Observation, EntityMatch, Insight, Opportunity row)

Minimum fields, per the product brief §4, implemented as a reusable
`ProvenanceMixin` (`packages/db/mixins.py`):

```
source_id            FK -> source
source_snapshot_id   FK -> source_snapshot (nullable — some facts are derived, not fetched)
retrieved_at          timestamptz
observed_at           timestamptz   (may differ from retrieved_at: a page fetched today
                                      can state a price effective from an earlier date)
parser_name           text
parser_version        text
extraction_method     enum(HTML_SELECTOR, JSON_FIELD, API_RESPONSE, MANUAL, FIXTURE, DERIVED)
confidence            numeric(4,3)  0.000-1.000, deterministic per extraction_method,
                                     never AI-assigned for this field
```

Additional fields, present but nullable, populated only when an AI call
contributed to the row (`AIProvenanceMixin`, composed on top of the above for
tables where AI involvement is possible — never on raw Observation tables):

```
model_provider   text   nullable
model_name       text   nullable
prompt_version   text   nullable
ai_run_id        FK -> ai_run, nullable
```

`price_observation`, `inventory_observation`, `review_observation`,
`demand_observation` use **only** `ProvenanceMixin` — they can never carry AI
provenance fields, structurally enforcing "AI output is never a Fact/Observation"
(§9 of the brief). `entity_match`, `insight`, `opportunity` use both mixins.

## 4. Core tables

### source
Registry of everywhere data comes from.
```
id                  uuid pk
name                text
source_type         enum(MARKETPLACE_HTML, MARKETPLACE_API, GOVERNMENT_API,
                         COMMUNITY_FORUM, NEWS, SOCIAL, FIXTURE, MANUAL)
trust_tier          enum(OFFICIAL, PRIMARY, REPUTABLE_SECONDARY, MARKETPLACE,
                         COMMUNITY, SOCIAL, UNKNOWN)
factual_reliability enum(LOW, MEDIUM, HIGH)   -- how likely stated facts are true
signal_value        enum(LOW, MEDIUM, HIGH)   -- how useful even if unreliable
country             text nullable (ISO 3166-1 alpha-2)
base_url            text nullable
is_mock             boolean not null          -- Phase 1: true for all fixture sources
is_active           boolean not null default true
created_at          timestamptz
```

### raw_object
Content-addressed pointer into the raw data lake (MinIO).
```
id             uuid pk
content_hash   text unique not null   -- sha256 of raw bytes; dedupes re-fetches
mime_type      text
byte_size      int
storage_path   text                   -- bucket/key
created_at     timestamptz
```

### source_snapshot
One fetch attempt.
```
id                 uuid pk
source_id          FK -> source
source_url         text
retrieved_at       timestamptz
raw_object_id      FK -> raw_object, nullable (nullable = fetch failed before body captured)
parser_name        text
parser_version     text
extraction_method  enum (see above)
status             enum(SUCCESS, FAILED, PARTIAL)
error_detail       text nullable
unique(source_id, source_url, retrieved_at)   -- idempotency: see §5
```

### brand / manufacturer
```
id               uuid pk
name             text
name_normalized  text          -- lowercased, whitespace-collapsed, used by Stage 3 matching
aliases          text[]        -- e.g. ["OLFA", "オルファ", "올파"]
country          text nullable
created_at       timestamptz
```

### market
```
id            uuid pk
code          text unique   -- "JP", "KR"
name          text
currency_code text          -- "JPY", "KRW"
```

### marketplace
```
id            uuid pk
market_id     FK -> market
name          text          -- "Rakuten", "Coupang", ...
marketplace_type enum(ECOMMERCE_GENERAL, ECOMMERCE_MARKETPLACE, C2C, BRAND_DIRECT)
base_url      text nullable
created_at    timestamptz
```

### seller
```
id             uuid pk
marketplace_id FK -> marketplace
external_seller_id  text nullable  -- id on the marketplace, when known
name           text
first_seen_at  timestamptz
last_seen_at   timestamptz
```

### product
The canonical, market-agnostic entity — created or merged into by entity
resolution. A raw listing does **not** need a `product` row to exist; it
first exists as a `product_variant` with `product_id = NULL` ("unresolved").
```
id                  uuid pk
canonical_title     text
category            text nullable
brand_id            FK -> brand, nullable
manufacturer_id     FK -> manufacturer, nullable
primary_identifier_type  enum(JAN, EAN, UPC, GTIN, ISBN, MPN, MODEL_NUMBER, NONE)
primary_identifier  text nullable
status              enum(ACTIVE, MERGED, SPLIT)
merged_into_id       FK -> product, nullable   -- set when status=MERGED
created_at, updated_at
```

### product_variant
A specific sellable SKU (color/size/pack variant) as observed on one market's
listing, before or after being linked to a canonical `product`.
```
id                uuid pk
product_id        FK -> product, nullable      -- NULL until entity resolution links it
market_id         FK -> market
title_raw         text                          -- exactly as seen on source
title_language    text                          -- "ja", "ko"
brand_raw         text nullable
identifier_type   enum (same as product.primary_identifier_type)
identifier_value  text nullable
model_number      text nullable
dimensions_mm     jsonb nullable   -- {l,w,h}
weight_g          int nullable
capacity          text nullable
material          text nullable
color             text nullable
pack_quantity     int nullable
attributes_extra  jsonb            -- anything else, source-specific
embedding         vector(1536) nullable   -- pgvector; populated only when AI enabled
created_at, updated_at
```

### offer
A specific seller's listing of a `product_variant` on a `marketplace`.
```
id                 uuid pk
product_variant_id FK -> product_variant
marketplace_id     FK -> marketplace
seller_id          FK -> seller, nullable
listing_url        text
currency_code      text
status             enum(ACTIVE, INACTIVE, UNKNOWN)
first_seen_at      timestamptz
last_seen_at       timestamptz
unique(marketplace_id, listing_url)
```

### price_observation / inventory_observation / review_observation / demand_observation
Append-only time series, each row = one measured value at one point in time.
All four include `ProvenanceMixin` fields plus:
```
price_observation:
  id, offer_id FK, price_amount int, currency_code text,
  observed_at, retrieved_at, ...provenance...
  unique(offer_id, source_snapshot_id)

inventory_observation:
  id, offer_id FK, in_stock boolean, stock_quantity int nullable,
  observed_at, retrieved_at, ...provenance...
  unique(offer_id, source_snapshot_id)

review_observation:
  id, product_variant_id FK, review_count int, average_rating numeric(3,2) nullable,
  observed_at, retrieved_at, ...provenance...
  unique(product_variant_id, source_snapshot_id)

demand_observation:
  id, product_variant_id FK, metric_type enum(SEARCH_INTEREST, REVIEW_VELOCITY, MANUAL_ESTIMATE),
  metric_value numeric, unit text, observed_at, retrieved_at, ...provenance...
  unique(product_variant_id, metric_type, source_snapshot_id)
```

### entity_match
Result of the entity resolution engine linking two `product_variant` rows.
```
id                  uuid pk
left_variant_id     FK -> product_variant
right_variant_id    FK -> product_variant
match_type          enum(EXACT, LIKELY, POSSIBLE, REJECTED, UNKNOWN)
match_stage         enum(IDENTIFIER, ATTRIBUTES, STRING, FUZZY, EMBEDDING, VISION, LLM_JUDGE)
match_confidence    numeric(4,3)
evidence            jsonb         -- per-stage feature values that drove the decision
algorithm_version   text
resolved_product_id FK -> product, nullable   -- set only when match_type in (EXACT, LIKELY)
                                                -- and confidence >= merge threshold
reviewed_by_human   boolean default false
created_at          timestamptz
...AIProvenanceMixin fields (populated only if match_stage = LLM_JUDGE)...
```
Never updated or deleted. A corrected match is a new row; the superseded row
is left in place with `resolved_product_id` unchanged for audit history —
"what did we believe, and when" must be reconstructable.

### event
```
id              uuid pk
entity_type     enum(PRODUCT, PRODUCT_VARIANT, OFFER, SELLER)
entity_id       uuid
event_type      enum(PRICE_DROP, PRICE_RISE, NEW_SELLER, SELLER_EXIT, STOCK_OUT,
                     RESTOCK, NEW_PRODUCT, REVIEW_ACCELERATION, OPPORTUNITY_SCORE_CHANGE)
previous_value  jsonb
new_value       jsonb
change_pct      numeric nullable
observed_at     timestamptz
evidence        jsonb    -- observation ids that produced this event
confidence      numeric(4,3)
analysis_run_id FK -> analysis_run
created_at      timestamptz
```

### insight
```
id                uuid pk
product_id        FK -> product, nullable
title             text
narrative         text
supporting_facts  jsonb    -- list of {table, id} references
is_ai_generated   boolean not null
ai_assisted_fields text[]  -- which fields (e.g. ["narrative"]) came from AI; scores never do
confidence        numeric(4,3)
analysis_run_id   FK -> analysis_run
created_at        timestamptz
...ProvenanceMixin + AIProvenanceMixin...
```

### opportunity
```
id                   uuid pk
product_id           FK -> product
opportunity_type     enum(IMPORT_RESALE)     -- only value in Phase 1
opportunity_score    numeric(5,2)   0-100
confidence_score     numeric(5,2)   0-100, computed independently — see AI_POLICY.md
sub_scores           jsonb   -- {weighted_components: {demand, competition, price_gap, margin,
                              --  trend, supply, logistics, regulation} each with
                              --  {score, weight, contribution}; confidence_components:
                              --  {source_count, source_reliability, freshness,
                              --  identifier_tier, completeness, ai_independence} each 0-100}
weights_version      text    -- points at the config/opportunity_weights.yaml version used
economics            jsonb   -- {japan_purchase_price_jpy, target_sale_price_krw, jpy_krw_fx,
                              --  landed_cost_krw, gross_profit_krw, contribution_margin_krw,
                              --  contribution_margin_rate, break_even_sale_price_krw,
                              --  jp_offer_id, kr_offer_id, jp_seller_count, kr_seller_count}
                              --  (packages/scoring/margin.py MarginResult + the two offers used)
regulation_status    enum(UNKNOWN, LIKELY_LOW, REVIEW_REQUIRED, KNOWN_RESTRICTED)
regulation_basis     text nullable
status               enum(NEW, ACTIVE, STALE, REJECTED)
analysis_run_id      FK -> analysis_run
created_at, updated_at
...ProvenanceMixin (source rollup) + AIProvenanceMixin (if narrative AI-assisted)...
```

### user_decision
```
id              uuid pk
opportunity_id  FK -> opportunity
user_email      text            -- single-user Phase 1; kept as a real field, not
                                  hardcoded, so multi-user is additive later
decision        enum(BUY_TEST, WATCH, REJECT, ARCHIVE)
reason          text nullable
note            text nullable
created_at      timestamptz
```

### watchlist_item
```
id           uuid pk
user_email   text
entity_type  enum(PRODUCT, BRAND, CATEGORY, KEYWORD)
entity_ref   text     -- product id (as text) / brand id / category slug / keyword string
note         text nullable
created_at   timestamptz
```

### analysis_run
```
id            uuid pk
run_type      enum(INGEST, MATCH, SCORE, FULL)
status        enum(RUNNING, SUCCEEDED, FAILED, PARTIAL)
started_at, completed_at  timestamptz
stats         jsonb    -- counts: sources processed, observations written, events, etc.
triggered_by  text     -- "worker:scheduled" | "worker:manual" | "seed"
algorithm_version text
error_detail  text nullable
```

### ai_run
```
id                uuid pk
analysis_run_id   FK -> analysis_run, nullable
provider          text
model             text
purpose           enum(ENTITY_MATCH_JUDGE, NAME_NORMALIZATION, CATEGORY_CLASSIFICATION,
                       OPPORTUNITY_NARRATIVE, COUNTER_ARGUMENT, EMBEDDING)
input_tokens, output_tokens, cached_tokens  int nullable
estimated_cost_usd  numeric(10,6) nullable
started_at, completed_at  timestamptz
latency_ms        int
status            enum(SUCCESS, FAILED, DISABLED)
prompt_version    text
error_detail      text nullable
```

## 5. Idempotency

Every table a collector writes to has a natural-key `unique` constraint (see
inline `unique(...)` above) and writes go through `INSERT ... ON CONFLICT DO
NOTHING`/upsert. Running the same fixture ingestion job twice is a documented
integration test (`tests/integration/test_idempotent_ingest.py`) — row counts
must be identical after the second run.

## 6. "Fact" as a query, not a table

A materialized `fact` table storing "the current normalized value" would be a
second place a price could be wrong relative to the Observation it was
derived from. Instead, `packages/intelligence/facts.py` exposes read-only
query functions (`latest_price(offer_id)`, `latest_inventory(offer_id)`, ...)
that select the most recent Observation per key. `packages/scoring` consumes
these functions, never raw tables directly, so if the projection logic ever
needs to change (e.g. "latest" becomes "latest non-outlier"), there is one
place to change it. This is ADR-0004.

## 7. Extensibility for future domains (Phase 3+)

`event`, `insight`, `watchlist_item` use `entity_type` + `entity_id` rather
than a hard FK to `product` specifically so a future `Company`, `Regulation`,
or `NewsArticle` entity can participate without altering these tables. Adding
a new domain in Phase 3+ means: add the new entity tables, add new
`entity_type` enum values, add a new `Collector` — `event`/`insight` do not
change shape. `opportunity_type` is an enum with one value today
(`IMPORT_RESALE`) rather than a free-text field, so new opportunity types are
additive enum values plus (if needed) their own JSON shape inside
`sub_scores`/`economics`, not a new table per opportunity type.

## 8. Time model

Every Observation table has both `observed_at` (when the underlying fact was
true) and `retrieved_at` (when OMNIS fetched it) so `"what was the price on
2026-08-01"` is `select ... where observed_at <= '2026-08-01' order by
observed_at desc limit 1`, and `"what did OMNIS know on 2026-08-01"` (a
different, equally important question) is the same query against
`retrieved_at` instead. `Offer.first_seen_at`/`last_seen_at` and
`Seller.first_seen_at`/`last_seen_at` give entity-level lifespans without
scanning the observation tables. Phase 1 does not implement bitemporal
`valid_from`/`valid_to` correction ranges (no backfill-correction UI yet) —
noted as a Phase 2 gap in ROADMAP.md, not silently dropped.
