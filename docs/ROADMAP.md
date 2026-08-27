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

**Delivered in this Phase 2 build**: FX as first-class Observation data
(`packages/fx`, ADR-0006) with history/sensitivity/staleness; explicit
`Source.data_mode` (ADR-0007); `MARGIN_THRESHOLD_CROSSED`/`FX_MOVE`/
`FX_DRIVEN_OPPORTUNITY` events + point-in-time opportunity history endpoint;
`Insight.kind` taxonomy + a genuinely new Missing Data insight (ADR-0008);
a deterministic Forecast direction classifier with no fabricated
probability (ADR-0009); a Data Quality Monitor (yield-drop detection only —
see Known Gaps below) that can exclude a bad collector's data from scoring;
a health dashboard endpoint; a Telegram adapter for broadcast + a personal
query bot (ADR-0010); real (not fabricated) research into JP/KR marketplace
and FX APIs (`docs/LIVE_SOURCE_RESEARCH.md`); Windows one-command
operation scripts.

**Explicitly NOT delivered yet — real follow-up work, not oversights**:
- Real, ToS-compliant marketplace connectors for JP/KR — `docs/LIVE_SOURCE_RESEARCH.md`
  recommends Rakuten (JP) and Naver Shopping (KR) as the first candidates,
  but no connector against either has been built; fixture collectors are
  still what's running. Each remains its own scoped task per
  `docs/MASTER_SPEC.md` §19 — no connector is built against an unverified
  API/selector.
- Content-level data quality anomalies (e.g. "this run's average price is
  wildly different from history") — only yield-drop (item count vs a
  previous run) is implemented; see `docs/ARCHITECTURE.md` §7.
- Live verification of `FrankfurterFXProvider` and `HTTPTelegramAdapter`
  against the real network — both were built against documented, stable
  public APIs but could not be exercised from the development sandbox
  (outbound network policy blocked both `api.frankfurter.dev` and
  `api.telegram.org`).
- Next.js dependency upgrade (`docs/NPM_AUDIT_PLAN.md`) — 5 high-severity
  npm audit findings, all requiring a major-version bump, staged as a
  dedicated future change rather than forced through alongside everything
  else in this build.
- Scheduling (recurring collector runs) and Watchlist-triggered alerts —
  the worker still runs on demand; the Telegram broadcast fires only as
  part of a manually/externally triggered pipeline run.
- Bitemporal correction (`valid_from`/`valid_to`) for backfilled/corrected
  observations.
- `opportunity_outcome` evaluation table (see EVALUATION.md §6) — the
  Forecast schema is calibration-ready (`actual_outcome`/`evaluated_at`
  columns exist, ADR-0009) but nothing populates them yet.
- Seller history / inventory-change tracking beyond point-in-time snapshots.
- A real always-on Telegram bot deployment (webhook mode or a supervised
  process) — `python -m apps.worker.main telegram-bot` is an on-demand
  long-polling loop today, matching Phase 1's "no scheduler yet" scope.

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
