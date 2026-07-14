"""tests/unit/investment/decision/reasoning/test_argument_analysis.py"""
from __future__ import annotations

import pytest

from iios.investment.decision.reasoning.argument_engine import ArgumentEngine, ArgumentReport
from iios.investment.decision.reasoning.argument_strength import ArgumentStrength
from iios.investment.decision.reasoning.hypothesis_engine import HypothesisEngine
from iios.investment.decision.reasoning.opposing_arguments import OpposingArguments
from iios.investment.decision.reasoning.reasoning_constants import (
    ArgumentStrengthLevel,
    ArgumentType,
    SignalDirection,
)
from iios.investment.decision.reasoning.supporting_arguments import Argument, SupportingArguments


# ========================= SupportingArguments ===========================

class TestSupportingArguments:
    def test_build_returns_argument(self, positive_signals):
        sa  = SupportingArguments()
        args = sa.build("HYP-1", "Bullish hypothesis.", positive_signals)
        assert len(args) == 1
        assert args[0].argument_type == ArgumentType.SUPPORTING

    def test_empty_signals_returns_empty(self):
        sa = SupportingArguments()
        assert sa.build("HYP-1", "stmt", []) == []

    def test_trace_ids_present(self, positive_signals):
        sa   = SupportingArguments()
        args = sa.build("HYP-1", "stmt", positive_signals)
        assert len(args[0].trace_ids) == len(positive_signals)

    def test_strength_score_range(self, positive_signals):
        sa   = SupportingArguments()
        args = sa.build("HYP-1", "stmt", positive_signals)
        assert 0.0 <= args[0].strength_score <= 1.0

    def test_is_immutable(self, positive_signals):
        sa   = SupportingArguments()
        args = sa.build("HYP-1", "stmt", positive_signals)
        with pytest.raises(Exception):
            args[0].claim = "mutated"  # type: ignore


# ========================= OpposingArguments =============================

class TestOpposingArguments:
    def test_build_returns_opposing(self, negative_signals):
        oa   = OpposingArguments()
        args = oa.build("HYP-1", "Bullish.", negative_signals)
        assert len(args) == 1
        assert args[0].argument_type == ArgumentType.OPPOSING

    def test_empty_signals(self):
        assert OpposingArguments().build("HYP-1", "stmt", []) == []


# ========================= ArgumentStrength ==============================

class TestArgumentStrength:
    def _make_arg(self, atype: ArgumentType, score: float) -> Argument:
        from datetime import datetime, timezone
        import uuid
        from iios.investment.decision.reasoning.reasoning_constants import ArgumentStrengthLevel
        return Argument(
            argument_id=str(uuid.uuid4()),
            hypothesis_id="H1",
            argument_type=atype,
            claim="test claim",
            evidence_ids=(),
            trace_ids=(),
            signal_keys=(),
            strength_score=score,
            strength_level=ArgumentStrengthLevel.from_score(score),
            created_at=datetime.now(timezone.utc),
        )

    def test_net_positive_when_more_support(self):
        strength = ArgumentStrength()
        args = [
            self._make_arg(ArgumentType.SUPPORTING, 0.8),
            self._make_arg(ArgumentType.SUPPORTING, 0.7),
            self._make_arg(ArgumentType.OPPOSING,   0.2),
        ]
        summary = strength.evaluate("H1", args)
        assert summary.net_strength > 0

    def test_net_negative_when_more_opposition(self):
        strength = ArgumentStrength()
        args = [
            self._make_arg(ArgumentType.SUPPORTING, 0.2),
            self._make_arg(ArgumentType.OPPOSING,   0.9),
        ]
        summary = strength.evaluate("H1", args)
        assert summary.net_strength < 0

    def test_strong_level_when_high_net(self):
        strength = ArgumentStrength()
        args = [self._make_arg(ArgumentType.SUPPORTING, 0.9)]
        summary = strength.evaluate("H1", args)
        assert summary.strength_level == ArgumentStrengthLevel.STRONG

    def test_to_dict(self, positive_signals):
        sa = SupportingArguments()
        args = sa.build("H1", "stmt", positive_signals)
        strength = ArgumentStrength()
        summary = strength.evaluate("H1", args)
        d = summary.to_dict()
        assert "net_strength" in d
        assert "strength_level" in d


# ========================= ArgumentEngine ================================

class TestArgumentEngine:
    def test_evaluate_all_returns_reports(self, mixed_signals):
        engine = HypothesisEngine()
        hyps, _ = engine.generate("X", "equity", mixed_signals)
        ae = ArgumentEngine()
        reports, step = ae.evaluate_all(hyps, mixed_signals)
        assert len(reports) == len(hyps)
        from iios.investment.decision.reasoning.reasoning_constants import ReasoningStepType
        assert step.step_type == ReasoningStepType.ARGUMENT_EVALUATION

    def test_bullish_report_has_supporting_args(self, positive_signals):
        engine = HypothesisEngine()
        hyps, _ = engine.generate("X", "equity", positive_signals)
        ae = ArgumentEngine()
        reports, _ = ae.evaluate_all(hyps, positive_signals)
        bullish_report = next(
            (r for r in reports if r.hypothesis_type_value == "bullish"), None
        )
        assert bullish_report is not None
        assert len(bullish_report.supporting_arguments) > 0

    def test_is_net_supported_for_bullish_positive(self, positive_signals):
        engine = HypothesisEngine()
        hyps, _ = engine.generate("X", "equity", positive_signals)
        ae = ArgumentEngine()
        reports, _ = ae.evaluate_all(hyps, positive_signals)
        bullish_report = next(r for r in reports if r.hypothesis_type_value == "bullish")
        assert bullish_report.is_net_supported

    def test_to_dict(self, mixed_signals):
        engine = HypothesisEngine()
        hyps, _ = engine.generate("X", "equity", mixed_signals)
        ae = ArgumentEngine()
        reports, _ = ae.evaluate_all(hyps, mixed_signals)
        d = reports[0].to_dict()
        assert "hypothesis_id" in d
        assert "is_net_supported" in d
