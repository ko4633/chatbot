# Stops the backend/frontend windows started by update-and-run.ps1 and
# stops (not removes — data is preserved) the Docker services.
. "$PSScriptRoot\_lib.ps1"
Set-Location $RepoRoot

Write-Step "Backend / Frontend 종료 중..."
$state = Get-RunState
if ($state) {
    foreach ($pidField in @("backendPid", "frontendPid")) {
        $procId = $state.$pidField
        if ($procId) {
            $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
            if ($proc) {
                Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
                Write-Ok "$pidField ($procId) 종료됨"
            }
        }
    }
    Remove-Item $StateFile -ErrorAction SilentlyContinue
} else {
    Write-Warn2 "실행 기록이 없습니다 — update-and-run.ps1으로 띄운 창이라면 직접 닫아주세요."
}

Write-Step "Docker 컨테이너 정지 중 (데이터는 보존됩니다)..."
if (Test-DockerRunning) {
    docker compose stop
    Write-Ok "Docker 컨테이너 정지됨"
}

Write-Host ""
Write-Host "종료되었습니다. 데이터는 유지됩니다 — 다시 시작하려면 .\scripts\update-and-run.ps1" -ForegroundColor Gray
