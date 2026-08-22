#!/usr/bin/env pwsh
<#
.SYNOPSIS
    One-time setup: pushes VPS_SSH_KEY (and other required secrets) to GitHub
    so that GitHub Actions auto-deploys on every git push.

    Run ONCE from the project root:
        .\scripts\setup_github_secret.ps1

.NOTES
    Requires: GitHub CLI (gh). Installs it automatically if missing.
              You will be prompted to log in to GitHub if not already.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ─── paths ───────────────────────────────────────────────────────────────────
$keyPath  = "$HOME\.ssh\trading_vps"
$VPS_HOST = "178.18.252.24"
$VPS_USER = "root"
$VPS_PORT = "22"

Write-Host ""
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host " AI Trading Brain — GitHub Secrets Setup" -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host ""

# ─── 1. Ensure GitHub CLI is present ─────────────────────────────────────────
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Host "[1/6] Installing GitHub CLI via winget..." -ForegroundColor Yellow
    winget install --id GitHub.cli --silent --accept-source-agreements --accept-package-agreements
    $ghCliPath = Join-Path $env:ProgramFiles "GitHub CLI"
    $env:PATH  = $env:PATH + ";" + $ghCliPath
    if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
        Write-Host "      Restart PowerShell after winget install, then re-run this script." -ForegroundColor Red
        exit 1
    }
}
Write-Host "[1/6] GitHub CLI: $(gh --version | Select-Object -First 1)" -ForegroundColor Green

# ─── 2. Authenticate if needed ───────────────────────────────────────────────
Write-Host "[2/6] Checking GitHub auth..." -ForegroundColor Yellow
$authStatus = gh auth status 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "      Not logged in — opening browser login..." -ForegroundColor Yellow
    gh auth login --web --git-protocol https
}
Write-Host "[2/6] GitHub auth OK" -ForegroundColor Green

# ─── 3. Detect repo ──────────────────────────────────────────────────────────
Write-Host "[3/6] Detecting GitHub repo..." -ForegroundColor Yellow
$remote = git remote get-url origin 2>$null
if ($remote -match "github\.com[:/](.+?)(?:\.git)?$") {
    $repoSlug = $Matches[1]
} else {
    Write-Host "ERROR: Could not determine GitHub repo from remote: $remote" -ForegroundColor Red
    exit 1
}
Write-Host "[3/6] Repo: $repoSlug" -ForegroundColor Green

# ─── 4. Read SSH private key ─────────────────────────────────────────────────
Write-Host "[4/6] Reading SSH private key from $keyPath..." -ForegroundColor Yellow
if (-not (Test-Path $keyPath)) {
    Write-Host "ERROR: SSH key not found at $keyPath" -ForegroundColor Red
    exit 1
}
$sshKey = Get-Content $keyPath -Raw
Write-Host "[4/6] Key read: $($sshKey.Split("`n").Count) lines" -ForegroundColor Green

# ─── 5. Push all 4 secrets to GitHub ─────────────────────────────────────────
Write-Host "[5/6] Setting GitHub repository secrets..." -ForegroundColor Yellow

$secrets = @{
    VPS_HOST    = $VPS_HOST
    VPS_USER    = $VPS_USER
    VPS_PORT    = $VPS_PORT
    VPS_SSH_KEY = $sshKey
}
foreach ($name in $secrets.Keys) {
    $val = $secrets[$name]
    # pipe via stdin to avoid key appearing in process args
    $val | gh secret set $name --repo $repoSlug
    if ($LASTEXITCODE -eq 0) {
        Write-Host "      ✅ $name set" -ForegroundColor Green
    } else {
        Write-Host "      ❌ Failed to set $name" -ForegroundColor Red
        exit 1
    }
}

# ─── 6. Verify ───────────────────────────────────────────────────────────────
Write-Host "[6/6] Verifying secrets..." -ForegroundColor Yellow
gh secret list --repo $repoSlug | Where-Object { $_ -match "VPS_" }
Write-Host ""
Write-Host "=================================================" -ForegroundColor Green
Write-Host " DONE. GitHub Actions will now auto-deploy on" -ForegroundColor Green
Write-Host " every 'git push origin main'." -ForegroundColor Green
Write-Host " No more manual VPS steps required." -ForegroundColor Green
Write-Host "=================================================" -ForegroundColor Green
Write-Host ""
Write-Host "To trigger an immediate deploy without a code change:" -ForegroundColor Cyan
Write-Host "  gh workflow run deploy.yml --repo $repoSlug" -ForegroundColor White
