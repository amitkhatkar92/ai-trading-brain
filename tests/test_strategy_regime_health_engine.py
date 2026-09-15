"""
tests/test_strategy_regime_health_engine.py
==============================================
Self-learning module #24: StrategyHealthMonitor regime-aware disabling.

T01  Insufficient sample stays WAITING_FOR_EVIDENCE
T02  Strong negative (losing) signal starts SHADOW with direction=-1
T03  Strong positive (winning) signal never starts shadow (disable-only scope)
T04  Shadow blocked until enough new evidence accumulates
T05  Shadow promotes to ACTIVE (regime-disable) on reconfirming evidence
T06  Shadow REJECTS on contradicting new evidence
T07  ACTIVE auto-ROLLS_BACK when post-disable win-rate recovers
T08  get_regime_disabled_strategies() reflects only ACTIVE disables for
     the requested regime
T09  Cooldown blocks immediate re-evaluation
T10  Fail-open: run_daily_refinement_check() never raises
T11  Safety-contract source scan: zero imports of execution_engine/
     order_manager/dhan_feed/broker/risk_control; strategy_health_monitor.py
     is never imported or modified by this module
"""
from __future__ import annotations

import os
from unittest.mock import patch

import pytest

import trade_monitoring.strategy_regime_health_engine as engine


@pytest.fixture(autouse=True)
def _isolated_store(tmp_path):
    with patch.object(engine, "_STATE_PATH", str(tmp_path / "state.json")), \
         patch.object(engine, "_DISABLES_PATH", str(tmp_path / "active_disables.json")), \
         patch.object(engine, "_STORE_DIR", str(tmp_path)), \
         patch.object(engine, "_LEDGER_PATH", str(tmp_path / "ledger.jsonl")):
        yield


def _records(n_total, win_rate):
    recs = []
    win_acc = 0.0
    for i in range(n_total):
        win_acc += win_rate
        won = win_acc >= 1.0
        if won:
            win_acc -= 1.0
        recs.append({"timestamp": f"2026-01-{i+1:02d}T00:00:00", "won": won, "r_multiple": 1.0 if won else -1.0})
    return recs


def test_t01_insufficient_sample_waits():
    records = _records(10, win_rate=0.2)
    with patch("meta_learning.regime_map_evidence_log.get_records", return_value=records), \
         patch("meta_learning.regime_map_evidence_log.get_pairs_with_evidence",
               return_value=[("bear_market", "Hedging_Model")]):
        result = engine.run_daily_refinement_check()
    assert result["per_pair"]["bear_market::Hedging_Model"]["status"] == engine.STATUS_WAITING


def test_t02_strong_negative_signal_starts_shadow():
    records = _records(60, win_rate=0.15)
    with patch("meta_learning.regime_map_evidence_log.get_records", return_value=records), \
         patch("meta_learning.regime_map_evidence_log.get_pairs_with_evidence",
               return_value=[("bear_market", "Hedging_Model")]):
        result = engine.run_daily_refinement_check()
    assert result["per_pair"]["bear_market::Hedging_Model"]["status"] == engine.STATUS_SHADOW


def test_t03_positive_signal_never_shadowed():
    records = _records(40, win_rate=0.80)
    with patch("meta_learning.regime_map_evidence_log.get_records", return_value=records), \
         patch("meta_learning.regime_map_evidence_log.get_pairs_with_evidence",
               return_value=[("bear_market", "Hedging_Model")]):
        result = engine.run_daily_refinement_check()
    assert result["per_pair"]["bear_market::Hedging_Model"]["status"] == engine.STATUS_WAITING


def test_t04_shadow_blocked_until_enough_new_evidence():
    all_records = _records(60, win_rate=0.15)
    with patch("meta_learning.regime_map_evidence_log.get_pairs_with_evidence",
               return_value=[("bear_market", "Hedging_Model")]):
        with patch("meta_learning.regime_map_evidence_log.get_records", return_value=all_records):
            engine.run_daily_refinement_check()
        with_few_more = all_records + _records(5, win_rate=0.15)
        with patch("meta_learning.regime_map_evidence_log.get_records", return_value=with_few_more):
            result = engine.run_daily_refinement_check()
    assert result["per_pair"]["bear_market::Hedging_Model"]["status"] == engine.STATUS_SHADOW


def test_t05_shadow_promotes_on_reconfirmation():
    all_records = _records(60, win_rate=0.15)
    with patch("meta_learning.regime_map_evidence_log.get_pairs_with_evidence",
               return_value=[("bear_market", "Hedging_Model")]):
        with patch("meta_learning.regime_map_evidence_log.get_records", return_value=all_records):
            engine.run_daily_refinement_check()
        new_evidence = _records(15, win_rate=0.15)
        with patch("meta_learning.regime_map_evidence_log.get_records", return_value=all_records + new_evidence):
            result = engine.run_daily_refinement_check()
    assert result["per_pair"]["bear_market::Hedging_Model"]["status"] == engine.STATUS_ACTIVE


def test_t06_shadow_rejects_on_contradicting_evidence():
    all_records = _records(60, win_rate=0.15)
    with patch("meta_learning.regime_map_evidence_log.get_pairs_with_evidence",
               return_value=[("bear_market", "Hedging_Model")]):
        with patch("meta_learning.regime_map_evidence_log.get_records", return_value=all_records):
            engine.run_daily_refinement_check()
        new_evidence = _records(15, win_rate=0.90)
        with patch("meta_learning.regime_map_evidence_log.get_records", return_value=all_records + new_evidence):
            result = engine.run_daily_refinement_check()
    assert result["per_pair"]["bear_market::Hedging_Model"]["status"] == engine.STATUS_REJECTED


def test_t07_active_auto_rolls_back_on_recovery():
    all_records = _records(60, win_rate=0.15)
    confirm_evidence = _records(15, win_rate=0.15)
    with patch("meta_learning.regime_map_evidence_log.get_pairs_with_evidence",
               return_value=[("bear_market", "Hedging_Model")]):
        with patch("meta_learning.regime_map_evidence_log.get_records", return_value=all_records):
            engine.run_daily_refinement_check()
        with patch("meta_learning.regime_map_evidence_log.get_records", return_value=all_records + confirm_evidence):
            engine.run_daily_refinement_check()
        recovery_evidence = _records(15, win_rate=0.90)
        with patch("meta_learning.regime_map_evidence_log.get_records",
                   return_value=all_records + confirm_evidence + recovery_evidence):
            result = engine.run_daily_refinement_check()
    assert result["per_pair"]["bear_market::Hedging_Model"]["status"] == engine.STATUS_ROLLED_BACK


def test_t08_get_regime_disabled_strategies_scoped_by_regime():
    engine._write_json(engine._DISABLES_PATH, {"bear_market::Hedging_Model": {"disabled_at": "x"}})
    assert engine.get_regime_disabled_strategies("bear_market") == {"Hedging_Model"}
    assert engine.get_regime_disabled_strategies("bull_trend") == set()


def test_t09_cooldown_blocks_immediate_reevaluation():
    records = _records(10, win_rate=0.2)
    with patch("meta_learning.regime_map_evidence_log.get_pairs_with_evidence",
               return_value=[("bear_market", "Hedging_Model")]):
        with patch("meta_learning.regime_map_evidence_log.get_records", return_value=records):
            engine.run_daily_refinement_check()
        strong_records = _records(60, win_rate=0.15)
        with patch("meta_learning.regime_map_evidence_log.get_records", return_value=strong_records):
            result = engine.run_daily_refinement_check()
    assert result["per_pair"]["bear_market::Hedging_Model"]["status"] == engine.STATUS_WAITING


def test_t10_fail_open_never_raises():
    with patch("meta_learning.regime_map_evidence_log.get_pairs_with_evidence", side_effect=RuntimeError("boom")):
        result = engine.run_daily_refinement_check()
    assert result["status"] == "ERROR"


def test_t11_safety_contract_source_scan():
    src_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "trade_monitoring", "strategy_regime_health_engine.py",
    )
    src = open(src_path, encoding="utf-8").read()
    for forbidden in ("execution_engine", "order_manager", "dhan_feed", "broker", "risk_control"):
        assert f"import {forbidden}" not in src
        assert f"from {forbidden}" not in src
    assert "import strategy_health_monitor" not in src
    assert "strategy_health_monitor import" not in src
