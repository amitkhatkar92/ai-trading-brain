"""
tests/test_options_health_history.py
========================================
Item #10: Options Health Metrics Dashboard.

T01  record_daily_options_health_snapshot() persists one record per
     tracked symbol with a live chain
T02  Same-day re-trigger is a guarded no-op
T03  get_options_health_status() reports WAITING_FOR_EVIDENCE below
     MIN_HISTORY_DAYS
T04  get_options_health_status() computes real averages once gated
     evidence exists
T05  A symbol with no chain state is skipped, not recorded
T06  Fail-open: record_daily_options_health_snapshot() never raises
T07  Fail-open: get_options_health_status() never raises
T08  Safety-contract source scan
"""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

import data_feeds.options_health_history as oph


@pytest.fixture(autouse=True)
def _isolated_store(tmp_path):
    with patch.object(oph, "_STORE_DIR", str(tmp_path)), \
         patch.object(oph, "_HISTORY_PATH", str(tmp_path / "options_health_history.jsonl")), \
         patch.object(oph, "_STATE_PATH", str(tmp_path / "state.json")):
        yield


def _fake_chain(strike_count=10, with_oi=8, pcr=1.0):
    contracts = []
    for i in range(strike_count):
        c = MagicMock()
        c.open_interest = 100 if i < with_oi else 0
        contracts.append(c)
    chain = MagicMock()
    chain.contracts = contracts
    chain.pcr = pcr
    return chain


def _fake_feed_manager(chain, source="DHAN", is_live=True):
    from datetime import datetime
    fm = MagicMock()
    fm.get_options_chain_state_snapshot.return_value = {
        "chain": chain, "source": source, "is_live": is_live, "fetched_at": datetime.now(),
    }
    return fm


def test_t01_snapshot_persists_one_record_per_symbol():
    fm = _fake_feed_manager(_fake_chain())
    with patch("data_feeds.get_feed_manager", return_value=fm):
        result = oph.record_daily_options_health_snapshot(trade_date="2026-09-01")
    assert result["recorded"] == len(oph.TRACKED_SYMBOLS)
    recs = oph.get_records()
    assert len(recs) == len(oph.TRACKED_SYMBOLS)


def test_t02_same_day_retrigger_noop():
    fm = _fake_feed_manager(_fake_chain())
    with patch("data_feeds.get_feed_manager", return_value=fm):
        oph.record_daily_options_health_snapshot(trade_date="2026-09-01")
        result = oph.record_daily_options_health_snapshot(trade_date="2026-09-01")
    assert result.get("skipped") == "already_recorded_today"


def test_t03_below_history_floor_waits():
    fm = _fake_feed_manager(_fake_chain())
    with patch("data_feeds.get_feed_manager", return_value=fm):
        oph.record_daily_options_health_snapshot(trade_date="2026-09-01")
    status = oph.get_options_health_status("NIFTY")
    assert status["status"] == "WAITING_FOR_EVIDENCE"


def test_t04_gated_status_computes_averages():
    for i in range(7):
        fm = _fake_feed_manager(_fake_chain(strike_count=10, with_oi=8, pcr=1.0))
        with patch("data_feeds.get_feed_manager", return_value=fm):
            oph.record_daily_options_health_snapshot(trade_date=f"2026-09-{i+1:02d}")
    status = oph.get_options_health_status("NIFTY")
    assert status["status"] == "ACTIVE"
    assert status["avg_strike_count"] == 10
    assert status["avg_oi_coverage_pct"] == 80.0


def test_t05_no_chain_state_skipped():
    fm = MagicMock()
    fm.get_options_chain_state_snapshot.return_value = {}
    with patch("data_feeds.get_feed_manager", return_value=fm):
        result = oph.record_daily_options_health_snapshot(trade_date="2026-09-01")
    assert result["recorded"] == 0


def test_t06_fail_open_on_snapshot():
    with patch("data_feeds.get_feed_manager", side_effect=RuntimeError("boom")):
        result = oph.record_daily_options_health_snapshot(trade_date="2026-09-01")
    assert result["status"] == "OK"   # per-symbol snapshot fails open, batch still OK
    assert result["recorded"] == 0


def test_t07_fail_open_on_status():
    with patch.object(oph, "get_history_days_count", side_effect=RuntimeError("boom")):
        status = oph.get_options_health_status("NIFTY")
    assert status["status"] == "WAITING_FOR_EVIDENCE"


def test_t08_safety_contract_source_scan():
    src_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data_feeds", "options_health_history.py",
    )
    src = open(src_path, encoding="utf-8").read()
    for forbidden in ("execution_engine", "order_manager", "broker"):
        assert f"import {forbidden}" not in src
        assert f"from {forbidden}" not in src
