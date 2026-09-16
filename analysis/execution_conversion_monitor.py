"""
analysis/execution_conversion_monitor.py
============================================
Self-Learning Ecosystem follow-up (7-day layer-wise rejection audit,
2026-09-16): standing daily metric for the approved->placed execution
conversion rate.

Audit finding: of 59 decision-engine-approved signals over 7 trading
days, only 3 (5%) ever became a real placed order -- with zero existing
visibility or alerting on this gap. This module closes that gap with a
lightweight, read-only daily summary, mirroring the established pattern
in analysis/rejection_attribution_monitor.py.

Reads only control_tower.db's ct_events table (decision.approved,
execution.order.placed, execution.order.not_placed, execution.order.
rejected event types -- see communication/events.py::EventType). Never
writes to ct_events/ct_decisions, never touches execution_engine,
risk_control, or knowledge_authority. Purely observational.
"""
from __future__ import annotations

import json
import os
import sqlite3
from collections import Counter
from datetime import date
from typing import Any, Dict, List, Optional

from utils import get_logger

log = get_logger(__name__)

_ROOT       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CT_DB_PATH  = os.path.join(_ROOT, "data", "control_tower.db")
SUMMARY_DIR = os.path.join(_ROOT, "data", "execution_conversion")
SUMMARY_FILE = os.path.join(SUMMARY_DIR, "daily_summary.jsonl")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(CT_DB_PATH, timeout=1)
    conn.execute("PRAGMA busy_timeout = 800")
    conn.row_factory = sqlite3.Row
    return conn


class ExecutionConversionMonitor:
    """Standing agent: measures the approved -> actually-placed conversion rate."""

    def run_daily_cycle(self, trade_date: Optional[str] = None) -> Dict[str, Any]:
        """Compute today's (or `trade_date`'s) conversion summary. Never raises."""
        try:
            return self._run_impl(trade_date or date.today().isoformat())
        except Exception as exc:
            log.debug("[ExecutionConversionMonitor] cycle error: %s", exc)
            return {"status": "ERROR", "error": str(exc)}

    def _run_impl(self, trade_date: str) -> Dict[str, Any]:
        if not os.path.exists(CT_DB_PATH):
            return {"status": "NO_DB", "trade_date": trade_date}

        conn = _connect()
        try:
            rows = conn.execute(
                "SELECT event_type, payload FROM ct_events WHERE ts LIKE ?",
                (f"{trade_date}%",),
            ).fetchall()
        finally:
            conn.close()

        approved = sum(1 for r in rows if r["event_type"] == "decision.approved")
        placed   = sum(1 for r in rows if r["event_type"] == "execution.order.placed")

        not_placed_reasons: Counter = Counter()
        for r in rows:
            if r["event_type"] not in ("execution.order.not_placed", "execution.order.rejected"):
                continue
            try:
                payload = json.loads(r["payload"]) if r["payload"] else {}
            except Exception:
                payload = {}
            reason = payload.get("reason", "UNKNOWN")
            not_placed_reasons[reason] += 1

        conversion_rate = round(placed / approved, 4) if approved > 0 else None
        dominant_reason = not_placed_reasons.most_common(1)[0][0] if not_placed_reasons else None

        summary = {
            "status":           "OK",
            "trade_date":       trade_date,
            "approved":         approved,
            "placed":           placed,
            "conversion_rate":  conversion_rate,
            "not_placed_reasons": dict(not_placed_reasons),
            "dominant_not_placed_reason": dominant_reason,
        }
        self._write_daily_summary(summary)
        return summary

    def _write_daily_summary(self, summary: Dict[str, Any]) -> None:
        try:
            os.makedirs(SUMMARY_DIR, exist_ok=True)
            # Idempotent per trade_date: replace any existing entry for the
            # same date rather than appending duplicates on same-day re-runs.
            existing: List[Dict[str, Any]] = []
            if os.path.exists(SUMMARY_FILE):
                with open(SUMMARY_FILE, encoding="utf-8") as fh:
                    for line in fh:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            rec = json.loads(line)
                            if rec.get("trade_date") != summary["trade_date"]:
                                existing.append(rec)
                        except Exception:
                            continue
            existing.append(summary)
            with open(SUMMARY_FILE, "w", encoding="utf-8") as fh:
                for rec in existing:
                    fh.write(json.dumps(rec) + "\n")
        except Exception as exc:
            log.debug("[ExecutionConversionMonitor] summary write skipped: %s", exc)

    def get_conversion_history(self, n: int = 7) -> List[Dict[str, Any]]:
        """Read-only accessor: last n daily summaries, oldest first. Never raises."""
        try:
            if not os.path.exists(SUMMARY_FILE):
                return []
            records: List[Dict[str, Any]] = []
            with open(SUMMARY_FILE, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        records.append(json.loads(line))
                    except Exception:
                        continue
            records.sort(key=lambda r: r.get("trade_date", ""))
            return records[-n:]
        except Exception:
            return []


_monitor: Optional[ExecutionConversionMonitor] = None


def get_execution_conversion_monitor() -> ExecutionConversionMonitor:
    global _monitor
    if _monitor is None:
        _monitor = ExecutionConversionMonitor()
    return _monitor


def run_daily_execution_conversion() -> Dict[str, Any]:
    """Convenience entrypoint for master_orchestrator's EOD stage. Never raises."""
    try:
        return get_execution_conversion_monitor().run_daily_cycle()
    except Exception as exc:
        return {"status": "ERROR", "error": str(exc)}
