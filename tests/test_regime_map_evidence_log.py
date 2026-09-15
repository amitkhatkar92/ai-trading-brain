"""
tests/test_regime_map_evidence_log.py
========================================
Self-Learning Ecosystem -- Post-roadmap Priority 5 (part 1): ACQUISITION
for meta_learning/regime_map_evidence_log.py.

T01  record_regime_trade() appends a correctly-shaped JSONL record
T02  get_records() filters by regime and/or strategy correctly
T03  get_records() returns time-ordered (oldest-first) records
T04  get_pairs_with_evidence() returns distinct (regime, strategy) pairs
T05  Fail-open: record_regime_trade() never raises on I/O error
T06  Fail-open: get_records() never raises on corrupt lines (skips them)
T07  Safety contract: zero imports of execution_engine/order_manager/
     dhan_feed/broker/risk_control
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

import meta_learning.regime_map_evidence_log as evlog


@pytest.fixture(autouse=True)
def _isolated_store(tmp_path):
    path = tmp_path / "regime_map_evidence.jsonl"
    with patch.object(evlog, "_EVIDENCE_PATH", str(path)), \
         patch.object(evlog, "_STORE_DIR", str(tmp_path)):
        yield path


def test_t01_record_shape(_isolated_store):
    evlog.record_regime_trade("BULL_TREND", "Breakout_Volume", r_multiple=1.5, won=True, order_id="ORD1")
    recs = evlog.get_records()
    assert len(recs) == 1
    rec = recs[0]
    assert rec["regime"] == "BULL_TREND"
    assert rec["strategy"] == "Breakout_Volume"
    assert rec["r_multiple"] == 1.5
    assert rec["won"] is True
    assert rec["order_id"] == "ORD1"
    assert "timestamp" in rec


def test_t02_filter_by_regime_and_strategy(_isolated_store):
    evlog.record_regime_trade("BULL_TREND", "Breakout_Volume", r_multiple=1.0, won=True)
    evlog.record_regime_trade("BEAR_MARKET", "Hedging_Model", r_multiple=-0.5, won=False)
    evlog.record_regime_trade("BULL_TREND", "Momentum_Retest", r_multiple=0.5, won=True)

    assert len(evlog.get_records(regime="BULL_TREND")) == 2
    assert len(evlog.get_records(strategy="Hedging_Model")) == 1
    assert len(evlog.get_records(regime="BULL_TREND", strategy="Momentum_Retest")) == 1
    assert len(evlog.get_records(regime="VOLATILE")) == 0


def test_t03_time_ordered_oldest_first(_isolated_store):
    for i in range(5):
        evlog.record_regime_trade("RANGE_MARKET", "Mean_Reversion", r_multiple=float(i), won=True)
    recs = evlog.get_records(regime="RANGE_MARKET")
    assert [r["r_multiple"] for r in recs] == [0.0, 1.0, 2.0, 3.0, 4.0]


def test_t04_distinct_pairs(_isolated_store):
    evlog.record_regime_trade("BULL_TREND", "Breakout_Volume", r_multiple=1.0, won=True)
    evlog.record_regime_trade("BULL_TREND", "Breakout_Volume", r_multiple=1.0, won=True)
    evlog.record_regime_trade("BEAR_MARKET", "Hedging_Model", r_multiple=-0.5, won=False)
    pairs = evlog.get_pairs_with_evidence()
    assert pairs == [("BEAR_MARKET", "Hedging_Model"), ("BULL_TREND", "Breakout_Volume")]


def test_t05_fail_open_on_record_error(_isolated_store):
    with patch("builtins.open", side_effect=OSError("disk full")):
        evlog.record_regime_trade("BULL_TREND", "Breakout_Volume", r_multiple=1.0, won=True)
    # never raised


def test_t06_fail_open_on_corrupt_lines(_isolated_store):
    with open(_isolated_store, "w", encoding="utf-8") as f:
        f.write("not valid json\n")
        f.write('{"regime": "BULL_TREND", "strategy": "X", "won": true}\n')
    recs = evlog.get_records()
    assert len(recs) == 1
    assert recs[0]["strategy"] == "X"


def test_t07_no_forbidden_imports():
    import os
    src_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "meta_learning", "regime_map_evidence_log.py",
    )
    src = open(src_path, encoding="utf-8").read()
    for forbidden in ("execution_engine", "order_manager", "dhan_feed", "broker", "risk_control"):
        assert f"import {forbidden}" not in src
        assert f"from {forbidden}" not in src
