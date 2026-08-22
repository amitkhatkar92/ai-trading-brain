"""
live_operations/phase3_live_monitor.py
========================================
Phase 3 — Live Monitor (LIVE_MONITOR_REPORT.md)

Continuous intraday monitoring of:
  - Broker status and data feed health
  - Open positions and risk exposure
  - Portfolio allocation and capital utilisation
  - Maximum loss and drawdown
  - Order status (pending/partial fills)
  - API failure tracking
  - WebSocket connection status

Wraps CycleHealthMonitor and DhanFeed telemetry.
Does NOT modify any trading state — observe only.
"""
from __future__ import annotations

import csv
import json
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from .lol_config import (
    DATA_DIR, FILE_PAPER_TRADES, FILE_DAILY_JSON, MONITOR_INTERVAL_SEC,
    DB_CONTROL_TOWER,
)
from .report_writer import (
    report_header, section, kv, kv_ok, kv_warn, kv_fail,
    hr, badge, now_ist_str
)

IST = timezone(timedelta(hours=5, minutes=30))
_HEALTH_DIR = DATA_DIR / "health_reports"


# ── Snapshot dataclass ─────────────────────────────────────────────────────

@dataclass
class LiveSnapshot:
    """Point-in-time operational state snapshot."""
    ts:               str = ""
    broker_status:    str = "UNKNOWN"    # LIVE_VERIFIED | PARTIAL_LIVE | FALLBACK | SIMULATION
    feed_mode:        str = "UNKNOWN"
    ws_running:       bool = False
    open_positions:   int = 0
    total_exposure:   float = 0.0
    capital:          float = 0.0
    cash_pct:         float = 0.0
    daily_pnl:        float = 0.0
    daily_pnl_pct:    float = 0.0
    max_drawdown_pct: float = 0.0
    pending_orders:   int = 0
    api_fail_streak:  int = 0
    cycle_count:      int = 0
    last_cycle_ms:    int = 0
    last_verdict:     str = "UNKNOWN"
    nifty_ltp:        float = 0.0
    vix_level:        float = 0.0
    warnings:         List[str] = field(default_factory=list)


def _load_json(path: Path, default: Any = None) -> Any:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _open_positions_from_csv() -> List[Dict]:
    if not FILE_PAPER_TRADES.exists():
        return []
    open_pos = []
    try:
        with open(FILE_PAPER_TRADES, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("event", "OPEN") == "OPEN" and not row.get("exit_price", ""):
                    try:
                        entry = float(row.get("entry_price", 0) or 0)
                        qty   = int(row.get("quantity", 0) or 0)
                        open_pos.append({
                            "symbol":  row.get("symbol", ""),
                            "qty":     qty,
                            "entry":   entry,
                            "sl":      float(row.get("stop_loss", 0) or 0),
                            "value":   entry * qty,
                        })
                    except (ValueError, TypeError):
                        pass
    except Exception:
        pass
    return open_pos


def _get_last_health_report() -> Dict:
    if not _HEALTH_DIR.exists():
        return {}
    reports = sorted(_HEALTH_DIR.glob("*.json"), reverse=True)
    if not reports:
        return {}
    return _load_json(reports[0], {})


def _get_dhan_runtime_mode() -> str:
    """Read Dhan runtime mode without instantiating a new connection."""
    try:
        from data_feeds.data_feed_manager import get_feed_manager
        fm = get_feed_manager()
        dhan = getattr(fm, "dhan", None)
        if dhan is not None:
            return dhan.get_runtime_mode()
        return "SIMULATION"
    except Exception:
        return "UNKNOWN"


def _get_control_tower_stats(today: str) -> Dict:
    """Read today's cycle stats from control_tower.db (read-only)."""
    result = {"cycle_count": 0, "last_ms": 0, "last_verdict": "UNKNOWN"}
    if not DB_CONTROL_TOWER.exists():
        return result
    try:
        import sqlite3
        conn = sqlite3.connect(str(DB_CONTROL_TOWER), timeout=3)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT COUNT(*) as n, MAX(cycle_ms) as last_ms "
            "FROM ct_cycles WHERE DATE(started_at) = ?",
            (today,)
        ).fetchone()
        if row:
            result["cycle_count"] = row["n"] or 0
            result["last_ms"]     = row["last_ms"] or 0
        conn.close()
    except Exception:
        pass
    return result


def capture_snapshot(today: Optional[str] = None) -> LiveSnapshot:
    """Capture a current operational state snapshot."""
    if today is None:
        today = date.today().isoformat()

    snap = LiveSnapshot(ts=now_ist_str())

    # ── Broker / feed mode ─────────────────────────────────────────────
    snap.broker_status = _get_dhan_runtime_mode()
    snap.feed_mode     = snap.broker_status

    # ── Open positions from paper_trades.csv ──────────────────────────
    open_pos = _open_positions_from_csv()
    snap.open_positions  = len(open_pos)
    snap.total_exposure  = sum(p["value"] for p in open_pos)

    # ── Capital and utilisation ────────────────────────────────────────
    daily = _load_json(FILE_DAILY_JSON, {})
    snap.capital  = float(daily.get("pilot_capital", 0) or 0)
    cum_pnl       = float(daily.get("cumulative", {}).get("cum_pnl", 0) or 0)
    today_pnl_raw = daily.get("today", {}).get("net_pnl", 0)
    snap.daily_pnl     = float(today_pnl_raw or 0)
    snap.daily_pnl_pct = (snap.daily_pnl / snap.capital * 100) if snap.capital else 0.0
    snap.cash_pct      = max(0, 100 - (snap.total_exposure / snap.capital * 100)) if snap.capital else 100.0

    # ── Drawdown ───────────────────────────────────────────────────────
    try:
        import config as _cfg
        max_dd_pct = getattr(_cfg, "MAX_DRAWDOWN_PCT", 0.10) * 100
        snap.max_drawdown_pct = abs(min(0.0, snap.daily_pnl_pct))
    except Exception:
        pass

    # ── Control Tower stats ────────────────────────────────────────────
    ct = _get_control_tower_stats(today)
    snap.cycle_count  = ct["cycle_count"]
    snap.last_cycle_ms = ct["last_ms"]
    snap.last_verdict  = ct.get("last_verdict", "UNKNOWN")

    # ── Market data ────────────────────────────────────────────────────
    try:
        from data_feeds import get_feed_manager
        fm   = get_feed_manager()
        qn   = fm.yahoo.get_quote("NIFTY")
        qv   = fm.yahoo.get_quote("INDIAVIX")
        snap.nifty_ltp  = qn.close if qn else 0.0
        snap.vix_level  = qv.close if qv else 0.0
    except Exception:
        pass

    # ── Warnings ──────────────────────────────────────────────────────
    if snap.daily_pnl_pct <= -2.0:
        snap.warnings.append(f"DAILY_LOSS_LIMIT approaching: {snap.daily_pnl_pct:.2f}%")
    if snap.vix_level > 30:
        snap.warnings.append(f"HIGH_VIX: {snap.vix_level:.1f}")
    if snap.broker_status in ("FALLBACK", "SIMULATION"):
        snap.warnings.append(f"DATA_FEED_DEGRADED: {snap.broker_status}")
    if snap.cash_pct < 10:
        snap.warnings.append(f"LOW_CASH: only {snap.cash_pct:.0f}% cash available")

    return snap


def format_monitor_report(snap: LiveSnapshot, report_date: str) -> str:
    lines = [report_header("LIVE MONITOR REPORT", report_date,
                           f"Snapshot: {snap.ts}")]

    lines.append(section("BROKER & DATA FEED"))
    _kv = kv_ok if snap.broker_status == "LIVE_VERIFIED" else kv_warn
    lines.append(_kv("Broker status:", snap.broker_status))
    lines.append(kv("Data feed mode:", snap.feed_mode))

    lines.append(section("OPEN POSITIONS & EXPOSURE"))
    lines.append(kv("Open positions:", snap.open_positions))
    lines.append(kv("Total exposure:", f"₹{snap.total_exposure:,.0f}"))
    lines.append(kv("Capital utilised:", f"{100-snap.cash_pct:.1f}%"))
    lines.append(kv("Cash available:", f"{snap.cash_pct:.1f}%"))

    lines.append(section("P&L & RISK"))
    pnl_kv = kv_ok if snap.daily_pnl >= 0 else kv_warn
    lines.append(pnl_kv("Daily P&L:", f"₹{snap.daily_pnl:+,.0f}  ({snap.daily_pnl_pct:+.2f}%)"))
    lines.append(kv("Max drawdown today:", f"{snap.max_drawdown_pct:.2f}%"))

    lines.append(section("MARKET"))
    lines.append(kv("NIFTY LTP:", f"₹{snap.nifty_ltp:,.2f}" if snap.nifty_ltp else "N/A"))
    vix_kv = kv_warn if snap.vix_level > 20 else kv_ok
    lines.append(vix_kv("India VIX:", f"{snap.vix_level:.1f}" if snap.vix_level else "N/A"))

    lines.append(section("TRADING ENGINE"))
    lines.append(kv("Cycles today:", snap.cycle_count))
    lines.append(kv("Last cycle duration:", f"{snap.last_cycle_ms}ms"))

    if snap.warnings:
        lines.append(section("WARNINGS"))
        for w in snap.warnings:
            lines.append(f"  ⚠  {w}")
    else:
        lines.append(section("WARNINGS"))
        lines.append("  None")

    lines.append(f"\n{hr()}")
    return "\n".join(lines)
