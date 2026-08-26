# OMNIS — Personal Intelligence OS

Phase 1: **Product Intelligence Foundation** — Japan → Korea import/resale
opportunity discovery, with full provenance, deterministic scoring, and an
auditable evidence trail from raw source to final recommendation.

Read `docs/MASTER_SPEC.md` first. `CLAUDE.md` is the binding constitution for
any agent (human or AI) working in this repo.

## What's here

- `apps/api` — FastAPI backend (the only thing `apps/web` talks to)
- `apps/worker` — CLI: ingest fixtures + run the analysis pipeline
- `apps/web` — Next.js frontend ("Today's Intelligence" + Opportunity Detail)
- `packages/` — db models/migrations, AI provider adapter, collectors, entity
  resolution, scoring, intelligence orchestration, observability
- `docs/` — architecture, data model, AI policy, security, evaluation,
  roadmap, runbook, ADRs
- `tests/` — unit, integration, contract, fixtures, evals
- `legacy/` — a pre-existing unrelated demo file, kept as-is (not part of OMNIS)

## Quick start

```bash
cp .env.example .env          # fill in secrets (all optional for Phase 1 — see below)
docker compose up -d postgres redis minio
pip install -e ".[dev]"       # backend deps (Python 3.11+)
scripts/migrate.sh
scripts/seed.sh                # loads the bundled JP/KR fixture dataset and runs the pipeline
(cd apps/web && npm install)
uvicorn apps.api.main:app --reload      # http://localhost:8000
(cd apps/web && npm run dev)            # http://localhost:3000
```

Windows: use the `.ps1` equivalent of every script in `scripts/`.

No API key required — the system runs fully in deterministic `AI_DISABLED`
mode by default (see `docs/AI_POLICY.md` §6). Every source in Phase 1 is a
bundled fixture; the UI and API both label this clearly (`MOCK DATA` badge,
`X-Omnis-Data-Mode` response header) — see `docs/ROADMAP.md` for what's real
vs. planned.

## Day-to-day commands

See `docs/RUNBOOK.md` for the full list (migrate, seed, run the pipeline,
test, lint, reset local data).

## Tests

```bash
scripts/test.sh    # 54 tests: unit, integration, contract, entity-resolution eval
scripts/lint.sh     # ruff + mypy + eslint
```
