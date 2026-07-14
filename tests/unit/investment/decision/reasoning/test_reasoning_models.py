"""tests/unit/investment/decision/reasoning/test_reasoning_models.py"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from iios.investment.decision.reasoning.reasoning_constants import ReasoningStepType, ReasoningStatus
from iios.investment.decision.reasoning.reasoning_step import ReasoningStep, make_step
from iios.investment.decision.reasoning.reasoning_chain import ReasoningChain, build_chain
from iios.investment.decision.reasoning.reasoning_history import ReasoningHistory
from iios.investment.decision.reasoning.reasoning_statistics import ReasoningStatisticsTracker


# ========================= ReasoningStep =================================

class TestReasoningStep:
    def test_make_step_creates_valid_step(self):
        step = make_step(
            step_type=ReasoningStepType.EVIDENCE_REVIEW,
            description="Review evidence.",
            intermediate_conclusion="10 items reviewed.",
        )
        assert step.step_id
        assert step.step_type == ReasoningStepType.EVIDENCE_REVIEW
        assert step.confidence == 70.0
        assert step.order == 0

    def test_confidence_clamped(self):
        step = make_step(
            ReasoningStepType.EVIDENCE_REVIEW, "d", "c", confidence=150.0
        )
        assert step.confidence == 100.0

    def test_is_immutable(self):
        step = make_step(ReasoningStepType.EVIDENCE_REVIEW, "d", "c")
        with pytest.raises(Exception):
            step.description = "mutated"  # type: ignore

    def test_to_dict_has_keys(self):
        step = make_step(ReasoningStepType.EVIDENCE_REVIEW, "d", "c",
                         evidence_trace_ids=("t1", "t2"))
        d = step.to_dict()
        assert "step_id" in d
        assert "step_type" in d
        assert "evidence_trace_ids" in d
        assert d["evidence_trace_ids"] == ["t1", "t2"]


# ========================= ReasoningChain ================================

class TestReasoningChain:
    def _steps(self):
        return [
            make_step(ReasoningStepType.EVIDENCE_REVIEW, "d1", "c1", order=0),
            make_step(ReasoningStepType.CONTEXT_ANALYSIS, "d2", "c2", order=1),
            make_step(ReasoningStepType.SIGNAL_INTERPRETATION, "d3", "c3", order=2),
        ]

    def test_build_chain(self, decision_id):
        steps = self._steps()
        chain = build_chain(decision_id=decision_id, steps=steps, final_conclusion="Done.")
        assert chain.step_count == 3
        assert chain.final_conclusion == "Done."

    def test_steps_sorted_by_order(self, decision_id):
        steps = [
            make_step(ReasoningStepType.CONTEXT_ANALYSIS, "d", "c", order=2),
            make_step(ReasoningStepType.EVIDENCE_REVIEW, "d", "c", order=0),
        ]
        chain = build_chain(decision_id, steps, "Done.")
        orders = [s.order for s in chain.steps]
        assert orders == sorted(orders)

    def test_avg_confidence(self, decision_id):
        steps = [
            make_step(ReasoningStepType.EVIDENCE_REVIEW, "d", "c", confidence=80.0, order=0),
            make_step(ReasoningStepType.CONTEXT_ANALYSIS, "d", "c", confidence=60.0, order=1),
        ]
        chain = build_chain(decision_id, steps, "Done.")
        assert chain.avg_step_confidence == pytest.approx(70.0)

    def test_all_trace_ids_unique(self, decision_id):
        t1, t2 = str(uuid.uuid4()), str(uuid.uuid4())
        steps = [
            make_step(ReasoningStepType.EVIDENCE_REVIEW, "d", "c", evidence_trace_ids=(t1, t2), order=0),
            make_step(ReasoningStepType.CONTEXT_ANALYSIS, "d", "c", evidence_trace_ids=(t1,), order=1),
        ]
        chain = build_chain(decision_id, steps, "Done.")
        assert chain.total_evidence_refs == 2   # t1 counted once

    def test_steps_of_type(self, decision_id):
        steps = self._steps()
        chain = build_chain(decision_id, steps, "Done.")
        ev_steps = chain.steps_of_type(ReasoningStepType.EVIDENCE_REVIEW)
        assert len(ev_steps) == 1

    def test_to_dict(self, decision_id):
        chain = build_chain(decision_id, self._steps(), "Done.")
        d = chain.to_dict()
        assert d["step_count"] == 3
        assert "steps" in d


# ========================= ReasoningHistory ==============================

class TestReasoningHistory:
    def _snap(self, subject_id="INFY", decision_id=None, quality=80.0):
        from tests.unit.investment.decision.reasoning.conftest import _ev_item, _snap
        from iios.investment.decision.evidence.evidence_constants import EvidenceSourceType
        did = decision_id or str(uuid.uuid4())
        items = [
            _ev_item("price", 100.0, EvidenceSourceType.MARKET, decision_id=did, subject_id=subject_id),
            _ev_item("risk_score", 40.0, EvidenceSourceType.RISK, decision_id=did, subject_id=subject_id),
        ]
        ev_snap = _snap(items, decision_id=did, subject_id=subject_id, quality=quality)
        # Build a real ReasoningSnapshot
        from iios.investment.decision.reasoning.decision_reasoning_engine import DecisionReasoningEngine
        engine = DecisionReasoningEngine()
        engine.start()
        return engine.reason_sync(ev_snap)

    def test_record_and_get(self):
        hist = ReasoningHistory()
        snap = self._snap()
        hist.record(snap)
        assert hist.get(snap.snapshot_id) is snap

    def test_for_subject(self):
        hist = ReasoningHistory()
        snap = self._snap(subject_id="WIPRO")
        hist.record(snap)
        assert len(hist.for_subject("WIPRO")) == 1

    def test_count(self):
        hist = ReasoningHistory()
        for _ in range(3):
            hist.record(self._snap())
        assert hist.count() == 3

    def test_latest_for_subject(self):
        hist = ReasoningHistory()
        snap = self._snap(subject_id="TCS")
        hist.record(snap)
        assert hist.latest_for_subject("TCS") is snap


# ========================= ReasoningStatisticsTracker ====================

class TestReasoningStatisticsTracker:
    def test_empty(self):
        t = ReasoningStatisticsTracker()
        s = t.summary()
        assert s.total_snapshots == 0

    def test_records(self):
        from tests.unit.investment.decision.reasoning.conftest import _ev_item, _snap
        from iios.investment.decision.evidence.evidence_constants import EvidenceSourceType
        from iios.investment.decision.reasoning.decision_reasoning_engine import DecisionReasoningEngine
        did = str(uuid.uuid4())
        items = [
            _ev_item("price", 100.0, EvidenceSourceType.MARKET, decision_id=did),
            _ev_item("risk_score", 40.0, EvidenceSourceType.RISK, decision_id=did),
        ]
        ev_snap = _snap(items, decision_id=did)
        engine  = DecisionReasoningEngine()
        engine.start()
        r_snap  = engine.reason_sync(ev_snap)
        t = ReasoningStatisticsTracker()
        t.record(r_snap)
        s = t.summary()
        assert s.total_snapshots == 1
        assert s.avg_quality >= 0
