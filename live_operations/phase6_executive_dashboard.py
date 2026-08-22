"""
live_operations/phase6_executive_dashboard.py
===============================================
Phase 6 — Executive Dashboard (EXECUTIVE_SUMMARY.md)

Daily, weekly, and monthly executive summaries including:
  - Capital, Return, Drawdown
  - Knowledge growth (feature count)
  - Research completed (studies, hypotheses)
  - DNA added / retired
  - Platform health score

Reads from all available data sources — no external API calls.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from .lol_config import (
    DATA_DIR, FILE_DAILY_JSON, FILE_EDE_FEATURES,
    FILE_HYPOTHESIS_REG, DB_CONTROL_TOWER,
)
from .report_writer import (
    report_header, section, kv, kv_ok, kv_warn, hr, now_ist_str
)


def _load_json(path: Path, default: Any = None) -> Any:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _feature_count() -> int:
    db = _load_json(FILE_EDE_FEATURES, {})
    if isinstance(db, list):
        return len(db)
    if isinstance(db, dict):
        return sum(len(v) for v in db.values() if isinstance(v, list))
    return 0


def _hypothesis_count() -> Dict:
    reg = _load_json(FILE_HYPOTHESIS_REG, {})
    if isinstance(reg, list):
        total = len(reg)
        confirmed = sum(1 for h in reg if isinstance(h, dict) and
                        h.get("status", "").upper() in ("CONFIRMED", "VALIDATED"))
        return {"total": total, "confirmed": confirmed}
    if isinstance(reg, dict):
        hyps = reg.get("hypotheses", [])
        total = len(hyps)
        confirmed = sum(1 for h in hyps if isinstance(h, dict) and
                        h.get("status", "").upper() in ("CONFIRMED", "VALIDATED"))
        return {"total": total, "confirmed": confirmed}
    return {"total": 0, "confirmed": 0}


def _dna_counts() -> Dict:
    """Count IDR DNA records."""
    db_path = DATA_DIR / "mls" / "institutional_dna.db"
    result  = {"total": 0, "active": 0, "retired": 0}
    if not db_path.exists():
        # Try IDRRepository
        try:
            from market_learning.idr_repository import IDRRepository
            idr   = IDRRepository()
            stats = idr.statistics()
            result["total"]   = stats.get("total_dna", 0)
            result["active"]  = stats.get("active_dna", 0)
            result["retired"] = stats.get("retired_dna", 0)
        except Exception:
            pass
        return result
    try:
        conn = sqlite3.connect(str(db_path), timeout=3)
        row  = conn.execute("SELECT COUNT(*) FROM institutional_dna").fetchone()
        if row:
            result["total"] = row[0]
        try:
            row2 = conn.execute(
                "SELECT COUNT(*) FROM institutional_dna WHERE status='ACTIVE'"
            ).fetchone()
            row3 = conn.execute(
                "SELECT COUNT(*) FROM institutional_dna WHERE status='RETIRED'"
            ).fetchone()
            result["active"]  = row2[0] if row2 else 0
            result["retired"] = row3[0] if row3 else 0
        except Exception:
            pass
        conn.close()
    except Exception:
        pass
    return result


def _platform_health_score(today: str) -> float:
    """0.0–1.0 platform health from last N cycles."""
    if not DB_CONTROL_TOWER.exists():
        return 0.5
    try:
        conn = sqlite3.connect(str(DB_CONTROL_TOWER), timeout=3)
        row  = conn.execute(
            "SELECT COUNT(*) as total, SUM(had_error) as errors "
            "FROM ct_cycles WHERE DATE(started_at) = ?",
            (today,)
        ).fetchone()
        conn.close()
        if row and row[0]:
            return max(0.0, 1.0 - (row[1] or 0) / row[0])
    except Exception:
        pass
    return 0.5


def _studies_completed(since: str) -> int:
    """Count study JSON files created since date."""
    count = 0
    for f in DATA_DIR.glob("study*.json"):
        try:
            if f.stat().st_mtime >= _date_to_ts(since):
                count += 1
        except Exception:
            pass
    return count


def _date_to_ts(d: str) -> float:
    import time
    return time.mktime(date.fromisoformat(d).timetuple())


def _pnl_series(days: int = 30) -> List[float]:
    """Last N days of daily P&L from paper_trading_daily.json."""
    daily = _load_json(FILE_DAILY_JSON, {})
    hist  = daily.get("history", [])
    if not hist:
        return []
    return [float(h.get("net_pnl", 0)) for h in hist[-days:]]


def generate_executive_summary(
    report_date: Optional[str] = None,
    period: str = "daily",    # daily | weekly | monthly
) -> str:
    if report_date is None:
        report_date = date.today().isoformat()

    today    = date.fromisoformat(report_date)
    daily    = _load_json(FILE_DAILY_JSON, {})
    feat_cnt = _feature_count()
    hyp      = _hypothesis_count()
    dna      = _dna_counts()
    health   = _platform_health_score(report_date)

    import config as _cfg
    capital    = getattr(_cfg, "TOTAL_CAPITAL", 0)
    paper_mode = getattr(_cfg, "PAPER_TRADING", True)

    cum_pnl = float(daily.get("cumulative", {}).get("cum_pnl", 0) or 0)
    cum_ret = float(daily.get("cumulative", {}).get("cum_return_pct", 0) or 0)

    # Period window
    if period == "weekly":
        since = (today - timedelta(days=7)).isoformat()
        label = "Weekly"
    elif period == "monthly":
        since = (today - timedelta(days=30)).isoformat()
        label = "Monthly"
    else:
        since = report_date
        label = "Daily"

    # Period-specific P&L
    pnl_series = _pnl_series(7 if period == "weekly" else 30 if period == "monthly" else 1)
    period_pnl = sum(pnl_series)
    period_ret = (period_pnl / capital * 100) if capital else 0.0

    # Drawdown: max run-down from peak in period
    peak = 0.0
    max_dd = 0.0
    running = 0.0
    for p in pnl_series:
        running += p
        if running > peak:
            peak = running
        dd = (peak - running)
        if dd > max_dd:
            max_dd = dd
    max_dd_pct = (max_dd / capital * 100) if capital else 0.0

    studies = _studies_completed(since)

    lines = [
        report_header(f"EXECUTIVE SUMMARY — {label.upper()}", report_date,
                      f"Mode: {'PAPER' if paper_mode else 'LIVE'}")
    ]

    # ── Capital & Returns ─────────────────────────────────────────────
    lines.append(section("CAPITAL & RETURNS"))
    lines.append(kv("Trading capital:", f"₹{capital:,.0f}"))
    pnl_kv = kv_ok if period_pnl >= 0 else kv_warn
    lines.append(pnl_kv(f"P&L ({label}):", f"₹{period_pnl:+,.0f}  ({period_ret:+.2f}%)"))
    lines.append(kv("Cumulative P&L:", f"₹{cum_pnl:+,.0f}  ({cum_ret:+.2f}%)"))
    lines.append(kv(f"Max drawdown ({label}):", f"{max_dd_pct:.2f}%"))

    # ── Knowledge Growth ──────────────────────────────────────────────
    lines.append(section("KNOWLEDGE GROWTH"))
    lines.append(kv("Feature records (EDE):", f"{feat_cnt:,}"))
    lines.append(kv("Hypotheses total:", hyp["total"]))
    lines.append(kv("Hypotheses confirmed:", hyp["confirmed"]))
    lines.append(kv(f"Research studies ({label}):", studies))

    # ── DNA Repository ────────────────────────────────────────────────
    lines.append(section("INSTITUTIONAL DNA"))
    lines.append(kv("DNA total:", dna["total"]))
    lines.append(kv("DNA active:", dna["active"]))
    lines.append(kv("DNA retired:", dna["retired"]))

    # ── Platform Health ───────────────────────────────────────────────
    lines.append(section("PLATFORM HEALTH"))
    health_pct = health * 100
    h_kv = kv_ok if health_pct >= 90 else kv_warn
    lines.append(h_kv("Health score:", f"{health_pct:.0f}%"))
    lines.append(kv("Control Tower DB:", "AVAILABLE" if DB_CONTROL_TOWER.exists() else "MISSING"))
    lines.append(kv("Feature DB:", "AVAILABLE" if FILE_EDE_FEATURES.exists() else "MISSING"))
    lines.append(kv("Hypothesis Registry:", "AVAILABLE" if FILE_HYPOTHESIS_REG.exists() else "MISSING"))

    lines.append(f"\n{hr()}")
    lines.append(f"  Generated: {now_ist_str()}")
    lines.append(hr())
    return "\n".join(lines)
