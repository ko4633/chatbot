#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
ruff check .
ruff format --check .
mypy packages apps/api apps/worker
(cd apps/web && npm run lint)
