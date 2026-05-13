#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Deploy one or more Python files to the VPS trading container.

.DESCRIPTION
    STANDARD DEPLOYMENT RULE:
      Code change → scp to VPS host → docker cp into container → docker restart

    Never use just 'scp + docker restart' — Python source is BAKED INTO the
    image, not bind-mounted. Only /app/data and .env are bind-mounted.
    docker cp is required for every Python file change.

.PARAMETER Files
    One or more workspace-relative paths (e.g. orchestrator/master_orchestrator.py).
    If omitted, a menu of commonly-deployed files is shown.

.PARAMETER NoRestart
    Copy files but do NOT restart the container. Use when you want to batch
    multiple file deploys before a single restart.

.EXAMPLE
    # Deploy one file
    .\scripts\deploy.ps1 orchestrator/master_orchestrator.py

    # Deploy multiple files then restart once
    .\scripts\deploy.ps1 orchestrator/master_orchestrator.py data_feeds/yahoo_feed.py

    # Copy only, restart manually later
    .\scripts\deploy.ps1 trade_monitoring/trade_monitor.py -NoRestart
#>

param(
    [string[]] $Files,
    [switch]   $NoRestart
)

$ErrorActionPreference = "Stop"

# ── Config ────────────────────────────────────────────────────────────────────
$VPS_HOST    = "root@178.18.252.24"
$SSH_KEY     = "$HOME\.ssh\trading_vps"
$CONTAINER   = "ai-trading-brain"
$LOCAL_ROOT  = "c:\Users\UCIC\OneDrive\Desktop\ai_trading_brain"
$REMOTE_HOST = "/root/ai-trading-brain"
$APP_ROOT    = "/app"

# ── Common files menu (shown when no args given) ───────────────────────────
$COMMON = @(
    "orchestrator/master_orchestrator.py",
    "data_feeds/yahoo_feed.py",
    "trade_monitoring/trade_monitor.py",
    "execution_engine/order_manager.py",
    "notifications/telegram_bot.py",
    "config.py",
    "main.py"
)

function ssh_cmd($cmd) {
    ssh -i $SSH_KEY $VPS_HOST $cmd
    if ($LASTEXITCODE -ne 0) { throw "Remote command failed: $cmd" }
}

# ── Interactive menu if no files given ────────────────────────────────────────
if (-not $Files) {
    Write-Host ""
    Write-Host "=== ai-trading-brain deploy ===" -ForegroundColor Cyan
    Write-Host "Common files (enter number, or type a path):"
    for ($i = 0; $i -lt $COMMON.Count; $i++) {
        Write-Host "  [$($i+1)] $($COMMON[$i])"
    }
    Write-Host ""
    $input = Read-Host "File(s) to deploy [number or path, space-separated]"
    $tokens = $input.Trim() -split '\s+'
    $Files = @()
    foreach ($t in $tokens) {
        if ($t -match '^\d+$' -and [int]$t -ge 1 -and [int]$t -le $COMMON.Count) {
            $Files += $COMMON[[int]$t - 1]
        } else {
            $Files += $t
        }
    }
}

if (-not $Files) { Write-Host "No files specified. Exiting." ; exit 0 }

Write-Host ""
Write-Host "Files to deploy:" -ForegroundColor Yellow
$Files | ForEach-Object { Write-Host "  - $_" }
Write-Host ""

# ── Deploy each file ──────────────────────────────────────────────────────────
foreach ($rel in $Files) {
    $rel = $rel -replace '\\', '/'   # normalise to forward slashes
    $local   = "$LOCAL_ROOT\$($rel -replace '/', '\')"
    $remote  = "$REMOTE_HOST/$rel"
    $inapp   = "$APP_ROOT/$rel"

    if (-not (Test-Path $local)) {
        Write-Warning "LOCAL FILE NOT FOUND: $local -- skipping"
        continue
    }

    Write-Host "[1/3] SCP  $rel -> VPS host..." -ForegroundColor Cyan
    scp -i $SSH_KEY $local "${VPS_HOST}:${remote}"
    if ($LASTEXITCODE -ne 0) { throw "SCP failed for $rel" }

    Write-Host "[2/3] docker cp -> container $CONTAINER..." -ForegroundColor Cyan
    ssh_cmd "docker cp $remote ${CONTAINER}:${inapp}"

    # Verify MD5s match
    $md5_host      = (ssh_cmd "md5sum $remote").Split()[0]
    $md5_container = (ssh_cmd "docker exec $CONTAINER md5sum $inapp").Split()[0]
    if ($md5_host -ne $md5_container) {
        throw "MD5 MISMATCH for $rel -- deploy may have failed"
    }
    Write-Host "       MD5 verified OK  ($md5_host)" -ForegroundColor Green
    Write-Host ""
}

# ── Restart ───────────────────────────────────────────────────────────────────
if ($NoRestart) {
    Write-Host "[!] -NoRestart specified -- container NOT restarted." -ForegroundColor Yellow
    Write-Host "    Run:  ssh -i `"$SSH_KEY`" $VPS_HOST `"docker restart $CONTAINER`""
} else {
    Write-Host "[3/3] Restarting container $CONTAINER..." -ForegroundColor Cyan
    ssh_cmd "docker restart $CONTAINER"
    Write-Host ""
    Write-Host "Waiting 10s for startup..." -ForegroundColor Gray
    Start-Sleep -Seconds 10
    $logs = ssh_cmd "docker logs --tail=8 $CONTAINER 2>&1"
    Write-Host "--- Last 8 log lines ---" -ForegroundColor Gray
    Write-Host $logs
    Write-Host "------------------------" -ForegroundColor Gray
}

Write-Host ""
Write-Host "DEPLOY COMPLETE." -ForegroundColor Green
