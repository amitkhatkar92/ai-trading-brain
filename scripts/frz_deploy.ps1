<#
.SYNOPSIS
    FRZ-001 Deployment Script — wraps push_deploy.ps1 with pre/post release management checks.

.DESCRIPTION
    Runs the FRZ-001 pre-deploy checklist before deployment and post-deploy verification
    after deployment. The core push_deploy.ps1 is UNTOUCHED and called verbatim.

.EXAMPLE
    .\scripts\frz_deploy.ps1
    .\scripts\frz_deploy.ps1 -SkipPreCheck
    .\scripts\frz_deploy.ps1 -SkipPostCheck
    .\scripts\frz_deploy.ps1 -DryRun
#>

param(
    [switch]$SkipPreCheck,
    [switch]$SkipPostCheck,
    [switch]$DryRun
)

Set-StrictMode -Off
$ErrorActionPreference = "Continue"

$ROOT    = Split-Path $PSScriptRoot -Parent
$PYTHON  = Join-Path $ROOT ".venv\Scripts\python.exe"
$FRZ_CMD = "$PYTHON -m release_manager.frz_runner"

function Write-Section([string]$title) {
    Write-Host ""
    Write-Host ("=" * 55) -ForegroundColor Cyan
    Write-Host "  $title" -ForegroundColor Cyan
    Write-Host ("=" * 55) -ForegroundColor Cyan
}

# ─── Pre-deploy checks ────────────────────────────────────────────────────────
if (-not $SkipPreCheck) {
    Write-Section "FRZ-001 Pre-Deploy Checks"

    if ($DryRun) {
        Write-Host "[DRY RUN] Skipping actual pre-deploy checks" -ForegroundColor Yellow
    } else {
        $preResult = & $PYTHON -m release_manager.frz_runner deploy
        $preExit   = $LASTEXITCODE

        if ($preExit -ne 0) {
            Write-Host ""
            Write-Host "BLOCKED: Pre-deploy checks FAILED. Deployment aborted." -ForegroundColor Red
            exit 1
        }
    }
}

# ─── Core deployment (UNTOUCHED) ──────────────────────────────────────────────
Write-Section "Deploying (push_deploy.ps1)"

if ($DryRun) {
    Write-Host "[DRY RUN] Would run: .\scripts\push_deploy.ps1" -ForegroundColor Yellow
} else {
    & "$PSScriptRoot\push_deploy.ps1"
    $deployExit = $LASTEXITCODE
    if ($deployExit -ne 0) {
        Write-Host ""
        Write-Host "Deployment FAILED (exit $deployExit). Post-deploy checks skipped." -ForegroundColor Red
        exit $deployExit
    }
}

# ─── Post-deploy checks ───────────────────────────────────────────────────────
if (-not $SkipPostCheck) {
    Write-Section "FRZ-001 Post-Deploy Checks"

    if ($DryRun) {
        Write-Host "[DRY RUN] Skipping post-deploy checks" -ForegroundColor Yellow
    } else {
        # Container consistency check
        Write-Host "Checking container consistency..." -ForegroundColor DarkGray
        & $PYTHON -m release_manager.frz_runner container

        # Release certificate
        Write-Host ""
        Write-Host "Generating release certificate..." -ForegroundColor DarkGray
        & $PYTHON -m release_manager.frz_runner cert

        Write-Host ""
        Write-Host "Post-deploy checks complete." -ForegroundColor Green
    }
}

Write-Section "FRZ-001 Deployment Complete"
& $PYTHON -m release_manager.frz_runner status
