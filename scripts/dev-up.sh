#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  echo "No .env found — copying .env.example. Fill in secrets before continuing." >&2
  cp .env.example .env
fi

docker compose up -d postgres redis minio
echo "Waiting for postgres/redis/minio to become healthy..."
docker compose up -d --wait postgres redis minio

echo "Run 'scripts/migrate.sh' then 'scripts/seed.sh' next."
