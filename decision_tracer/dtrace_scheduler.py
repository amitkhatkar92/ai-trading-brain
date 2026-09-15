"""
decision_tracer/dtrace_scheduler.py
======================================
Self-Learning Ecosystem -- Post-roadmap Priority 4: activates
decision_tracer (DTA-001), previously only a standalone, human-invoked
CLI tool (`python -m decision_tracer.dtrace_runner --symbol X`).

Audit finding (before writing any code): decision_tracer is genuinely
diagnostic/explanatory by original design -- it answers "why did the
system decide X for this symbol" after the fact, and its own docstring
scope is READ-ONLY reconstruction of the decision chain. It was never
designed to feed a future trading decision, and this module does NOT
invent that claim: no output here is read back into any live gate.

What was a real, honest gap: nothing ever RAN it automatically. A human
had to know a symbol name and type a CLI command. This module closes
exactly that gap -- automatic daily batch tracing of symbols that had a
real recorded decision today (control_tower.db's ct_decisions/
ct_cycles tables, the same source dtrace_collector.py already reads),
bounded to a small sample per day, with results persisted for
observability (Sandy) instead of only ever existing as a one-off
Markdown file a human had to go looking for.

Safety: read-only w.r.t. all trading/decision state (reuses
dtrace_runner.run_dta(), completely unchanged). Writes only to the
existing data/dta/ report directory (dtrace_reporter.py's own output,
unchanged) and a new, isolated, append-only
data/dta/scheduler/run_history.jsonl. Zero imports of execution_engine,
order_manager, broker APIs, or risk_control. Never raises.
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

from utils import get_logger

log = get_logger(__name__)

_ROOT       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DB_CTRL    = os.path.join(_ROOT, "data", "control_tower.db")
_RUN_DIR    = os.path.join(_ROOT, "data", "dta", "scheduler")
_RUN_HISTORY = os.path.join(_RUN_DIR, "run_history.jsonl")

MAX_SYMBOLS_PER_DAY = 10   # bounded -- each trace reads several JSON/DB stores


def run_daily_trace_batch(trace_date: Optional[str] = None,
                           max_symbols: int = MAX_SYMBOLS_PER_DAY) -> Dict[str, Any]:
    """
    Automatically traces up to max_symbols distinct symbols that had a
    real recorded decision on trace_date (default: today), via the
    existing, unchanged dtrace_runner.run_dta(). Never raises.
    """
    try:
        return _run_impl(trace_date or date.today().isoformat(), max_symbols)
    except Exception as exc:
        log.debug("[DTraceScheduler] batch error: %s", exc)
        return {"status": "ERROR", "error": str(exc)}


def _run_impl(trace_date: str, max_symbols: int) -> Dict[str, Any]:
    symbols = _symbols_with_decision_on(trace_date, max_symbols)
    if not symbols:
        return {"status": "OK", "trace_date": trace_date, "symbols_traced": 0, "traces": []}

    from decision_tracer.dtrace_runner import run_dta

    traces: List[Dict[str, Any]] = []
    for symbol in symbols:
        try:
            result = run_dta(symbol, target_date=trace_date, report_date=trace_date)
            traces.append({
                "symbol": symbol,
                "decision": result.get("decision"),
                "answered": result.get("answered"),
                "total_questions": result.get("total_questions"),
                "report_path": result.get("report_path"),
            })
        except Exception as exc:
            log.debug("[DTraceScheduler] trace failed for %s: %s", symbol, exc)

    summary = {
        "status": "OK",
        "trace_date": trace_date,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "symbols_traced": len(traces),
        "traces": traces,
    }
    _record_run(summary)
    return summary


def _symbols_with_decision_on(trace_date: str, limit: int) -> List[str]:
    if not os.path.exists(_DB_CTRL):
        return []
    try:
        conn = sqlite3.connect(_DB_CTRL, timeout=5)
        try:
            rows = conn.execute(
                """
                SELECT DISTINCT d.symbol
                FROM ct_decisions d
                JOIN ct_cycles c ON d.cycle_id = c.cycle_id
                WHERE date(c.started_at) = ?
                ORDER BY c.started_at DESC
                LIMIT ?
                """,
                (trace_date, limit),
            ).fetchall()
            return [r[0] for r in rows if r[0]]
        finally:
            conn.close()
    except sqlite3.Error as exc:
        log.debug("[DTraceScheduler] symbol query failed: %s", exc)
        return []


def get_last_run_summary() -> Optional[Dict[str, Any]]:
    """Read-only accessor (Sandy-style): most recent batch run, or None."""
    records = _read_jsonl(_RUN_HISTORY)
    return records[-1] if records else None


def get_run_history(n: int = 20) -> List[Dict[str, Any]]:
    """Read-only accessor: last n batch runs, oldest-first."""
    return _read_jsonl(_RUN_HISTORY)[-n:]


def _record_run(summary: Dict[str, Any]) -> None:
    try:
        os.makedirs(_RUN_DIR, exist_ok=True)
        with open(_RUN_HISTORY, "a", encoding="utf-8") as f:
            f.write(json.dumps(summary, default=str) + "\n")
    except OSError as exc:
        log.debug("[DTraceScheduler] history write skipped: %s", exc)


def _read_jsonl(path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        return []
    records: List[Dict[str, Any]] = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        pass
    return records
