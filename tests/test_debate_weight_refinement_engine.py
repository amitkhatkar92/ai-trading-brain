"""
tests/test_debate_weight_refinement_engine.py
=================================================
Self-Learning Ecosystem -- Post-roadmap Priority 3 (part 2):
SYNTHESIS + GOVERNANCE for MultiAgentDebate weight self-tuning.

T01  get_effective_weights() returns exact DEFAULT_WEIGHTS with no
     override file present
T02  Insufficient sample (< MIN_SAMPLE_FOR_VALIDATION) stays WAITING
T03  A strong, consistent, statistically-valid positive signal
     transitions WAITING -> SHADOW_ACTIVE with a bounded positive delta
T04  A strong, consistent negative signal produces a bounded NEGATIVE
     delta
T05  Shadow does not promote to ACTIVE until MIN_SHADOW_NEW_EVIDENCE new
     resolved votes have accumulated since shadow started
T06  Shadow promotes to ACTIVE once new evidence reconfirms the same
     direction, and get_effective_weights() then reflects the bounded
     delta
T07  Shadow REJECTS if new evidence contradicts the original direction
T08  ACTIVE rolls back automatically if post-activation evidence
     degrades below the rollback floor
T09  Weight delta is always bounded to +/-MAX_WEIGHT_DELTA even with a
     perfect (or perfectly wrong) accuracy signal
T10  Cooldown: a WAITING debater is not re-evaluated again immediately
     after a fresh check
T11  Fail-open: run_daily_refinement_check() never raises even when the
     vote tracker import itself fails
T12  Safety contract: zero imports of execution_engine/order_manager/
     dhan_feed/broker/risk_control anywhere in this module; AGENT_WEIGHTS
     in decision_ai/decision_engine.py is never imported directly here
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

import debate_system.debate_weight_refinement_engine as wre


@pytest.fixture(autouse=True)
def _isolated_store(tmp_path):
    state_path = str(tmp_path / "weight_refinement_state.json")
    overrides_path = str(tmp_path / "active_weight_overrides.json")
    ledger_path = str(tmp_path / "weight_refinement_ledger.jsonl")
    with patch.object(wre, "_STATE_PATH", state_path), \
         patch.object(wre, "_OVERRIDES_PATH", overrides_path), \
         patch.object(wre, "_LEDGER_PATH", ledger_path):
        wre._cache_mtime = None
        wre._cache_values = None
        yield


def _records(n_correct, n_incorrect, start="2020-01-01"):
    """Time-ordered records with correct/incorrect INTERLEAVED evenly
    (not blocked) so a 70/30 time-ordered split preserves the same
    accuracy ratio in both the train and OOS segments -- a blocked
    all-correct-then-all-incorrect ordering would put a skewed ratio in
    whichever segment the split boundary lands in, which is not
    representative of a debater with a stable, real accuracy rate."""
    from datetime import date, timedelta as td
    n = n_correct + n_incorrect
    if n == 0:
        return []
    labels = []
    correct_acc = 0.0
    incorrect_acc = 0.0
    for i in range(n):
        # Bresenham-style interleaving: pick whichever label is more "behind" its target ratio
        if n_correct and (correct_acc / n_correct if n_correct else 1) <= (incorrect_acc / n_incorrect if n_incorrect else 1):
            labels.append(True)
            correct_acc += 1
        else:
            labels.append(False)
            incorrect_acc += 1
    d = date.fromisoformat(start)
    return [{"decision_date": (d + td(days=i)).isoformat(), "correct": labels[i]} for i in range(n)]


def test_t01_default_weights_no_override(_isolated_store):
    weights = wre.get_effective_weights()
    assert weights == wre.DEFAULT_WEIGHTS


def test_t02_insufficient_sample_stays_waiting(_isolated_store):
    records = _records(20, 10)  # 30 total < MIN_SAMPLE_FOR_VALIDATION (50)
    with patch("debate_system.debate_vote_tracker.get_resolved_records_for_agent",
               return_value=records):
        result = wre.run_daily_refinement_check()
    assert result["per_agent"]["TechnicalAnalystAI"]["status"] == wre.STATUS_WAITING


def test_t03_strong_positive_signal_starts_shadow(_isolated_store):
    # 80% accuracy across 60 samples -- strong, consistent positive signal
    records = _records(48, 12)
    with patch("debate_system.debate_vote_tracker.get_resolved_records_for_agent",
               return_value=records):
        result = wre.run_daily_refinement_check()
    status = result["per_agent"]["TechnicalAnalystAI"]["status"]
    assert status == wre.STATUS_SHADOW
    weights = wre.get_effective_weights()
    assert weights["TechnicalAnalystAI"] == wre.DEFAULT_WEIGHTS["TechnicalAnalystAI"]  # shadow = zero live effect


def test_t04_strong_negative_signal_produces_negative_delta(_isolated_store):
    # 20% accuracy -- consistently WRONG debater
    records = _records(12, 48)
    with patch("debate_system.debate_vote_tracker.get_resolved_records_for_agent",
               return_value=records):
        wre.run_daily_refinement_check()
    state = wre._read_json(wre._STATE_PATH, {})
    assert state["TechnicalAnalystAI"]["status"] == wre.STATUS_SHADOW
    assert state["TechnicalAnalystAI"]["candidate_delta"] < 0


def test_t05_shadow_not_promoted_without_enough_new_evidence(_isolated_store):
    records = _records(48, 12)
    with patch("debate_system.debate_vote_tracker.get_resolved_records_for_agent",
               return_value=records):
        wre.run_daily_refinement_check()  # -> SHADOW

    more_records = records + _records(5, 0, start="2020-06-01")  # only 5 new, need 20
    with patch("debate_system.debate_vote_tracker.get_resolved_records_for_agent",
               return_value=more_records):
        result = wre.run_daily_refinement_check()
    assert result["per_agent"]["TechnicalAnalystAI"]["status"] == wre.STATUS_SHADOW


def test_t06_shadow_promotes_to_active_and_weight_reflects_delta(_isolated_store):
    records = _records(48, 12)
    with patch("debate_system.debate_vote_tracker.get_resolved_records_for_agent",
               return_value=records):
        wre.run_daily_refinement_check()  # -> SHADOW

    confirming_new = _records(18, 2, start="2020-06-01")  # 90% -- reconfirms positive direction
    more_records = records + confirming_new
    with patch("debate_system.debate_vote_tracker.get_resolved_records_for_agent",
               return_value=more_records):
        result = wre.run_daily_refinement_check()

    assert result["per_agent"]["TechnicalAnalystAI"]["status"] == wre.STATUS_ACTIVE
    weights = wre.get_effective_weights()
    assert weights["TechnicalAnalystAI"] > wre.DEFAULT_WEIGHTS["TechnicalAnalystAI"]
    assert weights["TechnicalAnalystAI"] <= wre.DEFAULT_WEIGHTS["TechnicalAnalystAI"] + wre.MAX_WEIGHT_DELTA


def test_t07_shadow_rejects_on_contradicting_new_evidence(_isolated_store):
    records = _records(48, 12)  # positive signal -> shadow
    with patch("debate_system.debate_vote_tracker.get_resolved_records_for_agent",
               return_value=records):
        wre.run_daily_refinement_check()

    contradicting_new = _records(2, 18, start="2020-06-01")  # 10% -- contradicts
    more_records = records + contradicting_new
    with patch("debate_system.debate_vote_tracker.get_resolved_records_for_agent",
               return_value=more_records):
        result = wre.run_daily_refinement_check()

    assert result["per_agent"]["TechnicalAnalystAI"]["status"] == wre.STATUS_REJECTED
    weights = wre.get_effective_weights()
    assert weights["TechnicalAnalystAI"] == wre.DEFAULT_WEIGHTS["TechnicalAnalystAI"]


def test_t08_active_rolls_back_on_degradation(_isolated_store):
    records = _records(48, 12)
    with patch("debate_system.debate_vote_tracker.get_resolved_records_for_agent",
               return_value=records):
        wre.run_daily_refinement_check()  # SHADOW
    confirming_new = _records(18, 2, start="2020-06-01")
    active_records = records + confirming_new
    with patch("debate_system.debate_vote_tracker.get_resolved_records_for_agent",
               return_value=active_records):
        wre.run_daily_refinement_check()  # ACTIVE

    degrading_new = _records(2, 18, start="2021-01-01")  # post-activation accuracy craters
    final_records = active_records + degrading_new
    with patch("debate_system.debate_vote_tracker.get_resolved_records_for_agent",
               return_value=final_records):
        result = wre.run_daily_refinement_check()

    assert result["per_agent"]["TechnicalAnalystAI"]["status"] == wre.STATUS_ROLLED_BACK
    weights = wre.get_effective_weights()
    assert weights["TechnicalAnalystAI"] == wre.DEFAULT_WEIGHTS["TechnicalAnalystAI"]


def test_t09_delta_always_bounded(_isolated_store):
    perfect_records = _records(60, 0)  # 100% accuracy
    card = wre._scorecard(perfect_records)
    delta = wre._candidate_delta(card)
    assert abs(delta) <= wre.MAX_WEIGHT_DELTA

    terrible_records = _records(0, 60)  # 0% accuracy
    card2 = wre._scorecard(terrible_records)
    delta2 = wre._candidate_delta(card2)
    assert abs(delta2) <= wre.MAX_WEIGHT_DELTA


def test_t10_cooldown_prevents_immediate_recheck(_isolated_store):
    # First check: insufficient sample -> WAITING, but last_checked_at gets stamped
    with patch("debate_system.debate_vote_tracker.get_resolved_records_for_agent",
               return_value=_records(5, 5)):
        wre.run_daily_refinement_check()
    state_before = wre._read_json(wre._STATE_PATH, {})
    assert "last_checked_at" in state_before["TechnicalAnalystAI"]

    # Second check, immediately after: even with now-qualifying evidence,
    # cooldown must block a fresh evaluation (no state change to SHADOW yet).
    with patch("debate_system.debate_vote_tracker.get_resolved_records_for_agent",
               return_value=_records(48, 12)):
        result = wre.run_daily_refinement_check()
    assert result["per_agent"]["TechnicalAnalystAI"]["status"] == wre.STATUS_WAITING


def test_t11_fail_open_on_import_error(_isolated_store):
    with patch("debate_system.debate_vote_tracker.get_resolved_records_for_agent",
               side_effect=RuntimeError("boom")):
        result = wre.run_daily_refinement_check()
    assert result["status"] == "ERROR"


def test_t12_no_forbidden_imports_and_no_live_agent_weights_import():
    import os
    src_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "debate_system", "debate_weight_refinement_engine.py",
    )
    src = open(src_path, encoding="utf-8").read()
    for forbidden in ("execution_engine", "order_manager", "dhan_feed", "broker", "risk_control"):
        assert f"import {forbidden}" not in src, f"forbidden import found: {forbidden}"
        assert f"from {forbidden}" not in src, f"forbidden import found: {forbidden}"
    assert "from decision_ai" not in src
    assert "import decision_ai" not in src
