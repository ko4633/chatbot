# Pulls latest code, installs changed dependencies, and migrates the
# database — without starting/restarting backend or frontend. Useful when
# they're already running and you just want to refresh code + schema.
. "$PSScriptRoot\_lib.ps1"
Set-Location $RepoRoot

Write-Step "최신 버전 확인 중 (git pull)..."
$gitStatus = git status --porcelain 2>$null
if ($gitStatus) {
    Write-Warn2 "로컬에 저장하지 않은 변경사항이 있어 git pull을 건너뜁니다."
} else {
    git fetch origin 2>&1 | Out-Null
    git pull --ff-only
    if ($LASTEXITCODE -ne 0) {
        Write-Fail "업데이트에 실패했습니다 (충돌 가능성). 수동으로 확인해주세요."
        exit 1
    }
    Write-Ok "업데이트 완료"
}

$python = Test-PythonInstalled
if (-not $python) { exit 1 }

Write-Step "Python 의존성 확인 중..."
if (Test-DependencyChanged "pyproject.toml" "pyproject") {
    & $python -m pip install -e ".[dev]" --quiet
    Write-Ok "Python 의존성 설치 완료"
} else {
    Write-Ok "변경 없음"
}

if (Test-NodeInstalled) {
    Write-Step "npm 의존성 확인 중..."
    Push-Location (Join-Path $RepoRoot "apps\web")
    if (Test-DependencyChanged "package-lock.json" "npm") {
        npm.cmd install
        Write-Ok "npm 의존성 설치 완료"
    } else {
        Write-Ok "변경 없음"
    }
    Pop-Location
}

Write-Step "데이터베이스 마이그레이션 실행 중..."
if (Test-DockerRunning) {
    & $python -m alembic -c packages/db/alembic.ini upgrade head
    if ($LASTEXITCODE -ne 0) {
        Write-Fail "Migration에 실패했습니다."
        exit 1
    }
    Write-Ok "마이그레이션 완료"
} else {
    Write-Warn2 "Docker가 꺼져 있어 migration을 건너뜁니다. PostgreSQL이 필요합니다."
}

Write-Host ""
Write-Host "업데이트 완료. Backend/Frontend를 재시작하려면 .\scripts\stop.ps1 후 .\scripts\update-and-run.ps1" -ForegroundColor Gray
