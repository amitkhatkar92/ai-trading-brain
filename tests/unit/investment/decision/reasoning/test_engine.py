"""tests/unit/investment/decision/reasoning/test_engine.py"""
from __future__ import annotations

import uuid

import pytest
import pytest_asyncio

from iios.investment.decision.reasoning.decision_reasoning_engine import DecisionReasoningEngine
from iios.investment.decision.reasoning.reasoning_constants import (
    ReasoningEngineStatus,
    ReasoningStatus,
)
from iios.investment.decision.reasoning.reasoning_snapshot import ReasoningSnapshot
from iios.investment.decision.reasoning.reasoning_trace import ReasoningTrace


# ========================= Lifecycle =====================================

class TestEngineLifecycle:
    def test_initial_status(self):
        engine = DecisionReasoningEngine()
        assert engine.status == ReasoningEngineStatus.INITIALIZING

    def test_start_makes_ready(self):
        engine = DecisionReasoningEngine()
        engine.start()
        assert engine.status == ReasoningEngineStatus.READY

    def test_stop(self):
        engine = DecisionReasoningEngine()
        engine.start()
        engine.stop()
        assert engine.status == ReasoningEngineStatus.STOPPED

    def test_reason_before_start_raises(self, minimal_evidence_snapshot):
        engine = DecisionReasoningEngine()
        with pytest.raises(RuntimeError):
            engine.reason_sync(minimal_evidence_snapshot)


# ========================= Async Reasoning ===============================

@pytest.mark.asyncio
class TestAsyncReasoning:
    async def test_reason_returns_snapshot(self, rich_evidence_snapshot):
        engine = DecisionReasoningEngine()
        engine.start()
        snap = await engine.reason(rich_evidence_snapshot)
        assert isinstance(snap, ReasoningSnapshot)

    async def test_snapshot_is_complete(self, rich_evidence_snapshot):
        engine = DecisionReasoningEngine()
        engine.start()
        snap = await engine.reason(rich_evidence_snapshot)
        assert snap.is_complete

    async def test_snapshot_decision_id_matches(self, rich_evidence_snapshot):
        engine = DecisionReasoningEngine()
        engine.start()
        snap = await engine.reason(rich_evidence_snapshot)
        assert snap.decision_id == rich_evidence_snapshot.decision_id

    async def test_snapshot_has_hypotheses(self, rich_evidence_snapshot):
        engine = DecisionReasoningEngine()
        engine.start()
        snap = await engine.reason(rich_evidence_snapshot)
        assert len(snap.hypotheses) >= 3

    async def test_snapshot_has_reasoning_chain(self, rich_evidence_snapshot):
        engine = DecisionReasoningEngine()
        engine.start()
        snap = await engine.reason(rich_evidence_snapshot)
        assert snap.reasoning_chain.step_count >= 8

    async def test_snapshot_quality_in_range(self, rich_evidence_snapshot):
        engine = DecisionReasoningEngine()
        engine.start()
        snap = await engine.reason(rich_evidence_snapshot)
        assert 0.0 <= snap.quality_score.overall <= 100.0

    async def test_custom_decision_id(self, rich_evidence_snapshot):
        engine = DecisionReasoningEngine()
        engine.start()
        custom_id = str(uuid.uuid4())
        snap = await engine.reason(rich_evidence_snapshot, decision_id=custom_id)
        assert snap.decision_id == custom_id

    async def test_version_increments(self, rich_evidence_snapshot, subject_id):
        engine = DecisionReasoningEngine()
        engine.start()
        s1 = await engine.reason(rich_evidence_snapshot)
        s2 = await engine.reason(rich_evidence_snapshot, decision_id=str(uuid.uuid4()))
        assert s2.version > s1.version

    async def test_evidence_snapshot_id_tracked(self, rich_evidence_snapshot):
        engine = DecisionReasoningEngine()
        engine.start()
        snap = await engine.reason(rich_evidence_snapshot)
        assert snap.evidence_snapshot_id == rich_evidence_snapshot.snapshot_id

    async def test_minimal_snapshot_completes(self, minimal_evidence_snapshot):
        engine = DecisionReasoningEngine()
        engine.start()
        snap = await engine.reason(minimal_evidence_snapshot)
        assert snap is not None

    async def test_engine_returns_to_ready_after_reason(self, rich_evidence_snapshot):
        engine = DecisionReasoningEngine()
        engine.start()
        await engine.reason(rich_evidence_snapshot)
        assert engine.status == ReasoningEngineStatus.READY


# ========================= Sync Wrapper ==================================

class TestSyncWrapper:
    def test_reason_sync(self, rich_evidence_snapshot):
        engine = DecisionReasoningEngine()
        engine.start()
        snap = engine.reason_sync(rich_evidence_snapshot)
        assert isinstance(snap, ReasoningSnapshot)
        assert snap.is_complete


# ========================= Query API =====================================

class TestQueryAPI:
    def test_get_snapshot(self, rich_evidence_snapshot):
        engine = DecisionReasoningEngine()
        engine.start()
        snap = engine.reason_sync(rich_evidence_snapshot)
        retrieved = engine.get_snapshot(snap.snapshot_id)
        assert retrieved is snap

    def test_get_snapshot_missing_returns_none(self):
        engine = DecisionReasoningEngine()
        engine.start()
        assert engine.get_snapshot("nonexistent") is None

    def test_get_history_for_subject(self, rich_evidence_snapshot, subject_id):
        engine = DecisionReasoningEngine()
        engine.start()
        engine.reason_sync(rich_evidence_snapshot)
        history = engine.get_history(subject_id)
        assert len(history) >= 1

    def test_get_latest(self, rich_evidence_snapshot, subject_id):
        engine = DecisionReasoningEngine()
        engine.start()
        engine.reason_sync(rich_evidence_snapshot)
        latest = engine.get_latest(subject_id)
        assert latest is not None

    def test_get_trace(self, rich_evidence_snapshot):
        engine = DecisionReasoningEngine()
        engine.start()
        snap  = engine.reason_sync(rich_evidence_snapshot)
        trace = engine.get_trace(snap.snapshot_id)
        assert isinstance(trace, ReasoningTrace)
        assert trace.depth() > 0

    def test_get_hypotheses(self, rich_evidence_snapshot):
        engine = DecisionReasoningEngine()
        engine.start()
        snap  = engine.reason_sync(rich_evidence_snapshot)
        hyps  = engine.get_hypotheses(snap.decision_id)
        assert len(hyps) >= 3

    def test_stats_structure(self, rich_evidence_snapshot):
        engine = DecisionReasoningEngine()
        engine.start()
        engine.reason_sync(rich_evidence_snapshot)
        s = engine.stats()
        assert "status" in s
        assert "health" in s
        assert "stats" in s

    def test_snapshot_to_dict(self, rich_evidence_snapshot):
        engine = DecisionReasoningEngine()
        engine.start()
        snap = engine.reason_sync(rich_evidence_snapshot)
        d = snap.to_dict()
        for key in ("snapshot_id", "decision_id", "subject_id", "status",
                    "quality_score", "final_conclusion", "step_count"):
            assert key in d

    def test_is_usable_when_complete(self, rich_evidence_snapshot):
        engine = DecisionReasoningEngine()
        engine.start()
        snap = engine.reason_sync(rich_evidence_snapshot)
        assert snap.is_usable
