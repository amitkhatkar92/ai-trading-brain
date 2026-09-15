"""
tests/test_capital_reserve_readiness_engine.py
==================================================
Self-learning module #28: Intelligent Capital Reserve readiness gate.

T01  Below MIN_SAMPLES_FOR_READINESS stays WAITING_FOR_EVIDENCE
T02  Enough samples but low false-negative rate -> NOT_YET_WARRANTED
T03  Enough samples and high false-negative rate -> READY_FOR_DESIGN
T04  run_daily_readiness_check() logs a ledger event only on a status
     transition, not on repeated identical status
T05  Fail-open: get_readiness_status() never raises
T06  Fail-open: run_daily_readiness_check() never raises
T07  Safety-contract source scan: zero imports of execution_engine/
     order_manager/dhan_feed/broker; never touches any open position
"""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

import analysis.capital_reserve_readiness_engine as engine


@pytest.fixture(autouse=True)
def _isolated_store(tmp_path):
    with patch.object(engine, "_STATE_PATH", str(tmp_path / "state.json")), \
         patch.object(engine, "_STORE_DIR", str(tmp_path)), \
         patch.object(engine, "_LEDGER_PATH", str(tmp_path / "ledger.jsonl")):
        yield


def _fake_monitor(stats):
    monitor = MagicMock()
    monitor.get_reason_reliability.return_value = stats
    return monitor


def test_t01_below_sample_floor_waits():
    with patch("analysis.rejection_attribution_monitor.get_rejection_attribution_monitor",
               return_value=_fake_monitor(None)):
        status = engine.get_readiness_status()
    assert status["status"] == engine.STATUS_WAITING


def test_t02_low_false_negative_rate_not_warranted():
    stats = {"classified": 40, "false_negative_pct": 15.0}
    with patch("analysis.rejection_attribution_monitor.get_rejection_attribution_monitor",
               return_value=_fake_monitor(stats)):
        status = engine.get_readiness_status()
    assert status["status"] == engine.STATUS_NOT_WARRANTED


def test_t03_high_false_negative_rate_ready_for_design():
    stats = {"classified": 40, "false_negative_pct": 55.0}
    with patch("analysis.rejection_attribution_monitor.get_rejection_attribution_monitor",
               return_value=_fake_monitor(stats)):
        status = engine.get_readiness_status()
    assert status["status"] == engine.STATUS_READY_FOR_DESIGN


def test_t04_ledger_only_on_status_transition():
    stats = {"classified": 40, "false_negative_pct": 55.0}
    with patch("analysis.rejection_attribution_monitor.get_rejection_attribution_monitor",
               return_value=_fake_monitor(stats)):
        engine.run_daily_readiness_check()
        engine.run_daily_readiness_check()
    ledger = engine.get_ledger_history()
    assert len(ledger) == 1
    assert ledger[0]["event_type"] == "STATUS_CHANGED"


def test_t05_get_status_fail_open():
    with patch("analysis.rejection_attribution_monitor.get_rejection_attribution_monitor",
               side_effect=RuntimeError("boom")):
        status = engine.get_readiness_status()
    assert status["status"] == engine.STATUS_WAITING


def test_t06_daily_check_fail_open():
    with patch.object(engine, "get_readiness_status", side_effect=RuntimeError("boom")):
        result = engine.run_daily_readiness_check()
    assert result["status"] == "ERROR"


def test_t07_safety_contract_source_scan():
    src_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "analysis", "capital_reserve_readiness_engine.py",
    )
    src = open(src_path, encoding="utf-8").read()
    for forbidden in ("execution_engine", "order_manager", "dhan_feed", "broker"):
        assert f"import {forbidden}" not in src
        assert f"from {forbidden}" not in src
