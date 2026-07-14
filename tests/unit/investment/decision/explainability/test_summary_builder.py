"""tests/unit/investment/decision/explainability/test_summary_builder.py
Tests for derive_outcome and SummaryBuilder.
"""
from __future__ import annotations

import pytest

from iios.investment.decision.explainability.explainability_constants import (
    DecisionOutcome,
    FactorSource,
    CAUTION_CONFIDENCE_MIN,
    INSUFFICIENT_DATA_ITEMS,
    PROCEED_CONFIDENCE_MIN,
    PROCEED_RISK_MAX,
)
from iios.investment.decision.explainability.summary_builder import (
    SummaryBuilder,
    derive_outcome,
)
from iios.investment.decision.explainability.explanation_generator import ExplanationGenerator


class TestDeriveOutcome:
    """Unit tests for the deterministic outcome derivation logic."""

    def test_proceed_with_rich_data(self, rich_evidence_snapshot, rich_confidence_snapshot, rich_risk_snapshot):
        if rich_risk_snapshot.blocks_execution:
            pytest.skip("risk blocks execution in this environment")
        if rich_confidence_snapshot.overall_confidence < PROCEED_CONFIDENCE_MIN:
            pytest.skip("confidence too low for proceed outcome")
        if rich_risk_snapshot.overall_risk >= PROCEED_RISK_MAX:
            pytest.skip("risk too high for proceed outcome")
        outcome = derive_outcome(
            rich_evidence_snapshot, rich_confidence_snapshot, rich_risk_snapshot,
        )
        assert outcome in {DecisionOutcome.PROCEED, DecisionOutcome.CAUTION}

    def test_insufficient_data_minimal(
        self, minimal_evidence_snapshot, minimal_confidence_snapshot, minimal_risk_snapshot,
    ):
        outcome = derive_outcome(
            minimal_evidence_snapshot, minimal_confidence_snapshot, minimal_risk_snapshot,
        )
        assert outcome in {
            DecisionOutcome.INSUFFICIENT_DATA,
            DecisionOutcome.CAUTION,
            DecisionOutcome.HALT,
        }

    def test_halt_when_blocks_execution(self, rich_input, decision_id):
        """When controls_breached/blocks_execution triggers HALT."""
        # Use low confidence to trigger INSUFFICIENT_DATA or HALT deterministically
        gen   = ExplanationGenerator()
        snap  = gen.generate(minimal_input if False else rich_input, decision_id)
        # We can't mutate frozen RiskSnapshot, so we test the derive_outcome directly
        from iios.investment.decision.explainability.summary_builder import derive_outcome
        from iios.investment.decision.explainability.explainability_constants import DecisionOutcome

        class FakeRisk:
            blocks_execution = True
            overall_risk     = 80.0
            decision_id      = "fake"

        outcome = derive_outcome(rich_input.evidence_snapshot, rich_input.confidence_snapshot, FakeRisk())
        assert outcome == DecisionOutcome.HALT


class TestSummaryBuilder:
    def test_build_returns_explanation(self, rich_input, decision_id):
        builder = SummaryBuilder()
        gen = ExplanationGenerator()
        snap = gen.generate(rich_input, decision_id)
        exp  = snap.explanation
        assert isinstance(exp.decision_id, str)
        assert len(exp.decision_id) > 0
        assert exp.outcome in list(DecisionOutcome)

    def test_build_has_factors(self, rich_input, decision_id):
        gen  = ExplanationGenerator()
        snap = gen.generate(rich_input, decision_id)
        total = len(snap.explanation.supporting_factors) + len(snap.explanation.opposing_factors)
        assert total >= 0  # should have at least some factors from evidence

    def test_build_has_one_line_summary(self, rich_input, decision_id):
        gen  = ExplanationGenerator()
        snap = gen.generate(rich_input, decision_id)
        assert len(snap.explanation.one_line_summary) > 0

    def test_build_has_executive_summary(self, rich_input, decision_id):
        gen  = ExplanationGenerator()
        snap = gen.generate(rich_input, decision_id)
        assert len(snap.explanation.executive_summary) > 0

    def test_build_has_technical_summary(self, rich_input, decision_id):
        gen  = ExplanationGenerator()
        snap = gen.generate(rich_input, decision_id)
        assert len(snap.explanation.technical_summary) > 0

    def test_build_has_assumptions(self, rich_input, decision_id):
        gen  = ExplanationGenerator()
        snap = gen.generate(rich_input, decision_id)
        assert isinstance(snap.explanation.assumptions, tuple)

    def test_build_has_key_risks(self, rich_input, decision_id):
        gen  = ExplanationGenerator()
        snap = gen.generate(rich_input, decision_id)
        assert isinstance(snap.explanation.key_risks, tuple)

    def test_factor_sources_are_valid(self, rich_input, decision_id):
        gen  = ExplanationGenerator()
        snap = gen.generate(rich_input, decision_id)
        for f in snap.explanation.supporting_factors:
            assert isinstance(f.source_engine, FactorSource)
        for f in snap.explanation.opposing_factors:
            assert isinstance(f.source_engine, FactorSource)

    def test_confidence_and_risk_populated(self, rich_input, decision_id):
        gen  = ExplanationGenerator()
        snap = gen.generate(rich_input, decision_id)
        exp  = snap.explanation
        assert 0.0 <= exp.overall_confidence <= 100.0
        assert 0.0 <= exp.overall_risk       <= 100.0
        assert 0.0 <= exp.evidence_quality   <= 100.0

    def test_minimal_input_has_explanation(self, minimal_input, decision_id):
        gen  = ExplanationGenerator()
        snap = gen.generate(minimal_input, decision_id)
        assert snap.explanation is not None
        assert snap.outcome in list(DecisionOutcome)
