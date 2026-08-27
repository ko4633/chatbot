-- Runs once on first container start (docker-entrypoint-initdb.d convention).
-- Alembic's initial migration also issues this (belt-and-braces: a fresh
-- volume gets it here, a pre-existing one gets it from the migration).
CREATE EXTENSION IF NOT EXISTS vector;
