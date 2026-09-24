"""
tests/test_target_expansion_refinement_engine.py
====================================================
Self-learning module #29 (SYNTHESIS + GOVERNANCE) -- evidence-gated
auto-tuning of the Dynamic Target Expansion multiplier.

T01  Insufficient sample stays WAITING_FOR_EVIDENCE
T02  Strong positive signal (win rate reliably > 0.5) starts SHADOW
     with direction=+1
T03  No signal (win rate ~= 0.5) stays WAITING
T04  Shadow blocked until enough new evidence accumulates
T05  Shadow promotes to ACTIVE on reconfirming evidence
T06  Shadow REJECTS on contradicting new evidence
T07  ACTIVE auto-ROLLS_BACK when post-activation evidence degrades
T08  get_effective_expansion_multiplier() with no active adjustment ==
     exact config.py default
T09  An ACTIVE positive adjustment widens the multiplier, bounded by
     MAX_MULTIPLIER
T10  A validated NEGATIVE signal narrows the multiplier, bounded by
     MIN_MULTIPLIER -- never disables the mechanism outright
T11  Cooldown blocks immediate re-evaluation
T12  Fail-open: run_daily_refinement_check() never raises
T13  Safety-contract source scan: zero imports of execution_engine/
     order_manager/dhan_feed/broker; trade_monitor.py is never imported
     or modified by this module
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

import learning_system.target_expansion_refinement_engine as engine


@pytest.fixture(autouse=True)
def _isolated_store(tmp_path):
    with patch.object(engine, "_STATE_PATH", str(tmp_path / "state.json")), \
         patch.object(engine, "_TUNING_PATH", str(tmp_path / "active_tuning.json")), \
         patch.object(engine, "_STORE_DIR", str(tmp_path)), \
         patch.object(engine, "_LEDGER_PATH", str(tmp_path / "ledger.jsonl")):
        engine._cache_mtime = None
        engine._cache_multiplier = None
        yield


def _records(n, win_rate):
    """n time-ordered records with the given proportion classified WIN."""
    acc = 0.0
    out = []
    for i in range(n):
        acc += win_rate
        won = acc >= 1.0
        if won:
            acc -= 1.0
        out.append({"timestamp": f"2026-01-{i+1:03d}", "outcome": "WIN" if won else "LOSS"})
    return out


def _patch_records(records):
    return patch(
        "learning_system.target_expansion_evidence_log.get_records",
        return_value=records,
    )


def test_t01_insufficient_sample_waits():
    with _patch_records(_records(5, 0.8)):
        result = engine.run_daily_refinement_check()
    assert result["state_status"] == engine.STATUS_WAITING


def test_t02_strong_positive_signal_starts_shadow():
    with _patch_records(_records(60, 0.85)):
        result = engine.run_daily_refinement_check()
    assert result["state_status"] == engine.STATUS_SHADOW
    state = engine._read_json(engine._STATE_PATH, {})
    assert state["direction"] == 1


def test_t03_no_signal_stays_waiting():
    with _patch_records(_records(30, 0.5)):
        result = engine.run_daily_refinement_check()
    assert result["state_status"] == engine.STATUS_WAITING


def test_t04_shadow_blocked_until_enough_new_evidence():
    with _patch_records(_records(60, 0.85)):
        engine.run_daily_refinement_check()
    state = engine._read_json(engine._STATE_PATH, {})
    state.pop("last_checked_at", None)
    engine._write_json(engine._STATE_PATH, state)
    with _patch_records(_records(65, 0.85)):
        result = engine.run_daily_refinement_check()
    assert result["state_status"] == engine.STATUS_SHADOW


def test_t05_shadow_promotes_to_active_on_reconfirmation():
    with _patch_records(_records(60, 0.85)):
        engine.run_daily_refinement_check()
    with _patch_records(_records(75, 0.85)):
        result = engine.run_daily_refinement_check()
    assert result["state_status"] == engine.STATUS_ACTIVE


def test_t06_shadow_rejects_on_contradicting_evidence():
    with _patch_records(_records(60, 0.85)):
        engine.run_daily_refinement_check()
    contradicting = _records(60, 0.85) + _records(20, 0.10)
    with _patch_records(contradicting):
        result = engine.run_daily_refinement_check()
    assert result["state_status"] == engine.STATUS_REJECTED


def test_t07_active_rolls_back_on_degradation():
    with _patch_records(_records(60, 0.85)):
        engine.run_daily_refinement_check()
    with _patch_records(_records(75, 0.85)):
        engine.run_daily_refinement_check()
    degrading = _records(75, 0.85) + _records(15, 0.10)
    with _patch_records(degrading):
        result = engine.run_daily_refinement_check()
    assert result["state_status"] == engine.STATUS_ROLLED_BACK


def test_t08_default_multiplier_with_no_override():
    assert engine.get_effective_expansion_multiplier() == engine.DEFAULT_MULTIPLIER


def test_t09_active_positive_adjustment_widens_bounded():
    with _patch_records(_records(60, 0.90)):
        engine.run_daily_refinement_check()
    with _patch_records(_records(75, 0.90)):
        engine.run_daily_refinement_check()
    mult = engine.get_effective_expansion_multiplier()
    assert mult > engine.DEFAULT_MULTIPLIER
    assert mult <= engine.MAX_MULTIPLIER


def test_t10_negative_signal_narrows_bounded_never_zero():
    with _patch_records(_records(60, 0.15)):
        engine.run_daily_refinement_check()
    state = engine._read_json(engine._STATE_PATH, {})
    assert state["direction"] == -1
    with _patch_records(_records(75, 0.15)):
        engine.run_daily_refinement_check()
    mult = engine.get_effective_expansion_multiplier()
    assert mult < engine.DEFAULT_MULTIPLIER
    assert mult >= engine.MIN_MULTIPLIER
    assert mult > 0   # never disabled outright


def test_t11_cooldown_blocks_immediate_recheck():
    with _patch_records(_records(30, 0.5)):
        engine.run_daily_refinement_check()
    with _patch_records(_records(30, 0.90)):
        result = engine.run_daily_refinement_check()
    assert result["state_status"] == engine.STATUS_WAITING
    assert result["detail"] == "cooldown"


def test_t12_fail_open_never_raises():
    with patch(
        "learning_system.target_expansion_evidence_log.get_records",
        side_effect=RuntimeError("boom"),
    ):
        result = engine.run_daily_refinement_check()
    assert result["status"] == "ERROR"


def test_t13_safety_contract_source_scan():
    import inspect
    src = inspect.getsource(engine)
    forbidden = ("import execution_engine", "from execution_engine",
                 "import order_manager", "from order_manager",
                 "import dhan_feed", "from dhan_feed",
                 "import broker", "from broker",
                 "from trade_monitoring.trade_monitor import",
                 "import trade_monitoring.trade_monitor")
    for token in forbidden:
        assert token not in src, f"forbidden import found: {token}"
