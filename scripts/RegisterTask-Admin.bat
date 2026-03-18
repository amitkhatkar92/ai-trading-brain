@echo off
REM =================================================================
REM AI Trading Brain — Windows Task Scheduler Setup (Admin) 
REM =================================================================
REM This batch file must be run as Administrator
REM Usage: Right-click this file → "Run as administrator"
REM =================================================================

setlocal enabledelayedexpansion

REM Check for admin privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo.
    echo ❌ ERROR: This script requires Administrator privileges
    echo.
    echo Please do the following:
    echo   1. Right-click on THIS BATCH FILE
    echo   2. Select "Run as administrator"
    echo   3. Click "Yes" when Windows asks for permission
    echo.
    pause
    exit /b 1
)

REM Get project root (parent of scripts folder)
for %%A in ("%~dp0.") do set "PROJECT_ROOT=%%~dpA"
set "PROJECT_ROOT=%PROJECT_ROOT:~0,-1%"
set "BAT_FILE=%PROJECT_ROOT%\scripts\autostart.bat"
set "TASK_NAME=AiTradingBrain"

echo.
echo ============================================================
echo   AI Trading Brain - Windows Task Setup
echo ============================================================
echo.
echo Project Root : %PROJECT_ROOT%
echo Autostart    : %BAT_FILE%
echo Task Name    : %TASK_NAME%
echo.

REM Check if autostart.bat exists
if not exist "%BAT_FILE%" (
    echo ❌ ERROR: autostart.bat not found at:
    echo    %BAT_FILE%
    pause
    exit /b 1
)

REM Delete existing task if it exists
echo Removing any existing task...
schtasks /delete /tn %TASK_NAME% /f 2>nul

REM Wait a moment
timeout /t 1 /nobreak >nul 2>&1

REM Create the scheduled task
echo.
echo Creating scheduled task...
echo.

schtasks /create ^
    /tn %TASK_NAME% ^
    /tr "%BAT_FILE%" ^
    /sc weekly ^
    /d MON,TUE,WED,THU,FRI ^
    /st 08:00:00 ^
    /rl limited ^
    /f

if errorlevel 1 (
    echo.
    echo ❌ ERROR: Failed to create task
    echo    Error code: %ERRORLEVEL%
    pause
    exit /b 1
)

REM Also add logon trigger using PowerShell
echo.
echo Adding logon trigger (runs at user login too)...
powershell -Command "if (Get-ScheduledTask -TaskName '%TASK_NAME%' -ErrorAction SilentlyContinue) { $task = Get-ScheduledTask -TaskName '%TASK_NAME%'; $logonTrigger = New-ScheduledTaskTrigger -AtLogOn; $task.Triggers += $logonTrigger; Set-ScheduledTask -TaskName '%TASK_NAME%' -Trigger $task.Triggers }"

echo.
echo ============================================================
echo   ✅ SUCCESS!
echo ============================================================
echo.
echo Task '%TASK_NAME%' has been registered with:
echo   - Trigger 1: Monday-Friday at 08:00 AM
echo   - Trigger 2: At user logon (covers late power-on)
echo   - Application: %BAT_FILE%
echo   - Run Level: Limited (no admin needed at runtime)
echo.
echo The system will:
echo   1. Start the dashboard on localhost:8501
echo   2. Run the trading brain in paper trading mode
echo   3. Log output to: %PROJECT_ROOT%\logs\
echo.
echo Logs:
echo   - %PROJECT_ROOT%\logs\scheduler.log
echo   - %PROJECT_ROOT%\logs\dashboard.log
echo.
echo To test immediately, run:
echo   schtasks /run /tn %TASK_NAME%
echo.
echo To remove later, run:
echo   schtasks /delete /tn %TASK_NAME% /f
echo.
pause
