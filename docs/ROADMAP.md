# OMNIS — Roadmap

## Phase 1 — Product Intelligence Foundation (this build)

Scope: one opportunity type (`IMPORT_RESALE`), fixture-based JP/KR data,
full provenance chain, deterministic scoring, entity resolution stages 1-5 +
7, Next.js UI for Today's Intelligence + Opportunity Detail.

Definition of done:
- [ ] `docker compose up` brings up Postgres, Redis, MinIO, api, worker, web
- [ ] Alembic migration creates the full schema from empty
- [ ] Seed command loads the JP/KR demo fixture set
- [ ] Worker runs ingest → entity resolution → scoring → opportunity pipeline
- [ ] API serves opportunity list + detail with full evidence trail
- [ ] Web UI shows Today's Intelligence table + Opportunity Detail page
- [ ] Mock data is labeled as mock in the UI and via API response header
- [ ] Unit/integration/contract/scoring/entity-matching tests pass
- [ ] Golden dataset false-positive rate = 0

Known Phase 1 gaps (deliberate, not oversights): no live marketplace
connectors, no bitemporal valid_from/valid_to correction ranges, no
multi-user auth, no Multi-Agent verification pipeline, no vision-based entity
matching (Stage 6 stubbed), no scheduled/recurring collection (worker runs
on demand), no alerting.

## Phase 2 — Live Connectors & Continuous Tracking

- Real, ToS-compliant marketplace connectors for at least one JP and one KR
  source (each scoped as its own task per `docs/MASTER_SPEC.md` §19 — no
  connector is built against an unverified API/selector).
- Scheduling (recurring collector runs) and Watchlist-triggered alerts.
- Bitemporal correction (`valid_from`/`valid_to`) for backfilled/corrected
  observations.
- `opportunity_outcome` evaluation table (see EVALUATION.md §6).
- Seller history / inventory-change tracking beyond point-in-time snapshots.

## Phase 3 — Additional Domains

Search demand signals, community/SNS signals, news, government/regulation
data sources, trade statistics. Enabled by the `entity_type`/`entity_id`
polymorphic design in `event`/`insight`/`watchlist_item` (DATA_MODEL.md §7) —
new domains add tables and enum values, not schema rewrites.

## Phase 4 — General Entity Graph

Company intelligence, supply chain intelligence, cross-entity relationship
graph. Revisit whether a graph-native store (e.g. a property graph engine) is
justified once real query patterns exist — not decided speculatively now.

## Phase 5 — Autonomous Research

Research Planner → Query Generation → Source Selection → Collection →
Evidence Extraction → Cross Validation → Counter Research → Synthesis →
Confidence → Research Report (`docs/MASTER_SPEC.md`/product brief §30). The
Researcher/Skeptic/Verifier/Judge multi-agent flow (AI_POLICY.md §8) is
introduced here, scoped to validating the highest-scoring Opportunities only.

## Phase 6 — Continuous Discovery

Anomaly detection, cross-domain opportunity detection, a personal
intelligence feed — "the information finds the user" as described in
`docs/MASTER_SPEC.md` §1.

## Explicitly out of scope (not just "later" — not planned)

Full-world crawling, automated trading, unattended purchasing/payment,
automated ordering/selling, hundreds of site connectors, a full real-time
streaming platform, unlimited autonomous agents, a self-hosted foundation
model, fully automated regulatory/customs determination. If any of these
becomes genuinely necessary, it requires a new ADR and an explicit decision
to revisit this list — it is not a default trajectory.
