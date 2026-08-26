$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
alembic -c packages/db/alembic.ini upgrade head
