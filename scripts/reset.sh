#!/usr/bin/env bash
# Destructive: drops all local OMNIS data (Postgres volume, MinIO volume).
set -euo pipefail
cd "$(dirname "$0")/.."

read -r -p "This deletes ALL local OMNIS data (Postgres + MinIO volumes). Type 'yes' to continue: " confirm
if [ "$confirm" != "yes" ]; then
  echo "Aborted."
  exit 1
fi

docker compose down -v
echo "Local data volumes removed. Run scripts/dev-up.sh, then migrate.sh and seed.sh to start fresh."
