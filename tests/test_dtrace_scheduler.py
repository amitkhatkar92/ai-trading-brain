"""
tests/test_dtrace_scheduler.py
=================================
Self-Learning Ecosystem -- Post-roadmap Priority 4: activation of
decision_tracer via decision_tracer/dtrace_scheduler.py.

T01  No decisions recorded for the trace_date -> zero symbols traced,
     run_dta() never called
T02  Distinct symbols with a decision on trace_date are traced via the
     existing, unchanged run_dta() -- bounded to max_symbols
T03  A per-symbol trace failure does not block tracing the remaining
     symbols
T04  get_last_run_summary() / get_run_history() read back correctly,
     oldest-first
T05  Fail-open: never raises when the control_tower.db query itself
     raises
T06  Fail-open: never raises when run_dta() itself raises for every
     symbol
T07  Safety contract: zero imports of execution_engine/order_manager/
     dhan_feed/broker/risk_control anywhere in this module
"""
from __future__ import annotations

import json
import sqlite3
from unittest.mock import patch

import pytest

import decision_tracer.dtrace_scheduler as sched


@pytest.fixture(autouse=True)
def _isolated_history(tmp_path):
    history_file = tmp_path / "run_history.jsonl"
    with patch.object(sched, "_RUN_DIR", str(tmp_path)), \
         patch.object(sched, "_RUN_HISTORY", str(history_file)):
        yield history_file


@pytest.fixture
def _real_db(tmp_path):
    db_path = tmp_path / "control_tower.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE ct_cycles (cycle_id TEXT PRIMARY KEY, started_at TEXT)")
    conn.execute("CREATE TABLE ct_decisions (symbol TEXT, cycle_id TEXT)")
    conn.commit()
    conn.close()
    with patch.object(sched, "_DB_CTRL", str(db_path)):
        yield db_path


def _seed(db_path, rows):
    conn = sqlite3.connect(str(db_path))
    for i, (symbol, started_at) in enumerate(rows):
        cycle_id = f"CYC{i}"
        conn.execute("INSERT INTO ct_cycles (cycle_id, started_at) VALUES (?, ?)", (cycle_id, started_at))
        conn.execute("INSERT INTO ct_decisions (symbol, cycle_id) VALUES (?, ?)", (symbol, cycle_id))
    conn.commit()
    conn.close()


def test_t01_no_decisions_zero_symbols(_real_db):
    with patch("decision_tracer.dtrace_runner.run_dta") as mock_run:
        result = sched.run_daily_trace_batch(trace_date="2026-09-15")
    mock_run.assert_not_called()
    assert result["status"] == "OK"
    assert result["symbols_traced"] == 0


def test_t02_distinct_symbols_traced_bounded(_real_db):
    _seed(_real_db, [
        ("RELIANCE", "2026-09-15 09:30:00"),
        ("TCS", "2026-09-15 09:31:00"),
        ("RELIANCE", "2026-09-15 09:32:00"),  # duplicate symbol, different cycle
    ])
    with patch("decision_tracer.dtrace_runner.run_dta") as mock_run:
        mock_run.return_value = {"decision": "APPROVED", "answered": 5, "total_questions": 8, "report_path": "x.md"}
        result = sched.run_daily_trace_batch(trace_date="2026-09-15", max_symbols=10)
    assert result["symbols_traced"] == 2   # RELIANCE + TCS, deduped
    assert mock_run.call_count == 2


def test_t03_one_symbol_failure_does_not_block_others(_real_db):
    _seed(_real_db, [("RELIANCE", "2026-09-15 09:30:00"), ("TCS", "2026-09-15 09:31:00")])
    def _side_effect(symbol, **kwargs):
        if symbol == "RELIANCE":
            raise RuntimeError("boom")
        return {"decision": "REJECTED", "answered": 4, "total_questions": 8, "report_path": "y.md"}
    with patch("decision_tracer.dtrace_runner.run_dta", side_effect=_side_effect):
        result = sched.run_daily_trace_batch(trace_date="2026-09-15")
    assert result["symbols_traced"] == 1
    assert result["traces"][0]["symbol"] == "TCS"


def test_t04_run_history_read_back_oldest_first(_isolated_history):
    sched._record_run({"status": "OK", "trace_date": "2026-09-01", "symbols_traced": 1})
    sched._record_run({"status": "OK", "trace_date": "2026-09-08", "symbols_traced": 3})
    latest = sched.get_last_run_summary()
    assert latest["symbols_traced"] == 3
    hist = sched.get_run_history(n=10)
    assert [h["symbols_traced"] for h in hist] == [1, 3]


def test_t05_fail_open_on_db_query_error(tmp_path):
    bad_db = tmp_path / "not_a_real_db_but_exists.db"
    bad_db.write_text("not a real sqlite file", encoding="utf-8")
    with patch.object(sched, "_DB_CTRL", str(bad_db)):
        result = sched.run_daily_trace_batch(trace_date="2026-09-15")
    assert result["status"] == "OK"
    assert result["symbols_traced"] == 0


def test_t06_fail_open_when_run_dta_always_raises(_real_db):
    _seed(_real_db, [("RELIANCE", "2026-09-15 09:30:00")])
    with patch("decision_tracer.dtrace_runner.run_dta", side_effect=RuntimeError("boom")):
        result = sched.run_daily_trace_batch(trace_date="2026-09-15")
    assert result["status"] == "OK"
    assert result["symbols_traced"] == 0


def test_t07_no_forbidden_imports():
    import os
    src_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "decision_tracer", "dtrace_scheduler.py",
    )
    src = open(src_path, encoding="utf-8").read()
    for forbidden in ("execution_engine", "order_manager", "dhan_feed", "broker", "risk_control"):
        assert f"import {forbidden}" not in src, f"forbidden import found: {forbidden}"
        assert f"from {forbidden}" not in src, f"forbidden import found: {forbidden}"
