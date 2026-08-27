#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
alembic -c packages/db/alembic.ini upgrade head
