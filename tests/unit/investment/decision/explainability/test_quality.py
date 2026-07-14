"""tests/unit/investment/decision/explainability/test_quality.py
Tests for TransparencyScorer, TraceabilityScorer,
ExplainabilityQualityEvaluator, ExplainabilityHealthMonitor.
"""
from __future__ import annotations

import pytest

from iios.investment.decision.explainability.explainability_constants import (
    DecisionOutcome,
    ExplainabilityStatus,
)
from iios.investment.decision.explainability.explainability_health import (
    ExplainabilityHealthMonitor,
    ExplainabilityHealthReport,
)
from iios.investment.decision.explainability.explainability_quality import (
    ExplainabilityQualityEvaluator,
)
from iios.investment.decision.explainability.explanation_generator import ExplanationGenerator
from iios.investment.decision.explainability.traceability_engine import TraceabilityEngine
from iios.investment.decision.explainability.traceability_score import TraceabilityScorer
from iios.investment.decision.explainability.transparency_score import TransparencyScorer


# ─── TransparencyScorer ──────────────────────────────────────────────────────

class TestTransparencyScorer:
    def _build(self, rich_input, decision_id):
        gen   = ExplanationGenerator()
        snap  = gen.generate(rich_input, decision_id)
        te    = TraceabilityEngine()
        trace = te.build_trace(
            rich_input.evidence_snapshot,
            rich_input.reasoning_snapshot,
            rich_input.confidence_snapshot,
            rich_input.risk_snapshot,
            outcome=snap.outcome.value,
        )
        return snap.explanation, trace

    def test_score_in_range(self, rich_input, decision_id):
        exp, trace = self._build(rich_input, decision_id)
        ts    = TransparencyScorer()
        score = ts.score(exp, trace)
        assert 0.0 <= score <= 100.0

    def test_rich_input_above_minimal(self, rich_input, decision_id, minimal_input):
        exp_rich, trace_rich = self._build(rich_input, decision_id)
        import uuid
        d2 = str(uuid.uuid4())
        gen  = ExplanationGenerator()
        snap = gen.generate(minimal_input, d2)
        te   = TraceabilityEngine()
        trace_min = te.build_trace(
            minimal_input.evidence_snapshot,
            minimal_input.reasoning_snapshot,
            minimal_input.confidence_snapshot,
            minimal_input.risk_snapshot,
            outcome=snap.outcome.value,
        )
        ts = TransparencyScorer()
        score_rich = ts.score(exp_rich, trace_rich)
        score_min  = ts.score(snap.explanation, trace_min)
        assert score_rich >= score_min

    def test_score_is_float(self, rich_input, decision_id):
        exp, trace = self._build(rich_input, decision_id)
        ts = TransparencyScorer()
        assert isinstance(ts.score(exp, trace), float)


# ─── TraceabilityScorer ──────────────────────────────────────────────────────

class TestTraceabilityScorer:
    def _trace(self, inp, decision_id):
        gen   = ExplanationGenerator()
        snap  = gen.generate(inp, decision_id)
        te    = TraceabilityEngine()
        return te.build_trace(
            inp.evidence_snapshot, inp.reasoning_snapshot,
            inp.confidence_snapshot, inp.risk_snapshot,
            outcome=snap.outcome.value,
        )

    def test_score_in_range(self, rich_input, decision_id):
        trace = self._trace(rich_input, decision_id)
        ts    = TraceabilityScorer()
        score = ts.score(trace)
        assert 0.0 <= score <= 100.0

    def test_rich_higher_than_minimal(self, rich_input, decision_id, minimal_input):
        import uuid
        trace_rich = self._trace(rich_input, decision_id)
        trace_min  = self._trace(minimal_input, str(uuid.uuid4()))
        ts = TraceabilityScorer()
        assert ts.score(trace_rich) >= ts.score(trace_min)

    def test_score_is_float(self, rich_input, decision_id):
        trace = self._trace(rich_input, decision_id)
        ts    = TraceabilityScorer()
        assert isinstance(ts.score(trace), float)


# ─── ExplainabilityQualityEvaluator ─────────────────────────────────────────

class TestExplainabilityQualityEvaluator:
    def _build(self, inp, decision_id):
        gen   = ExplanationGenerator()
        snap  = gen.generate(inp, decision_id)
        te    = TraceabilityEngine()
        trace = te.build_trace(
            inp.evidence_snapshot, inp.reasoning_snapshot,
            inp.confidence_snapshot, inp.risk_snapshot,
            outcome=snap.outcome.value,
        )
        ts    = TransparencyScorer()
        tscore = ts.score(snap.explanation, trace)
        return snap.explanation, trace, tscore

    def test_score_in_range(self, rich_input, decision_id):
        exp, trace, tscore = self._build(rich_input, decision_id)
        evaluator = ExplainabilityQualityEvaluator()
        q = evaluator.evaluate(exp, trace, tscore)
        assert 0.0 <= q <= 100.0

    def test_returns_float(self, rich_input, decision_id):
        exp, trace, tscore = self._build(rich_input, decision_id)
        evaluator = ExplainabilityQualityEvaluator()
        assert isinstance(evaluator.evaluate(exp, trace, tscore), float)

    def test_zero_transparency_lowers_score(self, rich_input, decision_id):
        exp, trace, tscore = self._build(rich_input, decision_id)
        evaluator = ExplainabilityQualityEvaluator()
        high = evaluator.evaluate(exp, trace, tscore)
        low  = evaluator.evaluate(exp, trace, 0.0)
        assert high >= low


# ─── ExplainabilityHealthMonitor ────────────────────────────────────────────

class TestExplainabilityHealthMonitor:
    def test_initial_report(self):
        m = ExplainabilityHealthMonitor()
        r = m.report()
        assert isinstance(r, ExplainabilityHealthReport)
        assert r.total_generations == 0
        assert r.consecutive_failures == 0

    def test_record_success(self):
        m = ExplainabilityHealthMonitor()
        m.set_status(ExplainabilityStatus.READY)
        m.record_success(100.0)
        r = m.report()
        assert r.successful == 1
        assert r.consecutive_failures == 0

    def test_record_failure_increments(self):
        m = ExplainabilityHealthMonitor()
        m.record_failure()
        r = m.report()
        assert r.failed == 1
        assert r.consecutive_failures == 1

    def test_success_resets_consecutive(self):
        m = ExplainabilityHealthMonitor()
        m.record_failure()
        m.record_failure()
        m.record_success(50.0)
        r = m.report()
        assert r.consecutive_failures == 0

    def test_5_failures_degrade(self):
        m = ExplainabilityHealthMonitor()
        for _ in range(5):
            m.record_failure()
        r = m.report()
        assert r.status == ExplainabilityStatus.DEGRADED

    def test_is_healthy_when_ready(self):
        m = ExplainabilityHealthMonitor()
        m.set_status(ExplainabilityStatus.READY)
        r = m.report()
        assert r.is_healthy

    def test_is_not_healthy_when_stopped(self):
        m = ExplainabilityHealthMonitor()
        m.set_status(ExplainabilityStatus.STOPPED)
        r = m.report()
        assert not r.is_healthy

    def test_reset(self):
        m = ExplainabilityHealthMonitor()
        m.record_success(100.0)
        m.reset()
        r = m.report()
        assert r.total_generations == 0

    def test_avg_duration(self):
        m = ExplainabilityHealthMonitor()
        m.set_status(ExplainabilityStatus.READY)
        m.record_success(100.0)
        m.record_success(200.0)
        r = m.report()
        assert r.avg_duration_ms == pytest.approx(150.0, abs=1.0)

    def test_to_dict(self):
        m = ExplainabilityHealthMonitor()
        r = m.report()
        d = r.to_dict()
        assert "status" in d
        assert "is_healthy" in d
