"""
tests/test_sizing_bounds_refinement_engine.py
=================================================
Self-learning module #27: confidence + strategy-history combined sizing
-- calibration layer for perf_weight's own bounds.

T01  Insufficient sample stays WAITING_FOR_EVIDENCE
T02  Strong positive signal (boosted cohort outperforms) starts SHADOW
     with direction=+1
T03  No signal (cohorts equal) stays WAITING
T04  Shadow blocked until enough new evidence accumulates
T05  Shadow promotes to ACTIVE on reconfirming evidence
T06  Shadow REJECTS on contradicting new evidence
T07  ACTIVE auto-ROLLS_BACK when post-activation evidence degrades
T08  get_effective_perf_weight_bounds() with no active adjustment ==
     exact default (0.5, 2.0)
T09  An ACTIVE positive adjustment widens the upper bound, bounded by
     MAX_BOUND_ADJUSTMENT
T10  Cooldown blocks immediate re-evaluation
T11  Fail-open: run_daily_refinement_check() never raises
T12  Safety-contract source scan: zero imports of execution_engine/
     order_manager/dhan_feed/broker; portfolio_allocation_ai.py is never
     imported or modified by this module
"""
from __future__ import annotations

import os
from unittest.mock import patch

import pytest

import learning_system.sizing_bounds_refinement_engine as engine


@pytest.fixture(autouse=True)
def _isolated_store(tmp_path):
    with patch.object(engine, "_EVIDENCE_PATH", str(tmp_path / "evidence.jsonl")), \
         patch.object(engine, "_STATE_PATH", str(tmp_path / "state.json")), \
         patch.object(engine, "_BOUNDS_PATH", str(tmp_path / "active_bounds.json")), \
         patch.object(engine, "_STORE_DIR", str(tmp_path)), \
         patch.object(engine, "_LEDGER_PATH", str(tmp_path / "ledger.jsonl")):
        engine._cache_mtime = None
        engine._cache_bounds = None
        yield


def _cohort_records(n_per_cohort, boosted_win_rate, not_boosted_win_rate):
    """Interleave boosted/not-boosted records, each cohort's wins spread
    proportionally so a 70/30 chronological split preserves both ratios."""
    def _wins(n, wr):
        acc = 0.0
        out = []
        for _ in range(n):
            acc += wr
            w = acc >= 1.0
            if w:
                acc -= 1.0
            out.append(w)
        return out

    boosted_wins = _wins(n_per_cohort, boosted_win_rate)
    not_boosted_wins = _wins(n_per_cohort, not_boosted_win_rate)
    recs = []
    for i in range(n_per_cohort):
        recs.append({"timestamp": f"2026-01-{i+1:03d}", "strategy": "X",
                      "perf_weight": 1.5, "r_multiple": 1.0 if boosted_wins[i] else -1.0,
                      "won": boosted_wins[i]})
        recs.append({"timestamp": f"2026-01-{i+1:03d}b", "strategy": "X",
                      "perf_weight": 1.0, "r_multiple": 1.0 if not_boosted_wins[i] else -1.0,
                      "won": not_boosted_wins[i]})
    return recs


def test_t01_insufficient_sample_waits():
    records = _cohort_records(5, 0.7, 0.3)
    with patch("learning_system.sizing_bounds_refinement_engine.get_records", return_value=records):
        result = engine.run_daily_refinement_check()
    assert result["state_status"] == engine.STATUS_WAITING


def test_t02_strong_positive_signal_starts_shadow():
    records = _cohort_records(40, 0.75, 0.25)
    with patch("learning_system.sizing_bounds_refinement_engine.get_records", return_value=records):
        result = engine.run_daily_refinement_check()
    assert result["state_status"] == engine.STATUS_SHADOW


def test_t03_no_signal_stays_waiting():
    records = _cohort_records(40, 0.5, 0.5)
    with patch("learning_system.sizing_bounds_refinement_engine.get_records", return_value=records):
        result = engine.run_daily_refinement_check()
    assert result["state_status"] == engine.STATUS_WAITING


def test_t04_shadow_blocked_until_enough_new_evidence():
    all_records = _cohort_records(40, 0.75, 0.25)
    with patch("learning_system.sizing_bounds_refinement_engine.get_records", return_value=all_records):
        engine.run_daily_refinement_check()  # -> SHADOW
        with_few_more = all_records + _cohort_records(3, 0.75, 0.25)
        with patch("learning_system.sizing_bounds_refinement_engine.get_records", return_value=with_few_more):
            result = engine.run_daily_refinement_check()
    assert result["state_status"] == engine.STATUS_SHADOW


def test_t05_shadow_promotes_on_reconfirmation():
    all_records = _cohort_records(40, 0.75, 0.25)
    with patch("learning_system.sizing_bounds_refinement_engine.get_records", return_value=all_records):
        engine.run_daily_refinement_check()  # -> SHADOW
    new_evidence = _cohort_records(10, 0.75, 0.25)
    with patch("learning_system.sizing_bounds_refinement_engine.get_records", return_value=all_records + new_evidence):
        result = engine.run_daily_refinement_check()
    assert result["state_status"] == engine.STATUS_ACTIVE


def test_t06_shadow_rejects_on_contradicting_evidence():
    all_records = _cohort_records(40, 0.75, 0.25)
    with patch("learning_system.sizing_bounds_refinement_engine.get_records", return_value=all_records):
        engine.run_daily_refinement_check()  # -> SHADOW
    new_evidence = _cohort_records(10, 0.25, 0.75)   # reversed
    with patch("learning_system.sizing_bounds_refinement_engine.get_records", return_value=all_records + new_evidence):
        result = engine.run_daily_refinement_check()
    assert result["state_status"] == engine.STATUS_REJECTED


def test_t07_active_auto_rolls_back_on_degradation():
    all_records = _cohort_records(40, 0.75, 0.25)
    confirm_evidence = _cohort_records(10, 0.75, 0.25)
    with patch("learning_system.sizing_bounds_refinement_engine.get_records", return_value=all_records):
        engine.run_daily_refinement_check()  # -> SHADOW
    with patch("learning_system.sizing_bounds_refinement_engine.get_records", return_value=all_records + confirm_evidence):
        engine.run_daily_refinement_check()  # -> ACTIVE
    recovery_evidence = _cohort_records(10, 0.25, 0.75)
    with patch("learning_system.sizing_bounds_refinement_engine.get_records",
               return_value=all_records + confirm_evidence + recovery_evidence):
        result = engine.run_daily_refinement_check()
    assert result["state_status"] == engine.STATUS_ROLLED_BACK


def test_t08_default_bounds_with_no_adjustment():
    assert engine.get_effective_perf_weight_bounds() == (engine.DEFAULT_LOWER_BOUND, engine.DEFAULT_UPPER_BOUND)


def test_t09_active_positive_adjustment_widens_upper_bound():
    engine._write_json(engine._BOUNDS_PATH, {"upper_adjustment": 0.3})
    lo, hi = engine.get_effective_perf_weight_bounds()
    assert lo == engine.DEFAULT_LOWER_BOUND
    assert hi == engine.DEFAULT_UPPER_BOUND + 0.3


def test_t10_cooldown_blocks_immediate_reevaluation():
    records = _cohort_records(5, 0.7, 0.3)
    with patch("learning_system.sizing_bounds_refinement_engine.get_records", return_value=records):
        engine.run_daily_refinement_check()  # -> WAITING, sets last_checked_at
    strong_records = _cohort_records(40, 0.75, 0.25)
    with patch("learning_system.sizing_bounds_refinement_engine.get_records", return_value=strong_records):
        result = engine.run_daily_refinement_check()
    assert result["state_status"] == engine.STATUS_WAITING


def test_t11_fail_open_never_raises():
    with patch("learning_system.sizing_bounds_refinement_engine.get_records", side_effect=RuntimeError("boom")):
        result = engine.run_daily_refinement_check()
    assert result["status"] == "ERROR"


def test_t12_safety_contract_source_scan():
    src_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "learning_system", "sizing_bounds_refinement_engine.py",
    )
    src = open(src_path, encoding="utf-8").read()
    for forbidden in ("execution_engine", "order_manager", "dhan_feed", "broker"):
        assert f"import {forbidden}" not in src
        assert f"from {forbidden}" not in src
    assert "import portfolio_allocation_ai" not in src
    assert "portfolio_allocation_ai import" not in src
