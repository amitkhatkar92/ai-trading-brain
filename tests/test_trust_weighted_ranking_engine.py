"""
tests/test_trust_weighted_ranking_engine.py
===============================================
Self-learning module #26 (part 2): SYNTHESIS + GOVERNANCE for
opportunity_engine/trust_weighted_ranking_engine.py.

T01  get_effective_score() returns raw_score unchanged below the global
     MIN_HISTORY_DAYS gate
T02  get_effective_score() returns raw_score unchanged for a symbol with
     insufficient per-symbol history even if the global gate is met
T03  Once gated, a low trust score reduces the ranking score
T04  Once gated, a trust score of 1.0 leaves the score unchanged
T05  Degenerate-symbol guard: flat low scores across the whole window
     are treated as neutral (1.0), not penalised
T06  Fail-open: get_effective_score() never raises, falls back to raw_score
T07  run_daily_snapshot_and_check() reports gate_met correctly
T08  get_status() read-only accessor never raises
T09  Safety-contract source scan
"""
from __future__ import annotations

import os
from unittest.mock import patch

import pytest

import opportunity_engine.trust_weighted_ranking_engine as engine


def _recs(symbol, scores):
    return [{"date": f"2026-09-{i+1:02d}", "symbol": symbol, "trust_score": s} for i, s in enumerate(scores)]


def test_t01_below_global_gate_returns_raw_score():
    with patch("data_feeds.trust_score_history.get_history_days_count", return_value=2):
        result = engine.get_effective_score("RELIANCE", 10.0, today_trust_score=0.3)
    assert result == 10.0


def test_t02_below_per_symbol_history_returns_raw_score():
    with patch("data_feeds.trust_score_history.get_history_days_count", return_value=5), \
         patch("data_feeds.trust_score_history.get_records", return_value=_recs("RELIANCE", [0.5, 0.5])):
        result = engine.get_effective_score("RELIANCE", 10.0)
    assert result == 10.0


def test_t03_gated_low_trust_reduces_score():
    scores = [0.4, 0.5, 0.6, 0.7, 0.6]
    with patch("data_feeds.trust_score_history.get_history_days_count", return_value=5), \
         patch("data_feeds.trust_score_history.get_records", return_value=_recs("RELIANCE", scores)):
        result = engine.get_effective_score("RELIANCE", 10.0)
    assert result < 10.0


def test_t04_gated_perfect_trust_leaves_score_unchanged():
    scores = [1.0, 1.0, 1.0, 1.0, 1.0]
    with patch("data_feeds.trust_score_history.get_history_days_count", return_value=5), \
         patch("data_feeds.trust_score_history.get_records", return_value=_recs("RELIANCE", scores)):
        result = engine.get_effective_score("RELIANCE", 10.0)
    assert result == pytest.approx(10.0)


def test_t05_degenerate_flat_low_scores_treated_as_neutral():
    scores = [0.3, 0.3, 0.3, 0.3, 0.3]   # zero variance, below ceiling -- likely restart artifact
    with patch("data_feeds.trust_score_history.get_history_days_count", return_value=5), \
         patch("data_feeds.trust_score_history.get_records", return_value=_recs("RELIANCE", scores)):
        result = engine.get_effective_score("RELIANCE", 10.0)
    assert result == pytest.approx(10.0)


def test_t06_fail_open_never_raises():
    with patch("data_feeds.trust_score_history.get_history_days_count", side_effect=RuntimeError("boom")):
        result = engine.get_effective_score("RELIANCE", 10.0)
    assert result == 10.0


def test_t07_daily_check_reports_gate_status():
    with patch("data_feeds.trust_score_history.record_daily_trust_snapshot", return_value={"status": "OK"}), \
         patch("data_feeds.trust_score_history.get_history_days_count", return_value=6):
        result = engine.run_daily_snapshot_and_check()
    assert result["gate_met"] is True
    assert result["history_days_count"] == 6


def test_t08_get_status_never_raises():
    with patch("data_feeds.trust_score_history.get_history_days_count", side_effect=RuntimeError("boom")):
        status = engine.get_status()
    assert status["gate_met"] is False


def test_t09_safety_contract_source_scan():
    src_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "opportunity_engine", "trust_weighted_ranking_engine.py",
    )
    src = open(src_path, encoding="utf-8").read()
    for forbidden in ("execution_engine", "order_manager", "dhan_feed", "broker", "risk_control"):
        assert f"import {forbidden}" not in src
        assert f"from {forbidden}" not in src
