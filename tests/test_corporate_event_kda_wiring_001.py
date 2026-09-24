"""
tests/test_corporate_event_kda_wiring_001.py
================================================
Self-learning module #32 -- wiring tests: KDA fourth nudge, pipeline
observation builder, OrderRecord field, close_position() gating,
TradeSignal fields.

T01  Zero effect when no active adjustment exists (dormant on deploy)
T02  Bounded positive nudge applied when score clears POSITIVE_THRESHOLD
     and an ACTIVE adjustment exists
T03  No nudge when score does NOT clear POSITIVE_THRESHOLD
T04  Fail-open: get_corporate_event_adjustment raising leaves relevance
     unaffected
T05  Relevance never leaves [0.1, 1.0] with the nudge applied
T06  All four bridges (ARS, institutional-flow, company-growth,
     corporate-event) can apply together, still bounded
T07  Pipeline observation builder threads corporate_event_score from
     the signal into the obs dict
T08  OrderRecord.corporate_event_score defaults to None
T09  close_position() gates the evidence-log call on
     `rec.corporate_event_score is not None`
T10  TradeSignal has corporate_event_score / corporate_event_available
     fields, defaulting to None
"""
from __future__ import annotations

import inspect
from unittest.mock import patch

import pytest

from tests.test_kda_001 import KDA, _bm, _obs


def test_t01_zero_effect_with_no_active_adjustment():
    rec = KDA.evaluate(_obs(scanner_confidence=8.5, corporate_event_score=0.9), behaviour=_bm())
    expected_relevance = min(max(8.5 / 10.0, 0.1), 1.0)
    assert rec.authority_components.relevance == round(expected_relevance, 4)


def test_t02_bounded_positive_nudge_applied():
    with patch(
        "learning_system.corporate_event_refinement_engine.get_corporate_event_adjustment",
        return_value=0.05,
    ):
        rec = KDA.evaluate(_obs(scanner_confidence=8.5, corporate_event_score=0.9), behaviour=_bm())
    expected = min(max(8.5 / 10.0 + 0.05, 0.1), 1.0)
    assert rec.authority_components.relevance == round(expected, 4)


def test_t03_no_nudge_when_helper_returns_zero():
    with patch(
        "learning_system.corporate_event_refinement_engine.get_corporate_event_adjustment",
        return_value=0.0,
    ):
        rec = KDA.evaluate(_obs(scanner_confidence=8.5, corporate_event_score=0.1), behaviour=_bm())
    expected = min(max(8.5 / 10.0, 0.1), 1.0)
    assert rec.authority_components.relevance == round(expected, 4)


def test_t04_fail_open_on_exception():
    with patch(
        "learning_system.corporate_event_refinement_engine.get_corporate_event_adjustment",
        side_effect=RuntimeError("boom"),
    ):
        rec = KDA.evaluate(_obs(scanner_confidence=8.5, corporate_event_score=0.9), behaviour=_bm())
    expected = min(max(8.5 / 10.0, 0.1), 1.0)
    assert rec.authority_components.relevance == round(expected, 4)


def test_t05_relevance_clamped_within_bounds():
    with patch(
        "learning_system.corporate_event_refinement_engine.get_corporate_event_adjustment",
        return_value=0.05,
    ):
        rec = KDA.evaluate(_obs(scanner_confidence=10.0, corporate_event_score=0.9), behaviour=_bm())
    assert 0.1 <= rec.authority_components.relevance <= 1.0
    assert 0.0 <= rec.authority_components.composite_authority <= 1.0


def test_t06_all_four_bridges_apply_together_bounded():
    with patch(
        "learning_system.institutional_flow_refinement_engine.get_institutional_flow_adjustment",
        return_value=0.05,
    ), patch(
        "learning_system.company_growth_refinement_engine.get_company_growth_adjustment",
        return_value=0.05,
    ), patch(
        "learning_system.corporate_event_refinement_engine.get_corporate_event_adjustment",
        return_value=0.05,
    ):
        rec = KDA.evaluate(
            _obs(scanner_confidence=8.5, institutional_flow_score=0.9,
                 company_growth_score=0.9, corporate_event_score=0.9),
            behaviour=_bm(),
        )
    expected = min(max(8.5 / 10.0 + 0.05 + 0.05 + 0.05, 0.1), 1.0)
    assert rec.authority_components.relevance == round(expected, 4)


def test_t07_pipeline_observation_builder_threads_score():
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
        company_growth_score = 0.65
        corporate_event_score = 0.77

    pipeline = KnowledgeDecisionPipeline.__new__(KnowledgeDecisionPipeline)
    obs = pipeline._build_observation(_FakeSignal(), market_ctx={"regime": "bull_trend"})
    assert obs["corporate_event_score"] == 0.77


def test_t08_order_record_defaults_to_none():
    from execution_engine.order_manager import OrderRecord

    rec = OrderRecord(order_id="O1", symbol="X", direction="BUY", quantity=1,
                       entry_price=100.0, stop_loss=90.0, target=120.0, strategy="s")
    assert rec.corporate_event_score is None


def test_t09_close_position_gates_evidence_call():
    from execution_engine import order_manager as om_mod

    src = inspect.getsource(om_mod.OrderManager.close_position)
    assert "if rec.corporate_event_score is not None:" in src
    assert "record_corporate_event_outcome" in src


def test_t10_trade_signal_has_corporate_event_fields():
    from models.trade_signal import TradeSignal, SignalDirection, SignalType

    sig = TradeSignal(
        symbol="X", direction=SignalDirection.BUY, signal_type=SignalType.EQUITY,
        entry_price=100.0, stop_loss=90.0, target_price=120.0,
        quantity=1, strategy_name="s", source_agent="test",
    )
    assert sig.corporate_event_score is None
    assert sig.corporate_event_available is None
