$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

if (-not (Test-Path ".env")) {
    Write-Warning "No .env found - copying .env.example. Fill in secrets before continuing."
    Copy-Item ".env.example" ".env"
}

docker compose up -d postgres redis minio
Write-Host "Waiting for postgres/redis/minio to become healthy..."
docker compose up -d --wait postgres redis minio

Write-Host "Run 'scripts\migrate.ps1' then 'scripts\seed.ps1' next."
