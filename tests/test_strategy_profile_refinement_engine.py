"""
tests/test_strategy_profile_refinement_engine.py
====================================================
Self-learning module #25: profile-aware governance auto-apply.

T01  Below MIN_SAMPLE_FOR_AUTO_APPLY stays WAITING regardless of suggestion
T02  No suggestion (None) stays WAITING
T03  Non-HIGH confidence suggestion stays WAITING (never auto-shadowed)
T04  HIGH-confidence suggestion differing from current profile starts SHADOW
T05  Suggestion matching current profile already stays WAITING (no-op)
T06  Shadow blocked until enough new trades accumulate
T07  Shadow promotes to ACTIVE and calls apply_profile_override() exactly
     once with the reconfirmed candidate
T08  Shadow REJECTS when reconfirmation suggestion differs
T09  Cooldown blocks immediate re-evaluation after WAITING
T10  Fail-open: run_daily_refinement_check() never raises
T11  Safety-contract source scan
"""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

import trade_monitoring.strategy_profile_refinement_engine as engine


@pytest.fixture(autouse=True)
def _isolated_store(tmp_path):
    with patch.object(engine, "_STATE_PATH", str(tmp_path / "state.json")), \
         patch.object(engine, "_STORE_DIR", str(tmp_path)), \
         patch.object(engine, "_LEDGER_PATH", str(tmp_path / "ledger.jsonl")):
        yield


def _fake_shm(names, trades, current_profile, suggestion, confidence, reasoning="r"):
    shm = MagicMock()
    shm.get_tracked_strategy_names.return_value = names
    shm.get_trades_count.side_effect = lambda n: trades
    shm.get_profile_type.side_effect = lambda n: current_profile
    shm.get_profile_suggestion.side_effect = lambda n: (suggestion, confidence, reasoning)
    return shm


def test_t01_below_min_sample_waits():
    shm = _fake_shm(["Momentum_Retest"], trades=10, current_profile="UNKNOWN",
                     suggestion="LOW_WR_HIGH_R", confidence="HIGH")
    result = engine.run_daily_refinement_check(shm)
    assert result["per_strategy"]["Momentum_Retest"]["status"] == engine.STATUS_WAITING


def test_t02_no_suggestion_waits():
    shm = _fake_shm(["Momentum_Retest"], trades=60, current_profile="UNKNOWN",
                     suggestion=None, confidence="")
    result = engine.run_daily_refinement_check(shm)
    assert result["per_strategy"]["Momentum_Retest"]["status"] == engine.STATUS_WAITING


def test_t03_non_high_confidence_waits():
    shm = _fake_shm(["Momentum_Retest"], trades=60, current_profile="UNKNOWN",
                     suggestion="LOW_WR_HIGH_R", confidence="MEDIUM")
    result = engine.run_daily_refinement_check(shm)
    assert result["per_strategy"]["Momentum_Retest"]["status"] == engine.STATUS_WAITING


def test_t04_high_confidence_diverging_starts_shadow():
    shm = _fake_shm(["Momentum_Retest"], trades=60, current_profile="UNKNOWN",
                     suggestion="LOW_WR_HIGH_R", confidence="HIGH")
    result = engine.run_daily_refinement_check(shm)
    assert result["per_strategy"]["Momentum_Retest"]["status"] == engine.STATUS_SHADOW


def test_t05_suggestion_matches_current_profile_stays_waiting():
    shm = _fake_shm(["Momentum_Retest"], trades=60, current_profile="LOW_WR_HIGH_R",
                     suggestion="LOW_WR_HIGH_R", confidence="HIGH")
    result = engine.run_daily_refinement_check(shm)
    assert result["per_strategy"]["Momentum_Retest"]["status"] == engine.STATUS_WAITING


def test_t06_shadow_blocked_until_enough_new_trades():
    shm = _fake_shm(["Momentum_Retest"], trades=60, current_profile="UNKNOWN",
                     suggestion="LOW_WR_HIGH_R", confidence="HIGH")
    engine.run_daily_refinement_check(shm)  # -> SHADOW at trades=60
    shm.get_trades_count.side_effect = lambda n: 65   # only 5 new trades
    result = engine.run_daily_refinement_check(shm)
    assert result["per_strategy"]["Momentum_Retest"]["status"] == engine.STATUS_SHADOW


def test_t07_shadow_promotes_and_applies_override_once():
    shm = _fake_shm(["Momentum_Retest"], trades=60, current_profile="UNKNOWN",
                     suggestion="LOW_WR_HIGH_R", confidence="HIGH")
    shm.apply_profile_override.return_value = True
    engine.run_daily_refinement_check(shm)  # -> SHADOW
    shm.get_trades_count.side_effect = lambda n: 80   # 20 new trades, above MIN_SHADOW_NEW_TRADES=15
    result = engine.run_daily_refinement_check(shm)
    assert result["per_strategy"]["Momentum_Retest"]["status"] == engine.STATUS_ACTIVE
    shm.apply_profile_override.assert_called_once()
    args = shm.apply_profile_override.call_args[0]
    assert args[0] == "Momentum_Retest"
    assert args[1] == "LOW_WR_HIGH_R"


def test_t08_shadow_rejects_when_reconfirmation_diverges():
    shm = _fake_shm(["Momentum_Retest"], trades=60, current_profile="UNKNOWN",
                     suggestion="LOW_WR_HIGH_R", confidence="HIGH")
    engine.run_daily_refinement_check(shm)  # -> SHADOW
    shm.get_trades_count.side_effect = lambda n: 80
    shm.get_profile_suggestion.side_effect = lambda n: ("HIGH_WR_LOW_R", "HIGH", "changed")
    result = engine.run_daily_refinement_check(shm)
    assert result["per_strategy"]["Momentum_Retest"]["status"] == engine.STATUS_REJECTED
    shm.apply_profile_override.assert_not_called()


def test_t09_cooldown_blocks_immediate_reevaluation():
    shm = _fake_shm(["Momentum_Retest"], trades=10, current_profile="UNKNOWN",
                     suggestion=None, confidence="")
    engine.run_daily_refinement_check(shm)  # -> WAITING, sets last_checked_at
    shm2 = _fake_shm(["Momentum_Retest"], trades=60, current_profile="UNKNOWN",
                      suggestion="LOW_WR_HIGH_R", confidence="HIGH")
    result = engine.run_daily_refinement_check(shm2)
    assert result["per_strategy"]["Momentum_Retest"]["status"] == engine.STATUS_WAITING


def test_t10_fail_open_never_raises():
    shm = MagicMock()
    shm.get_tracked_strategy_names.side_effect = RuntimeError("boom")
    result = engine.run_daily_refinement_check(shm)
    assert result["status"] == "ERROR"


def test_t11_safety_contract_source_scan():
    src_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "trade_monitoring", "strategy_profile_refinement_engine.py",
    )
    src = open(src_path, encoding="utf-8").read()
    for forbidden in ("execution_engine", "order_manager", "dhan_feed", "broker", "risk_control"):
        assert f"import {forbidden}" not in src
        assert f"from {forbidden}" not in src
