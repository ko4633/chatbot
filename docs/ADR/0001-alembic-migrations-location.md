# ADR-0001: Alembic migrations live under packages/db/migrations, not top-level migrations/

## Status
Accepted

## Context
The product brief's suggested layout has a top-level `migrations/` directory
alongside `packages/db/`. Alembic's `env.py` needs a direct, non-fragile
import path to the SQLAlchemy `Base` metadata and model modules to
autogenerate migrations correctly.

## Decision
Place Alembic config and versions under `packages/db/migrations/`, next to
the models (`packages/db/models/`) they describe. `alembic.ini`'s
`script_location` points here. A one-line wrapper (`scripts/migrate.sh`)
runs `alembic -c packages/db/alembic.ini upgrade head` so the top-level
developer experience (`scripts/migrate.sh`) is unaffected by this choice.

## Consequences
- Positive: no fragile relative-import gymnastics in `env.py`; the migration
  code lives with the code it migrates, which is where a reader looks first.
- Negative: deviates from the brief's literal suggested tree. Documented in
  `docs/ARCHITECTURE.md` §5 so it isn't mistaken for an oversight.
