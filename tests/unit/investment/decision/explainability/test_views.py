"""tests/unit/investment/decision/explainability/test_views.py
Tests for ExecutiveView, AnalystView, DeveloperView, AuditView.
"""
from __future__ import annotations

import pytest

from iios.investment.decision.explainability.analyst_view import AnalystView, build_analyst_view
from iios.investment.decision.explainability.audit_view import AuditView, build_audit_view
from iios.investment.decision.explainability.developer_view import DeveloperView, build_developer_view
from iios.investment.decision.explainability.executive_view import ExecutiveView, build_executive_view
from iios.investment.decision.explainability.explanation_generator import ExplanationGenerator
from iios.investment.decision.explainability.traceability_engine import TraceabilityEngine


class TestExecutiveView:
    def _view(self, rich_input, decision_id) -> ExecutiveView:
        gen  = ExplanationGenerator()
        snap = gen.generate(rich_input, decision_id)
        return build_executive_view(snap)

    def test_returns_view(self, rich_input, decision_id):
        v = self._view(rich_input, decision_id)
        assert isinstance(v, ExecutiveView)

    def test_decision_id(self, rich_input, decision_id):
        v = self._view(rich_input, decision_id)
        assert v.decision_id == decision_id

    def test_summary_non_empty(self, rich_input, decision_id):
        v = self._view(rich_input, decision_id)
        # one_line_summary is the executive summary field
        assert len(v.one_line_summary) > 0

    def test_to_dict(self, rich_input, decision_id):
        v = self._view(rich_input, decision_id)
        d = v.to_dict()
        assert "decision_id" in d
        assert "one_line_summary" in d

    def test_frozen(self, rich_input, decision_id):
        v = self._view(rich_input, decision_id)
        with pytest.raises((AttributeError, TypeError)):
            v.summary = "mutated"  # type: ignore


class TestAnalystView:
    def _view(self, rich_input, decision_id) -> AnalystView:
        gen  = ExplanationGenerator()
        snap = gen.generate(rich_input, decision_id)
        return build_analyst_view(snap)

    def test_returns_view(self, rich_input, decision_id):
        v = self._view(rich_input, decision_id)
        assert isinstance(v, AnalystView)

    def test_decision_id(self, rich_input, decision_id):
        v = self._view(rich_input, decision_id)
        assert v.decision_id == decision_id

    def test_to_dict(self, rich_input, decision_id):
        v = self._view(rich_input, decision_id)
        d = v.to_dict()
        assert isinstance(d, dict)
        assert "decision_id" in d

    def test_frozen(self, rich_input, decision_id):
        v = self._view(rich_input, decision_id)
        with pytest.raises((AttributeError, TypeError)):
            v.decision_id = "X"  # type: ignore


class TestDeveloperView:
    def _view(self, rich_input, decision_id) -> DeveloperView:
        gen  = ExplanationGenerator()
        snap = gen.generate(rich_input, decision_id)
        return build_developer_view(snap)

    def test_returns_view(self, rich_input, decision_id):
        v = self._view(rich_input, decision_id)
        assert isinstance(v, DeveloperView)

    def test_decision_id(self, rich_input, decision_id):
        v = self._view(rich_input, decision_id)
        assert v.decision_id == decision_id

    def test_generation_duration_non_negative(self, rich_input, decision_id):
        v = self._view(rich_input, decision_id)
        assert v.generation_duration_ms >= 0

    def test_to_dict(self, rich_input, decision_id):
        v = self._view(rich_input, decision_id)
        d = v.to_dict()
        assert isinstance(d, dict)
        assert "decision_id" in d

    def test_frozen(self, rich_input, decision_id):
        v = self._view(rich_input, decision_id)
        with pytest.raises((AttributeError, TypeError)):
            v.decision_id = "X"  # type: ignore


class TestAuditView:
    def _view(self, rich_input, decision_id, rich_evidence_snapshot,
              rich_reasoning_snapshot, rich_confidence_snapshot, rich_risk_snapshot) -> AuditView:
        gen  = ExplanationGenerator()
        snap = gen.generate(rich_input, decision_id)
        engine = TraceabilityEngine()
        trace  = engine.build_trace(
            rich_evidence_snapshot,
            rich_reasoning_snapshot,
            rich_confidence_snapshot,
            rich_risk_snapshot,
            outcome=snap.outcome.value,
        )
        return build_audit_view(snap, trace, "compliant")

    def test_returns_view(
        self, rich_input, decision_id,
        rich_evidence_snapshot, rich_reasoning_snapshot,
        rich_confidence_snapshot, rich_risk_snapshot,
    ):
        v = self._view(
            rich_input, decision_id,
            rich_evidence_snapshot, rich_reasoning_snapshot,
            rich_confidence_snapshot, rich_risk_snapshot,
        )
        assert isinstance(v, AuditView)

    def test_decision_id(
        self, rich_input, decision_id,
        rich_evidence_snapshot, rich_reasoning_snapshot,
        rich_confidence_snapshot, rich_risk_snapshot,
    ):
        v = self._view(
            rich_input, decision_id,
            rich_evidence_snapshot, rich_reasoning_snapshot,
            rich_confidence_snapshot, rich_risk_snapshot,
        )
        assert v.decision_id == decision_id

    def test_policy_compliance_field(
        self, rich_input, decision_id,
        rich_evidence_snapshot, rich_reasoning_snapshot,
        rich_confidence_snapshot, rich_risk_snapshot,
    ):
        v = self._view(
            rich_input, decision_id,
            rich_evidence_snapshot, rich_reasoning_snapshot,
            rich_confidence_snapshot, rich_risk_snapshot,
        )
        assert v.policy_compliance == "compliant"

    def test_to_dict(
        self, rich_input, decision_id,
        rich_evidence_snapshot, rich_reasoning_snapshot,
        rich_confidence_snapshot, rich_risk_snapshot,
    ):
        v = self._view(
            rich_input, decision_id,
            rich_evidence_snapshot, rich_reasoning_snapshot,
            rich_confidence_snapshot, rich_risk_snapshot,
        )
        d = v.to_dict()
        assert isinstance(d, dict)
        assert "decision_id" in d

    def test_frozen(
        self, rich_input, decision_id,
        rich_evidence_snapshot, rich_reasoning_snapshot,
        rich_confidence_snapshot, rich_risk_snapshot,
    ):
        v = self._view(
            rich_input, decision_id,
            rich_evidence_snapshot, rich_reasoning_snapshot,
            rich_confidence_snapshot, rich_risk_snapshot,
        )
        with pytest.raises((AttributeError, TypeError)):
            v.decision_id = "X"  # type: ignore
