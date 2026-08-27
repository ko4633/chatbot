# ADR-0004: "Fact" is a query over Observations, not a materialized table

## Status
Accepted

## Context
The product brief's information-layer diagram (§3) names `FACT` as a
distinct layer between `OBSERVATION` and `EVENT`, with an example
("Product A, Japan Market Price = 3,980 JPY"). Section 7's entity list,
however, does not include a `Fact` table among the entities to model,
listing `PriceObservation` etc. directly.

A literal `fact` table holding "the current normalized value per key" would
need to be kept in sync with the Observation tables on every insert, which
creates a second place a value could be wrong relative to its source
Observation — directly working against the provenance principle this whole
system is built around (product brief §0, "정확성"/"추적 가능성").

## Decision
"Fact" is implemented as a set of read-only query functions
(`packages/intelligence/facts.py`: `latest_price(offer_id)`,
`latest_inventory(offer_id)`, `latest_review_stats(product_variant_id)`,
`latest_demand(product_variant_id, metric_type)`), each a straightforward
"most recent Observation matching this key" query. `packages/scoring`
consumes these functions exclusively, never raw Observation tables directly.

## Consequences
- Positive: a Fact is always provably derived from its Observation(s) by
  construction — there is no separate write path to get out of sync.
- Positive: if the definition of "current" ever needs to change (e.g.
  outlier-exclusion, cross-source reconciliation when multiple sources
  disagree), there is exactly one place to change it.
- Negative: every Fact lookup is a query, not an indexed point-read of a
  materialized row. Acceptable at Phase 1 data volumes; if this becomes a
  real performance issue, the fix is a materialized view refreshed from the
  same query, not a hand-maintained table — noted here so a future
  performance pass doesn't reintroduce the sync-drift problem this ADR
  avoided.
