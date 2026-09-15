"""
tests/test_regime_map_refinement_engine.py
=============================================
Self-Learning Ecosystem -- Post-roadmap Priority 5 (part 2): SYNTHESIS +
GOVERNANCE for strategy_lab/regime_map_refinement_engine.py.

T01  Insufficient sample stays WAITING_FOR_EVIDENCE
T02  Strong negative (losing) signal starts SHADOW with direction=-1
T03  Strong positive (winning) signal never starts shadow (demotion-only scope)
T04  Shadow blocked until enough new evidence accumulates
T05  Shadow promotes to ACTIVE on reconfirming new negative evidence
T06  Shadow REJECTS on contradicting new evidence
T07  ACTIVE auto-ROLLS_BACK when post-demotion win-rate recovers
T08  get_effective_regime_map() with no demotions == exact static _REGIME_MAP
T09  An ACTIVE demotion removes exactly that (regime, strategy) pair
T10  Safety floor: a demotion that would empty a regime's candidate list
     is refused
T11  Only pairs already present in the static _REGIME_MAP are ever
     evaluated -- never invents a new candidate
T12  Cooldown blocks immediate re-evaluation after a WAITING/REJECTED check
T13  Fail-open: run_daily_refinement_check() never raises
T14  Safety-contract source scan: zero imports of execution_engine/
     order_manager/dhan_feed/broker; regime_strategy_map.py is never
     imported or modified by this module
"""
from __future__ import annotations

import os
from unittest.mock import patch

import pytest

import strategy_lab.regime_map_refinement_engine as engine


@pytest.fixture(autouse=True)
def _isolated_store(tmp_path):
    state_path = tmp_path / "state.json"
    demotions_path = tmp_path / "active_demotions.json"
    ledger_path = tmp_path / "ledger.jsonl"
    with patch.object(engine, "_STATE_PATH", str(state_path)), \
         patch.object(engine, "_DEMOTIONS_PATH", str(demotions_path)), \
         patch.object(engine, "_STORE_DIR", str(tmp_path)), \
         patch.object(engine, "_LEDGER_PATH", str(ledger_path)):
        # Reset the module-level mtime cache between tests
        engine._cache_mtime = None
        engine._cache_map = None
        yield


def _records(n_total, win_rate, won_by_default=True):
    """
    Build n_total records with the given win_rate, interleaved
    proportionally (not blocked all-correct-then-incorrect) so a 70/30
    chronological split preserves the same ratio in both segments.
    """
    n_win = round(n_total * win_rate)
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
    status = result["per_pair"]["bear_market::Hedging_Model"]["status"]
    assert status == engine.STATUS_WAITING


def test_t02_strong_negative_signal_starts_shadow():
    records = _records(60, win_rate=0.15)  # strongly losing
    with patch("meta_learning.regime_map_evidence_log.get_records", return_value=records), \
         patch("meta_learning.regime_map_evidence_log.get_pairs_with_evidence",
               return_value=[("bear_market", "Hedging_Model")]):
        result = engine.run_daily_refinement_check()
    status = result["per_pair"]["bear_market::Hedging_Model"]["status"]
    assert status == engine.STATUS_SHADOW


def test_t03_positive_signal_never_shadowed():
    records = _records(40, win_rate=0.80)  # strongly winning
    with patch("meta_learning.regime_map_evidence_log.get_records", return_value=records), \
         patch("meta_learning.regime_map_evidence_log.get_pairs_with_evidence",
               return_value=[("bear_market", "Hedging_Model")]):
        result = engine.run_daily_refinement_check()
    status = result["per_pair"]["bear_market::Hedging_Model"]["status"]
    assert status == engine.STATUS_WAITING


def test_t04_shadow_blocked_until_enough_new_evidence():
    all_records = _records(60, win_rate=0.15)
    with patch("meta_learning.regime_map_evidence_log.get_records", return_value=all_records), \
         patch("meta_learning.regime_map_evidence_log.get_pairs_with_evidence",
               return_value=[("bear_market", "Hedging_Model")]):
        engine.run_daily_refinement_check()  # -> SHADOW at n=40

        with_few_more = all_records + _records(5, win_rate=0.20)
        with patch("meta_learning.regime_map_evidence_log.get_records", return_value=with_few_more):
            result = engine.run_daily_refinement_check()
    status = result["per_pair"]["bear_market::Hedging_Model"]["status"]
    assert status == engine.STATUS_SHADOW  # not enough new evidence yet (5 < 12)


def test_t05_shadow_promotes_on_reconfirmation():
    all_records = _records(60, win_rate=0.15)
    with patch("meta_learning.regime_map_evidence_log.get_pairs_with_evidence",
               return_value=[("bear_market", "Hedging_Model")]):
        with patch("meta_learning.regime_map_evidence_log.get_records", return_value=all_records):
            engine.run_daily_refinement_check()  # -> SHADOW

        new_evidence = _records(15, win_rate=0.20)
        with patch("meta_learning.regime_map_evidence_log.get_records", return_value=all_records + new_evidence):
            result = engine.run_daily_refinement_check()
    status = result["per_pair"]["bear_market::Hedging_Model"]["status"]
    assert status == engine.STATUS_ACTIVE


def test_t06_shadow_rejects_on_contradicting_evidence():
    all_records = _records(60, win_rate=0.15)
    with patch("meta_learning.regime_map_evidence_log.get_pairs_with_evidence",
               return_value=[("bear_market", "Hedging_Model")]):
        with patch("meta_learning.regime_map_evidence_log.get_records", return_value=all_records):
            engine.run_daily_refinement_check()  # -> SHADOW

        new_evidence = _records(15, win_rate=0.90)  # strategy recovered strongly
        with patch("meta_learning.regime_map_evidence_log.get_records", return_value=all_records + new_evidence):
            result = engine.run_daily_refinement_check()
    status = result["per_pair"]["bear_market::Hedging_Model"]["status"]
    assert status == engine.STATUS_REJECTED


def test_t07_active_auto_rolls_back_on_recovery():
    all_records = _records(60, win_rate=0.15)
    confirm_evidence = _records(15, win_rate=0.20)
    with patch("meta_learning.regime_map_evidence_log.get_pairs_with_evidence",
               return_value=[("bear_market", "Hedging_Model")]):
        with patch("meta_learning.regime_map_evidence_log.get_records", return_value=all_records):
            engine.run_daily_refinement_check()  # -> SHADOW
        with patch("meta_learning.regime_map_evidence_log.get_records", return_value=all_records + confirm_evidence):
            engine.run_daily_refinement_check()  # -> ACTIVE

        recovery_evidence = _records(15, win_rate=0.90)
        with patch("meta_learning.regime_map_evidence_log.get_records",
                   return_value=all_records + confirm_evidence + recovery_evidence):
            result = engine.run_daily_refinement_check()
    status = result["per_pair"]["bear_market::Hedging_Model"]["status"]
    assert status == engine.STATUS_ROLLED_BACK


def test_t08_effective_map_matches_static_with_no_demotions():
    from strategy_lab.meta_strategy_controller import _REGIME_MAP
    effective = engine.get_effective_regime_map()
    assert effective == {k: list(v) for k, v in _REGIME_MAP.items()}


def test_t09_active_demotion_removes_exact_pair():
    engine._write_json(engine._DEMOTIONS_PATH, {"bear_market::Hedging_Model": {"demoted_at": "x"}})
    effective = engine.get_effective_regime_map()
    assert "Hedging_Model" not in effective["bear_market"]
    # other regimes/strategies untouched
    assert "Hedging_Model" in effective.get("volatile", [])


def test_t10_safety_floor_refuses_to_empty_a_regime(monkeypatch):
    fake_map = {"LONE_REGIME": ["OnlyStrategy"]}
    with patch("strategy_lab.meta_strategy_controller._REGIME_MAP", fake_map):
        engine._write_json(engine._DEMOTIONS_PATH, {"LONE_REGIME::OnlyStrategy": {"demoted_at": "x"}})
        effective = engine.get_effective_regime_map()
    assert effective["LONE_REGIME"] == ["OnlyStrategy"]  # demotion refused


def test_t11_only_evaluates_existing_candidates():
    records = _records(60, win_rate=0.15)
    with patch("meta_learning.regime_map_evidence_log.get_records", return_value=records), \
         patch("meta_learning.regime_map_evidence_log.get_pairs_with_evidence",
               return_value=[("bear_market", "NotARealCandidate")]):
        result = engine.run_daily_refinement_check()
    assert result["per_pair"] == {}


def test_t12_cooldown_blocks_immediate_reevaluation():
    records = _records(10, win_rate=0.20)  # below MIN_SAMPLE -> WAITING, sets last_checked_at
    with patch("meta_learning.regime_map_evidence_log.get_pairs_with_evidence",
               return_value=[("bear_market", "Hedging_Model")]):
        with patch("meta_learning.regime_map_evidence_log.get_records", return_value=records):
            engine.run_daily_refinement_check()

        # Now provide enough evidence for a real signal -- but cooldown should still block
        strong_records = _records(60, win_rate=0.15)
        with patch("meta_learning.regime_map_evidence_log.get_records", return_value=strong_records):
            result = engine.run_daily_refinement_check()
    status = result["per_pair"]["bear_market::Hedging_Model"]["status"]
    assert status == engine.STATUS_WAITING  # cooldown active, no fresh scorecard evaluated


def test_t13_fail_open_never_raises():
    with patch("meta_learning.regime_map_evidence_log.get_pairs_with_evidence", side_effect=RuntimeError("boom")):
        result = engine.run_daily_refinement_check()
    assert result["status"] == "ERROR"


def test_t14_safety_contract_source_scan():
    src_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "strategy_lab", "regime_map_refinement_engine.py",
    )
    src = open(src_path, encoding="utf-8").read()
    for forbidden in ("execution_engine", "order_manager", "dhan_feed", "broker"):
        assert f"import {forbidden}" not in src
        assert f"from {forbidden}" not in src
    assert "import risk_control" not in src
    assert "from risk_control" not in src
    # never imports the existing, already-live per-regime ranking tracker
    assert "import regime_strategy_map" not in src
    assert "regime_strategy_map import" not in src
