"""
live_operations/phase2_premarket_report.py
============================================
Phase 2 — Pre-Market Report (PRE_MARKET_REPORT.md)

Assembles a complete operational briefing from existing data sources:
  - Market regime (from last full cycle's MarketSnapshot)
  - Watchlist candidates (from scanner_memory.json / nifty500_universe.json)
  - Portfolio status (from paper_trades.csv)
  - Cash available (from paper_trading_daily.json)
  - Research alerts (from Scientific Director journal)
  - High-confidence opportunities (from scanner_memory.json)

Read-only. Writes one .md file per day.
"""
from __future__ import annotations

import csv
import json
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from .lol_config import (
    DATA_DIR, FILE_PAPER_TRADES, FILE_DAILY_JSON,
    FILE_STRATEGY_PERF,
)
from .report_writer import (
    report_header, section, kv, kv_warn, kv_ok, hr, badge, now_ist_str
)

IST = timezone(timedelta(hours=5, minutes=30))

_SCANNER_MEMORY   = DATA_DIR / "scanner_memory.json"
_NIFTY500_UNIV    = DATA_DIR / "nifty500_universe.json"
_SD_JOURNAL       = DATA_DIR / "scientific_journal.json"
_REGIME_HIST      = DATA_DIR / "regime_probability_history.json"
_HEALTH_DIR       = DATA_DIR / "health_reports"


def _load_json(path: Path, default: Any = None) -> Any:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _load_paper_trades(today: str) -> Dict:
    """Parse paper_trades.csv and return today's summary."""
    result = {
        "open": [],
        "closed_today": [],
        "pnl_today": 0.0,
        "wins_today": 0,
        "losses_today": 0,
    }
    if not FILE_PAPER_TRADES.exists():
        return result
    try:
        with open(FILE_PAPER_TRADES, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ts  = row.get("timestamp", row.get("date", ""))
                evt = row.get("event", "OPEN")
                if evt == "OPEN" and row.get("exit_price", "") == "":
                    result["open"].append({
                        "symbol":   row.get("symbol", ""),
                        "direction": row.get("direction", ""),
                        "qty":      row.get("quantity", ""),
                        "entry":    row.get("entry_price", ""),
                        "sl":       row.get("stop_loss", ""),
                        "target":   row.get("target", ""),
                        "strategy": row.get("strategy", ""),
                        "conf":     row.get("confidence", ""),
                    })
                elif evt == "CLOSE" and today in str(ts):
                    try:
                        pnl = float(row.get("pnl", 0) or 0)
                    except ValueError:
                        pnl = 0.0
                    result["closed_today"].append({
                        "symbol": row.get("symbol", ""),
                        "pnl":    pnl,
                        "reason": row.get("reason", ""),
                    })
                    result["pnl_today"] += pnl
                    if pnl > 0:
                        result["wins_today"]  += 1
                    else:
                        result["losses_today"] += 1
    except Exception:
        pass
    return result


def _load_daily_json() -> Dict:
    return _load_json(FILE_DAILY_JSON, {})


def _load_regime() -> str:
    hist = _load_json(_REGIME_HIST, {})
    if isinstance(hist, list) and hist:
        last = hist[-1]
        return last.get("regime", last.get("label", "UNKNOWN"))
    if isinstance(hist, dict):
        entries = hist.get("history", hist.get("entries", []))
        if entries:
            return entries[-1].get("regime", "UNKNOWN")
    return "UNKNOWN"


def _load_scanner_memory() -> List[Dict]:
    sm = _load_json(_SCANNER_MEMORY, {})
    if isinstance(sm, dict):
        candidates = sm.get("candidates", sm.get("signals", []))
        return candidates if isinstance(candidates, list) else []
    if isinstance(sm, list):
        return sm
    return []


def _load_sd_alerts() -> List[str]:
    journal = _load_json(_SD_JOURNAL, {})
    if not journal:
        return []
    entries = journal.get("entries", journal if isinstance(journal, list) else [])
    alerts = []
    today = date.today().isoformat()
    for e in (entries or []):
        if isinstance(e, dict):
            ts  = str(e.get("timestamp", e.get("date", "")))
            sev = str(e.get("severity", e.get("level", "INFO"))).upper()
            msg = str(e.get("message", e.get("content", "")))
            if today in ts or sev in ("CRITICAL", "HIGH", "WARNING"):
                alerts.append(f"[{sev}] {msg[:120]}")
    return alerts[-10:]   # last 10


def _load_last_cycle_health() -> str:
    if not _HEALTH_DIR.exists():
        return "No health reports"
    reports = sorted(_HEALTH_DIR.glob("*.json"), reverse=True)
    if not reports:
        return "No health reports"
    try:
        with open(reports[0], encoding="utf-8") as f:
            d = json.load(f)
        verdict = d.get("verdict", d.get("health", "UNKNOWN"))
        cycle   = d.get("cycle_id", reports[0].stem)
        return f"Last cycle={cycle}  verdict={verdict}"
    except Exception:
        return "Health report unreadable"


def generate_premarket_report(report_date: Optional[str] = None) -> str:
    if report_date is None:
        report_date = date.today().isoformat()

    today_str = report_date
    trades    = _load_paper_trades(today_str)
    daily     = _load_daily_json()
    regime    = _load_regime()
    scanner   = _load_scanner_memory()
    sd_alerts = _load_sd_alerts()
    cycle_h   = _load_last_cycle_health()

    import config as _cfg
    capital       = getattr(_cfg, "TOTAL_CAPITAL", 0)
    paper_mode    = getattr(_cfg, "PAPER_TRADING", True)
    active_broker = getattr(_cfg, "ACTIVE_BROKER", "unknown")

    pilot_cap  = daily.get("pilot_capital", capital)
    cum_pnl    = daily.get("cumulative", {}).get("cum_pnl", 0)
    cum_ret    = daily.get("cumulative", {}).get("cum_return_pct", 0)
    cash       = pilot_cap + cum_pnl  # rough available cash

    lines: List[str] = [
        report_header("PRE-MARKET REPORT", report_date,
                      f"Mode: {'PAPER' if paper_mode else 'LIVE'}  Broker: {active_broker.upper()}")
    ]

    # ── Market Regime ───────────────────────────────────────────────────
    lines.append(section("TODAY'S MARKET REGIME"))
    lines.append(kv("Regime:",         regime))
    lines.append(kv("Report date:",    report_date))
    try:
        from data_feeds import get_feed_manager
        fm = get_feed_manager()
        q  = fm.yahoo.get_quote("NIFTY")
        if q:
            lines.append(kv("NIFTY (last close):", f"₹{q.close:,.2f}"))
        q2 = fm.yahoo.get_quote("INDIAVIX")
        if q2:
            vix = q2.close
            vix_note = "ELEVATED" if vix > 20 else "NORMAL"
            lines.append(kv("India VIX:", f"{vix:.1f}  [{vix_note}]"))
    except Exception:
        lines.append(kv("Market data:", "Unavailable — check feed"))

    # ── Portfolio Status ────────────────────────────────────────────────
    lines.append(section("PORTFOLIO STATUS"))
    lines.append(kv("Trading capital:",   f"₹{pilot_cap:,.0f}"))
    lines.append(kv("Cumulative P&L:",    f"₹{cum_pnl:+,.0f}  ({cum_ret:+.2f}%)"))
    lines.append(kv("Est. cash available:", f"₹{cash:,.0f}"))
    lines.append(kv("Open positions:",    len(trades["open"])))

    if trades["open"]:
        lines.append("\n  Open Positions:")
        for pos in trades["open"][:15]:
            conf = f"conf={pos['conf']}" if pos['conf'] else ""
            lines.append(f"    {pos['symbol']:<14} {pos['direction']:<5} qty={pos['qty']:<5}"
                         f" entry=₹{pos['entry']:<8} sl=₹{pos['sl']:<8} {conf}")
    else:
        lines.append("  No open positions.")

    # ── Watchlist / High-Confidence Opportunities ──────────────────────
    lines.append(section("HIGH CONFIDENCE OPPORTUNITIES"))
    if scanner:
        # Sort by confidence if available
        try:
            scored = sorted(
                [s for s in scanner if isinstance(s, dict)],
                key=lambda x: float(x.get("confidence", x.get("score", 0))),
                reverse=True
            )[:10]
        except Exception:
            scored = scanner[:10]

        if scored:
            for sig in scored:
                sym   = sig.get("symbol", "?")
                conf  = sig.get("confidence", sig.get("score", "?"))
                dir_  = sig.get("direction", sig.get("side", "?"))
                strat = sig.get("strategy", "?")
                lines.append(f"    {sym:<14} {dir_:<5} conf={conf}  strategy={strat}")
        else:
            lines.append("  No scanner candidates available.")
    else:
        lines.append("  No scanner memory loaded (run pre-market scan first).")

    # ── Research / SD Alerts ────────────────────────────────────────────
    lines.append(section("SCIENTIFIC DIRECTOR NOTES"))
    if sd_alerts:
        for alert in sd_alerts:
            lines.append(f"  {alert}")
    else:
        lines.append("  No SD alerts for today.")

    # ── System Health ───────────────────────────────────────────────────
    lines.append(section("SYSTEM HEALTH (LAST CYCLE)"))
    lines.append(f"  {cycle_h}")

    lines.append(f"\n{hr()}")
    lines.append(f"  Generated: {now_ist_str()}")
    lines.append(hr())

    return "\n".join(lines)
