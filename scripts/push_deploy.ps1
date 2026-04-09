#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Push local commits to GitHub AND deploy to VPS in one command.
    Replaces manual: git push + ssh + git pull + docker rebuild

    Usage:
        .\scripts\push_deploy.ps1           # push current branch + deploy
        .\scripts\push_deploy.ps1 -SkipPush # deploy only (re-deploy without new commit)
        .\scripts\push_deploy.ps1 -DryRun   # show what would be done, do nothing

    Git alias (set once):
        git config alias.deploy "!powershell -ExecutionPolicy Bypass -File scripts/push_deploy.ps1"
    Then use:
        git deploy
#>

param(
    [switch]$SkipPush,
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$VPS_SSH_KEY = "$HOME\.ssh\trading_vps"
$VPS_HOST    = "root@178.18.252.24"
$PROJECT_DIR = "/root/ai-trading-brain"

function Write-Step([string]$step, [string]$msg, [string]$color = "Cyan") {
    Write-Host "[$step] $msg" -ForegroundColor $color
}

function Run-SSH([string]$cmd) {
    if ($DryRun) {
        Write-Host "  DRY-RUN SSH: $cmd" -ForegroundColor DarkGray
        return
    }
    ssh -i $VPS_SSH_KEY -o StrictHostKeyChecking=no $VPS_HOST $cmd
    if ($LASTEXITCODE -ne 0) {
        throw "SSH command failed (exit $LASTEXITCODE): $cmd"
    }
}

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "  AI Trading Brain — Push & Deploy" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""

# ─── Step 1: Show what's uncommitted ─────────────────────────────────────────
$uncommitted = git status --short 2>$null
if ($uncommitted) {
    Write-Host "[!] Uncommitted changes detected:" -ForegroundColor Yellow
    $uncommitted | ForEach-Object { Write-Host "    $_" -ForegroundColor Yellow }
    Write-Host ""
    $ans = Read-Host "    Stage and commit all? (y/N)"
    if ($ans -match "^[Yy]$") {
        $msg = Read-Host "    Commit message"
        if (-not $DryRun) {
            git add -A
            git commit -m $msg
        } else {
            Write-Host "  DRY-RUN: git add -A && git commit -m '$msg'" -ForegroundColor DarkGray
        }
    } else {
        Write-Host "    Skipping uncommitted changes." -ForegroundColor DarkGray
    }
    Write-Host ""
}

# ─── Step 2: Push to GitHub ───────────────────────────────────────────────────
if (-not $SkipPush) {
    Write-Step "2/4" "Pushing to GitHub (origin main)..."
    if (-not $DryRun) {
        git push origin main
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Push failed — aborting deploy." -ForegroundColor Red
            exit 1
        }
    } else {
        Write-Host "  DRY-RUN: git push origin main" -ForegroundColor DarkGray
    }
    Write-Host "[2/4] Push OK" -ForegroundColor Green
} else {
    Write-Step "2/4" "Skipping push (-SkipPush flag)" "DarkGray"
}

# ─── Step 3: Deploy on VPS ───────────────────────────────────────────────────
Write-Step "3/4" "Deploying on VPS $VPS_HOST ..."
Run-SSH @"
set -e
cd $PROJECT_DIR
echo '--- git pull ---'
git fetch origin
git reset --hard origin/main
echo '--- docker rebuild + restart ---'
docker compose build --no-cache ai-trading-brain 2>&1 | tail -3
docker compose up -d --force-recreate
echo '--- containers ---'
docker ps --filter name=ai-trading-brain --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo 'DEPLOY_DONE'
"@
Write-Host "[3/4] VPS deploy complete" -ForegroundColor Green

# ─── Step 4: Smoke-check logs ────────────────────────────────────────────────
Write-Step "4/4" "Checking container startup logs (10s)..."
Start-Sleep -Seconds 10
if (-not $DryRun) {
    $logs = ssh -i $VPS_SSH_KEY -o StrictHostKeyChecking=no $VPS_HOST `
        "docker logs ai-trading-brain --tail 20 2>&1 | grep -E 'started|cycle|healthy|ERROR|CRITICAL' || true"
    $logs | ForEach-Object {
        $col = if ($_ -match "ERROR|CRITICAL") { "Red" } else { "White" }
        Write-Host "  $_" -ForegroundColor $col
    }
}

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
Write-Host "  DONE: local → GitHub → VPS all in sync ✓" -ForegroundColor Green
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
Write-Host ""
