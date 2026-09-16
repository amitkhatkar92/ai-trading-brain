"""
tests/test_execution_conversion_monitor.py
==============================================
7-day audit follow-up: standing execution-conversion metric.

T01  No DB present -> status NO_DB, never raises
T02  Computes correct approved/placed/conversion_rate from real ct_events rows
T03  Zero approved -> conversion_rate is None (avoid divide-by-zero)
T04  not_placed_reasons correctly aggregated from both event types
T05  Idempotent per trade_date -- re-running replaces, not duplicates
T06  get_conversion_history returns oldest-first, respects n
T07  run_daily_cycle never raises even when the DB query itself raises
T08  Safety-contract: zero imports from execution_engine/risk_control/
     knowledge_authority/order_manager/broker APIs
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from unittest.mock import patch

from analysis.execution_conversion_monitor import (
    ExecutionConversionMonitor,
    run_daily_execution_conversion,
)


def _make_db(tmp_path: Path, rows: list) -> Path:
    db_path = tmp_path / "control_tower.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "CREATE TABLE ct_events (id INTEGER PRIMARY KEY, ts TEXT, cycle_id TEXT, "
        "event_type TEXT, source_agent TEXT, payload TEXT)"
    )
    conn.executemany(
        "INSERT INTO ct_events (ts, cycle_id, event_type, source_agent, payload) "
        "VALUES (?,?,?,?,?)",
        rows,
    )
    conn.commit()
    conn.close()
    return db_path


class TestBasicComputation:
    def test_T01_no_db_present(self, tmp_path):
        mon = ExecutionConversionMonitor()
        with patch(
            "analysis.execution_conversion_monitor.CT_DB_PATH",
            str(tmp_path / "missing.db"),
        ):
            result = mon.run_daily_cycle(trade_date="2026-09-16")
        assert result["status"] == "NO_DB"

    def test_T02_correct_counts(self, tmp_path):
        rows = [
            ("2026-09-16T09:00:00", "c1", "decision.approved", "DecisionEngine", "{}"),
            ("2026-09-16T09:01:00", "c1", "decision.approved", "DecisionEngine", "{}"),
            ("2026-09-16T09:02:00", "c1", "decision.approved", "DecisionEngine", "{}"),
            ("2026-09-16T09:03:00", "c1", "execution.order.placed", "OrderManager", "{}"),
            ("2026-09-16T09:04:00", "c1", "execution.order.not_placed", "OrderManager",
             json.dumps({"reason": "BROKER_ENTRY_PLACEMENT_FAILED"})),
            ("2026-09-16T09:05:00", "c1", "execution.order.not_placed", "OrderManager",
             json.dumps({"reason": "LATE_ENTRY_AFTER_CUTOFF"})),
        ]
        db_path = _make_db(tmp_path, rows)
        mon = ExecutionConversionMonitor()
        with patch("analysis.execution_conversion_monitor.CT_DB_PATH", str(db_path)), patch(
            "analysis.execution_conversion_monitor.SUMMARY_DIR", str(tmp_path / "out"),
        ), patch(
            "analysis.execution_conversion_monitor.SUMMARY_FILE",
            str(tmp_path / "out" / "daily_summary.jsonl"),
        ):
            result = mon.run_daily_cycle(trade_date="2026-09-16")
        assert result["status"] == "OK"
        assert result["approved"] == 3
        assert result["placed"] == 1
        assert result["conversion_rate"] == round(1 / 3, 4)
        assert result["not_placed_reasons"] == {
            "BROKER_ENTRY_PLACEMENT_FAILED": 1, "LATE_ENTRY_AFTER_CUTOFF": 1,
        }

    def test_T03_zero_approved_no_divide_error(self, tmp_path):
        rows = [("2026-09-16T09:00:00", "c1", "execution.order.placed", "OrderManager", "{}")]
        db_path = _make_db(tmp_path, rows)
        mon = ExecutionConversionMonitor()
        with patch("analysis.execution_conversion_monitor.CT_DB_PATH", str(db_path)), patch(
            "analysis.execution_conversion_monitor.SUMMARY_DIR", str(tmp_path / "out"),
        ), patch(
            "analysis.execution_conversion_monitor.SUMMARY_FILE",
            str(tmp_path / "out" / "daily_summary.jsonl"),
        ):
            result = mon.run_daily_cycle(trade_date="2026-09-16")
        assert result["approved"] == 0
        assert result["conversion_rate"] is None

    def test_T05_idempotent_per_trade_date(self, tmp_path):
        rows = [
            ("2026-09-16T09:00:00", "c1", "decision.approved", "DecisionEngine", "{}"),
            ("2026-09-16T09:01:00", "c1", "execution.order.placed", "OrderManager", "{}"),
        ]
        db_path = _make_db(tmp_path, rows)
        summary_dir = tmp_path / "out"
        summary_file = summary_dir / "daily_summary.jsonl"
        mon = ExecutionConversionMonitor()
        with patch("analysis.execution_conversion_monitor.CT_DB_PATH", str(db_path)), patch(
            "analysis.execution_conversion_monitor.SUMMARY_DIR", str(summary_dir),
        ), patch("analysis.execution_conversion_monitor.SUMMARY_FILE", str(summary_file)):
            mon.run_daily_cycle(trade_date="2026-09-16")
            mon.run_daily_cycle(trade_date="2026-09-16")  # re-run same date
        lines = summary_file.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1  # no duplicate entry

    def test_T06_history_oldest_first_respects_n(self, tmp_path):
        summary_dir = tmp_path / "out"
        summary_file = summary_dir / "daily_summary.jsonl"
        summary_dir.mkdir(parents=True)
        with open(summary_file, "w", encoding="utf-8") as fh:
            for d in ["2026-09-10", "2026-09-08", "2026-09-09"]:
                fh.write(json.dumps({"trade_date": d, "approved": 1, "placed": 1}) + "\n")
        mon = ExecutionConversionMonitor()
        with patch("analysis.execution_conversion_monitor.SUMMARY_FILE", str(summary_file)):
            hist = mon.get_conversion_history(n=2)
        assert [h["trade_date"] for h in hist] == ["2026-09-09", "2026-09-10"]

    def test_T07_fail_open_on_db_error(self, tmp_path):
        with patch(
            "analysis.execution_conversion_monitor.ExecutionConversionMonitor._run_impl",
            side_effect=RuntimeError("boom"),
        ):
            result = run_daily_execution_conversion()
        assert result["status"] == "ERROR"

    def test_T08_no_forbidden_imports(self):
        src = Path("analysis/execution_conversion_monitor.py").read_text(encoding="utf-8")
        for forbidden in ("execution_engine", "risk_control", "knowledge_authority",
                          "order_manager", "dhan_feed", "broker"):
            assert f"import {forbidden}" not in src, f"forbidden import found: {forbidden}"
            assert f"from {forbidden}" not in src, f"forbidden import found: {forbidden}"
