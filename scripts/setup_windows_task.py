"""
AI Trading Brain — Windows Task Scheduler Setup
================================================
Run this once (as Administrator or current user) to register a scheduled task
that starts the trading system automatically at 08:00 on every weekday.

Usage:
    python scripts/setup_windows_task.py [--uninstall] [--status]

Options:
    (no flag)     Create / update the scheduled task
    --uninstall   Remove the scheduled task
    --status      Show current task status
    --start-now   Trigger the task immediately (for testing)

The task:
    Name     : AiTradingBrain
    Trigger  : Daily at 08:00, Monday–Friday
    Action   : Run scripts/autostart.bat
    Settings : Start even if on battery; do NOT stop on idle
    User     : Current logged-in user (no password required)
"""

from __future__ import annotations
import subprocess
import sys
import os
import argparse
from pathlib import Path

TASK_NAME   = "AiTradingBrain"
# Resolve paths relative to the project root (one level up from scripts/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BAT_PATH     = PROJECT_ROOT / "scripts" / "autostart.bat"


# ── helpers ──────────────────────────────────────────────────────────────

def run(cmd: list[str], capture: bool = True) -> tuple[int, str]:
    result = subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
        shell=False,
    )
    return result.returncode, (result.stdout + result.stderr).strip()


def task_exists() -> bool:
    code, out = run(["schtasks", "/Query", "/TN", TASK_NAME, "/FO", "LIST"])
    return code == 0


# ── actions ──────────────────────────────────────────────────────────────

def install() -> None:
    """Register the scheduled task (creates or updates)."""
    if not BAT_PATH.exists():
        print(f"❌  autostart.bat not found at: {BAT_PATH}")
        sys.exit(1)

    action = "create"
    if task_exists():
        print(f"Task '{TASK_NAME}' already exists — updating…")
        # Delete first so we can re-create cleanly
        run(["schtasks", "/Delete", "/TN", TASK_NAME, "/F"])
        action = "update"

    # Build XML definition for a richer task than schtasks CLI allows inline
    xml = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>AI Trading Brain — starts at 08:00 on trading days; also at logon if PC was off</Description>
  </RegistrationInfo>
  <Triggers>
    <!-- Primary: Weekdays 08:00 IST -->
    <CalendarTrigger>
      <StartBoundary>2026-01-01T08:00:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByWeek>
        <WeeksInterval>1</WeeksInterval>
        <DaysOfWeek>
          <Monday/>
          <Tuesday/>
          <Wednesday/>
          <Thursday/>
          <Friday/>
        </DaysOfWeek>
      </ScheduleByWeek>
    </CalendarTrigger>
    <!-- Fallback: At user logon — covers power-on after market opens -->
    <LogonTrigger>
      <Enabled>true</Enabled>
    </LogonTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <StartWhenAvailable>true</StartWhenAvailable>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{BAT_PATH}</Command>
      <WorkingDirectory>{PROJECT_ROOT}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>"""

    # Write XML to a temp file and import it
    xml_path = PROJECT_ROOT / "scripts" / "_task_def.xml"
    xml_path.write_text(xml, encoding="utf-16")

    code, out = run(
        ["schtasks", "/Create", "/TN", TASK_NAME, "/XML", str(xml_path), "/F"]
    )
    xml_path.unlink(missing_ok=True)   # clean up temp file

    if code == 0:
        print(f"✅  Task '{TASK_NAME}' {action}d successfully.")
        print(f"    Trigger 1 : Monday–Friday at 08:00")
        print(f"    Trigger 2 : At user logon (covers power-on after market opens)")
        print(f"    StartWhenAvailable: true (runs ASAP if missed)")
        print(f"    Action    : {BAT_PATH}")
        print(f"    Logs      : {PROJECT_ROOT / 'logs' / 'scheduler.log'}")
    else:
        print(f"❌  schtasks failed (code {code}):\n{out}")
        print("    Try running as Administrator if permission is denied.")
        sys.exit(1)


def uninstall() -> None:
    """Remove the scheduled task."""
    if not task_exists():
        print(f"Task '{TASK_NAME}' does not exist — nothing to remove.")
        return
    code, out = run(["schtasks", "/Delete", "/TN", TASK_NAME, "/F"])
    if code == 0:
        print(f"✅  Task '{TASK_NAME}' removed.")
    else:
        print(f"❌  Failed to remove task (code {code}):\n{out}")


def status() -> None:
    """Show current task registration and last run info."""
    if not task_exists():
        print(f"Task '{TASK_NAME}' is NOT registered.")
        return
    _, out = run(["schtasks", "/Query", "/TN", TASK_NAME, "/FO", "LIST", "/V"])
    print(out)


def start_now() -> None:
    """Trigger the task immediately (useful for testing)."""
    if not task_exists():
        print(f"Task '{TASK_NAME}' is not registered. Run without flags to install first.")
        return
    code, out = run(["schtasks", "/Run", "/TN", TASK_NAME])
    if code == 0:
        print(f"✅  Task '{TASK_NAME}' started.")
    else:
        print(f"❌  Failed to start task (code {code}):\n{out}")


# ── CLI ──────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Register AI Trading Brain as a Windows scheduled task"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--uninstall",  action="store_true", help="Remove the task")
    group.add_argument("--status",     action="store_true", help="Show task status")
    group.add_argument("--start-now",  action="store_true", help="Trigger task immediately")
    args = parser.parse_args()

    if sys.platform != "win32":
        print("❌  This script is Windows-only (uses schtasks.exe).")
        print("    On Linux/macOS use a cron entry instead:")
        print(f"    0 8 * * 1-5  cd {PROJECT_ROOT} && .venv/bin/python main.py --schedule")
        sys.exit(1)

    if args.uninstall:
        uninstall()
    elif args.status:
        status()
    elif args.start_now:
        start_now()
    else:
        install()


if __name__ == "__main__":
    main()
