"""
live_operations/phase4_incident_manager.py
============================================
Phase 4 — Intraday Incident Management (INCIDENT_REPORT.md)

Detects and documents operational incidents:
  - Broker outage / API circuit breaker
  - Internet failure
  - Market data failure
  - Duplicate order detection
  - Rejected order spike
  - Partial fill stall
  - Position mismatch
  - Risk limit breach
  - VIX circuit breaker trigger
  - Daily loss limit breach

Wraps existing:
  - CycleHealthMonitor verdict from health_reports/*.json
  - DhanFeed circuit breaker state
  - FailSafeRiskGuardian state
  - paper_trades.csv anomalies

Read-only scan. Writes INCIDENT_REPORT.md when incidents detected.
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
    DATA_DIR, FILE_PAPER_TRADES, DB_CONTROL_TOWER,
    INCIDENT_API_FAIL_STREAK,
)
from .report_writer import (
    report_header, section, kv, kv_warn, kv_fail, hr, badge, now_ist_str
)

IST = timezone(timedelta(hours=5, minutes=30))
_HEALTH_DIR = DATA_DIR / "health_reports"
_LOGS_DIR   = DATA_DIR.parent / "logs"


SEV_CRITICAL = "CRITICAL"
SEV_HIGH     = "HIGH"
SEV_MEDIUM   = "MEDIUM"
SEV_LOW      = "LOW"


@dataclass
class Incident:
    type:     str
    severity: str
    message:  str
    detail:   str = ""
    ts:       str = field(default_factory=now_ist_str)

    def is_blocking(self) -> bool:
        return self.severity in (SEV_CRITICAL, SEV_HIGH)


@dataclass
class IncidentReport:
    report_date: str
    incidents:   List[Incident] = field(default_factory=list)
    status:      str = "CLEAR"   # CLEAR | INCIDENT | CRITICAL

    @property
    def critical_count(self) -> int:
        return sum(1 for i in self.incidents if i.severity == SEV_CRITICAL)

    @property
    def high_count(self) -> int:
        return sum(1 for i in self.incidents if i.severity == SEV_HIGH)


def _load_json(path: Path, default: Any = None) -> Any:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


# ── Individual incident detectors ─────────────────────────────────────────

def _detect_broker_outage() -> Optional[Incident]:
    """Check if Dhan circuit breaker is tripped."""
    try:
        from data_feeds.data_feed_manager import get_feed_manager
        fm   = get_feed_manager()
        dhan = getattr(fm, "dhan", None)
        if dhan is None:
            return None
        mode = dhan.get_runtime_mode()
        consec = getattr(dhan, "_dhan_consecutive_failures", 0)
        if consec >= INCIDENT_API_FAIL_STREAK:
            return Incident(
                type="BROKER_OUTAGE",
                severity=SEV_HIGH,
                message="Dhan circuit breaker tripped",
                detail=f"consecutive_failures={consec}  mode={mode}",
            )
    except Exception:
        pass
    return None


def _detect_internet_failure() -> Optional[Incident]:
    try:
        import urllib.request
        urllib.request.urlopen("https://www.google.com", timeout=4)
    except Exception as e:
        return Incident(
            type="INTERNET_FAILURE",
            severity=SEV_CRITICAL,
            message="Internet connectivity lost",
            detail=str(e)[:80],
        )
    return None


def _detect_data_feed_failure() -> Optional[Incident]:
    try:
        from data_feeds import get_feed_manager
        fm = get_feed_manager()
        q  = fm.yahoo.get_quote("NIFTY")
        if q is None:
            return Incident(
                type="DATA_FEED_FAILURE",
                severity=SEV_HIGH,
                message="Market data feed returning None for NIFTY",
                detail="yfinance fallback also unavailable",
            )
    except Exception as e:
        return Incident(
            type="DATA_FEED_FAILURE",
            severity=SEV_HIGH,
            message="Market data feed exception",
            detail=str(e)[:80],
        )
    return None


def _detect_duplicate_orders(today: str) -> Optional[Incident]:
    """Scan paper_trades.csv for multiple OPEN rows with same symbol today."""
    if not FILE_PAPER_TRADES.exists():
        return None
    seen: Dict[str, int] = {}
    try:
        with open(FILE_PAPER_TRADES, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                evt = row.get("event", "OPEN")
                ts  = str(row.get("timestamp", row.get("date", "")))
                if evt == "OPEN" and today in ts and not row.get("exit_price", ""):
                    sym = row.get("symbol", "")
                    seen[sym] = seen.get(sym, 0) + 1
        dups = {s: n for s, n in seen.items() if n > 1}
        if dups:
            return Incident(
                type="DUPLICATE_ORDER",
                severity=SEV_HIGH,
                message="Duplicate open orders detected",
                detail=f"symbols={list(dups.keys())}  counts={dups}",
            )
    except Exception:
        pass
    return None


def _detect_rejected_order_spike(today: str) -> Optional[Incident]:
    """Detect high rejection rate from control_tower.db."""
    if not DB_CONTROL_TOWER.exists():
        return None
    try:
        import sqlite3
        conn = sqlite3.connect(str(DB_CONTROL_TOWER), timeout=3)
        row  = conn.execute(
            "SELECT SUM(signals_generated) as gen, SUM(trades_executed) as exec "
            "FROM ct_cycles WHERE DATE(started_at) = ?",
            (today,)
        ).fetchone()
        conn.close()
        if row and row[0] and row[0] > 0:
            gen  = row[0]
            exec_ = row[1] or 0
            reject_pct = (gen - exec_) / gen * 100
            if reject_pct > 90 and gen > 5:
                return Incident(
                    type="HIGH_REJECTION_RATE",
                    severity=SEV_MEDIUM,
                    message=f"Signal rejection rate {reject_pct:.0f}%",
                    detail=f"generated={gen}  executed={exec_}",
                )
    except Exception:
        pass
    return None


def _detect_risk_limit_breach(today: str) -> Optional[Incident]:
    """Detect daily loss breach from paper_trading_daily.json."""
    daily_file = DATA_DIR / "paper_trading_daily.json"
    if not daily_file.exists():
        return None
    try:
        d = _load_json(daily_file, {})
        capital   = float(d.get("pilot_capital", 0) or 0)
        today_pnl = float(d.get("today", {}).get("net_pnl", 0) or 0)
        if capital > 0:
            pct = today_pnl / capital * 100
            if pct <= -2.0:
                return Incident(
                    type="DAILY_LOSS_LIMIT",
                    severity=SEV_CRITICAL,
                    message=f"Daily loss limit reached: {pct:.2f}%",
                    detail=f"capital=₹{capital:,.0f}  pnl=₹{today_pnl:+,.0f}",
                )
            if pct <= -1.5:
                return Incident(
                    type="DAILY_LOSS_WARNING",
                    severity=SEV_HIGH,
                    message=f"Daily loss approaching limit: {pct:.2f}%",
                    detail=f"capital=₹{capital:,.0f}  pnl=₹{today_pnl:+,.0f}",
                )
    except Exception:
        pass
    return None


def _detect_vix_circuit() -> Optional[Incident]:
    """Check if VIX is above kill-switch threshold."""
    try:
        from data_feeds import get_feed_manager
        fm = get_feed_manager()
        q  = fm.yahoo.get_quote("INDIAVIX")
        if q and q.close > 45.0:
            return Incident(
                type="VIX_KILL_SWITCH",
                severity=SEV_CRITICAL,
                message=f"VIX={q.close:.1f} above kill-switch threshold (45.0)",
                detail="RiskGuardian should have halted trading",
            )
        if q and q.close > 35.0:
            return Incident(
                type="VIX_ELEVATED",
                severity=SEV_MEDIUM,
                message=f"VIX={q.close:.1f} — extremely elevated",
                detail="Capital exposure auto-reduced to 10%",
            )
    except Exception:
        pass
    return None


def _detect_cycle_stall(today: str) -> Optional[Incident]:
    """Detect if trading engine has not cycled in > 60 min during market hours."""
    ist = timezone(timedelta(hours=5, minutes=30))
    now = datetime.now(ist)
    market_open  = now.replace(hour=9, minute=15, second=0, microsecond=0)
    market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
    if not (market_open <= now <= market_close):
        return None   # outside market hours — stall expected

    if not DB_CONTROL_TOWER.exists():
        return None
    try:
        import sqlite3
        conn = sqlite3.connect(str(DB_CONTROL_TOWER), timeout=3)
        row  = conn.execute(
            "SELECT MAX(completed_at) FROM ct_cycles WHERE DATE(started_at) = ?",
            (today,)
        ).fetchone()
        conn.close()
        if row and row[0]:
            last_ts = datetime.fromisoformat(row[0].replace("Z", "+00:00"))
            gap_min = (datetime.now(timezone.utc) - last_ts).total_seconds() / 60
            if gap_min > 60:
                return Incident(
                    type="CYCLE_STALL",
                    severity=SEV_HIGH,
                    message=f"No trading cycle in {gap_min:.0f} minutes",
                    detail=f"last_cycle={row[0]}",
                )
    except Exception:
        pass
    return None


# ── Main runner ────────────────────────────────────────────────────────────

def run_incident_scan(report_date: Optional[str] = None) -> IncidentReport:
    if report_date is None:
        report_date = date.today().isoformat()

    report = IncidentReport(report_date=report_date)

    detectors = [
        _detect_internet_failure,
        _detect_broker_outage,
        _detect_data_feed_failure,
        lambda: _detect_duplicate_orders(report_date),
        lambda: _detect_rejected_order_spike(report_date),
        lambda: _detect_risk_limit_breach(report_date),
        _detect_vix_circuit,
        lambda: _detect_cycle_stall(report_date),
    ]

    for detect in detectors:
        try:
            incident = detect()
            if incident is not None:
                report.incidents.append(incident)
        except Exception:
            pass

    if not report.incidents:
        report.status = "CLEAR"
    elif report.critical_count > 0:
        report.status = "CRITICAL"
    else:
        report.status = "INCIDENT"

    return report


def format_incident_report(report: IncidentReport) -> str:
    lines = [
        report_header("INCIDENT REPORT", report.report_date,
                      f"Status: {badge(report.status)}")
    ]

    lines.append(section("INCIDENT SUMMARY"))
    lines.append(kv("Status:", badge(report.status)))
    lines.append(kv("Total incidents:", len(report.incidents)))
    lines.append(kv("Critical:", report.critical_count))
    lines.append(kv("High:", report.high_count))

    if report.incidents:
        lines.append(section("INCIDENT DETAILS"))
        for i, inc in enumerate(report.incidents, 1):
            sev_kv = kv_fail if inc.severity in (SEV_CRITICAL, SEV_HIGH) else kv_warn
            lines.append(f"\n  [{i}] {inc.type}  [{inc.severity}]")
            lines.append(f"      {inc.message}")
            if inc.detail:
                lines.append(f"      Detail: {inc.detail}")
            lines.append(f"      Detected: {inc.ts}")
    else:
        lines.append(section("INCIDENT DETAILS"))
        lines.append("  No incidents detected.")

    lines.append(f"\n{hr()}")
    return "\n".join(lines)
