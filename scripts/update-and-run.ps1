# One-command Windows entry point (product brief §3): checks project state,
# pulls updates, starts Docker services, installs deps only if changed,
# migrates, starts backend + frontend, health-checks, prints URLs.
#
# Run via: .\scripts\update-and-run.ps1
# Or double-click: scripts\update-and-run.cmd (works even if PowerShell's
# ExecutionPolicy would otherwise block .ps1 files from running directly).

. "$PSScriptRoot\_lib.ps1"
Set-Location $RepoRoot

Write-Host ""
Write-Host "OMNIS — 자동 업데이트 및 실행" -ForegroundColor Magenta
Write-Host "================================" -ForegroundColor Magenta
Write-Host ""

# --- 1. Project state check ---
Write-Step "프로젝트 상태 확인 중..."
if (-not (Test-Path (Join-Path $RepoRoot ".git"))) {
    Write-Fail "이 폴더는 git 저장소가 아닙니다. 'git clone https://github.com/ko4633/chatbot.git' 으로 먼저 받아주세요."
    exit 1
}
$gitStatus = git status --porcelain 2>$null
if ($gitStatus) {
    Write-Warn2 "로컬에 저장하지 않은 변경사항이 있어 자동 업데이트(git pull)를 건너뜁니다."
} else {
    Write-Step "최신 버전 확인 중 (git pull)..."
    git fetch origin 2>&1 | Out-Null
    $pullResult = git pull --ff-only 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Warn2 "자동 업데이트에 실패했습니다 (충돌 가능성). 현재 버전으로 계속 진행합니다."
        Write-Host "    $pullResult"
    } else {
        Write-Ok "최신 버전입니다."
    }
}

# --- 2. Docker ---
Write-Step "Docker 확인 중..."
if (-not (Test-DockerRunning)) { exit 1 }
Write-Ok "Docker 실행 중"

if (-not (Test-Path ".env")) {
    Write-Warn2 ".env 파일이 없어 .env.example을 복사합니다. POSTGRES_PASSWORD / MINIO_ROOT_PASSWORD를 채워주세요."
    Copy-Item ".env.example" ".env"
}

Write-Step "PostgreSQL / Redis / MinIO 컨테이너 시작 중..."
docker compose up -d postgres redis minio 2>&1 | ForEach-Object { Write-Host "    $_" }
if ($LASTEXITCODE -ne 0) {
    Write-Fail "Docker 컨테이너 시작에 실패했습니다. 위 로그를 확인해주세요."
    exit 1
}
docker compose up -d --wait postgres redis minio 2>&1 | Out-Null
Write-Ok "PostgreSQL / Redis / MinIO 준비 완료"

# --- 3. Python deps ---
$python = Test-PythonInstalled
if (-not $python) { exit 1 }

Write-Step "Python 의존성 확인 중..."
if (Test-DependencyChanged "pyproject.toml" "pyproject") {
    Write-Host "    변경 감지됨 — 설치 중 (몇 분 걸릴 수 있습니다)..."
    & $python -m pip install -e ".[dev]" --quiet
    if ($LASTEXITCODE -ne 0) {
        Write-Fail "Python 패키지 설치에 실패했습니다. 위 오류 메시지를 확인해주세요."
        exit 1
    }
    Write-Ok "Python 의존성 설치 완료"
} else {
    Write-Ok "변경 없음 — 설치 건너뜀"
}

# --- 4. npm deps ---
if (-not (Test-NodeInstalled)) { exit 1 }
Write-Step "npm 의존성 확인 중..."
Push-Location (Join-Path $RepoRoot "apps\web")
if (Test-DependencyChanged "package-lock.json" "npm") {
    Write-Host "    변경 감지됨 — 설치 중 (몇 분 걸릴 수 있습니다)..."
    npm.cmd install
    if ($LASTEXITCODE -ne 0) {
        Write-Fail "npm 패키지 설치에 실패했습니다. 위 오류 메시지를 확인해주세요."
        Pop-Location
        exit 1
    }
    Write-Ok "npm 의존성 설치 완료"
} else {
    Write-Ok "변경 없음 — 설치 건너뜀"
}
Pop-Location

# --- 5. Migration ---
Write-Step "데이터베이스 마이그레이션 실행 중..."
& $python -m alembic -c packages/db/alembic.ini upgrade head
if ($LASTEXITCODE -ne 0) {
    Write-Fail "Database migration에 실패했습니다. .env의 DB 접속 정보와 Docker 컨테이너 상태를 확인해주세요."
    exit 1
}
Write-Ok "마이그레이션 완료"

# --- 6. Seed if empty (first run convenience) ---
Write-Step "기존 데이터 확인 중..."
$checkSeed = & $python -c "
from packages.db.base import get_session_factory
from packages.db.models.opportunity import Opportunity
db = get_session_factory()()
print(db.query(Opportunity).count())
db.close()
" 2>$null
if ($checkSeed -eq "0") {
    Write-Host "    기존 데이터 없음 — 데모 데이터로 초기 실행합니다."
    & $python -m apps.worker.main seed
    if ($LASTEXITCODE -ne 0) {
        Write-Warn2 "초기 데이터 생성에 실패했습니다. 화면에 상품이 안 보이면 'scripts\update.ps1' 후 다시 시도해주세요."
    } else {
        Write-Ok "데모 데이터 생성 완료"
    }
} else {
    Write-Ok "기존 데이터 있음 ($checkSeed 개 Opportunity) — seed 건너뜀"
}

# --- 7. Start backend + frontend in their own visible windows ---
Write-Step "Backend 시작 중..."
$backendProc = Start-Process -PassThru -WindowStyle Normal powershell -ArgumentList @(
    "-NoExit", "-Command",
    "cd '$RepoRoot'; Write-Host 'OMNIS Backend (닫으면 backend가 종료됩니다)' -ForegroundColor Cyan; $python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000"
)

Write-Step "Frontend 시작 중..."
$frontendProc = Start-Process -PassThru -WindowStyle Normal powershell -ArgumentList @(
    "-NoExit", "-Command",
    "cd '$RepoRoot\apps\web'; Write-Host 'OMNIS Frontend (닫으면 frontend가 종료됩니다)' -ForegroundColor Cyan; npm.cmd run dev"
)

Save-RunState @{ backendPid = $backendProc.Id; frontendPid = $frontendProc.Id; startedAt = (Get-Date).ToString("o") }

# --- 8. Health check ---
Write-Step "Backend health check 중..."
if (Wait-ForHttpHealth "http://localhost:8000/health" 30) {
    Write-Ok "Backend 정상"
} else {
    Write-Warn2 "Backend가 아직 응답하지 않습니다 — 방금 뜬 'OMNIS Backend' 창의 로그를 확인해주세요."
}

Write-Step "Frontend health check 중..."
if (Wait-ForHttpHealth "http://localhost:3000" 45) {
    Write-Ok "Frontend 정상"
} else {
    Write-Warn2 "Frontend가 아직 응답하지 않습니다 — 방금 뜬 'OMNIS Frontend' 창의 로그를 확인해주세요 (첫 실행은 시간이 더 걸릴 수 있습니다)."
}

Write-Host ""
Write-Host "================================" -ForegroundColor Magenta
Write-Host " 실행 완료!" -ForegroundColor Magenta
Write-Host "   Frontend : http://localhost:3000" -ForegroundColor White
Write-Host "   Backend  : http://localhost:8000" -ForegroundColor White
Write-Host "   API Docs : http://localhost:8000/docs" -ForegroundColor White
Write-Host "   MinIO    : http://localhost:9001" -ForegroundColor White
Write-Host ""
Write-Host "종료하려면: .\scripts\stop.ps1 (또는 방금 뜬 두 창을 닫으세요)" -ForegroundColor Gray
Write-Host "================================" -ForegroundColor Magenta
