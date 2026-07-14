"""tests/unit/investment/decision/integration/test_aggregation.py
Tests for AggregationEngine, AggregationState, AggregationHistory,
and DecisionIntelligenceAggregator.
"""
from __future__ import annotations

import uuid
import pytest

from iios.investment.decision.integration.aggregation_engine import AggregationEngine
from iios.investment.decision.integration.aggregation_history import AggregationHistory
from iios.investment.decision.integration.aggregation_state import AggregationState
from iios.investment.decision.integration.decision_intelligence_aggregator import (
    DecisionIntelligenceAggregator,
)
from iios.investment.decision.integration.integration_constants import (
    ComponentId,
    COMPONENT_MAX_AGE_SECONDS,
)


class TestAggregationState:
    def test_initial_completeness_zero(self):
        s = AggregationState("D1", "INFY", "equity")
        assert s.completeness == 0.0

    def test_completeness_increases_with_components(self, _rich_pipeline):
        _, _, ev, rs, cs, ri, ex, cm = _rich_pipeline
        s = AggregationState("D1", "INFY", "equity")
        assert s.completeness == 0.0
        s.update(ComponentId.EVIDENCE, ev)
        assert s.completeness > 0.0

    def test_is_complete_with_all_required(self, _rich_pipeline):
        _, _, ev, rs, cs, ri, ex, cm = _rich_pipeline
        s = AggregationState("D1", "INFY", "equity")
        for cid, val in [
            (ComponentId.EVIDENCE, ev), (ComponentId.REASONING, rs),
            (ComponentId.CONFIDENCE, cs), (ComponentId.RISK, ri),
            (ComponentId.EXPLANATION, ex), (ComponentId.COMMITTEE, cm),
        ]:
            s.update(cid, val)
        assert s.is_complete

    def test_version_increments_on_update(self, _rich_pipeline):
        _, _, ev, *_ = _rich_pipeline
        s = AggregationState("D1", "INFY", "equity")
        v0 = s.version
        s.update(ComponentId.EVIDENCE, ev)
        assert s.version == v0 + 1

    def test_snapshot_is_immutable(self, _rich_pipeline):
        _, _, ev, *_ = _rich_pipeline
        s = AggregationState("D1", "INFY", "equity")
        s.update(ComponentId.EVIDENCE, ev)
        snap = s.snapshot()
        with pytest.raises((AttributeError, TypeError)):
            snap.evidence = None  # type: ignore

    def test_to_dict_structure(self, _rich_pipeline):
        _, _, ev, *_ = _rich_pipeline
        s = AggregationState("D1", "INFY", "equity")
        s.update(ComponentId.EVIDENCE, ev)
        d = s.to_dict()
        assert "decision_id"   in d
        assert "completeness"  in d
        assert "is_complete"   in d
        assert "present_components" in d

    def test_not_stale_immediately(self):
        s = AggregationState("D1", "INFY", "equity")
        assert not s.is_stale


class TestAggregationEngine:
    def test_create_empty_state(self):
        eng = AggregationEngine()
        s = eng.create("D1", "INFY", "equity")
        assert s.completeness == 0.0

    def test_create_with_evidence(self, _rich_pipeline):
        _, _, ev, *_ = _rich_pipeline
        eng = AggregationEngine()
        s   = eng.create("D1", "INFY", "equity", evidence=ev)
        assert s.evidence is ev

    def test_apply_update_wrong_subject_raises(self, _rich_pipeline):
        _, _, ev, *_ = _rich_pipeline
        eng = AggregationEngine()
        s   = AggregationState("D1", "WRONG_SUBJECT", "equity")
        with pytest.raises(ValueError, match="Subject mismatch"):
            eng.apply_update(s, ComponentId.EVIDENCE, ev)

    def test_apply_update_correct_subject(self, _rich_pipeline):
        _, sid, ev, *_ = _rich_pipeline
        eng = AggregationEngine()
        s   = AggregationState("D1", sid, "equity")
        eng.apply_update(s, ComponentId.EVIDENCE, ev)
        assert s.evidence is ev


class TestAggregationHistory:
    def test_record_and_retrieve(self, _rich_pipeline):
        _, _, ev, *_ = _rich_pipeline
        s  = AggregationState("D1", "INFY", "equity")
        s.update(ComponentId.EVIDENCE, ev)
        snap = s.snapshot()
        h    = AggregationHistory()
        h.record(snap)
        assert h.get_by_decision("D1") is snap

    def test_recent_returns_n(self, _rich_pipeline):
        _, _, ev, *_ = _rich_pipeline
        h = AggregationHistory()
        for i in range(5):
            s = AggregationState(f"D{i}", "INFY", "equity")
            s.update(ComponentId.EVIDENCE, ev)
            h.record(s.snapshot())
        assert len(h.recent(3)) == 3

    def test_known_subjects(self, _rich_pipeline):
        _, _, ev, *_ = _rich_pipeline
        h = AggregationHistory()
        for sid in ["INFY", "TCS"]:
            s = AggregationState("D1", sid, "equity")
            s.update(ComponentId.EVIDENCE, ev)
            h.record(s.snapshot())
        subjects = h.known_subjects()
        assert "INFY" in subjects

    def test_reset(self, _rich_pipeline):
        _, _, ev, *_ = _rich_pipeline
        h = AggregationHistory()
        s = AggregationState("D1", "INFY", "equity")
        s.update(ComponentId.EVIDENCE, ev)
        h.record(s.snapshot())
        h.reset()
        assert h.count() == 0


class TestDecisionIntelligenceAggregator:
    def test_submit_evidence_creates_state(self, _rich_pipeline):
        _, _, ev, *_ = _rich_pipeline
        agg = DecisionIntelligenceAggregator()
        agg.submit_evidence(ev)
        state = agg.get_state(ev.decision_id)
        assert state is not None
        assert state.evidence is ev

    def test_submit_reasoning(self, _rich_pipeline):
        _, _, ev, rs, *_ = _rich_pipeline
        agg = DecisionIntelligenceAggregator()
        agg.submit_evidence(ev)
        agg.submit_reasoning(rs)
        state = agg.get_state(ev.decision_id)
        assert state.reasoning is rs

    def test_active_decisions(self, _rich_pipeline):
        _, _, ev, *_ = _rich_pipeline
        agg = DecisionIntelligenceAggregator()
        agg.submit_evidence(ev)
        assert ev.decision_id in agg.active_decisions()

    def test_get_snapshot(self, _rich_pipeline):
        _, _, ev, *_ = _rich_pipeline
        agg = DecisionIntelligenceAggregator()
        agg.submit_evidence(ev)
        snap = agg.get_snapshot(ev.decision_id)
        assert snap is not None
        assert snap.evidence is ev

    def test_remove(self, _rich_pipeline):
        _, _, ev, *_ = _rich_pipeline
        agg = DecisionIntelligenceAggregator()
        agg.submit_evidence(ev)
        agg.remove(ev.decision_id)
        assert agg.get_state(ev.decision_id) is None
