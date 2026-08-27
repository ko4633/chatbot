# Quick status check of every OMNIS component — safe to run any time,
# makes no changes.
. "$PSScriptRoot\_lib.ps1"
Set-Location $RepoRoot

Write-Host ""
Write-Host "OMNIS Health Check" -ForegroundColor Magenta
Write-Host "===================" -ForegroundColor Magenta

Write-Step "Docker"
if (Test-DockerRunning) {
    docker compose ps --format "table {{.Name}}\t{{.Status}}" 2>$null | ForEach-Object { Write-Host "    $_" }
} else {
    Write-Host "    (Docker Desktop이 꺼져 있습니다)"
}

Write-Step "Backend (http://localhost:8000)"
try {
    $resp = Invoke-RestMethod -Uri "http://localhost:8000/health/full" -TimeoutSec 5
    Write-Ok "응답함"
    $resp | ConvertTo-Json -Depth 5 | Write-Host
} catch {
    try {
        $resp = Invoke-RestMethod -Uri "http://localhost:8000/health" -TimeoutSec 5
        Write-Ok "응답함 (기본 health만 — /health/full 미구현 버전)"
        $resp | ConvertTo-Json | Write-Host
    } catch {
        Write-Fail "Backend가 응답하지 않습니다. .\scripts\update-and-run.ps1 으로 시작해주세요."
    }
}

Write-Step "Frontend (http://localhost:3000)"
try {
    $resp = Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing -TimeoutSec 5
    Write-Ok "응답함 (HTTP $($resp.StatusCode))"
} catch {
    Write-Fail "Frontend가 응답하지 않습니다. .\scripts\update-and-run.ps1 으로 시작해주세요."
}

Write-Host ""
