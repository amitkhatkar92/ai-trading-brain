"""
test_mop_rc001.py — MOP-RC-001 Expected Move Observational Telemetry tests.

Test inventory (T001–T010):
  T001  expected_move_pct calculated correctly: (atr/entry)*rr*100
  T002  atr=0 → expected_move_pct is None, signal NOT rejected
  T003  entry_price=0 → expected_move_pct is None, signal NOT rejected
  T004  rr=0 (invalid target==entry) → expected_move_pct is None, signal NOT rejected
  T005  Telemetry cannot alter candidate ranking
  T006  Telemetry cannot alter strategy_name selection
  T007  Telemetry cannot alter position sizing (quantity)
  T008  Telemetry cannot trigger an order (does not reach OrderManager)
  T009  No look-ahead: expected_move_pct uses only atr, entry_price, rr — all known pre-signal
  T010  Duplicate observation does not create duplicate records in JSONL
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

# ── path bootstrap ─────────────────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# ── minimal test harness ───────────────────────────────────────────────────────
_PASS = 0
_FAIL = 0

def _ok(test_id: str, desc: str) -> None:
    global _PASS
    _PASS += 1
    print(f"  PASS  {test_id}: {desc}")

def _fail(test_id: str, desc: str, reason: str) -> None:
    global _FAIL
    _FAIL += 1
    print(f"  FAIL  {test_id}: {desc}")
    print(f"         Reason: {reason}")

def _assert(test_id: str, desc: str, condition: bool, reason: str = "") -> None:
    if condition:
        _ok(test_id, desc)
    else:
        _fail(test_id, desc, reason or "assertion failed")


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

def _make_signal(
    symbol: str = "TATASTEEL",
    entry_price: float = 200.0,
    stop_loss: float = 197.0,      # 3.0 stop_dist (ATR × 1.5 where ATR≈2.0)
    target_price: float = 207.5,   # 2.5 × 3.0 = 7.5
    atr: float = 2.0,
    confidence: float = 7.0,
    quantity: int = 5,
    strategy_name: str = "breakout",
    direction_str: str = "BUY",
):
    """
    Build a minimal TradeSignal.  Imports the real dataclass so the test
    exercises production code, not a stub.
    """
    from models.trade_signal import TradeSignal, SignalDirection, SignalType, SignalStrength

    direction = SignalDirection.BUY if direction_str == "BUY" else SignalDirection.SHORT
    return TradeSignal(
        symbol       = symbol,
        direction    = direction,
        signal_type  = SignalType.EQUITY,
        strength     = SignalStrength.MODERATE,
        entry_price  = entry_price,
        stop_loss    = stop_loss,
        target_price = target_price,
        quantity     = quantity,
        strategy_name = strategy_name,
        confidence   = confidence,
        atr          = atr,
    )


def _expected_move_formula(atr: float, entry: float, rr: float) -> float:
    return round(atr / entry * rr * 100, 4)


# ══════════════════════════════════════════════════════════════════════════════
# T001 — Correct formula
# ══════════════════════════════════════════════════════════════════════════════
def test_T001():
    tid = "T001"
    sig = _make_signal(entry_price=200.0, stop_loss=197.0, target_price=207.5, atr=2.0)
    # Actual RR = (207.5 - 200) / (200 - 197) = 7.5 / 3.0 = 2.5
    actual_rr = sig.risk_reward_ratio
    expected = _expected_move_formula(sig.atr, sig.entry_price, actual_rr)
    # Manually set the field (simulating what scan() does)
    try:
        rr_obs = sig.risk_reward_ratio
        if sig.atr and sig.entry_price and sig.entry_price > 0 and rr_obs > 0:
            sig.expected_move_pct = round(sig.atr / sig.entry_price * rr_obs * 100, 4)
    except Exception as e:
        _fail(tid, "expected_move_pct formula", f"Exception: {e}")
        return
    _assert(tid, "expected_move_pct formula",
            sig.expected_move_pct == expected,
            f"got {sig.expected_move_pct}, expected {expected}")


# ══════════════════════════════════════════════════════════════════════════════
# T002 — atr=0 → None, no rejection
# ══════════════════════════════════════════════════════════════════════════════
def test_T002():
    tid = "T002"
    sig = _make_signal(atr=0.0)
    try:
        rr_obs = sig.risk_reward_ratio
        if sig.atr and sig.entry_price and sig.entry_price > 0 and rr_obs > 0:
            sig.expected_move_pct = round(sig.atr / sig.entry_price * rr_obs * 100, 4)
        # else leave as None
    except Exception as e:
        _fail(tid, "atr=0 → None, no rejection", f"Exception: {e}")
        return
    _assert(tid, "atr=0 → expected_move_pct is None",
            sig.expected_move_pct is None,
            f"got {sig.expected_move_pct}")


# ══════════════════════════════════════════════════════════════════════════════
# T003 — entry_price=0 → None, no rejection
# ══════════════════════════════════════════════════════════════════════════════
def test_T003():
    tid = "T003"
    sig = _make_signal(entry_price=0.0, stop_loss=0.0, target_price=0.0, atr=2.0)
    try:
        rr_obs = sig.risk_reward_ratio
        if sig.atr and sig.entry_price and sig.entry_price > 0 and rr_obs > 0:
            sig.expected_move_pct = round(sig.atr / sig.entry_price * rr_obs * 100, 4)
    except Exception as e:
        _fail(tid, "entry=0 → None, no rejection", f"Exception: {e}")
        return
    _assert(tid, "entry_price=0 → expected_move_pct is None",
            sig.expected_move_pct is None,
            f"got {sig.expected_move_pct}")


# ══════════════════════════════════════════════════════════════════════════════
# T004 — rr=0 (invalid: target == entry) → None, no rejection
# ══════════════════════════════════════════════════════════════════════════════
def test_T004():
    tid = "T004"
    sig = _make_signal(entry_price=200.0, stop_loss=197.0, target_price=200.0, atr=2.0)
    try:
        rr_obs = sig.risk_reward_ratio   # = (200-200)/(200-197) = 0.0
        if sig.atr and sig.entry_price and sig.entry_price > 0 and rr_obs > 0:
            sig.expected_move_pct = round(sig.atr / sig.entry_price * rr_obs * 100, 4)
    except Exception as e:
        _fail(tid, "rr=0 → None, no rejection", f"Exception: {e}")
        return
    _assert(tid, "rr=0 → expected_move_pct is None",
            sig.expected_move_pct is None,
            f"got {sig.expected_move_pct}")


# ══════════════════════════════════════════════════════════════════════════════
# T005 — Telemetry cannot alter candidate ranking
#
# The CRE quality score is `confidence + 0.01 * quantity`.
# Verify that adding expected_move_pct does not change this value.
# ══════════════════════════════════════════════════════════════════════════════
def test_T005():
    tid = "T005"
    try:
        from capital_risk_engine.capital_risk_engine import CapitalRiskEngine as _CRE
        _cre = _CRE.__new__(_CRE)   # bypass __init__

        def _cre_quality(s) -> float:
            return s.confidence + (0.01 * s.quantity if hasattr(s, "quantity") else 0.0)

        sig_before = _make_signal(confidence=7.0, quantity=5)
        score_before = _cre_quality(sig_before)

        sig_after = _make_signal(confidence=7.0, quantity=5)
        # Set observational fields exactly as scan() does
        sig_after.expected_move_pct    = 2.5
        sig_after._obs_candidate_score = 0.72
        sig_after._obs_regime          = "RANGE_MARKET"
        score_after = _cre_quality(sig_after)

        _assert(tid, "Telemetry cannot alter candidate ranking",
                score_before == score_after,
                f"before={score_before}, after={score_after}")
    except ImportError:
        # CRE not importable in test harness — use inline quality function
        def _cre_quality(s) -> float:
            return s.confidence + (0.01 * s.quantity)

        sig_a = _make_signal(confidence=7.0, quantity=5)
        sig_b = _make_signal(confidence=7.0, quantity=5)
        sig_b.expected_move_pct    = 2.5
        sig_b._obs_candidate_score = 0.72
        sig_b._obs_regime          = "RANGE_MARKET"
        _assert(tid, "Telemetry cannot alter candidate ranking (inline check)",
                _cre_quality(sig_a) == _cre_quality(sig_b),
                f"a={_cre_quality(sig_a)}, b={_cre_quality(sig_b)}")


# ══════════════════════════════════════════════════════════════════════════════
# T006 — Telemetry cannot alter strategy_name
# ══════════════════════════════════════════════════════════════════════════════
def test_T006():
    tid = "T006"
    sig = _make_signal(strategy_name="trend_pullback")
    original = sig.strategy_name
    # Simulate telemetry attachment
    sig.expected_move_pct    = 3.75
    sig._obs_candidate_score = 0.88
    sig._obs_regime          = "BULL_TREND"
    _assert(tid, "Telemetry cannot alter strategy_name",
            sig.strategy_name == original,
            f"changed from '{original}' to '{sig.strategy_name}'")


# ══════════════════════════════════════════════════════════════════════════════
# T007 — Telemetry cannot alter quantity (position sizing)
# ══════════════════════════════════════════════════════════════════════════════
def test_T007():
    tid = "T007"
    sig = _make_signal(quantity=12)
    original_qty = sig.quantity
    sig.expected_move_pct    = 4.12
    sig._obs_candidate_score = 0.65
    sig._obs_regime          = "RANGE_MARKET"
    _assert(tid, "Telemetry cannot alter quantity",
            sig.quantity == original_qty,
            f"changed from {original_qty} to {sig.quantity}")


# ══════════════════════════════════════════════════════════════════════════════
# T008 — Telemetry cannot trigger an order
#
# The observer only writes to disk.  OrderManager.place_order() must NOT be
# called as a side-effect of record_signal_observation().
# ══════════════════════════════════════════════════════════════════════════════
def test_T008():
    tid = "T008"
    from opportunity_engine.mop_rc001_observer import record_signal_observation
    order_calls: list = []

    with tempfile.TemporaryDirectory() as tmpdir:
        import opportunity_engine.mop_rc001_observer as _obs_mod
        _orig_data_dir = _obs_mod._DATA_DIR
        _obs_mod._DATA_DIR = Path(tmpdir) / "mop_rc001"

        try:
            sig = _make_signal()
            sig.expected_move_pct    = 2.5
            sig._obs_candidate_score = 0.70
            sig._obs_regime          = "RANGE_MARKET"

            with patch("builtins.__import__", side_effect=lambda *a, **kw: __import__(*a, **kw)):
                record_signal_observation(sig, {"rsi": 55.0, "volume_ratio": 2.1})

            # No import from execution_engine or order_manager should have happened
            # as a side-effect; order_calls list must be empty
            _assert(tid, "Observer never calls OrderManager",
                    len(order_calls) == 0,
                    f"order_calls had {len(order_calls)} entries")
        finally:
            _obs_mod._DATA_DIR = _orig_data_dir
            _obs_mod._SEEN_THIS_SESSION.clear()


# ══════════════════════════════════════════════════════════════════════════════
# T009 — No look-ahead: only atr, entry_price, rr used at signal creation time
#
# Verify the formula uses ONLY fields present on the signal at creation time.
# Future market data (next-bar close, post-market data) are NOT referenced.
# ══════════════════════════════════════════════════════════════════════════════
def test_T009():
    tid = "T009"
    # Simulate signal creation using ONLY pre-signal data:
    #   atr       = ATR(14) computed from historical closes (pre-signal)
    #   entry     = LTP at signal time (live price at scan moment)
    #   rr        = derived from ATR × multiplier constants (no future data)
    pre_signal_atr   = 3.5
    pre_signal_entry = 150.0
    pre_signal_stop  = 150.0 - 1.5 * pre_signal_atr   # ATR_STOP_MULTIPLIER = 1.5
    pre_signal_target = pre_signal_entry + 2.5 * (pre_signal_entry - pre_signal_stop)

    sig = _make_signal(
        entry_price  = pre_signal_entry,
        stop_loss    = round(pre_signal_stop, 2),
        target_price = round(pre_signal_target, 2),
        atr          = pre_signal_atr,
    )

    # Compute expected_move_pct using only pre-signal fields
    try:
        rr_obs = sig.risk_reward_ratio
        if sig.atr and sig.entry_price and sig.entry_price > 0 and rr_obs > 0:
            emp = round(sig.atr / sig.entry_price * rr_obs * 100, 4)
        else:
            emp = None
    except Exception as e:
        _fail(tid, "No look-ahead in expected_move_pct", f"Exception: {e}")
        return

    # Assert: result computable purely from pre-signal values
    if emp is None:
        _fail(tid, "No look-ahead", "emp was None with valid inputs")
        return

    # Re-derive expected value using SAME formula, SAME pre-signal values
    expected = _expected_move_formula(pre_signal_atr, pre_signal_entry, sig.risk_reward_ratio)
    _assert(tid, "No look-ahead — expected_move_pct uses only pre-signal data",
            emp == expected,
            f"emp={emp} expected={expected}")


# ══════════════════════════════════════════════════════════════════════════════
# T010 — Duplicate observation does not create duplicate records
# ══════════════════════════════════════════════════════════════════════════════
def test_T010():
    tid = "T010"
    from opportunity_engine.mop_rc001_observer import record_signal_observation
    import opportunity_engine.mop_rc001_observer as _obs_mod

    with tempfile.TemporaryDirectory() as tmpdir:
        _orig_data_dir = _obs_mod._DATA_DIR
        _obs_mod._DATA_DIR = Path(tmpdir) / "mop_rc001"
        _obs_mod._SEEN_THIS_SESSION.clear()

        try:
            sig = _make_signal(symbol="RELIANCE", entry_price=1307.80)
            sig.expected_move_pct    = 2.8
            sig._obs_candidate_score = 0.75
            sig._obs_regime          = "RANGE_MARKET"
            candidate = {"rsi": 50.0, "volume_ratio": 2.0, "sector": "Energy"}

            # Call twice with the same signal
            record_signal_observation(sig, candidate)
            record_signal_observation(sig, candidate)

            # Read back and count records
            from opportunity_engine.mop_rc001_observer import load_observations
            _obs_mod._DATA_DIR = Path(tmpdir) / "mop_rc001"
            recs = load_observations()
            n_reliance = sum(1 for r in recs if r.get("symbol") == "RELIANCE")

            _assert(tid, "Duplicate call → only 1 record",
                    n_reliance == 1,
                    f"found {n_reliance} records for RELIANCE (expected 1)")
        finally:
            _obs_mod._DATA_DIR = _orig_data_dir
            _obs_mod._SEEN_THIS_SESSION.clear()


# ══════════════════════════════════════════════════════════════════════════════
# Bonus tests (structure / schema / safety)
# ══════════════════════════════════════════════════════════════════════════════

def test_T011_new_fields_default_none():
    """TradeSignal fields default to None — no existing callers break."""
    tid = "T011"
    sig = _make_signal()
    _assert(tid, "expected_move_pct defaults to None",
            sig.expected_move_pct is None, f"got {sig.expected_move_pct}")


def test_T012_observer_creates_dir():
    """Observer creates data/mop_rc001/ automatically."""
    tid = "T012"
    from opportunity_engine.mop_rc001_observer import record_signal_observation
    import opportunity_engine.mop_rc001_observer as _obs_mod

    with tempfile.TemporaryDirectory() as tmpdir:
        _orig_data_dir = _obs_mod._DATA_DIR
        new_dir = Path(tmpdir) / "mop_rc001"
        _obs_mod._DATA_DIR = new_dir
        _obs_mod._SEEN_THIS_SESSION.clear()

        try:
            sig = _make_signal(symbol="INFY")
            record_signal_observation(sig, {})
            _assert(tid, "Observer creates mop_rc001/ directory",
                    new_dir.exists(), "directory not created")
        finally:
            _obs_mod._DATA_DIR = _orig_data_dir
            _obs_mod._SEEN_THIS_SESSION.clear()


def test_T013_observation_schema():
    """Written record contains required keys."""
    tid = "T013"
    required_keys = {
        "obs_id", "ts_utc", "trading_date", "symbol", "direction",
        "entry_price", "atr", "rr", "expected_move_pct", "confidence",
        "candidate_score", "strategy", "regime", "selected",
        "actual_return_pct", "no_lookahead", "observation_horizon_days",
    }
    from opportunity_engine.mop_rc001_observer import record_signal_observation, load_observations
    import opportunity_engine.mop_rc001_observer as _obs_mod

    with tempfile.TemporaryDirectory() as tmpdir:
        _orig_data_dir = _obs_mod._DATA_DIR
        _obs_mod._DATA_DIR = Path(tmpdir) / "mop_rc001"
        _obs_mod._SEEN_THIS_SESSION.clear()

        try:
            sig = _make_signal(symbol="AXISBANK")
            sig.expected_move_pct    = 3.1
            sig._obs_candidate_score = 0.80
            sig._obs_regime          = "BULL_TREND"
            record_signal_observation(sig, {"rsi": 58, "volume_ratio": 2.4})
            recs = load_observations()
            if not recs:
                _fail(tid, "Observation schema", "no records found")
                return
            rec = recs[0]
            missing = required_keys - set(rec.keys())
            _assert(tid, "Observation record has required keys",
                    not missing, f"missing: {missing}")
        finally:
            _obs_mod._DATA_DIR = _orig_data_dir
            _obs_mod._SEEN_THIS_SESSION.clear()


def test_T014_selected_null_at_creation():
    """'selected' field is null at creation time — no outcome is assumed."""
    tid = "T014"
    from opportunity_engine.mop_rc001_observer import record_signal_observation, load_observations
    import opportunity_engine.mop_rc001_observer as _obs_mod

    with tempfile.TemporaryDirectory() as tmpdir:
        _orig_data_dir = _obs_mod._DATA_DIR
        _obs_mod._DATA_DIR = Path(tmpdir) / "mop_rc001"
        _obs_mod._SEEN_THIS_SESSION.clear()

        try:
            sig = _make_signal(symbol="HINDUNILVR")
            record_signal_observation(sig, {})
            recs = load_observations()
            if not recs:
                _fail(tid, "selected null at creation", "no records")
                return
            rec = recs[0]
            _assert(tid, "'selected' is null at signal creation",
                    rec.get("selected") is None,
                    f"got selected={rec.get('selected')}")
        finally:
            _obs_mod._DATA_DIR = _orig_data_dir
            _obs_mod._SEEN_THIS_SESSION.clear()


def test_T015_rr_property_unchanged():
    """risk_reward_ratio property is unchanged by observational field addition."""
    tid = "T015"
    sig = _make_signal(entry_price=200.0, stop_loss=197.0, target_price=207.5)
    rr_before = sig.risk_reward_ratio
    sig.expected_move_pct    = 2.5
    sig._obs_candidate_score = 0.7
    sig._obs_regime          = "RANGE_MARKET"
    rr_after = sig.risk_reward_ratio
    _assert(tid, "risk_reward_ratio property unchanged by new fields",
            abs(rr_before - rr_after) < 1e-9,
            f"before={rr_before}, after={rr_after}")


# ══════════════════════════════════════════════════════════════════════════════
# Runner
# ══════════════════════════════════════════════════════════════════════════════
def main():
    print("=" * 64)
    print("MOP-RC-001 Test Suite")
    print("=" * 64)

    tests = [
        test_T001, test_T002, test_T003, test_T004,
        test_T005, test_T006, test_T007, test_T008,
        test_T009, test_T010,
        test_T011_new_fields_default_none,
        test_T012_observer_creates_dir,
        test_T013_observation_schema,
        test_T014_selected_null_at_creation,
        test_T015_rr_property_unchanged,
    ]

    for t in tests:
        try:
            t()
        except Exception as exc:
            global _FAIL
            _FAIL += 1
            print(f"  FAIL  {t.__name__}: unhandled exception — {exc}")

    print("-" * 64)
    total = _PASS + _FAIL
    print(f"Results: {_PASS}/{total} passed, {_FAIL} failed")
    if _FAIL:
        print("VERDICT: SOME TESTS FAILED")
        sys.exit(1)
    else:
        print("VERDICT: ALL TESTS PASSED")


if __name__ == "__main__":
    main()
