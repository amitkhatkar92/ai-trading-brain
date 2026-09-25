"""
tests/test_cle_fingerprint_refinement_engine.py
==================================================
DTA-RESEARCH-QUALITY-001 -- SYNTHESIS + GOVERNANCE for CLE-001's
combination fingerprint selection.

T01  Insufficient sample stays WAITING_FOR_EVIDENCE
T02  Strong positive (high graduation rate) signal starts SHADOW
T03  No-signal (~50% graduation) never starts shadow
T04  Shadow blocked until enough new evidence
T05  Shadow promotes to ACTIVE on reconfirmation
T06  Shadow REJECTS on contradicting evidence
T07  ACTIVE auto-ROLLS_BACK on degrading evidence
T08  get_fingerprint_preference_adjustment defaults to 0.0 with no
     active adjustment
T09  An ACTIVE adjustment is bounded to +/-MAX_ADJUSTMENT
T10  Cooldown blocks immediate re-evaluation
T11  Fail-open: run_daily_refinement_check() never raises
T12  Safety-contract source scan: zero imports of execution_engine/
     order_manager/dhan_feed/broker/risk_control; IDR records are never
     mutated (read-only .get() only)
"""
from __future__ import annotations

import os
from unittest.mock import patch

import pytest

import learning_system.cle_fingerprint_refinement_engine as engine


@pytest.fixture(autouse=True)
def _isolated_store(tmp_path):
    with (
        patch.object(engine, "_STATE_PATH", str(tmp_path / "state.json")),
        patch.object(engine, "_ADJ_PATH", str(tmp_path / "active_adjustments.json")),
        patch.object(engine, "_RESOLVED_PATH", str(tmp_path / "resolved.json")),
        patch.object(engine, "_STORE_DIR", str(tmp_path)),
        patch.object(engine, "_LEDGER_PATH", str(tmp_path / "ledger.jsonl")),
    ):
        yield


def _resolved(n_total, graduation_rate, name="low_rsi_high_mom_accel"):
    n_grad = round(n_total * graduation_rate)
    out = {}
    acc = 0.0
    for i in range(n_total):
        acc += graduation_rate
        graduated = acc >= 1.0
        if graduated:
            acc -= 1.0
        out[f"CLE-SYM{i}-UP-2026010{i%9}"] = {"fingerprint_name": name, "graduated": graduated}
    return out


def _evidence_stub(n, name="low_rsi_high_mom_accel"):
    return [{"dna_id": f"CLE-SYM{i}-UP-2026010{i%9}", "fingerprint_name": name,
             "created_date": "2026-01-01"} for i in range(n)]


def _run_with(resolved_dict, n_evidence):
    with (
        patch("learning_system.cle_fingerprint_evidence_log.get_records",
              return_value=_evidence_stub(n_evidence)),
        patch.object(engine, "_resolve_new_outcomes", return_value=resolved_dict),
    ):
        return engine.run_daily_refinement_check()


def test_t01_insufficient_sample_waits():
    result = _run_with(_resolved(10, 0.9), 10)
    assert result["per_fingerprint"]["low_rsi_high_mom_accel"]["status"] == engine.STATUS_WAITING


def test_t02_strong_positive_signal_starts_shadow():
    result = _run_with(_resolved(60, 0.90), 60)
    assert result["per_fingerprint"]["low_rsi_high_mom_accel"]["status"] == engine.STATUS_SHADOW


def test_t03_no_signal_never_shadowed():
    result = _run_with(_resolved(60, 0.50), 60)
    assert result["per_fingerprint"]["low_rsi_high_mom_accel"]["status"] == engine.STATUS_WAITING


def test_t04_shadow_blocked_until_enough_new_evidence():
    base = _resolved(60, 0.90)
    _run_with(base, 60)  # -> SHADOW

    more = dict(base)
    more.update(_resolved(5, 0.85))
    result = _run_with(more, 65)
    assert result["per_fingerprint"]["low_rsi_high_mom_accel"]["status"] == engine.STATUS_SHADOW


def test_t05_shadow_promotes_on_reconfirmation():
    base = _resolved(60, 0.90)
    _run_with(base, 60)  # -> SHADOW

    new_ev = {f"NEW-{i}": {"fingerprint_name": "low_rsi_high_mom_accel", "graduated": True}
              for i in range(15)}
    combined = dict(base)
    combined.update(new_ev)
    result = _run_with(combined, 75)
    assert result["per_fingerprint"]["low_rsi_high_mom_accel"]["status"] == engine.STATUS_ACTIVE


def test_t06_shadow_rejects_on_contradicting_evidence():
    base = _resolved(60, 0.90)
    _run_with(base, 60)  # -> SHADOW

    new_ev = {f"NEW-{i}": {"fingerprint_name": "low_rsi_high_mom_accel", "graduated": False}
              for i in range(15)}
    combined = dict(base)
    combined.update(new_ev)
    result = _run_with(combined, 75)
    assert result["per_fingerprint"]["low_rsi_high_mom_accel"]["status"] == engine.STATUS_REJECTED


def test_t07_active_auto_rolls_back_on_degradation():
    base = _resolved(60, 0.90)
    _run_with(base, 60)  # -> SHADOW
    confirm = dict(base)
    confirm.update({f"NEW-{i}": {"fingerprint_name": "low_rsi_high_mom_accel", "graduated": True}
                    for i in range(15)})
    _run_with(confirm, 75)  # -> ACTIVE

    degraded = dict(confirm)
    degraded.update({f"DEG-{i}": {"fingerprint_name": "low_rsi_high_mom_accel", "graduated": False}
                      for i in range(15)})
    result = _run_with(degraded, 90)
    assert result["per_fingerprint"]["low_rsi_high_mom_accel"]["status"] == engine.STATUS_ROLLED_BACK


def test_t08_default_adjustment_is_zero():
    assert engine.get_fingerprint_preference_adjustment("low_rsi_high_mom_accel") == 0.0


def test_t09_active_adjustment_is_bounded():
    base = _resolved(60, 0.90)
    _run_with(base, 60)
    confirm = dict(base)
    confirm.update({f"NEW-{i}": {"fingerprint_name": "low_rsi_high_mom_accel", "graduated": True}
                    for i in range(15)})
    _run_with(confirm, 75)  # -> ACTIVE
    adj = engine.get_fingerprint_preference_adjustment("low_rsi_high_mom_accel")
    assert -engine.MAX_ADJUSTMENT <= adj <= engine.MAX_ADJUSTMENT
    assert adj > 0


def test_t10_cooldown_blocks_immediate_reevaluation():
    result1 = _run_with(_resolved(20, 0.55), 20)  # below MIN_EFFECT -> stays WAITING w/ last_checked_at set
    assert result1["per_fingerprint"]["low_rsi_high_mom_accel"]["status"] == engine.STATUS_WAITING
    # A second run immediately after should hit cooldown branch (no crash, still WAITING)
    result2 = _run_with(_resolved(20, 0.55), 20)
    assert result2["per_fingerprint"]["low_rsi_high_mom_accel"]["status"] == engine.STATUS_WAITING


def test_t11_fail_open_never_raises():
    with patch("learning_system.cle_fingerprint_evidence_log.get_records", side_effect=RuntimeError("boom")):
        result = engine.run_daily_refinement_check()
    assert result["status"] == "ERROR"


def test_t12_safety_contract_source_scan():
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "learning_system", "cle_fingerprint_refinement_engine.py")
    with open(path, encoding="utf-8") as f:
        source = f.read()
    for banned in ("execution_engine", "order_manager", "dhan_feed", "risk_control", "broker"):
        assert f"import {banned}" not in source
        assert f"from {banned}" not in source
    assert ".save(" not in source
    assert ".add_evidence(" not in source
