# OMNIS — Runbook

## First-time setup

```bash
cp .env.example .env
docker compose up -d postgres redis minio
scripts/migrate.sh        # or scripts\migrate.ps1 on Windows
scripts/seed.sh           # or scripts\seed.ps1
docker compose up -d api worker web
```

Windows users: every `scripts/*.sh` has a `scripts/*.ps1` equivalent. Run
from PowerShell, not cmd.exe.

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
