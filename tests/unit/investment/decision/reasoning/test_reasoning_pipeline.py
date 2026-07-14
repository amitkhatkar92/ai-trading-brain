"""tests/unit/investment/decision/reasoning/test_reasoning_pipeline.py"""
from __future__ import annotations

import pytest
import pytest_asyncio

from iios.investment.decision.reasoning.decision_logic import DecisionLogic
from iios.investment.decision.reasoning.logic_validator import LogicValidator
from iios.investment.decision.reasoning.reasoning_constants import (
    LogicValidationStatus,
    ReasoningStepType,
)
from iios.investment.decision.reasoning.reasoning_pipeline import (
    BaseReasoningModule,
    ReasoningContext,
    ReasoningPipeline,
)
from iios.investment.decision.reasoning.reasoning_step import ReasoningStep, make_step
from iios.investment.decision.reasoning.reasoning_trace import ReasoningTrace


# ========================= LogicValidator ================================

class TestLogicValidator:
    def test_valid_when_no_contradictions(self, positive_signals):
        from iios.investment.decision.reasoning.hypothesis_engine import HypothesisEngine
        from iios.investment.decision.reasoning.argument_engine import ArgumentEngine
        engine = HypothesisEngine()
        hyps, _ = engine.generate("X", "equity", positive_signals)
        ae = ArgumentEngine()
        reports, _ = ae.evaluate_all(hyps, positive_signals)
        lv = LogicValidator()
        result, step = lv.validate(hyps, reports)
        assert result.status.is_usable
        assert step.step_type == ReasoningStepType.CROSS_VALIDATION

    def test_empty_hypotheses_insufficient(self):
        lv = LogicValidator()
        result, _ = lv.validate([], [])
        assert result.status == LogicValidationStatus.INSUFFICIENT

    def test_to_dict(self, positive_signals):
        from iios.investment.decision.reasoning.hypothesis_engine import HypothesisEngine
        from iios.investment.decision.reasoning.argument_engine import ArgumentEngine
        engine = HypothesisEngine()
        hyps, _ = engine.generate("X", "equity", positive_signals)
        ae = ArgumentEngine()
        reports, _ = ae.evaluate_all(hyps, positive_signals)
        lv = LogicValidator()
        result, _ = lv.validate(hyps, reports)
        d = result.to_dict()
        assert "status" in d
        assert "is_usable" in d


# ========================= DecisionLogic =================================

class TestDecisionLogic:
    def test_extract_returns_final_conclusion(self, positive_signals):
        from iios.investment.decision.reasoning.hypothesis_engine import HypothesisEngine
        from iios.investment.decision.reasoning.argument_engine import ArgumentEngine
        from iios.investment.decision.reasoning.context_analyzer import ContextAnalyzer
        from iios.investment.decision.reasoning.signal_interpreter import SignalInterpreter
        interp = SignalInterpreter()
        labelled, _ = interp.interpret_all(positive_signals)
        analyzer = ContextAnalyzer()
        profile, _ = analyzer.analyze("INFY", "equity", labelled)
        engine = HypothesisEngine()
        hyps, _ = engine.generate("INFY", "equity", labelled)
        ae = ArgumentEngine()
        reports, _ = ae.evaluate_all(hyps, labelled)
        dl = DecisionLogic()
        primary, steps, conclusion = dl.extract("INFY", "equity", profile, hyps, reports)
        assert len(conclusion) > 0
        assert len(steps) == 2  # INTERMEDIATE_CONCLUSION + FINAL_REASONING
        assert steps[-1].step_type == ReasoningStepType.FINAL_REASONING


# ========================= ReasoningPipeline =============================

@pytest.mark.asyncio
class TestReasoningPipeline:
    async def test_execute_returns_result(self, rich_evidence_snapshot, decision_id, subject_id):
        pipeline = ReasoningPipeline()
        ctx = ReasoningContext(
            decision_id=decision_id,
            subject_id=subject_id,
            subject_type="equity",
            evidence_snapshot=rich_evidence_snapshot,
        )
        result = await pipeline.execute(ctx)
        assert result.chain is not None
        assert result.chain.step_count >= 8

    async def test_hypotheses_generated(self, rich_evidence_snapshot, decision_id, subject_id):
        pipeline = ReasoningPipeline()
        ctx = ReasoningContext(
            decision_id=decision_id,
            subject_id=subject_id,
            subject_type="equity",
            evidence_snapshot=rich_evidence_snapshot,
        )
        result = await pipeline.execute(ctx)
        assert len(result.hypotheses) >= 3

    async def test_argument_reports_generated(self, rich_evidence_snapshot, decision_id, subject_id):
        pipeline = ReasoningPipeline()
        ctx = ReasoningContext(
            decision_id=decision_id,
            subject_id=subject_id,
            subject_type="equity",
            evidence_snapshot=rich_evidence_snapshot,
        )
        result = await pipeline.execute(ctx)
        assert len(result.argument_reports) == len(result.hypotheses)

    async def test_logic_result_present(self, rich_evidence_snapshot, decision_id, subject_id):
        pipeline = ReasoningPipeline()
        ctx = ReasoningContext(
            decision_id=decision_id,
            subject_id=subject_id,
            subject_type="equity",
            evidence_snapshot=rich_evidence_snapshot,
        )
        result = await pipeline.execute(ctx)
        assert result.logic_result is not None

    async def test_extra_module_executed(self, rich_evidence_snapshot, decision_id, subject_id):
        """A pluggable extra module adds its step to the chain."""
        extra_steps = []

        class StubModule(BaseReasoningModule):
            @property
            def module_name(self): return "StubModule"
            @property
            def step_type(self): return ReasoningStepType.EVIDENCE_REVIEW
            async def execute(self, context: ReasoningContext):
                s = make_step(
                    step_type=ReasoningStepType.EVIDENCE_REVIEW,
                    description="stub extra step",
                    intermediate_conclusion="stub",
                    order=99,
                    module_name="StubModule",
                )
                extra_steps.append(s)
                return [s]

        pipeline = ReasoningPipeline(extra_modules=[StubModule()])
        ctx = ReasoningContext(
            decision_id=decision_id,
            subject_id=subject_id,
            subject_type="equity",
            evidence_snapshot=rich_evidence_snapshot,
        )
        result = await pipeline.execute(ctx)
        # stub module ran
        assert len(extra_steps) == 1
        module_names = {s.module_name for s in result.chain.steps}
        assert "StubModule" in module_names

    async def test_empty_evidence_snapshot(self, minimal_evidence_snapshot, decision_id, subject_id):
        pipeline = ReasoningPipeline()
        ctx = ReasoningContext(
            decision_id=decision_id,
            subject_id=subject_id,
            subject_type="equity",
            evidence_snapshot=minimal_evidence_snapshot,
        )
        result = await pipeline.execute(ctx)
        assert result.chain is not None


# ========================= ReasoningTrace ================================

class TestReasoningTrace:
    def _build_trace(self, decision_id, subject_id, rich_evidence_snapshot):
        import asyncio
        pipeline = ReasoningPipeline()
        ctx = ReasoningContext(
            decision_id=decision_id,
            subject_id=subject_id,
            subject_type="equity",
            evidence_snapshot=rich_evidence_snapshot,
        )
        result = asyncio.run(pipeline.execute(ctx))
        return ReasoningTrace(result.chain)

    def test_entries_match_steps(self, decision_id, subject_id, rich_evidence_snapshot):
        trace = self._build_trace(decision_id, subject_id, rich_evidence_snapshot)
        assert trace.depth() == len(trace.entries())

    def test_entries_by_step_type(self, decision_id, subject_id, rich_evidence_snapshot):
        trace = self._build_trace(decision_id, subject_id, rich_evidence_snapshot)
        ev_entries = trace.entries_for_step_type(ReasoningStepType.EVIDENCE_REVIEW)
        assert len(ev_entries) >= 1

    def test_all_trace_ids(self, decision_id, subject_id, rich_evidence_snapshot):
        trace = self._build_trace(decision_id, subject_id, rich_evidence_snapshot)
        assert len(trace.all_trace_ids()) > 0

    def test_avg_confidence(self, decision_id, subject_id, rich_evidence_snapshot):
        trace = self._build_trace(decision_id, subject_id, rich_evidence_snapshot)
        assert 0.0 <= trace.avg_confidence() <= 100.0

    def test_to_dict_structure(self, decision_id, subject_id, rich_evidence_snapshot):
        trace = self._build_trace(decision_id, subject_id, rich_evidence_snapshot)
        d = trace.to_dict()
        assert "chain_id" in d
        assert "entries" in d
        assert "final_conclusion" in d
