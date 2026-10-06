"""
tests/test_dta_early_move_scan_001.py
========================================
DTA-EARLY-MOVE-SCAN-001 — close the 09:45->10:30 scan gap using EMP-001's
own 60-day live research.

EMP-001 (early_move_audit/) has been running daily (wired into
_do_eod_learning()) and accumulating real evidence on whether an
opening-window scan adds predictive value beyond the previous-day-only
scan the system started with. Checked its live, current (2026-10-05)
recommendation: OPTION_E ("previous-day + opening-window combined is
best"), with real persistence data showing 10:00 IST already has 68.3%
directional continuation to close -- a real, evidenced checkpoint that
the live SCHEDULE never scanned (09:45 "trade_decision" jumped straight
to 10:30 "mid_morning_scan", a 45-minute gap with zero per-stock
scanning in between; MarketMonitor's continuous 30s tick only watches
NIFTY/BANKNIFTY/INDIAVIX, not individual equity candidates).

Fix: added SCHEDULE["late_morning_scan"]="10:00" and wired it into
start_scheduler() via the exact same self._guarded_cycle() pattern
already used for every other intraday full-cycle slot (trade_decision,
mid_morning_scan, mid_session_scan, afternoon_scan, early_afternoon_scan,
closing_analysis). Purely additive: does not touch the 09:45
ExecutionWindowBlock (ANY order attempt from this slot is still subject
to the exact same risk/execution gates as every other scheduled cycle --
this only adds a scan, it does not change when orders are allowed),
does not touch risk control, capital allocation, or any strategy logic.

T01  SCHEDULE["late_morning_scan"] == "10:00"
T02  late_morning_scan is strictly between trade_decision (09:45) and
     mid_morning_scan (10:30) -- no collision with either
T03  start_scheduler() wires late_morning_scan via self._guarded_cycle
     (the same full-cycle handler used by every other intraday slot,
     not a different/weaker code path)
T04  scheduler_health.py's missed-slot detection includes the new slot
T05  the new slot does not appear anywhere near the ExecutionWindowBlock
     constant definition -- confirms the 09:45 guard itself is untouched
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def test_T01_schedule_has_late_morning_scan_at_1000():
    import config
    assert config.SCHEDULE["late_morning_scan"] == "10:00"


def test_T02_late_morning_scan_between_trade_decision_and_mid_morning():
    import config
    assert config.SCHEDULE["trade_decision"] < config.SCHEDULE["late_morning_scan"]
    assert config.SCHEDULE["late_morning_scan"] < config.SCHEDULE["mid_morning_scan"]


def test_T03_start_scheduler_wires_late_morning_scan_via_guarded_cycle():
    orches = _REPO / "orchestrator" / "master_orchestrator.py"
    text = orches.read_text(encoding="utf-8")
    idx = text.find('SCHEDULE["late_morning_scan"]')
    assert idx != -1, "late_morning_scan not referenced in master_orchestrator.py"
    # The wiring line itself must call self._guarded_cycle (same handler as
    # every other intraday full-cycle slot), not a bespoke/weaker path.
    line_start = text.rfind("\n", 0, idx)
    line_end = text.find("\n", idx)
    line = text[line_start:line_end]
    assert "self._guarded_cycle" in line


def test_T04_scheduler_health_includes_late_morning_scan():
    orches = _REPO / "orchestrator" / "scheduler_health.py"
    text = orches.read_text(encoding="utf-8")
    assert '"late_morning_scan"' in text


def test_T05_execution_window_guard_constant_unchanged():
    om = _REPO / "execution_engine" / "order_manager.py"
    text = om.read_text(encoding="utf-8")
    assert "_EXEC_WIN_OPEN_H, _EXEC_WIN_OPEN_M = 9, 45" in text
    assert "late_morning_scan" not in text
