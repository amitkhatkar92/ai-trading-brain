"""
tests/test_institutional_flow_refinement_engine.py
======================================================
Self-learning module #30 (SYNTHESIS + GOVERNANCE) -- evidence-gated
validation of the institutional-flow score's predictive value, and its
bounded KDA relevance nudge.

T01  Insufficient sample stays WAITING_FOR_EVIDENCE
T02  Strong positive signal (high-score cohort outperforms) starts
     SHADOW with direction=+1
T03  No signal (cohorts equal) stays WAITING
T04  Shadow blocked until enough new evidence accumulates
T05  Shadow promotes to ACTIVE on reconfirming evidence
T06  Shadow REJECTS on contradicting new evidence
T07  ACTIVE auto-ROLLS_BACK when post-activation evidence degrades
T08  get_institutional_flow_adjustment() with no active adjustment == 0.0
T09  get_institutional_flow_adjustment(None) == 0.0 (fail-open on
     missing score)
T10  An ACTIVE positive adjustment only applies above POSITIVE_THRESHOLD
T11  Cooldown blocks immediate re-evaluation
T12  Fail-open: run_daily_refinement_check() never raises
T13  Safety-contract source scan: zero imports of execution_engine/
     order_manager/dhan_feed/broker; equity_scanner_ai.py and
     knowledge_decision_authority.py are never imported by this module
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

import learning_system.institutional_flow_refinement_engine as engine


@pytest.fixture(autouse=True)
def _isolated_store(tmp_path):
    with patch.object(engine, "_STATE_PATH", str(tmp_path / "state.json")), \
         patch.object(engine, "_ADJ_PATH", str(tmp_path / "active_adjustment.json")), \
         patch.object(engine, "_STORE_DIR", str(tmp_path)), \
         patch.object(engine, "_LEDGER_PATH", str(tmp_path / "ledger.jsonl")):
        engine._cache_mtime = None
        engine._cache_adjustment = None
        yield


def _cohort_records(n_per_cohort, high_win_rate, low_win_rate):
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

    high_wins = _wins(n_per_cohort, high_win_rate)
    low_wins = _wins(n_per_cohort, low_win_rate)
    recs = []
    for i in range(n_per_cohort):
        recs.append({"timestamp": f"2026-01-{i+1:03d}", "strategy": "X",
                      "institutional_flow_score": 0.5, "r_multiple": 1.0 if high_wins[i] else -1.0,
                      "won": high_wins[i]})
        recs.append({"timestamp": f"2026-01-{i+1:03d}b", "strategy": "X",
                      "institutional_flow_score": 0.0, "r_multiple": 1.0 if low_wins[i] else -1.0,
                      "won": low_wins[i]})
    return recs


def _patch_records(records):
    return patch(
        "learning_system.institutional_flow_evidence_log.get_records",
        return_value=records,
    )


def test_t01_insufficient_sample_waits():
    with _patch_records(_cohort_records(5, 0.8, 0.3)):
        result = engine.run_daily_refinement_check()
    assert result["state_status"] == engine.STATUS_WAITING


def test_t02_strong_positive_signal_starts_shadow():
    with _patch_records(_cohort_records(30, 0.85, 0.30)):
        result = engine.run_daily_refinement_check()
    assert result["state_status"] == engine.STATUS_SHADOW
    state = engine._read_json(engine._STATE_PATH, {})
    assert state["direction"] == 1


def test_t03_no_signal_stays_waiting():
    with _patch_records(_cohort_records(30, 0.5, 0.5)):
        result = engine.run_daily_refinement_check()
    assert result["state_status"] == engine.STATUS_WAITING


def test_t04_shadow_blocked_until_enough_new_evidence():
    with _patch_records(_cohort_records(30, 0.85, 0.30)):
        engine.run_daily_refinement_check()
    state = engine._read_json(engine._STATE_PATH, {})
    state.pop("last_checked_at", None)
    engine._write_json(engine._STATE_PATH, state)
    with _patch_records(_cohort_records(35, 0.85, 0.30)):
        result = engine.run_daily_refinement_check()
    assert result["state_status"] == engine.STATUS_SHADOW


def test_t05_shadow_promotes_to_active_on_reconfirmation():
    with _patch_records(_cohort_records(30, 0.85, 0.30)):
        engine.run_daily_refinement_check()
    with _patch_records(_cohort_records(45, 0.85, 0.30)):
        result = engine.run_daily_refinement_check()
    assert result["state_status"] == engine.STATUS_ACTIVE


def test_t06_shadow_rejects_on_contradicting_evidence():
    with _patch_records(_cohort_records(30, 0.85, 0.30)):
        engine.run_daily_refinement_check()
    contradicting = _cohort_records(30, 0.85, 0.30) + _cohort_records(15, 0.30, 0.85)
    with _patch_records(contradicting):
        result = engine.run_daily_refinement_check()
    assert result["state_status"] == engine.STATUS_REJECTED


def test_t07_active_rolls_back_on_degradation():
    with _patch_records(_cohort_records(30, 0.90, 0.20)):
        engine.run_daily_refinement_check()
    with _patch_records(_cohort_records(45, 0.90, 0.20)):
        engine.run_daily_refinement_check()
    degrading = _cohort_records(45, 0.90, 0.20) + _cohort_records(10, 0.20, 0.90)
    with _patch_records(degrading):
        result = engine.run_daily_refinement_check()
    assert result["state_status"] == engine.STATUS_ROLLED_BACK


def test_t08_default_adjustment_with_no_override():
    assert engine.get_institutional_flow_adjustment(0.5) == 0.0


def test_t09_none_score_returns_zero():
    assert engine.get_institutional_flow_adjustment(None) == 0.0


def test_t10_active_adjustment_only_above_threshold():
    with _patch_records(_cohort_records(30, 0.90, 0.20)):
        engine.run_daily_refinement_check()
    with _patch_records(_cohort_records(45, 0.90, 0.20)):
        engine.run_daily_refinement_check()
    # Above threshold -> real bounded adjustment applied
    above = engine.get_institutional_flow_adjustment(engine.POSITIVE_THRESHOLD + 0.1)
    assert above > 0.0
    assert above <= engine.MAX_ADJUSTMENT
    # Below/at threshold -> no adjustment
    below = engine.get_institutional_flow_adjustment(engine.POSITIVE_THRESHOLD - 0.1)
    assert below == 0.0


def test_t11_cooldown_blocks_immediate_recheck():
    with _patch_records(_cohort_records(30, 0.5, 0.5)):
        engine.run_daily_refinement_check()
    with _patch_records(_cohort_records(30, 0.90, 0.20)):
        result = engine.run_daily_refinement_check()
    assert result["state_status"] == engine.STATUS_WAITING
    assert result["detail"] == "cooldown"


def test_t12_fail_open_never_raises():
    with patch(
        "learning_system.institutional_flow_evidence_log.get_records",
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
                 "from opportunity_engine.equity_scanner_ai import",
                 "import opportunity_engine.equity_scanner_ai",
                 "from knowledge_authority.knowledge_decision_authority import",
                 "import knowledge_authority.knowledge_decision_authority")
    for token in forbidden:
        assert token not in src, f"forbidden import found: {token}"
