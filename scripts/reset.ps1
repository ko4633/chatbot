$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

$confirm = Read-Host "This deletes ALL local OMNIS data (Postgres + MinIO volumes). Type 'yes' to continue"
if ($confirm -ne "yes") {
    Write-Host "Aborted."
    exit 1
}

docker compose down -v
Write-Host "Local data volumes removed. Run scripts\dev-up.ps1, then migrate.ps1 and seed.ps1 to start fresh."
