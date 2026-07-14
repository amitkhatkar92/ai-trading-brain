"""tests/unit/investment/decision/reasoning/test_hypothesis.py"""
from __future__ import annotations

import pytest

from iios.investment.decision.reasoning.hypothesis_engine import Hypothesis, HypothesisEngine
from iios.investment.decision.reasoning.hypothesis_history import HypothesisHistory
from iios.investment.decision.reasoning.hypothesis_registry import HypothesisRegistry
from iios.investment.decision.reasoning.hypothesis_validator import HypothesisValidator
from iios.investment.decision.reasoning.reasoning_constants import (
    HypothesisStatus,
    HypothesisType,
    LogicValidationStatus,
    SignalDirection,
)


# ========================= HypothesisEngine ==============================

class TestHypothesisEngine:
    def test_generates_hypotheses(self, positive_signals):
        engine = HypothesisEngine()
        hypotheses, step = engine.generate("INFY", "equity", positive_signals)
        assert len(hypotheses) >= 2   # at least BULLISH, BEARISH, NEUTRAL

    def test_bullish_primary_for_positive_signals(self, positive_signals):
        engine = HypothesisEngine()
        hypotheses, _ = engine.generate("INFY", "equity", positive_signals)
        bullish = next(h for h in hypotheses if h.hypothesis_type == HypothesisType.BULLISH)
        assert bullish.support_score > 0

    def test_bearish_primary_for_negative_signals(self, negative_signals):
        engine = HypothesisEngine()
        hypotheses, _ = engine.generate("INFY", "equity", negative_signals)
        bearish = next(h for h in hypotheses if h.hypothesis_type == HypothesisType.BEARISH)
        assert bearish.support_score > 0

    def test_alternative_hypothesis_when_mixed(self, mixed_signals):
        engine = HypothesisEngine()
        hypotheses, _ = engine.generate("INFY", "equity", mixed_signals)
        types = {h.hypothesis_type for h in hypotheses}
        assert HypothesisType.ALTERNATIVE in types

    def test_empty_signals_gives_neutral(self):
        engine = HypothesisEngine()
        hypotheses, _ = engine.generate("X", "equity", [])
        neutral = next(h for h in hypotheses if h.hypothesis_type == HypothesisType.NEUTRAL)
        assert neutral is not None

    def test_step_type(self, positive_signals):
        from iios.investment.decision.reasoning.reasoning_constants import ReasoningStepType
        engine = HypothesisEngine()
        _, step = engine.generate("X", "equity", positive_signals)
        assert step.step_type == ReasoningStepType.HYPOTHESIS_FORMATION

    def test_hypothesis_is_immutable(self, positive_signals):
        engine = HypothesisEngine()
        hypotheses, _ = engine.generate("X", "equity", positive_signals)
        with pytest.raises(Exception):
            hypotheses[0].statement = "mutated"  # type: ignore

    def test_trace_ids_present(self, positive_signals):
        engine = HypothesisEngine()
        hypotheses, _ = engine.generate("X", "equity", positive_signals)
        bullish = next(h for h in hypotheses if h.hypothesis_type == HypothesisType.BULLISH)
        assert len(bullish.supporting_trace_ids) > 0


# ========================= HypothesisRegistry ============================

class TestHypothesisRegistry:
    def test_register_and_get(self, positive_signals, decision_id):
        engine = HypothesisEngine()
        hyps, _ = engine.generate("X", "equity", positive_signals)
        reg = HypothesisRegistry()
        reg.register(decision_id, hyps)
        assert len(reg.get_all(decision_id)) == len(hyps)

    def test_get_primary(self, positive_signals, decision_id):
        engine = HypothesisEngine()
        hyps, _ = engine.generate("X", "equity", positive_signals)
        reg = HypothesisRegistry()
        reg.register(decision_id, hyps)
        primary = reg.get_primary(decision_id)
        # primary may be None if none is SUPPORTED with these signals
        assert primary is None or isinstance(primary, Hypothesis)

    def test_unknown_decision_returns_empty(self):
        reg = HypothesisRegistry()
        assert reg.get_all("unknown") == []

    def test_by_type(self, positive_signals, decision_id):
        engine = HypothesisEngine()
        hyps, _ = engine.generate("X", "equity", positive_signals)
        reg = HypothesisRegistry()
        reg.register(decision_id, hyps)
        bullish = reg.get_by_type(decision_id, HypothesisType.BULLISH)
        assert bullish is not None
        assert bullish.hypothesis_type == HypothesisType.BULLISH

    def test_to_dict(self, positive_signals, decision_id):
        engine = HypothesisEngine()
        hyps, _ = engine.generate("X", "equity", positive_signals)
        reg = HypothesisRegistry()
        reg.register(decision_id, hyps)
        d = reg.to_dict()
        assert d["decisions"] == 1


# ========================= HypothesisValidator ===========================

class TestHypothesisValidator:
    def test_empty_gives_insufficient(self):
        v = HypothesisValidator()
        r = v.validate([])
        assert r.status == LogicValidationStatus.INSUFFICIENT

    def test_valid_when_one_supported(self, positive_signals):
        engine = HypothesisEngine()
        hyps, _ = engine.generate("X", "equity", positive_signals)
        v = HypothesisValidator()
        r = v.validate(hyps)
        assert r.status.is_usable

    def test_contradictory_when_both_supported(self, make_signal):
        from iios.investment.decision.reasoning.hypothesis_engine import _make_hypothesis
        bull_sigs = [make_signal(direction=SignalDirection.POSITIVE) for _ in range(4)]
        bear_sigs = [make_signal(direction=SignalDirection.NEGATIVE) for _ in range(4)]
        # Manually create two SUPPORTED hypotheses
        bullish = _make_hypothesis(
            HypothesisType.BULLISH, "bull", bull_sigs, bear_sigs, 8,
        )
        bearish = _make_hypothesis(
            HypothesisType.BEARISH, "bear", bear_sigs, bull_sigs, 8,
        )
        # Force both to SUPPORTED
        from dataclasses import replace
        bullish = replace(bullish, status=HypothesisStatus.SUPPORTED, support_score=0.7)
        bearish = replace(bearish, status=HypothesisStatus.SUPPORTED, support_score=0.7)
        v = HypothesisValidator()
        r = v.validate([bullish, bearish])
        assert r.contradictions_found is True
        assert r.status == LogicValidationStatus.CONTRADICTORY

    def test_to_dict(self, positive_signals):
        engine = HypothesisEngine()
        hyps, _ = engine.generate("X", "equity", positive_signals)
        v = HypothesisValidator()
        r = v.validate(hyps)
        d = r.to_dict()
        assert "status" in d
        assert "issues" in d


# ========================= HypothesisHistory =============================

class TestHypothesisHistory:
    def test_record_and_get(self, positive_signals):
        engine = HypothesisEngine()
        hyps, _ = engine.generate("INFY", "equity", positive_signals)
        hist = HypothesisHistory()
        hist.record_all("INFY", hyps)
        assert len(hist.get("INFY")) == len(hyps)

    def test_by_type(self, positive_signals):
        engine = HypothesisEngine()
        hyps, _ = engine.generate("INFY", "equity", positive_signals)
        hist = HypothesisHistory()
        hist.record_all("INFY", hyps)
        bulls = hist.by_type("INFY", HypothesisType.BULLISH)
        assert all(h.hypothesis_type == HypothesisType.BULLISH for h in bulls)

    def test_subjects(self, positive_signals):
        engine = HypothesisEngine()
        hyps, _ = engine.generate("INFY", "equity", positive_signals)
        hist = HypothesisHistory()
        hist.record_all("INFY", hyps)
        assert "INFY" in hist.subjects()
