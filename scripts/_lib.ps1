# Shared helpers for the Windows automation scripts. Dot-sourced, not run
# directly: ". $PSScriptRoot\_lib.ps1"
#
# Design notes (see docs/ADR — Phase 2 Windows automation):
# - Every external tool is invoked in a PATH-independent way
#   (python -m ..., npm.cmd, docker) because Windows Python installs don't
#   reliably put console-script shims (alembic.exe etc.) on PATH, and
#   PowerShell's npm.ps1 shim can itself be blocked by ExecutionPolicy —
#   both were real failures reported by a real Windows user running Phase 1.
# - Every failure prints a plain-language message before (optionally) the
#   raw error, never a bare stack trace as the only output.

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$StateFile = Join-Path $RepoRoot ".omnis-run-state.json"
$CacheDir = Join-Path $RepoRoot ".omnis-cache"

function Write-Step($msg) { Write-Host "==> $msg" -ForegroundColor Cyan }
function Write-Ok($msg) { Write-Host "    OK: $msg" -ForegroundColor Green }
function Write-Warn2($msg) { Write-Host "    WARNING: $msg" -ForegroundColor Yellow }
function Write-Fail($msg) {
    Write-Host ""
    Write-Host "XX  $msg" -ForegroundColor Red
    Write-Host ""
}

function Test-CommandExists($name) {
    return [bool](Get-Command $name -ErrorAction SilentlyContinue)
}

function Test-DockerRunning {
    if (-not (Test-CommandExists "docker")) {
        Write-Fail "Docker가 설치되어 있지 않습니다. Docker Desktop을 설치해주세요: https://www.docker.com/products/docker-desktop/"
        return $false
    }
    docker info *> $null
    if ($LASTEXITCODE -ne 0) {
        Write-Fail "Docker Desktop이 실행되지 않았습니다. Docker Desktop을 켠 뒤 (고래 아이콘이 트레이에 뜰 때까지 기다린 후) 다시 실행해주세요."
        return $false
    }
    return $true
}

function Test-NodeInstalled {
    if (-not (Test-CommandExists "node")) {
        Write-Fail "Node.js가 설치되어 있지 않습니다. https://nodejs.org 에서 LTS 버전을 설치해주세요."
        return $false
    }
    if (-not (Test-CommandExists "npm")) {
        Write-Fail "npm을 찾을 수 없습니다. Node.js를 다시 설치해주세요 (npm은 Node.js에 포함되어 있습니다)."
        return $false
    }
    return $true
}

function Test-PythonInstalled {
    foreach ($cmd in @("python", "py")) {
        if (Test-CommandExists $cmd) { return $cmd }
    }
    Write-Fail "Python이 설치되어 있지 않습니다. https://www.python.org/downloads/ 에서 Python 3.11 이상을 설치해주세요. 설치 시 'Add python.exe to PATH' 체크박스를 꼭 선택하세요."
    return $null
}

# Returns $true if the tracked file's content hash changed since the last
# recorded run (or was never recorded) — used to skip `pip install`/`npm
# install` on every single run, only doing it when dependencies actually changed.
function Test-DependencyChanged([string]$FilePath, [string]$CacheKey) {
    New-Item -ItemType Directory -Force -Path $CacheDir | Out-Null
    $cacheFile = Join-Path $CacheDir "$CacheKey.hash"
    if (-not (Test-Path $FilePath)) { return $true }
    $currentHash = (Get-FileHash -Path $FilePath -Algorithm SHA256).Hash
    if ((Test-Path $cacheFile) -and (Get-Content $cacheFile -Raw).Trim() -eq $currentHash) {
        return $false
    }
    Set-Content -Path $cacheFile -Value $currentHash
    return $true
}

function Wait-ForHttpHealth([string]$Url, [int]$TimeoutSeconds = 30) {
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3
            if ($resp.StatusCode -eq 200) { return $true }
        } catch {
            Start-Sleep -Seconds 2
        }
    }
    return $false
}

function Save-RunState([hashtable]$State) {
    $State | ConvertTo-Json | Set-Content -Path $StateFile
}

function Get-RunState {
    if (Test-Path $StateFile) {
        return Get-Content $StateFile -Raw | ConvertFrom-Json
    }
    return $null
}
