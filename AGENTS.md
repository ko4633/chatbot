# AGENTS.md

This repo follows `CLAUDE.md` as its constitution — read that first, it is
the authoritative set of rules. This file is a short operational pointer for
any agent (Claude Code or otherwise) picking up work here.

## Quick orientation

- Product intent: `docs/MASTER_SPEC.md`
- System design: `docs/ARCHITECTURE.md` (includes the adversarial review —
  read it before assuming a risk hasn't been considered)
- Schema: `docs/DATA_MODEL.md`
- What AI may/may not do: `docs/AI_POLICY.md`
- Running things: `docs/RUNBOOK.md`
- What's implemented vs planned: `docs/ROADMAP.md`

## Commands

```bash
docker compose up -d postgres redis minio
scripts/migrate.sh
scripts/seed.sh
scripts/run-pipeline.sh
scripts/test.sh
scripts/lint.sh
```

Windows: use the `.ps1` equivalent of each script above.

## Before you touch code

1. `git status` — don't clobber uncommitted work.
2. Read the module you're changing and its nearest doc section.
3. If the change touches the schema, plan the Alembic migration as part of
   the same change, not a follow-up.

## Before you call something done

- Tests you wrote actually ran and passed (paste/summarize the result, don't
  assert from reading the code).
- If you touched the API or a Collector/AIProvider interface,
  `tests/contract/` reflects the new shape.
- If you touched the schema, `docs/DATA_MODEL.md` reflects it too.
- Mock data stays labeled as mock; nothing pretends to be live that isn't.
