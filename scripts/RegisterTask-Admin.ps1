# AI Trading Brain — Windows Task Scheduler Setup (PowerShell)
# Run this as Administrator to register the scheduled task
# Usage: Right-click PowerShell → Run as administrator → copy this script path

$ErrorActionPreference = "Stop"

# Check if running as admin
$isAdmin = [bool](([System.Security.Principal.WindowsIdentity]::GetCurrent()).groups -match "S-1-5-32-544")
if (-not $isAdmin) {
    Write-Error "❌ This script must run as Administrator. Please right-click PowerShell and select 'Run as administrator'"
    exit 1
}

$TASK_NAME = "AiTradingBrain"
$PROJECT_ROOT = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$BAT_PATH = Join-Path $PROJECT_ROOT "scripts\autostart.bat"

Write-Host "🚀 AI Trading Brain — Windows Task Scheduler Setup" -ForegroundColor Cyan
Write-Host "=================================================="
Write-Host ""
Write-Host "Project Root  : $PROJECT_ROOT"
Write-Host "Autostart Bat : $BAT_PATH"
Write-Host "Task Name     : $TASK_NAME"
Write-Host ""

# Check if BAT file exists
if (-not (Test-Path $BAT_PATH)) {
    Write-Error "❌ autostart.bat not found at: $BAT_PATH"
    exit 1
}

# Check if task already exists
$existingTask = Get-ScheduledTask -TaskName $TASK_NAME -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host "ℹ️  Task '$TASK_NAME' already exists. Removing it to recreate fresh…" -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TASK_NAME -Confirm:$false
    Start-Sleep -Seconds 1
}

# Create trigger 1: Weekdays at 08:00
$startTime = Get-Date -Hour 8 -Minute 0 -Second 0
$trigger1 = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek Monday, Tuesday, Wednesday, Thursday, Friday -At $startTime

# Create trigger 2: At user logon
$trigger2 = New-ScheduledTaskTrigger -AtLogOn

# Create action: Run the batch file
$action = New-ScheduledTaskAction -Execute $BAT_PATH -WorkingDirectory $PROJECT_ROOT

# Create task settings
$settings = New-ScheduledTaskSettingsSet `
    -MultipleInstancesPolicy IgnoreNew `
    -StartWhenAvailable $true `
    -ExecutionTimeLimit ([timespan]::Zero) `
    -DontStopIfGoingOnBatteries `
    -AllowStartIfOnBatteries

# Register the task with both triggers
Register-ScheduledTask `
    -TaskName $TASK_NAME `
    -Action $action `
    -Trigger @($trigger1, $trigger2) `
    -Settings $settings `
    -Description "AI Trading Brain — starts at 08:00 on trading days; also at logon if PC was off" `
    -RunLevel Limited `
    -Force | Out-Null

Write-Host ""
Write-Host "✅ Task '$TASK_NAME' registered successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Configuration:"
Write-Host "  Trigger 1 : Monday–Friday at 08:00 IST"
Write-Host "  Trigger 2 : At user logon (covers power-on after market opens)"
Write-Host "  Action    : $BAT_PATH"
Write-Host "  Settings  : StartWhenAvailable=true, AllowBattery=true"
Write-Host ""
Write-Host "Logs will be written to:"
Write-Host "  - $PROJECT_ROOT\logs\scheduler.log (main)"
Write-Host "  - $PROJECT_ROOT\logs\dashboard.log (dashboard)"
Write-Host ""
Write-Host "To test the task immediately, run:"
Write-Host "  schtasks /run /tn $TASK_NAME"
Write-Host ""
Write-Host "To remove the task later, run:"
Write-Host "  schtasks /delete /tn $TASK_NAME /f"
Write-Host ""
