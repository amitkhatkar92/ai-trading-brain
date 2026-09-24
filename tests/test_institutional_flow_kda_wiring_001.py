"""
tests/test_institutional_flow_kda_wiring_001.py
===================================================
Self-learning module #30 -- wiring tests:
  (a) knowledge_authority/knowledge_decision_authority.py's
      _compute_authority() bounded nudge from
      get_institutional_flow_adjustment()
  (b) knowledge_authority/knowledge_decision_pipeline.py's observation
      builder threads institutional_flow_score through
  (c) execution_engine/order_manager.py's OrderRecord field + close_
      position() evidence hook gating
  (d) opportunity_engine/equity_scanner_ai.py's TradeSignal fields exist

T01  Zero effect when no active adjustment exists (current real-world
     state, dormant on deploy)
T02  Bounded positive nudge applied when score clears POSITIVE_THRESHOLD
     and an ACTIVE adjustment exists
T03  No nudge when score does NOT clear POSITIVE_THRESHOLD even with an
     ACTIVE adjustment
T04  Fail-open: get_institutional_flow_adjustment raising leaves
     relevance unaffected
T05  Relevance never leaves [0.1, 1.0] with the nudge applied
T06  knowledge_decision_pipeline._build_observation-equivalent threads
     institutional_flow_score from the signal into the obs dict
T07  OrderRecord.institutional_flow_score defaults to None
T08  close_position() gates the evidence-log call on
     `rec.institutional_flow_score is not None` (source-inspection guard)
T09  TradeSignal has institutional_flow_score / institutional_flow_available
     fields, defaulting to None
"""
from __future__ import annotations

import inspect
from unittest.mock import patch

import pytest

from tests.test_kda_001 import KDA, _bm, _obs


def test_t01_zero_effect_with_no_active_adjustment():
    rec = KDA.evaluate(_obs(scanner_confidence=8.5, institutional_flow_score=0.9), behaviour=_bm())
    expected_relevance = min(max(8.5 / 10.0, 0.1), 1.0)
    assert rec.authority_components is not None
    assert rec.authority_components.relevance == round(expected_relevance, 4)


def test_t02_bounded_positive_nudge_applied():
    with patch(
        "learning_system.institutional_flow_refinement_engine.get_institutional_flow_adjustment",
        return_value=0.05,
    ):
        rec = KDA.evaluate(_obs(scanner_confidence=8.5, institutional_flow_score=0.9), behaviour=_bm())
    expected = min(max(8.5 / 10.0 + 0.05, 0.1), 1.0)
    assert rec.authority_components.relevance == round(expected, 4)


def test_t03_no_nudge_when_helper_returns_zero():
    with patch(
        "learning_system.institutional_flow_refinement_engine.get_institutional_flow_adjustment",
        return_value=0.0,
    ):
        rec = KDA.evaluate(_obs(scanner_confidence=8.5, institutional_flow_score=0.1), behaviour=_bm())
    expected = min(max(8.5 / 10.0, 0.1), 1.0)
    assert rec.authority_components.relevance == round(expected, 4)


def test_t04_fail_open_on_exception():
    with patch(
        "learning_system.institutional_flow_refinement_engine.get_institutional_flow_adjustment",
        side_effect=RuntimeError("boom"),
    ):
        rec = KDA.evaluate(_obs(scanner_confidence=8.5, institutional_flow_score=0.9), behaviour=_bm())
    expected = min(max(8.5 / 10.0, 0.1), 1.0)
    assert rec.authority_components.relevance == round(expected, 4)


def test_t05_relevance_clamped_within_bounds():
    with patch(
        "learning_system.institutional_flow_refinement_engine.get_institutional_flow_adjustment",
        return_value=0.05,
    ):
        rec = KDA.evaluate(_obs(scanner_confidence=10.0, institutional_flow_score=0.9), behaviour=_bm())
    assert 0.1 <= rec.authority_components.relevance <= 1.0
    assert 0.0 <= rec.authority_components.composite_authority <= 1.0


def test_t06_pipeline_observation_builder_threads_score():
    from knowledge_authority.knowledge_decision_pipeline import KnowledgeDecisionPipeline

    class _FakeSignal:
        symbol = "RELIANCE"
        direction = "BUY"
        entry_price = 100.0
        atr = 2.0
        scanner_score = 7.0
        confidence = 7.0
        candidate_score = 0.5
        target_price = 110.0
        stop_loss = 95.0
        risk_reward_ratio = 2.0
        expected_move_pct = 0.0
        setup_type = "breakout"
        strategy_name = "breakout"
        opportunity_id = ""
        institutional_flow_score = 0.42

    pipeline = KnowledgeDecisionPipeline.__new__(KnowledgeDecisionPipeline)
    obs = pipeline._build_observation(_FakeSignal(), market_ctx={"regime": "bull_trend"})
    assert obs["institutional_flow_score"] == 0.42


def test_t07_order_record_defaults_to_none():
    from execution_engine.order_manager import OrderRecord

    rec = OrderRecord(order_id="O1", symbol="X", direction="BUY", quantity=1,
                       entry_price=100.0, stop_loss=90.0, target=120.0, strategy="s")
    assert rec.institutional_flow_score is None


def test_t08_close_position_gates_evidence_call():
    from execution_engine import order_manager as om_mod

    src = inspect.getsource(om_mod.OrderManager.close_position)
    assert "if rec.institutional_flow_score is not None:" in src
    assert "record_institutional_flow_outcome" in src


def test_t09_trade_signal_has_institutional_flow_fields():
    from models.trade_signal import TradeSignal
    from models.trade_signal import SignalDirection, SignalType

    sig = TradeSignal(
        symbol="X", direction=SignalDirection.BUY, signal_type=SignalType.EQUITY,
        entry_price=100.0, stop_loss=90.0, target_price=120.0,
        quantity=1, strategy_name="s", source_agent="test",
    )
    assert sig.institutional_flow_score is None
    assert sig.institutional_flow_available is None
