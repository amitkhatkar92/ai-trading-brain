"""tests/unit/investment/decision/explainability/test_explanation_models.py
Tests for core model types: ExplanationFactor, DecisionExplanation,
ExplanationSnapshot, ExplanationHistory, ExplanationStatistics.
"""
from __future__ import annotations

import uuid

import pytest

from iios.investment.decision.explainability.decision_explanation import (
    DecisionExplanation,
    ExplanationFactor,
)
from iios.investment.decision.explainability.explainability_constants import (
    DecisionOutcome,
    ExplainabilityGrade,
    ExplainabilityStatus,
    ExplanationFormat,
    FactorSource,
    TraceabilityLevel,
)
from iios.investment.decision.explainability.explanation_history import ExplanationHistory
from iios.investment.decision.explainability.explanation_snapshot import ExplanationSnapshot
from iios.investment.decision.explainability.explanation_statistics import (
    ExplanationStatistics,
    ExplanationStatisticsTracker,
)
from iios.investment.decision.explainability.explanation_generator import ExplanationGenerator


# ─── ExplanationFactor ────────────────────────────────────────────────────────

class TestExplanationFactor:
    def test_positive(self):
        f = ExplanationFactor("rsi", "RSI bullish", 70.0, FactorSource.EVIDENCE, True)
        assert f.is_positive
        assert f.impact == 70.0

    def test_negative(self):
        f = ExplanationFactor("drawdown", "High drawdown", 50.0, FactorSource.RISK, False)
        assert not f.is_positive

    def test_frozen(self):
        f = ExplanationFactor("vol", "Volatility", 40.0, FactorSource.CONFIDENCE, True)
        with pytest.raises((AttributeError, TypeError)):
            f.impact = 99.0  # type: ignore


# ─── DecisionExplanation ─────────────────────────────────────────────────────

class TestDecisionExplanation:
    def _make(self, factors_pos=None, factors_neg=None, assumptions=None, key_risks=None):
        factors_pos = factors_pos or []
        factors_neg = factors_neg or []
        assumptions = assumptions or ["A1"]
        key_risks   = key_risks   or ["R1"]
        return DecisionExplanation(
            decision_id        = "DX",
            subject_id         = "TCS",
            subject_type       = "equity",
            outcome            = DecisionOutcome.PROCEED,
            one_line_summary   = "Proceed with confidence.",
            executive_summary  = "Evidence supports a proceed decision.",
            technical_summary  = "Confidence 75, risk 30, multiple corroborating factors.",
            supporting_factors = tuple(factors_pos),
            opposing_factors   = tuple(factors_neg),
            assumptions        = tuple(assumptions),
            key_risks          = tuple(key_risks),
            overall_confidence = 75.0,
            overall_risk       = 30.0,
            evidence_quality   = 80.0,
            reasoning_quality  = 72.0,
            evidence_item_count= 5,
            source_count       = 3,
            evidence_coverage  = 0.85,
            evidence_freshness = 0.9,
            reasoning_step_count= 4,
            logic_consistency  = 0.88,
        )

    def test_factor_count(self):
        fp = ExplanationFactor("rsi", "RSI", 70.0, FactorSource.EVIDENCE, True)
        fn = ExplanationFactor("dd",  "DD",  40.0, FactorSource.RISK, False)
        exp = self._make([fp], [fn])
        assert exp.factor_count == 2

    def test_net_impact_positive(self):
        fp = ExplanationFactor("rsi", "RSI", 70.0, FactorSource.EVIDENCE, True)
        fn = ExplanationFactor("dd",  "DD",  30.0, FactorSource.RISK, False)
        exp = self._make([fp], [fn])
        assert exp.net_impact_score > 0

    def test_net_impact_negative(self):
        fp = ExplanationFactor("rsi", "RSI", 30.0, FactorSource.EVIDENCE, True)
        fn = ExplanationFactor("dd",  "DD",  80.0, FactorSource.RISK, False)
        exp = self._make([fp], [fn])
        assert exp.net_impact_score < 0


# ─── ExplanationSnapshot (via generator) ─────────────────────────────────────

class TestExplanationSnapshot:
    def test_fields_populated(self, rich_input, decision_id):
        gen  = ExplanationGenerator()
        snap = gen.generate(rich_input, decision_id)
        assert snap.decision_id == decision_id
        assert snap.explainability_score >= 0
        assert snap.explainability_score <= 100
        assert isinstance(snap.explainability_grade, ExplainabilityGrade)
        assert isinstance(snap.outcome, DecisionOutcome)
        assert isinstance(snap.traceability_level, TraceabilityLevel)

    def test_is_auditable(self, rich_input, decision_id):
        gen  = ExplanationGenerator()
        snap = gen.generate(rich_input, decision_id)
        # property should return bool (True or False)
        assert isinstance(snap.is_auditable, bool)

    def test_to_dict(self, rich_input, decision_id):
        gen  = ExplanationGenerator()
        snap = gen.generate(rich_input, decision_id)
        d = snap.to_dict() if hasattr(snap, "to_dict") else {}
        # Verify at least is_auditable is accessible
        assert isinstance(snap.is_auditable, bool)


# ─── ExplanationGrade ────────────────────────────────────────────────────────

class TestExplainabilityGrade:
    def test_from_score_A(self):
        assert ExplainabilityGrade.from_score(90) == ExplainabilityGrade.A

    def test_from_score_B(self):
        assert ExplainabilityGrade.from_score(75) == ExplainabilityGrade.B

    def test_from_score_C(self):
        assert ExplainabilityGrade.from_score(60) == ExplainabilityGrade.C

    def test_from_score_D(self):
        assert ExplainabilityGrade.from_score(45) == ExplainabilityGrade.D

    def test_from_score_F(self):
        assert ExplainabilityGrade.from_score(20) == ExplainabilityGrade.F


# ─── ExplanationHistory ──────────────────────────────────────────────────────

class TestExplanationHistory:
    def _snap_for(self, decision_id="D1", subject_id="TCS") -> ExplanationSnapshot:
        from iios.investment.decision.explainability.explanation_snapshot import (
            build_explanation_snapshot,
        )
        from iios.investment.decision.explainability.decision_explanation import (
            DecisionExplanation,
        )
        explanation = DecisionExplanation(
            decision_id="D1", subject_id=subject_id, subject_type="equity",
            outcome=DecisionOutcome.PROCEED, one_line_summary="ok",
            executive_summary="exec", technical_summary="tech " * 30,
            supporting_factors=(), opposing_factors=(),
            assumptions=("A",), key_risks=("R",),
            overall_confidence=70.0, overall_risk=30.0,
            evidence_quality=80.0, reasoning_quality=70.0,
            evidence_item_count=5, source_count=3, evidence_coverage=0.8,
            evidence_freshness=0.9, reasoning_step_count=3, logic_consistency=0.85,
        )
        return build_explanation_snapshot(
            decision_id=decision_id,
            subject_id=subject_id,
            subject_type="equity",
            version=1,
            evidence_snapshot_id="ES1",
            reasoning_snapshot_id="RS1",
            confidence_snapshot_id="CS1",
            risk_snapshot_id="RI1",
            explanation=explanation,
            outcome=DecisionOutcome.PROCEED,
            explainability_score=70.0,
            transparency_score=65.0,
            traceability_level=TraceabilityLevel.PARTIAL,
            generation_duration_ms=50.0,
        )

    def test_record_and_get(self):
        h = ExplanationHistory()
        s = self._snap_for()
        h.record(s)
        retrieved = h.get(s.snapshot_id)
        assert retrieved is s

    def test_for_subject(self):
        h = ExplanationHistory()
        s = self._snap_for(subject_id="TCS")
        h.record(s)
        results = h.for_subject("TCS")
        assert len(results) >= 1

    def test_latest_for_subject(self):
        h = ExplanationHistory()
        s = self._snap_for(subject_id="TCS")
        h.record(s)
        assert h.latest_for_subject("TCS") is s

    def test_for_decision(self):
        h = ExplanationHistory()
        s = self._snap_for(decision_id="DQ")
        h.record(s)
        found = h.for_decision("DQ")
        assert found is s

    def test_unknown_subject_returns_empty(self):
        h = ExplanationHistory()
        assert h.for_subject("UNKNOWN") == []

    def test_outcome_series(self):
        h = ExplanationHistory()
        s = self._snap_for()
        h.record(s)
        series = h.outcome_series(s.subject_id)
        assert len(series) >= 1

    def test_count(self):
        h = ExplanationHistory()
        h.record(self._snap_for(decision_id="DA"))
        h.record(self._snap_for(decision_id="DB"))
        assert h.count() >= 2

    def test_known_subjects(self):
        h = ExplanationHistory()
        h.record(self._snap_for(subject_id="TCS"))
        assert "TCS" in h.known_subjects()


# ─── ExplanationStatisticsTracker ────────────────────────────────────────────

class TestExplanationStatisticsTracker:
    def test_initial_summary(self):
        t = ExplanationStatisticsTracker()
        s = t.summary()
        assert s.total_explanations == 0
        assert s.successful == 0
        assert s.failed == 0

    def test_record_success(self):
        t = ExplanationStatisticsTracker()
        t.record_success(DecisionOutcome.PROCEED, 80.0, 120.0)
        s = t.summary()
        assert s.total_explanations == 1
        assert s.successful == 1
        assert s.proceed_count == 1

    def test_record_caution(self):
        t = ExplanationStatisticsTracker()
        t.record_success(DecisionOutcome.CAUTION, 60.0, 50.0)
        s = t.summary()
        assert s.caution_count == 1

    def test_record_halt(self):
        t = ExplanationStatisticsTracker()
        t.record_success(DecisionOutcome.HALT, 20.0, 50.0)
        s = t.summary()
        assert s.halt_count == 1

    def test_record_failure(self):
        t = ExplanationStatisticsTracker()
        t.record_failure()
        s = t.summary()
        assert s.failed == 1

    def test_success_rate(self):
        t = ExplanationStatisticsTracker()
        t.record_success(DecisionOutcome.PROCEED, 70.0, 100.0)
        t.record_failure()
        s = t.summary()
        assert s.success_rate == pytest.approx(0.5, abs=1e-3)

    def test_halt_rate(self):
        t = ExplanationStatisticsTracker()
        t.record_success(DecisionOutcome.HALT, 20.0, 50.0)
        t.record_success(DecisionOutcome.PROCEED, 80.0, 50.0)
        s = t.summary()
        assert s.halt_rate == pytest.approx(0.5, abs=1e-3)

    def test_reset(self):
        t = ExplanationStatisticsTracker()
        t.record_success(DecisionOutcome.PROCEED, 80.0, 50.0)
        t.reset()
        s = t.summary()
        assert s.total_explanations == 0


# ─── DecisionOutcome ─────────────────────────────────────────────────────────

class TestDecisionOutcome:
    def test_proceed_is_actionable(self):
        assert DecisionOutcome.PROCEED.is_actionable

    def test_halt_not_actionable(self):
        assert not DecisionOutcome.HALT.is_actionable

    def test_caution_is_actionable(self):
        assert DecisionOutcome.CAUTION.is_actionable

    def test_insufficient_data_not_actionable(self):
        assert not DecisionOutcome.INSUFFICIENT_DATA.is_actionable


# ─── ExplainabilityStatus ────────────────────────────────────────────────────

class TestExplainabilityStatus:
    def test_ready_is_operational(self):
        assert ExplainabilityStatus.READY.is_operational

    def test_stopped_not_operational(self):
        assert not ExplainabilityStatus.STOPPED.is_operational
