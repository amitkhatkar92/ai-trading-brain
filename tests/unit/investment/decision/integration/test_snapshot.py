"""tests/unit/investment/decision/integration/test_snapshot.py
Tests for DecisionIntelligenceSnapshot, DecisionSummaryBuilder, DecisionState.
"""
from __future__ import annotations

import pytest

from iios.investment.decision.integration.decision_intelligence_integration_engine import (
    DecisionIntelligenceIntegrationEngine,
)
from iios.investment.decision.integration.integration_constants import (
    QualityGrade,
    SnapshotStatus,
    ValidationStatus,
)
from iios.investment.decision.integration.decision_state import build_decision_state
from iios.investment.decision.integration.decision_summary import DecisionSummaryBuilder
from iios.investment.decision.integration.aggregation_engine import AggregationEngine
from iios.investment.decision.integration.integration_constants import ComponentId


def _run(pipeline):
    did, sid, ev, rs, cs, ri, ex, cm = pipeline
    eng = DecisionIntelligenceIntegrationEngine()
    eng.start()
    snap = eng.integrate_sync(
        decision_id=did + "_DEC", subject_id=sid, subject_type="equity",
        evidence=ev, reasoning=rs, confidence=cs, risk=ri,
        explanation=ex, committee=cm,
    )
    eng.stop()
    return snap


class TestDecisionIntelligenceSnapshot:
    def test_snapshot_not_none(self, _rich_pipeline):
        snap = _run(_rich_pipeline)
        assert snap is not None

    def test_snapshot_id_non_empty(self, _rich_pipeline):
        snap = _run(_rich_pipeline)
        assert len(snap.snapshot_id) > 0

    def test_decision_id_correct(self, _rich_pipeline):
        did, sid, *_ = _rich_pipeline
        snap = _run(_rich_pipeline)
        assert snap.decision_id == did + "_DEC"

    def test_subject_id_correct(self, _rich_pipeline):
        did, sid, *_ = _rich_pipeline
        snap = _run(_rich_pipeline)
        assert snap.subject_id == sid

    def test_snapshot_status_complete(self, _rich_pipeline):
        snap = _run(_rich_pipeline)
        assert snap.snapshot_status == SnapshotStatus.COMPLETE

    def test_completeness_one(self, _rich_pipeline):
        snap = _run(_rich_pipeline)
        assert snap.completeness == pytest.approx(1.0)

    def test_quality_grade_valid(self, _rich_pipeline):
        snap = _run(_rich_pipeline)
        assert snap.quality_grade in list(QualityGrade)

    def test_quality_score_in_range(self, _rich_pipeline):
        snap = _run(_rich_pipeline)
        assert 0.0 <= snap.quality_score <= 100.0

    def test_intelligence_score_in_range(self, _rich_pipeline):
        snap = _run(_rich_pipeline)
        assert 0.0 <= snap.overall_intelligence_score <= 100.0

    def test_overall_confidence_in_range(self, _rich_pipeline):
        snap = _run(_rich_pipeline)
        assert 0.0 <= snap.overall_confidence <= 100.0

    def test_summaries_present(self, _rich_pipeline):
        snap = _run(_rich_pipeline)
        assert snap.evidence_summary     is not None
        assert snap.reasoning_summary    is not None
        assert snap.confidence_summary   is not None
        assert snap.risk_summary         is not None
        assert snap.explanation_summary  is not None
        assert snap.committee_summary    is not None

    def test_is_publishable_boolean(self, _rich_pipeline):
        snap = _run(_rich_pipeline)
        assert isinstance(snap.is_publishable, bool)

    def test_to_dict_required_keys(self, _rich_pipeline):
        snap = _run(_rich_pipeline)
        d    = snap.to_dict()
        for key in ("snapshot_id", "decision_id", "subject_id", "snapshot_status",
                    "quality_score", "completeness", "evidence", "reasoning",
                    "confidence", "risk", "explanation", "committee"):
            assert key in d, f"Missing key: {key}"

    def test_frozen(self, _rich_pipeline):
        snap = _run(_rich_pipeline)
        with pytest.raises((AttributeError, TypeError)):
            snap.quality_score = 999.0  # type: ignore

    def test_created_at_present(self, _rich_pipeline):
        snap = _run(_rich_pipeline)
        assert snap.created_at is not None


class TestDecisionSummaryBuilder:
    def _snap(self, pipeline):
        did, sid, ev, rs, cs, ri, ex, cm = pipeline
        eng   = AggregationEngine()
        state = eng.create(
            decision_id=did+"_DEC", subject_id=sid, subject_type="equity",
            evidence=ev, reasoning=rs, confidence=cs, risk=ri,
            explanation=ex, committee=cm,
        )
        return state.snapshot()

    def test_evidence_summary(self, _rich_pipeline):
        snap = self._snap(_rich_pipeline)
        bld  = DecisionSummaryBuilder()
        s    = bld.evidence(snap)
        assert s is not None
        assert s.quality_score >= 0.0
        assert 0.0 <= s.coverage_fraction <= 1.0

    def test_reasoning_summary(self, _rich_pipeline):
        snap = self._snap(_rich_pipeline)
        bld  = DecisionSummaryBuilder()
        s    = bld.reasoning(snap)
        assert s is not None
        assert s.hypothesis_count >= 0

    def test_confidence_summary(self, _rich_pipeline):
        snap = self._snap(_rich_pipeline)
        bld  = DecisionSummaryBuilder()
        s    = bld.confidence(snap)
        assert s is not None
        assert 0.0 <= s.overall_confidence <= 100.0

    def test_risk_summary(self, _rich_pipeline):
        snap = self._snap(_rich_pipeline)
        bld  = DecisionSummaryBuilder()
        s    = bld.risk(snap)
        assert s is not None
        assert 0.0 <= s.overall_risk <= 100.0

    def test_explanation_summary(self, _rich_pipeline):
        snap = self._snap(_rich_pipeline)
        bld  = DecisionSummaryBuilder()
        s    = bld.explanation(snap)
        assert s is not None
        assert 0.0 <= s.explainability_score <= 100.0

    def test_committee_summary(self, _rich_pipeline):
        snap = self._snap(_rich_pipeline)
        bld  = DecisionSummaryBuilder()
        s    = bld.committee(snap)
        assert s is not None
        assert len(s.position) > 0

    def test_recommendation_summary_none_when_absent(self, _rich_pipeline):
        snap = self._snap(_rich_pipeline)
        # No recommendation in rich pipeline
        bld  = DecisionSummaryBuilder()
        s    = bld.recommendation(snap)
        assert s is None  # no recommendation submitted


class TestDecisionState:
    def test_build_complete(self):
        s = build_decision_state(
            "D1", "INFY", "equity",
            completeness      = 1.0,
            present           = ComponentId.required(),
            blocks_publishing = False,
            is_valid          = True,
            version           = 1,
        )
        assert s.snapshot_status == SnapshotStatus.COMPLETE
        assert s.is_publishable

    def test_build_partial(self):
        s = build_decision_state(
            "D1", "INFY", "equity",
            completeness      = 0.5,
            present           = frozenset({ComponentId.EVIDENCE, ComponentId.REASONING}),
            blocks_publishing = False,
            is_valid          = True,
            version           = 1,
        )
        assert s.snapshot_status == SnapshotStatus.PARTIAL

    def test_not_publishable_when_blocked(self):
        s = build_decision_state(
            "D1", "INFY", "equity",
            completeness      = 1.0,
            present           = ComponentId.required(),
            blocks_publishing = True,
            is_valid          = True,
            version           = 1,
        )
        assert not s.is_publishable

    def test_to_dict(self):
        s = build_decision_state(
            "D1", "INFY", "equity", 0.8,
            frozenset({ComponentId.EVIDENCE}), False, True, 1,
        )
        d = s.to_dict()
        assert "snapshot_status"   in d
        assert "is_publishable"    in d
