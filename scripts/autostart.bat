@echo off
:: =========================================================
:: AI Trading Brain -- PERMANENTLY DISABLED
:: =========================================================
:: This script is permanently disabled.
:: The trading system runs ONLY inside Docker on the VPS.
:: Run `docker compose up -d` on the VPS instead.
::
:: If you see this message from Task Scheduler, delete the
:: AiTradingBrain task via Task Scheduler (run as Administrator).
:: =========================================================
echo.
echo  BLOCKED: AI Trading Brain must run inside Docker on the VPS.
echo  This Windows autostart is permanently disabled.
echo  See: docker compose up -d on your VPS.
echo.
exit /b 1
