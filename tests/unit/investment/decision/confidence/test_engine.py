"""tests/unit/investment/decision/confidence/test_engine.py"""
from __future__ import annotations

import uuid

import pytest
import pytest_asyncio

from iios.investment.decision.confidence.confidence_constants import (
    ConfidenceEngineStatus,
    ConfidenceLevel,
)
from iios.investment.decision.confidence.confidence_pipeline import (
    BaseConfidenceModule,
    ConfidenceContext,
)
from iios.investment.decision.confidence.confidence_snapshot import ConfidenceSnapshot
from iios.investment.decision.confidence.decision_confidence_engine import (
    DecisionConfidenceEngine,
)


# ========================= Lifecycle =====================================

class TestEngineLifecycle:
    def test_initial_status_initializing(self):
        engine = DecisionConfidenceEngine()
        assert engine.status == ConfidenceEngineStatus.INITIALIZING

    def test_start_makes_ready(self):
        engine = DecisionConfidenceEngine()
        engine.start()
        assert engine.status == ConfidenceEngineStatus.READY

    def test_stop(self):
        engine = DecisionConfidenceEngine()
        engine.start()
        engine.stop()
        assert engine.status == ConfidenceEngineStatus.STOPPED

    def test_estimate_before_start_raises(self, rich_evidence_snapshot, rich_reasoning_snapshot):
        engine = DecisionConfidenceEngine()
        with pytest.raises(RuntimeError):
            engine.estimate_sync(rich_evidence_snapshot, rich_reasoning_snapshot)

    def test_estimate_after_stop_raises(self, rich_evidence_snapshot, rich_reasoning_snapshot):
        engine = DecisionConfidenceEngine()
        engine.start()
        engine.stop()
        with pytest.raises(RuntimeError):
            engine.estimate_sync(rich_evidence_snapshot, rich_reasoning_snapshot)


# ========================= Sync Estimation ===============================

class TestSyncEstimation:
    def test_returns_snapshot(self, rich_evidence_snapshot, rich_reasoning_snapshot):
        engine = DecisionConfidenceEngine()
        engine.start()
        snap = engine.estimate_sync(rich_evidence_snapshot, rich_reasoning_snapshot)
        assert isinstance(snap, ConfidenceSnapshot)

    def test_snapshot_is_usable(self, rich_evidence_snapshot, rich_reasoning_snapshot):
        engine = DecisionConfidenceEngine()
        engine.start()
        snap = engine.estimate_sync(rich_evidence_snapshot, rich_reasoning_snapshot)
        assert snap.is_usable

    def test_overall_confidence_in_range(self, rich_evidence_snapshot, rich_reasoning_snapshot):
        engine = DecisionConfidenceEngine()
        engine.start()
        snap = engine.estimate_sync(rich_evidence_snapshot, rich_reasoning_snapshot)
        assert 0.0 <= snap.overall_confidence <= 100.0

    def test_snapshot_decision_id_matches(self, rich_evidence_snapshot, rich_reasoning_snapshot):
        engine = DecisionConfidenceEngine()
        engine.start()
        snap = engine.estimate_sync(rich_evidence_snapshot, rich_reasoning_snapshot)
        assert snap.decision_id == rich_evidence_snapshot.decision_id

    def test_snapshot_subject_id_matches(self, rich_evidence_snapshot, rich_reasoning_snapshot):
        engine = DecisionConfidenceEngine()
        engine.start()
        snap = engine.estimate_sync(rich_evidence_snapshot, rich_reasoning_snapshot)
        assert snap.subject_id == rich_evidence_snapshot.subject_id

    def test_evidence_snapshot_id_tracked(self, rich_evidence_snapshot, rich_reasoning_snapshot):
        engine = DecisionConfidenceEngine()
        engine.start()
        snap = engine.estimate_sync(rich_evidence_snapshot, rich_reasoning_snapshot)
        assert snap.evidence_snapshot_id == rich_evidence_snapshot.snapshot_id

    def test_reasoning_snapshot_id_tracked(self, rich_evidence_snapshot, rich_reasoning_snapshot):
        engine = DecisionConfidenceEngine()
        engine.start()
        snap = engine.estimate_sync(rich_evidence_snapshot, rich_reasoning_snapshot)
        assert snap.reasoning_snapshot_id == rich_reasoning_snapshot.snapshot_id

    def test_scoring_snapshot_id_none_when_absent(self, rich_evidence_snapshot, rich_reasoning_snapshot):
        engine = DecisionConfidenceEngine()
        engine.start()
        snap = engine.estimate_sync(rich_evidence_snapshot, rich_reasoning_snapshot)
        assert snap.scoring_snapshot_id is None

    def test_minimal_snapshot_completes(self, minimal_evidence_snapshot, minimal_reasoning_snapshot):
        engine = DecisionConfidenceEngine()
        engine.start()
        snap = engine.estimate_sync(minimal_evidence_snapshot, minimal_reasoning_snapshot)
        assert snap is not None

    def test_engine_returns_to_ready(self, rich_evidence_snapshot, rich_reasoning_snapshot):
        engine = DecisionConfidenceEngine()
        engine.start()
        engine.estimate_sync(rich_evidence_snapshot, rich_reasoning_snapshot)
        assert engine.status == ConfidenceEngineStatus.READY


# ========================= Async Estimation ==============================

@pytest.mark.asyncio
class TestAsyncEstimation:
    async def test_async_returns_snapshot(self, rich_evidence_snapshot, rich_reasoning_snapshot):
        engine = DecisionConfidenceEngine()
        engine.start()
        snap = await engine.estimate(rich_evidence_snapshot, rich_reasoning_snapshot)
        assert isinstance(snap, ConfidenceSnapshot)

    async def test_async_confidence_in_range(self, rich_evidence_snapshot, rich_reasoning_snapshot):
        engine = DecisionConfidenceEngine()
        engine.start()
        snap = await engine.estimate(rich_evidence_snapshot, rich_reasoning_snapshot)
        assert 0.0 <= snap.overall_confidence <= 100.0

    async def test_no_scoring_snapshot(self, rich_evidence_snapshot, rich_reasoning_snapshot):
        engine = DecisionConfidenceEngine()
        engine.start()
        snap = await engine.estimate(rich_evidence_snapshot, rich_reasoning_snapshot, scoring_snapshot=None)
        assert snap.decision_confidence.scoring_available is False


# ========================= Version tracking ==============================

class TestVersionTracking:
    def test_version_increments(self, rich_evidence_snapshot, rich_reasoning_snapshot):
        engine = DecisionConfidenceEngine()
        engine.start()
        s1 = engine.estimate_sync(rich_evidence_snapshot, rich_reasoning_snapshot)
        s2 = engine.estimate_sync(rich_evidence_snapshot, rich_reasoning_snapshot)
        assert s2.version > s1.version

    def test_different_subjects_independent_versions(
        self, make_evidence_snapshot, make_ev_item, rich_reasoning_snapshot
    ):
        from iios.investment.decision.evidence.evidence_constants import EvidenceSourceType
        from iios.investment.decision.reasoning.decision_reasoning_engine import DecisionReasoningEngine

        ev1 = make_evidence_snapshot(
            [make_ev_item("p", 100, EvidenceSourceType.MARKET, decision_id="D_A", subject_id="AAA"),
             make_ev_item("r", 50,  EvidenceSourceType.RISK,   decision_id="D_A", subject_id="AAA")],
            decision_id="D_A", subject_id="AAA",
        )
        ev2 = make_evidence_snapshot(
            [make_ev_item("p", 200, EvidenceSourceType.MARKET, decision_id="D_B", subject_id="BBB"),
             make_ev_item("r", 40,  EvidenceSourceType.RISK,   decision_id="D_B", subject_id="BBB")],
            decision_id="D_B", subject_id="BBB",
        )
        re_engine = DecisionReasoningEngine()
        re_engine.start()
        re1 = re_engine.reason_sync(ev1)
        re2 = re_engine.reason_sync(ev2)

        engine = DecisionConfidenceEngine()
        engine.start()
        s_a1 = engine.estimate_sync(ev1, re1)
        s_b1 = engine.estimate_sync(ev2, re2)
        s_a2 = engine.estimate_sync(ev1, re1)
        assert s_a1.version == 1
        assert s_b1.version == 1
        assert s_a2.version == 2


# ========================= Query API =====================================

class TestQueryAPI:
    def test_get_snapshot(self, rich_evidence_snapshot, rich_reasoning_snapshot):
        engine = DecisionConfidenceEngine()
        engine.start()
        snap = engine.estimate_sync(rich_evidence_snapshot, rich_reasoning_snapshot)
        assert engine.get_snapshot(snap.snapshot_id) is snap

    def test_get_snapshot_missing_returns_none(self):
        engine = DecisionConfidenceEngine()
        engine.start()
        assert engine.get_snapshot("nonexistent") is None

    def test_get_history(self, rich_evidence_snapshot, rich_reasoning_snapshot):
        engine = DecisionConfidenceEngine()
        engine.start()
        engine.estimate_sync(rich_evidence_snapshot, rich_reasoning_snapshot)
        history = engine.get_history(rich_evidence_snapshot.subject_id)
        assert len(history) >= 1

    def test_get_latest(self, rich_evidence_snapshot, rich_reasoning_snapshot):
        engine = DecisionConfidenceEngine()
        engine.start()
        engine.estimate_sync(rich_evidence_snapshot, rich_reasoning_snapshot)
        latest = engine.get_latest(rich_evidence_snapshot.subject_id)
        assert latest is not None

    def test_get_quality(self, rich_evidence_snapshot, rich_reasoning_snapshot):
        engine = DecisionConfidenceEngine()
        engine.start()
        snap = engine.estimate_sync(rich_evidence_snapshot, rich_reasoning_snapshot)
        quality = engine.get_quality(snap.snapshot_id)
        assert quality is not None
        assert 0.0 <= quality.overall_quality <= 100.0

    def test_validate(self, rich_evidence_snapshot, rich_reasoning_snapshot):
        engine = DecisionConfidenceEngine()
        engine.start()
        snap = engine.estimate_sync(rich_evidence_snapshot, rich_reasoning_snapshot)
        v = engine.validate(snap.snapshot_id)
        assert v is not None
        assert isinstance(v.is_valid, bool)

    def test_confidence_series(self, rich_evidence_snapshot, rich_reasoning_snapshot):
        engine = DecisionConfidenceEngine()
        engine.start()
        engine.estimate_sync(rich_evidence_snapshot, rich_reasoning_snapshot)
        series = engine.confidence_series(rich_evidence_snapshot.subject_id)
        assert len(series) == 1
        assert 0.0 <= series[0] <= 100.0

    def test_stats_structure(self, rich_evidence_snapshot, rich_reasoning_snapshot):
        engine = DecisionConfidenceEngine()
        engine.start()
        engine.estimate_sync(rich_evidence_snapshot, rich_reasoning_snapshot)
        s = engine.stats()
        assert "status" in s
        assert "statistics" in s
        assert "health" in s
        assert "history" in s

    def test_snapshot_to_dict(self, rich_evidence_snapshot, rich_reasoning_snapshot):
        engine = DecisionConfidenceEngine()
        engine.start()
        snap = engine.estimate_sync(rich_evidence_snapshot, rich_reasoning_snapshot)
        d = snap.to_dict()
        for key in ("snapshot_id", "decision_id", "subject_id", "overall_confidence",
                    "confidence_level", "calibration_status", "quality_grade",
                    "is_usable", "created_at"):
            assert key in d


# ========================= Feedback / Calibration ========================

class TestFeedback:
    def test_record_outcome(self, rich_evidence_snapshot, rich_reasoning_snapshot):
        engine = DecisionConfidenceEngine()
        engine.start()
        snap = engine.estimate_sync(rich_evidence_snapshot, rich_reasoning_snapshot)
        # Should not raise
        engine.record_outcome(snap.decision_id, snap.overall_confidence, was_correct=True)
        assert engine.stats()["statistics"]["total_estimations"] == 1


# ========================= Pluggable module ==============================

@pytest.mark.asyncio
class TestPluggableModule:
    async def test_extra_module_executed(
        self, rich_evidence_snapshot, rich_reasoning_snapshot,
    ):
        executed = []

        class StubModule(BaseConfidenceModule):
            @property
            def module_name(self): return "StubModule"

            async def execute(self, ctx: ConfidenceContext) -> None:
                executed.append(True)

        from iios.investment.decision.confidence.confidence_pipeline import ConfidencePipeline
        pipeline = ConfidencePipeline(extra_modules=[StubModule()])
        engine   = DecisionConfidenceEngine(pipeline=pipeline)
        engine.start()
        await engine.estimate(rich_evidence_snapshot, rich_reasoning_snapshot)
        assert len(executed) == 1
