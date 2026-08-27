$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
ruff check .
ruff format --check .
mypy packages apps/api apps/worker
Push-Location apps/web
npm run lint
Pop-Location
