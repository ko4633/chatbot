# OMNIS — Runbook

## First-time setup

```bash
cp .env.example .env
docker compose up -d postgres redis minio
scripts/migrate.sh        # or scripts\migrate.ps1 on Windows
scripts/seed.sh           # or scripts\seed.ps1
docker compose up -d api worker web
```

Windows users: every `scripts/*.sh` has a `scripts/*.ps1` equivalent (and a
`.cmd` launcher that bypasses PowerShell's default ExecutionPolicy block).
For a non-developer one-command flow: `.\scripts\update-and-run.cmd` pulls
dependencies (via `python -m ...`/`npm.cmd`, never bare `pip`/`npm`, since
PATH-dependent console-script shims and PowerShell's `npm.ps1` block are
Windows-specific gotchas — see `scripts/update.ps1`) and starts the stack;
`.\scripts\health.cmd` checks it; `.\scripts\stop.cmd` stops it.

## Everyday commands

| Task | Command |
|---|---|
| Start everything | `docker compose up -d` |
| Stop everything | `docker compose down` |
| Tail logs | `docker compose logs -f api worker` |
| Run migrations | `scripts/migrate.sh` |
| Seed demo data | `scripts/seed.sh` |
| Run the analysis pipeline once | `scripts/run-pipeline.sh` |
| Run tests | `scripts/test.sh` |
| Lint + format | `scripts/lint.sh` |
| Reset local data (drops volumes) | `scripts/reset.sh` — **destructive, asks for confirmation** |

## Diagnosing a stuck/failed collector run

1. `docker compose logs worker` — each collector run logs its `source_id`
   and `analysis_run_id`.
2. Query `source_snapshot` for `status = 'FAILED'` rows and read
   `error_detail`.
3. A failed collector does not block others — check `analysis_run.stats`
   for the run-level summary (sources attempted/succeeded/failed).
4. Fixture collectors (Phase 1) fail only on a bug, not on network/site
   changes — a fixture failure is always a code bug, treat it as P1.

## Diagnosing a wrong/missing Opportunity

1. Find the `opportunity` row, read `analysis_run_id`.
2. From the UI Opportunity Detail page, "Evidence" and "Entity Match
   Evidence" sections link directly to every `source_snapshot` and
   `entity_match` row that contributed.
3. `sub_scores` JSON shows each component score and the weight applied —
   recompute by hand against `config/opportunity_weights.yaml` if a number
   looks wrong.
4. If a merge looks wrong (two different products treated as one), check
   `entity_match.match_stage`/`match_confidence`/`evidence` for that
   `product_id` — do not delete the row; flag it via
   `reviewed_by_human=true` and file the correction as noted in
   DATA_MODEL.md §4 (`entity_match`) — corrections are new rows, not edits.

## Enabling AI features

Set in `.env`:
```
AI_ENABLED=true
ANTHROPIC_API_KEY=<your key>
```
Restart `api` and `worker`. No key present → system runs in `AI_DISABLED`
mode automatically; this is not an error state.

## Enabling live FX rates (Phase 2)

Default (`FX_PROVIDER=manual`) reads `config/fx_rates.yaml` — no key
needed. To try the real Frankfurter API instead:
```
FX_PROVIDER=frankfurter
```
Its exact live response shape could not be network-verified from the
development sandbox this was built in (see ADR-0006) — check
https://frankfurter.dev's current docs before relying on it, and watch
`analysis_run.stats.fx.errors` after enabling.

## Enabling Telegram (Phase 2)

Set in `.env`:
```
TELEGRAM_BOT_TOKEN=<your bot token>
TELEGRAM_CHAT_ID=<channel/chat id to broadcast to>
TELEGRAM_BROADCAST_ENABLED=true   # off by default even with a token configured
```
Restart `worker`/`api`. New high-score Opportunities (`opportunity_score >=
TELEGRAM_BROADCAST_MIN_SCORE`, default 70) are pushed to `TELEGRAM_CHAT_ID`
at the end of each pipeline run. Run the personal query bot separately
(long-polling, on demand, not an always-on service in Phase 2):
```
python -m apps.worker.main telegram-bot
```
Send it `/help` for the command list (`/top`, `/filter`, `/why`,
`/counter`, `/track`, `/changes`). Network access to `api.telegram.org`
could not be verified from the development sandbox (ADR-0010) — test
against a real bot token before relying on this in production.

## Health dashboard (Phase 2)

`GET /health/dashboard` — one-screen check of DB/Redis/raw-store
connectivity, FX freshness, per-collector data quality, AI/Telegram
configuration, and the Live-vs-Mock rollup. Every field is a live probe,
never a cached value.

## npm audit (apps/web)

`npm audit` currently reports 5 high-severity findings, all requiring a
Next.js major-version bump to fix (none has a same-major patch available).
See `docs/NPM_AUDIT_PLAN.md` for the full investigation — do **not** run
`npm audit fix --force` without reading it first; it jumps two major
versions in one step with no verification.

## MinIO console

`http://localhost:9001` — credentials from `.env`
(`MINIO_ROOT_USER`/`MINIO_ROOT_PASSWORD`). Bucket `omnis-raw` holds raw
fetched objects, content-hash addressed.

## Database access

```
docker compose exec postgres psql -U omnis -d omnis
```

## Common issues

| Symptom | Likely cause | Fix |
|---|---|---|
| `api` fails to start, "relation does not exist" | migrations not run | `scripts/migrate.sh` |
| Opportunity list is empty | fixtures not seeded, or pipeline not run | `scripts/seed.sh && scripts/run-pipeline.sh` |
| Web shows "MOCK DATA" everywhere | expected in Phase 1 — no live connectors exist yet | not a bug |
| `AI_ENABLED=true` but narratives still say `AI_DISABLED:` | key missing/invalid | check `ANTHROPIC_API_KEY`, check `ai_run.error_detail` for the failed call |
| Opportunities missing for a product that used to have one | its Source is FAILED/QUARANTINED | check `GET /health/dashboard`'s `collectors` list; a FAILED source's data is excluded from scoring by design (docs/ARCHITECTURE.md §7) |
| Opportunity's economics look off after an FX change | FX may be STALE | check `economics.fx_is_stale` on the opportunity, or `GET /health/dashboard`'s `fx.is_stale` |
