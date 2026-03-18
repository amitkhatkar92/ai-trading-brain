@echo off
:: =========================================================
:: AI Trading Brain — Auto-Start Wrapper
:: =========================================================
:: Called by Windows Task Scheduler at 08:00 on weekdays.
:: Activates the virtual environment and starts the system
:: in scheduled daemon mode.  Logs to logs\scheduler.log.
:: =========================================================

:: Project root is the parent of this scripts\ folder
set "ROOT=%~dp0.."
set "LOGFILE=%ROOT%\logs\scheduler.log"
set "PYTHON=%ROOT%\.venv\Scripts\python.exe"

:: Create logs directory if it doesn't exist
if not exist "%ROOT%\logs" mkdir "%ROOT%\logs"

:: Timestamp helper
for /f "tokens=1-2 delims= " %%A in ('powershell -Command "Get-Date -Format \"yyyy-MM-dd HH:mm:ss\""') do set "TS=%%A %%B"

echo. >> "%LOGFILE%"
echo ============================================================ >> "%LOGFILE%"
echo %TS% | AI Trading Brain starting >> "%LOGFILE%"
echo ============================================================ >> "%LOGFILE%"

:: Set Unicode output and change to project root
set "PYTHONIOENCODING=utf-8"
cd /d "%ROOT%"

:: ── Launch Streamlit dashboard in background (port 8501) ───────────────────
set "DASHLOG=%ROOT%\logs\dashboard.log"
start "AiTradingDashboard" /B "%PYTHON%" -m streamlit run control_tower\dashboard_app.py ^
    --server.port 8501 --server.headless true ^
    --server.address localhost >> "%DASHLOG%" 2>&1

:: Wait 3s for dashboard to bind its port before the trading brain starts
timeout /t 3 /nobreak > nul

:: ── Run in paper trading + pilot capital mode (no live orders, ₹1L reference capital) ──
"%PYTHON%" main.py --schedule --paper --pilot >> "%LOGFILE%" 2>&1

:: Log exit
for /f "tokens=1-2 delims= " %%A in ('powershell -Command "Get-Date -Format \"yyyy-MM-dd HH:mm:ss\""') do set "TS2=%%A %%B"
echo %TS2% | Scheduler exited (code %ERRORLEVEL%) >> "%LOGFILE%"
