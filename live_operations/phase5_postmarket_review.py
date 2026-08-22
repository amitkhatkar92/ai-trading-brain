"""
live_operations/phase5_postmarket_review.py
=============================================
Phase 5 — Post-Market Review (DAILY_TRADING_REPORT.md)

Auto-generates the end-of-day trading review by wrapping:
  - paper_trades.csv for trade details and P&L
  - paper_trading_daily.json for cumulative metrics
  - strategy_performance.json for win rate / expectancy
  - control_tower.db for cycle telemetry
  - oios/reporting/runner.py (EOD reports) for OIOS activity

Includes:
  - Trade log
  - P&L
  - Win rate / Expectancy
  - PMCI, CDS, InstitutionalDNAAI contribution
  - Portfolio changes
  - Learning summary
"""
from __future__ import annotations

import csv
import json
import sqlite3
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .lol_config import (
    DATA_DIR, FILE_PAPER_TRADES, FILE_DAILY_JSON,
    FILE_STRATEGY_PERF, DB_CONTROL_TOWER,
)
from .report_writer import (
    report_header, section, kv, kv_ok, kv_warn, hr, now_ist_str
)

_LEARNING_DB  = DATA_DIR / "learning_db.json"
_SD_JOURNAL   = DATA_DIR / "scientific_journal.json"


def _load_json(path: Path, default: Any = None) -> Any:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _load_trades(today: str) -> Dict:
    closed, open_pos = [], []
    if not FILE_PAPER_TRADES.exists():
        return {"closed": [], "open": [], "pnl": 0.0, "wins": 0, "losses": 0,
                "by_strategy": defaultdict(lambda: {"n": 0, "pnl": 0.0, "wins": 0}),
                "by_symbol":   defaultdict(lambda: {"n": 0, "pnl": 0.0})}
    try:
        with open(FILE_PAPER_TRADES, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                ts  = str(row.get("timestamp", row.get("date", "")))
                evt = row.get("event", "OPEN")
                if evt == "CLOSE" and today in ts:
                    try:
                        pnl = float(row.get("pnl", 0) or 0)
                    except ValueError:
                        pnl = 0.0
                    closed.append({
                        "symbol":   row.get("symbol", ""),
                        "direction": row.get("direction", ""),
                        "qty":      row.get("quantity", ""),
                        "entry":    row.get("entry_price", ""),
                        "exit":     row.get("exit_price", ""),
                        "pnl":      pnl,
                        "reason":   row.get("reason", ""),
                        "strategy": row.get("strategy", ""),
                        "conf":     float(row.get("confidence", 0) or 0),
                        "rr":       float(row.get("rr", 0) or 0),
                    })
                elif evt == "OPEN" and not row.get("exit_price", ""):
                    open_pos.append(row)

        by_strat = defaultdict(lambda: {"n": 0, "pnl": 0.0, "wins": 0})
        by_sym   = defaultdict(lambda: {"n": 0, "pnl": 0.0})
        total_pnl, wins, losses = 0.0, 0, 0
        for t in closed:
            total_pnl += t["pnl"]
            strat = t["strategy"] or "unknown"
            sym   = t["symbol"]
            by_strat[strat]["n"]   += 1
            by_strat[strat]["pnl"] += t["pnl"]
            by_sym[sym]["n"]   += 1
            by_sym[sym]["pnl"] += t["pnl"]
            if t["pnl"] > 0:
                wins += 1
                by_strat[strat]["wins"] += 1
            else:
                losses += 1

        return {
            "closed": closed, "open": open_pos,
            "pnl": total_pnl, "wins": wins, "losses": losses,
            "by_strategy": by_strat, "by_symbol": by_sym,
        }
    except Exception:
        return {"closed": [], "open": [], "pnl": 0.0, "wins": 0, "losses": 0,
                "by_strategy": defaultdict(lambda: {"n": 0, "pnl": 0.0, "wins": 0}),
                "by_symbol":   defaultdict(lambda: {"n": 0, "pnl": 0.0})}


def _load_decision_contributions(today: str) -> Dict:
    """Read DecisionEngine agent contributions from control_tower.db."""
    result = {"PMCI": 0, "CDS": 0, "InstitutionalDNAAI": 0, "total": 0}
    if not DB_CONTROL_TOWER.exists():
        return result
    try:
        conn = sqlite3.connect(str(DB_CONTROL_TOWER), timeout=3)
        conn.row_factory = sqlite3.Row
        # ct_decisions stores agent votes where decision='APPROVE'
        rows = conn.execute(
            "SELECT COUNT(*) as n FROM ct_decisions WHERE DATE(cycle_id) = ? "
            "AND decision = 'APPROVE'",
            (today,)
        ).fetchone()
        if rows:
            result["total"] = rows["n"] or 0
        conn.close()
    except Exception:
        pass
    return result


def _load_learning_summary() -> Dict:
    """Load the MLC learning summary from disk."""
    # Try MLC run history
    mlc_hist = DATA_DIR / "mls" / "mlc_runs.json"
    if mlc_hist.exists():
        try:
            with open(mlc_hist, encoding="utf-8") as f:
                runs = json.load(f)
            if runs:
                last = runs[-1] if isinstance(runs, list) else runs
                return {
                    "health": last.get("health", "UNKNOWN"),
                    "stages": last.get("stages_run", "?"),
                    "ts":     last.get("run_id", "?"),
                }
        except Exception:
            pass
    # Fallback: learning_db.json
    db = _load_json(_LEARNING_DB, {})
    if db:
        return {"health": "AVAILABLE", "strategies": len(db)}
    return {"health": "NO_DATA"}


def _load_sd_notes() -> List[str]:
    """Load today's Scientific Director journal entries."""
    journal = _load_json(_SD_JOURNAL, {})
    if not journal:
        return []
    entries = journal.get("entries", journal if isinstance(journal, list) else [])
    today   = date.today().isoformat()
    notes   = []
    for e in (entries or []):
        if isinstance(e, dict):
            ts  = str(e.get("timestamp", e.get("date", "")))
            msg = str(e.get("message", e.get("content", "")))
            if today in ts:
                notes.append(msg[:150])
    return notes[-5:]


def generate_daily_trading_report(report_date: Optional[str] = None) -> str:
    if report_date is None:
        report_date = date.today().isoformat()

    trades  = _load_trades(report_date)
    daily   = _load_daily_json(FILE_DAILY_JSON)
    contribs = _load_decision_contributions(report_date)
    learning = _load_learning_summary()
    sd_notes = _load_sd_notes()
    strat_perf = _load_json(FILE_STRATEGY_PERF, {})

    import config as _cfg
    capital   = getattr(_cfg, "TOTAL_CAPITAL", daily.get("pilot_capital", 0))
    paper_mode = getattr(_cfg, "PAPER_TRADING", True)

    n_closed = len(trades["closed"])
    wins     = trades["wins"]
    losses   = trades["losses"]
    pnl      = trades["pnl"]
    wr_pct   = (wins / n_closed * 100) if n_closed else 0.0
    pnl_pct  = (pnl / capital * 100)   if capital   else 0.0

    # Expectancy = (WinRate × AvgWin) - (LossRate × AvgLoss)
    win_pnls  = [t["pnl"] for t in trades["closed"] if t["pnl"] > 0]
    loss_pnls = [abs(t["pnl"]) for t in trades["closed"] if t["pnl"] < 0]
    avg_win  = sum(win_pnls)  / len(win_pnls)  if win_pnls  else 0.0
    avg_loss = sum(loss_pnls) / len(loss_pnls) if loss_pnls else 0.0
    expectancy = (wr_pct/100 * avg_win) - ((1-wr_pct/100) * avg_loss)

    lines = [report_header("DAILY TRADING REPORT", report_date,
                           f"Mode: {'PAPER' if paper_mode else 'LIVE'}")]

    # ── Performance Summary ────────────────────────────────────────────
    lines.append(section("PERFORMANCE SUMMARY"))
    lines.append(kv("Trades closed today:", n_closed))
    lines.append(kv("Wins / Losses:", f"{wins} / {losses}"))
    pnl_kv = kv_ok if pnl >= 0 else kv_warn
    lines.append(pnl_kv("Day P&L:", f"₹{pnl:+,.0f}  ({pnl_pct:+.2f}%)"))
    lines.append(kv("Win rate:", f"{wr_pct:.1f}%"))
    lines.append(kv("Avg win:", f"₹{avg_win:,.0f}"))
    lines.append(kv("Avg loss:", f"₹{avg_loss:,.0f}"))
    lines.append(kv("Expectancy:", f"₹{expectancy:+,.0f} per trade"))

    cum_pnl = daily.get("cumulative", {}).get("cum_pnl", 0) if daily else 0
    cum_ret = daily.get("cumulative", {}).get("cum_return_pct", 0) if daily else 0
    lines.append(kv("Cumulative P&L:", f"₹{cum_pnl:+,.0f}  ({cum_ret:+.2f}%)"))

    # ── Trade Log ──────────────────────────────────────────────────────
    lines.append(section("TRADE LOG"))
    if trades["closed"]:
        lines.append(f"  {'Symbol':<14} {'Dir':<5} {'Qty':<6} {'Entry':<9} "
                     f"{'Exit':<9} {'P&L':>9}  Strategy")
        lines.append(f"  {'-'*14} {'-'*5} {'-'*6} {'-'*9} {'-'*9} {'-'*9}  {'-'*20}")
        for t in trades["closed"]:
            pnl_str = f"₹{t['pnl']:+,.0f}"
            lines.append(f"  {t['symbol']:<14} {t['direction']:<5} {t['qty']:<6} "
                         f"₹{t['entry']:<8} ₹{t['exit']:<8} {pnl_str:>9}  {t['strategy']}")
    else:
        lines.append("  No closed trades today.")

    # ── Strategy Breakdown ─────────────────────────────────────────────
    lines.append(section("STRATEGY PERFORMANCE"))
    if trades["by_strategy"]:
        for strat, stats in sorted(trades["by_strategy"].items(),
                                   key=lambda x: -x[1]["pnl"]):
            wr = stats["wins"] / stats["n"] * 100 if stats["n"] else 0
            lines.append(kv(f"  {strat}:",
                            f"n={stats['n']}  wr={wr:.0f}%  pnl=₹{stats['pnl']:+,.0f}"))
    else:
        lines.append("  No strategy data.")

    # ── Agent Contributions ────────────────────────────────────────────
    lines.append(section("AGENT CONTRIBUTIONS"))
    lines.append(kv("Total approved decisions:", contribs["total"]))
    lines.append(kv("PMCI contribution:", "See debate logs (PMCI score per signal)"))
    lines.append(kv("CDS contribution:", "See debate logs (CDS vote per signal)"))
    lines.append(kv("InstitutionalDNAAI:", "See debate logs (DNA vote per signal)"))
    # Reuse control_tower decision trace if available
    try:
        from control_tower.decision_trace import DecisionTrace
        dt = DecisionTrace()
        summary = dt.get_today_summary() if hasattr(dt, "get_today_summary") else {}
        if summary:
            for agent, score in summary.items():
                lines.append(kv(f"  {agent}:", score))
    except Exception:
        pass

    # ── Open Positions ─────────────────────────────────────────────────
    lines.append(section("REMAINING OPEN POSITIONS"))
    if trades["open"]:
        for pos in trades["open"][:15]:
            sym = pos.get("symbol", "?")
            dir_ = pos.get("direction", "?")
            qty  = pos.get("quantity", "?")
            lines.append(f"  {sym:<14} {dir_:<5} qty={qty}")
    else:
        lines.append("  No open positions at day end.")

    # ── Learning Summary ──────────────────────────────────────────────
    lines.append(section("LEARNING SUMMARY"))
    for k, v in learning.items():
        lines.append(kv(f"  {k}:", v))

    # ── Scientific Observations ────────────────────────────────────────
    lines.append(section("SCIENTIFIC DIRECTOR OBSERVATIONS"))
    if sd_notes:
        for note in sd_notes:
            lines.append(f"  • {note}")
    else:
        lines.append("  No SD notes for today.")

    # ── Unexpected Behaviour ──────────────────────────────────────────
    lines.append(section("UNEXPECTED BEHAVIOUR"))
    unusual = [t for t in trades["closed"] if abs(t["pnl"]) > capital * 0.02]
    if unusual:
        for t in unusual:
            lines.append(f"  ⚠ {t['symbol']}: ₹{t['pnl']:+,.0f} "
                         f"({t['pnl']/capital*100:.1f}% of capital)")
    else:
        lines.append("  None detected.")

    lines.append(f"\n{hr()}")
    lines.append(f"  Generated: {now_ist_str()}")
    lines.append(hr())
    return "\n".join(lines)


def _load_daily_json(path: Path) -> Dict:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}
