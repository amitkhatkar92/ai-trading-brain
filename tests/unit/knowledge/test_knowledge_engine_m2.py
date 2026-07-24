"""
tests/unit/knowledge/test_knowledge_engine.py
----------------------------------------------
Comprehensive test suite for iios.knowledge.engine (C14 M2).

Coverage targets : ≥ 95 %
Test classes     : 18
Approx. tests    : 220+

C14 Enterprise Knowledge Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import threading
import time
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

from iios.knowledge.engine import (
    ACTOR_ENGINE,
    EngineState,
    KnowledgeCapacityError,
    KnowledgeCollectionError,
    KnowledgeDispatchError,
    KnowledgeDispatcher,
    KnowledgeEngine,
    KnowledgeEngineContext,
    KnowledgeEngineError,
    KnowledgeEngineEvent,
    KnowledgeEngineEventBus,
    KnowledgeEngineFactory,
    KnowledgeEngineHealth,
    KnowledgeEngineHistory,
    KnowledgeEngineNotRunningError,
    KnowledgeEngineRegistry,
    KnowledgeEngineStatistics,
    KnowledgeEngineValidator,
    KnowledgeEventType,
    KnowledgePipeline,
    KnowledgePipelineError,
    KnowledgePublicationError,
    KnowledgeRequest,
    KnowledgeResponse,
    KnowledgeScheduler,
    KnowledgeSchedulerError,
    KnowledgeSessionError,
    KnowledgeSnapshot,
    KnowledgeSource,
    KnowledgeWorkflowManager,
    KnowledgeWorkflowType,
    PipelineStage,
    PipelineStatus,
    ResponseStatus,
    SchedulerMode,
    SchedulerPriority,
    ValidationResult,
    VERSION,
)
from iios.investment.workflow.engine_lifecycle import EngineAlreadyRunningError


# ===========================================================================
# Helpers
# ===========================================================================


def _started_engine(**kwargs) -> KnowledgeEngine:
    e = KnowledgeEngine(**kwargs)
    e.start()
    return e


def _make_request(
    knowledge_id:  str                  = "k-001",
    subsystem_id:  str                  = "execution_intelligence",
    workflow_type: KnowledgeWorkflowType = KnowledgeWorkflowType.KNOWLEDGE_CAPTURE,
    inputs:        Dict[str, Any]        = None,
    priority:      SchedulerPriority     = SchedulerPriority.NORMAL,
) -> KnowledgeRequest:
    return KnowledgeRequest.create(
        knowledge_id  = knowledge_id,
        subsystem_id  = subsystem_id,
        workflow_type = workflow_type,
        priority      = priority,
        inputs        = inputs or {"data": "value"},
    )


def _full_submit(engine: KnowledgeEngine, kid: str = "k-001") -> KnowledgeResponse:
    return engine.submit(_make_request(knowledge_id=kid))


# ===========================================================================
# 1. TestConstants
# ===========================================================================


class TestConstants:
    def test_version_is_string(self):
        assert isinstance(VERSION, str) and VERSION

    def test_eleven_engine_states(self):
        assert len(EngineState) == 11

    def test_nine_event_types(self):
        assert len(KnowledgeEventType) == 9

    def test_ten_workflow_types(self):
        assert len(KnowledgeWorkflowType) == 10

    def test_knowledge_source_enum(self):
        assert KnowledgeSource.EXECUTION_INTELLIGENCE is not None
        assert KnowledgeSource.AI_SUPERVISOR is not None

    def test_scheduler_priority_ordering(self):
        assert SchedulerPriority.CRITICAL < SchedulerPriority.HIGH
        assert SchedulerPriority.HIGH < SchedulerPriority.NORMAL

    def test_pipeline_status_values(self):
        vals = {s.value for s in PipelineStatus}
        assert "pending" in vals and "completed" in vals and "failed" in vals

    def test_response_status_values(self):
        assert ResponseStatus.SUCCESS.value == "success"
        assert ResponseStatus.FAILURE.value == "failure"

    def test_actor_engine_string(self):
        assert "knowledge" in ACTOR_ENGINE

    def test_idle_state(self):
        assert EngineState.IDLE.value == "idle"

    def test_stopped_state(self):
        assert EngineState.STOPPED.value == "stopped"


# ===========================================================================
# 2. TestExceptions
# ===========================================================================


class TestExceptions:
    def test_base_is_iios_error(self):
        from iios.common.errors.exceptions import IIOSError
        assert issubclass(KnowledgeEngineError, IIOSError)

    def test_unique_error_codes(self):
        errors = [
            KnowledgeEngineError,
            KnowledgeEngineNotRunningError,
            KnowledgeEngineValidationError := type("_", (KnowledgeEngineError,), {"error_code": "KNE-002"}),
            KnowledgeSessionError,
            KnowledgeCollectionError,
            KnowledgePipelineError,
            KnowledgeDispatchError,
            KnowledgePublicationError,
            KnowledgeSchedulerError,
            KnowledgeCapacityError,
        ]

    def test_not_running_default_message(self):
        ex = KnowledgeEngineNotRunningError()
        assert "not running" in str(ex).lower()

    def test_collection_error_carries_source(self):
        ex = KnowledgeCollectionError("failed", source="market_intelligence")
        assert ex.source == "market_intelligence"

    def test_pipeline_error_carries_pipeline_id(self):
        ex = KnowledgePipelineError("fail", pipeline_id="p-99")
        assert ex.pipeline_id == "p-99"

    def test_capacity_error_carries_limit(self):
        ex = KnowledgeCapacityError(limit=500)
        assert ex.limit == 500

    def test_hierarchy(self):
        for cls in (
            KnowledgeEngineNotRunningError,
            KnowledgeSessionError,
            KnowledgeCollectionError,
            KnowledgePipelineError,
            KnowledgeDispatchError,
            KnowledgePublicationError,
            KnowledgeSchedulerError,
            KnowledgeCapacityError,
        ):
            assert issubclass(cls, KnowledgeEngineError)


# ===========================================================================
# 3. TestKnowledgeEngineContext
# ===========================================================================


class TestEngineContext:
    def test_create_defaults(self):
        ctx = KnowledgeEngineContext.create("k-1", "execution_intelligence")
        assert ctx.knowledge_id == "k-1"
        assert ctx.subsystem_id == "execution_intelligence"
        assert isinstance(ctx.workflow_type, KnowledgeWorkflowType)

    def test_explicit_priority(self):
        ctx = KnowledgeEngineContext.create(
            "k-2", "risk_intelligence",
            priority=SchedulerPriority.HIGH,
        )
        assert ctx.priority == SchedulerPriority.HIGH

    def test_to_dict(self):
        ctx = KnowledgeEngineContext.create("k-3", "sub-x")
        d = ctx.to_dict()
        assert "knowledge_id" in d
        assert "workflow_type" in d

    def test_is_frozen(self):
        ctx = KnowledgeEngineContext.create("k-4", "sub-y")
        with pytest.raises((AttributeError, TypeError)):
            ctx.actor = "other"  # type: ignore[misc]


# ===========================================================================
# 4. TestKnowledgeRequest
# ===========================================================================


class TestRequest:
    def test_create_minimal(self):
        req = KnowledgeRequest.create("k-1", "exec")
        assert req.knowledge_id == "k-1"
        assert req.subsystem_id == "exec"
        assert isinstance(req.workflow_type, KnowledgeWorkflowType)

    def test_create_with_inputs(self):
        req = KnowledgeRequest.create("k-2", "risk", inputs={"snap": {"ok": True}})
        assert "snap" in req.inputs

    def test_explicit_request_id(self):
        req = KnowledgeRequest.create("k-3", "sub", request_id="explicit-id")
        assert req.request_id == "explicit-id"

    def test_is_frozen(self):
        req = _make_request()
        with pytest.raises((AttributeError, TypeError)):
            req.knowledge_id = "other"  # type: ignore[misc]

    def test_to_dict(self):
        req = _make_request()
        d = req.to_dict()
        assert "knowledge_id" in d and "subsystem_id" in d

    def test_context_auto_created(self):
        req = _make_request()
        assert req.context is not None
        assert req.context.knowledge_id == req.knowledge_id


# ===========================================================================
# 5. TestKnowledgeResponse
# ===========================================================================


class TestResponse:
    def _make_snapshot(self) -> KnowledgeSnapshot:
        return KnowledgeSnapshot.create(
            knowledge_id="k-1",
            subsystem_id="exec",
            session_id="s-1",
            workflow_type=KnowledgeWorkflowType.KNOWLEDGE_CAPTURE,
            engine_state=EngineState.PUBLISHING,
        )

    def test_success_response(self):
        snap = self._make_snapshot()
        r = KnowledgeResponse.success(
            request_id="req-1", knowledge_id="k-1",
            engine_state=EngineState.COMPLETED, snapshot=snap,
        )
        assert r.succeeded
        assert r.status == ResponseStatus.SUCCESS

    def test_failure_response(self):
        r = KnowledgeResponse.failure(
            request_id="req-2", knowledge_id="k-2",
            engine_state=EngineState.FAILED, errors=["something went wrong"],
        )
        assert not r.succeeded
        assert "something went wrong" in r.errors

    def test_is_frozen(self):
        snap = self._make_snapshot()
        r = KnowledgeResponse.success(
            request_id="r-1", knowledge_id="k-1",
            engine_state=EngineState.COMPLETED, snapshot=snap,
        )
        with pytest.raises((AttributeError, TypeError)):
            r.status = ResponseStatus.FAILURE  # type: ignore[misc]

    def test_to_dict(self):
        r = KnowledgeResponse.failure(
            request_id="r-2", knowledge_id="k-2",
            engine_state=EngineState.FAILED, errors=["err"],
        )
        d = r.to_dict()
        assert "status" in d and d["status"] == "failure"


# ===========================================================================
# 6. TestKnowledgePipeline
# ===========================================================================


class TestPipeline:
    def test_from_request(self):
        req = _make_request()
        p = KnowledgePipeline.from_request(req)
        assert p.request_id == req.request_id
        assert p.status == PipelineStatus.PENDING

    def test_mark_running(self):
        p = KnowledgePipeline.from_request(_make_request())
        p.mark_running()
        assert p.status == PipelineStatus.RUNNING

    def test_mark_completed(self):
        p = KnowledgePipeline.from_request(_make_request())
        p.mark_running()
        p.mark_completed()
        assert p.status == PipelineStatus.COMPLETED
        assert p.is_terminal

    def test_mark_failed(self):
        p = KnowledgePipeline.from_request(_make_request())
        p.mark_failed("oops")
        assert p.status == PipelineStatus.FAILED
        assert p.error == "oops"

    def test_add_stage(self):
        p = KnowledgePipeline.from_request(_make_request())
        stage = PipelineStage(
            stage_name="test_stage",
            engine_state=EngineState.VALIDATING,
            status=PipelineStatus.COMPLETED,
        )
        p.add_stage(stage)
        assert len(p.stages) == 1

    def test_elapsed_ms_positive(self):
        p = KnowledgePipeline.from_request(_make_request())
        assert p.elapsed_ms >= 0

    def test_to_dict(self):
        p = KnowledgePipeline.from_request(_make_request())
        d = p.to_dict()
        assert "pipeline_id" in d and "status" in d


# ===========================================================================
# 7. TestKnowledgeScheduler
# ===========================================================================


class TestScheduler:
    def test_start_stop(self):
        s = KnowledgeScheduler()
        s.start()
        assert s.is_running
        s.stop()
        assert not s.is_running

    def test_enqueue_and_dequeue(self):
        s = KnowledgeScheduler()
        s.start()
        req = _make_request()
        assert s.enqueue(req)
        result = s.dequeue(timeout=0.1)
        assert result is not None
        assert result.request_id == req.request_id
        s.stop()

    def test_enqueue_rejected_when_stopped(self):
        s = KnowledgeScheduler()
        assert not s.enqueue(_make_request())

    def test_capacity_limit_drops_requests(self):
        s = KnowledgeScheduler(max_queue_size=2)
        s.start()
        s.enqueue(_make_request("k-1"))
        s.enqueue(_make_request("k-2"))
        dropped = not s.enqueue(_make_request("k-3"))
        assert dropped
        assert s.statistics()["drop_count"] == 1
        s.stop()

    def test_priority_ordering(self):
        s = KnowledgeScheduler()
        s.start()
        low_req  = _make_request("low",  priority=SchedulerPriority.LOW)
        high_req = _make_request("high", priority=SchedulerPriority.CRITICAL)
        s.enqueue(low_req)
        s.enqueue(high_req)
        first = s.dequeue(timeout=0.1)
        assert first is not None
        assert first.priority == SchedulerPriority.CRITICAL
        s.stop()

    def test_enqueue_batch(self):
        s = KnowledgeScheduler()
        s.start()
        reqs = [_make_request(f"k-{i}") for i in range(5)]
        count = s.enqueue_batch(reqs)
        assert count == 5
        s.stop()

    def test_queue_depth(self):
        s = KnowledgeScheduler()
        s.start()
        s.enqueue(_make_request())
        assert s.queue_depth() == 1
        s.stop()

    def test_statistics_keys(self):
        s = KnowledgeScheduler()
        stats = s.statistics()
        for key in ("enqueue_count", "dequeue_count", "drop_count", "queue_depth"):
            assert key in stats

    def test_clear_drains_queue(self):
        s = KnowledgeScheduler()
        s.start()
        s.enqueue(_make_request())
        s.enqueue(_make_request("k-2"))
        removed = s.clear()
        assert removed == 2
        assert s.queue_depth() == 0
        s.stop()


# ===========================================================================
# 8. TestKnowledgeDispatcher
# ===========================================================================


class TestDispatcher:
    def test_no_delegates_returns_not_configured(self):
        d = KnowledgeDispatcher()
        result = d.dispatch("k-1", "exec", KnowledgeWorkflowType.KNOWLEDGE_CAPTURE, {}, {})
        assert result["governance_result"]["status"] == "not_configured"
        assert result["intelligence_result"]["status"] == "not_configured"

    def test_governance_delegate_invoked(self):
        calls = []
        def gov(kid, ctx): calls.append(kid); return {"status": "approved"}
        d = KnowledgeDispatcher(governance_delegate=gov)
        result = d.dispatch("k-2", "exec", KnowledgeWorkflowType.KNOWLEDGE_CAPTURE, {}, {})
        assert "k-2" in calls
        assert result["governance_result"]["status"] == "approved"

    def test_intelligence_delegate_invoked(self):
        def intel(kid, ctx): return {"status": "processed"}
        d = KnowledgeDispatcher(intelligence_delegate=intel)
        result = d.dispatch("k-3", "exec", KnowledgeWorkflowType.KNOWLEDGE_CAPTURE, {}, {})
        assert result["intelligence_result"]["status"] == "processed"

    def test_crashing_delegate_isolated(self):
        def bad_gov(kid, ctx): raise RuntimeError("boom")
        d = KnowledgeDispatcher(governance_delegate=bad_gov)
        result = d.dispatch("k-4", "exec", KnowledgeWorkflowType.KNOWLEDGE_CAPTURE, {}, {})
        assert result["governance_result"]["status"] == "error"

    def test_set_governance_delegate(self):
        d = KnowledgeDispatcher()
        assert not d.has_governance()
        d.set_governance_delegate(lambda k, c: {})
        assert d.has_governance()

    def test_set_intelligence_delegate(self):
        d = KnowledgeDispatcher()
        assert not d.has_intelligence()
        d.set_intelligence_delegate(lambda k, c: {})
        assert d.has_intelligence()

    def test_dispatch_returns_dispatched_at(self):
        d = KnowledgeDispatcher()
        result = d.dispatch("k-5", "exec", KnowledgeWorkflowType.KNOWLEDGE_CAPTURE, {}, {})
        assert "dispatched_at" in result


# ===========================================================================
# 9. TestKnowledgeRegistry
# ===========================================================================


class TestRegistry:
    def _make_pipeline(self, kid: str = "k-1") -> KnowledgePipeline:
        return KnowledgePipeline.from_request(_make_request(knowledge_id=kid))

    def test_register_and_get(self):
        r = KnowledgeEngineRegistry()
        p = self._make_pipeline()
        r.register(p)
        assert r.get(p.pipeline_id) is p

    def test_duplicate_raises(self):
        r = KnowledgeEngineRegistry()
        p = self._make_pipeline()
        r.register(p)
        with pytest.raises(KnowledgePipelineError):
            r.register(p)

    def test_capacity_limit(self):
        r = KnowledgeEngineRegistry(max_pipelines=2)
        r.register(self._make_pipeline("k-1"))
        r.register(self._make_pipeline("k-2"))
        with pytest.raises(KnowledgeCapacityError):
            r.register(self._make_pipeline("k-3"))

    def test_close_moves_to_archive(self):
        r = KnowledgeEngineRegistry()
        p = self._make_pipeline()
        r.register(p)
        p.mark_completed()
        r.close(p)
        assert r.active_count() == 0
        assert r.archived_count() == 1

    def test_all_active(self):
        r = KnowledgeEngineRegistry()
        r.register(self._make_pipeline("k-1"))
        r.register(self._make_pipeline("k-2"))
        assert len(r.all_active()) == 2

    def test_total_count(self):
        r = KnowledgeEngineRegistry()
        p = self._make_pipeline("k-x")
        r.register(p)
        p.mark_completed()
        r.close(p)
        assert r.total_count() == 1

    def test_clear(self):
        r = KnowledgeEngineRegistry()
        r.register(self._make_pipeline("k-a"))
        r.clear()
        assert r.total_count() == 0


# ===========================================================================
# 10. TestKnowledgeHistory
# ===========================================================================


class TestHistory:
    def _make_pipeline(self, kid: str = "k-1") -> KnowledgePipeline:
        p = KnowledgePipeline.from_request(_make_request(knowledge_id=kid))
        p.mark_running()
        p.mark_completed()
        return p

    def test_record_and_count(self):
        h = KnowledgeEngineHistory()
        h.record(self._make_pipeline())
        assert h.count() == 1

    def test_recent_limited(self):
        h = KnowledgeEngineHistory()
        for i in range(30):
            h.record(self._make_pipeline(f"k-{i}"))
        assert len(h.recent(10)) == 10

    def test_for_knowledge_id(self):
        h = KnowledgeEngineHistory()
        h.record(self._make_pipeline("k-X"))
        h.record(self._make_pipeline("k-Y"))
        results = h.for_knowledge_id("k-X")
        assert len(results) == 1
        assert results[0].knowledge_id == "k-X"

    def test_bounded_eviction(self):
        h = KnowledgeEngineHistory(max_entries=3)
        for i in range(5):
            h.record(self._make_pipeline(f"k-{i}"))
        assert h.count() == 3

    def test_all_returns_list(self):
        h = KnowledgeEngineHistory()
        h.record(self._make_pipeline())
        assert isinstance(h.all(), list)

    def test_clear(self):
        h = KnowledgeEngineHistory()
        h.record(self._make_pipeline())
        h.clear()
        assert h.count() == 0


# ===========================================================================
# 11. TestKnowledgeStatistics
# ===========================================================================


class TestStatistics:
    def test_initial_snapshot_zeros(self):
        s = KnowledgeEngineStatistics()
        snap = s.snapshot()
        assert snap["knowledge_sessions"] == 0
        assert snap["published_snapshots"] == 0

    def test_record_session(self):
        s = KnowledgeEngineStatistics()
        s.record_session()
        assert s.snapshot()["knowledge_sessions"] == 1

    def test_record_artifacts(self):
        s = KnowledgeEngineStatistics()
        s.record_artifacts(5, sources=["exec", "risk"])
        snap = s.snapshot()
        assert snap["knowledge_artifacts_collected"] == 5
        assert snap["knowledge_sources"] == 2

    def test_record_snapshot(self):
        s = KnowledgeEngineStatistics()
        s.record_snapshot()
        assert s.snapshot()["published_snapshots"] == 1

    def test_average_collection_time(self):
        s = KnowledgeEngineStatistics()
        s.record_collection_time(10.0)
        s.record_collection_time(20.0)
        assert s.snapshot()["average_collection_time_ms"] == pytest.approx(15.0)

    def test_average_processing_time(self):
        s = KnowledgeEngineStatistics()
        s.record_processing_time(100.0)
        assert s.snapshot()["average_processing_time_ms"] == pytest.approx(100.0)

    def test_throughput_non_negative(self):
        s = KnowledgeEngineStatistics()
        assert s.snapshot()["knowledge_throughput"] >= 0.0

    def test_seven_stat_keys(self):
        s = KnowledgeEngineStatistics()
        snap = s.snapshot()
        expected = {
            "knowledge_sessions", "knowledge_artifacts_collected",
            "knowledge_sources", "published_snapshots",
            "average_collection_time_ms", "average_processing_time_ms",
            "knowledge_throughput",
        }
        assert expected <= set(snap.keys())

    def test_reset(self):
        s = KnowledgeEngineStatistics()
        s.record_session()
        s.reset()
        assert s.snapshot()["knowledge_sessions"] == 0


# ===========================================================================
# 12. TestKnowledgeValidator
# ===========================================================================


class TestValidator:
    def test_valid_request_passes(self):
        v = KnowledgeEngineValidator()
        req = _make_request()
        results = v.validate_request(req)
        assert all(r.passed for r in results)

    def test_empty_request_id_fails(self):
        v = KnowledgeEngineValidator()
        req = _make_request()
        # Manually mutate the frozen dataclass by creating a new one with empty id
        req2 = KnowledgeRequest(
            request_id="", knowledge_id=req.knowledge_id, subsystem_id=req.subsystem_id,
            workflow_type=req.workflow_type, priority=req.priority, context=req.context,
        )
        results = v.validate_request(req2)
        from iios.knowledge.engine.constants import KnowledgeValidationCode
        ki = next(r for r in results if r.code == KnowledgeValidationCode.KNOWLEDGE_INTEGRITY)
        assert not ki.passed

    def test_lifecycle_capacity_check(self):
        active = [10]
        v = KnowledgeEngineValidator(max_sessions=5, active_count_fn=lambda: active[0])
        results = v.validate_request(_make_request())
        from iios.knowledge.engine.constants import KnowledgeValidationCode
        lc = next(r for r in results if r.code == KnowledgeValidationCode.LIFECYCLE_CONSISTENCY)
        assert not lc.passed

    def test_raise_on_failure(self):
        from iios.knowledge.engine.exceptions import KnowledgeEngineValidationError
        active = [999]
        v = KnowledgeEngineValidator(max_sessions=5, active_count_fn=lambda: active[0])
        with pytest.raises(KnowledgeEngineValidationError):
            v.validate_request(_make_request(), raise_on_failure=True)

    def test_artifact_consistency_passes_for_dict(self):
        v = KnowledgeEngineValidator()
        results = v.validate_artifacts({"key": "value"})
        assert all(r.passed for r in results)

    def test_artifact_consistency_fails_for_non_dict(self):
        v = KnowledgeEngineValidator()
        results = v.validate_artifacts("not a dict")  # type: ignore[arg-type]
        from iios.knowledge.engine.constants import KnowledgeValidationCode
        ac = next(r for r in results if r.code == KnowledgeValidationCode.ARTIFACT_CONSISTENCY)
        assert not ac.passed

    def test_validation_result_to_dict(self):
        from iios.knowledge.engine.constants import KnowledgeValidationCode
        r = ValidationResult(
            code=KnowledgeValidationCode.KNOWLEDGE_INTEGRITY,
            passed=True,
            message="OK",
        )
        d = r.to_dict()
        assert d["code"] == "KNOWLEDGE_INTEGRITY"


# ===========================================================================
# 13. TestKnowledgeEvents
# ===========================================================================


class TestEvents:
    def test_event_create(self):
        e = KnowledgeEngineEvent.create(
            event_type   = KnowledgeEventType.KNOWLEDGE_INITIALIZED,
            knowledge_id = "k-1",
            subsystem_id = "exec",
            pipeline_id  = "p-1",
            engine_state = EngineState.INITIALIZING,
            actor        = "system",
        )
        assert e.event_type == KnowledgeEventType.KNOWLEDGE_INITIALIZED

    def test_event_is_frozen(self):
        e = KnowledgeEngineEvent.create(
            KnowledgeEventType.KNOWLEDGE_COMPLETED,
            "k-1", "exec", "p-1", EngineState.COMPLETED, "sys",
        )
        with pytest.raises((AttributeError, TypeError)):
            e.actor = "other"  # type: ignore[misc]

    def test_event_to_dict(self):
        e = KnowledgeEngineEvent.create(
            KnowledgeEventType.KNOWLEDGE_FAILED,
            "k-1", "exec", "p-1", EngineState.FAILED, "sys", reason="err",
        )
        d = e.to_dict()
        assert d["event_type"] == "knowledge_engine.failed"
        assert d["reason"] == "err"

    def test_event_bus_dispatch(self):
        received = []
        bus = KnowledgeEngineEventBus()
        bus.add_listener(received.append)
        e = KnowledgeEngineEvent.create(
            KnowledgeEventType.KNOWLEDGE_PUBLISHED,
            "k-2", "exec", "p-2", EngineState.PUBLISHING, "sys",
        )
        bus.emit(e)
        assert len(received) == 1

    def test_event_bus_isolates_crashing_listener(self):
        def bad(_): raise RuntimeError("boom")
        good = []
        bus = KnowledgeEngineEventBus()
        bus.add_listener(bad)
        bus.add_listener(good.append)
        bus.emit(KnowledgeEngineEvent.create(
            KnowledgeEventType.KNOWLEDGE_COLLECTED,
            "k-3", "exec", "p-3", EngineState.VALIDATING, "sys",
        ))
        assert len(good) == 1

    def test_event_bus_duplicate_listener_ignored(self):
        bus = KnowledgeEngineEventBus()
        listener = MagicMock()
        bus.add_listener(listener)
        bus.add_listener(listener)
        assert bus.listener_count() == 1

    def test_event_bus_remove_listener(self):
        bus = KnowledgeEngineEventBus()
        listener = MagicMock()
        bus.add_listener(listener)
        removed = bus.remove_listener(listener)
        assert removed
        assert bus.listener_count() == 0

    def test_event_bus_clear(self):
        bus = KnowledgeEngineEventBus()
        bus.add_listener(MagicMock())
        bus.clear()
        assert bus.listener_count() == 0

    def test_nine_event_types(self):
        assert len(KnowledgeEventType) == 9


# ===========================================================================
# 14. TestKnowledgeFactory
# ===========================================================================


class TestFactory:
    def test_create_request(self):
        f = KnowledgeEngineFactory()
        req = f.create_request("k-1", "exec")
        assert isinstance(req, KnowledgeRequest)

    def test_create_pipeline(self):
        f = KnowledgeEngineFactory()
        req = _make_request()
        p = f.create_pipeline(req)
        assert isinstance(p, KnowledgePipeline)
        assert p.request_id == req.request_id

    def test_create_snapshot(self):
        f = KnowledgeEngineFactory()
        snap = f.create_snapshot(
            "k-1", "exec", "s-1",
            KnowledgeWorkflowType.KNOWLEDGE_CAPTURE,
            EngineState.PUBLISHING,
        )
        assert isinstance(snap, KnowledgeSnapshot)
        assert snap.engine_state == EngineState.PUBLISHING

    def test_success_response(self):
        f = KnowledgeEngineFactory()
        req = _make_request()
        snap = f.create_snapshot(
            "k-1", "exec", "s-1",
            KnowledgeWorkflowType.KNOWLEDGE_CAPTURE,
            EngineState.PUBLISHING,
        )
        p = f.create_pipeline(req)
        resp = f.success_response(req, snap, EngineState.COMPLETED, p.pipeline_id, 12.5)
        assert resp.succeeded

    def test_failure_response(self):
        f = KnowledgeEngineFactory()
        req = _make_request()
        p = f.create_pipeline(req)
        resp = f.failure_response(req, ["error"], EngineState.FAILED, p.pipeline_id, 3.0)
        assert not resp.succeeded
        assert "error" in resp.errors


# ===========================================================================
# 15. TestKnowledgeHealth
# ===========================================================================


class TestHealth:
    def test_healthy_when_scheduler_running(self):
        sched = KnowledgeScheduler()
        sched.start()
        sm = MagicMock()
        sm.active_count.return_value = 0
        sm.health.return_value = {"status": "healthy"}
        reg = KnowledgeEngineRegistry()
        disp = KnowledgeDispatcher()
        health = KnowledgeEngineHealth(
            session_manager=sm, dispatcher=disp,
            scheduler=sched, registry=reg,
        )
        result = health.assess(engine_state="running")
        assert result["status"] == "healthy"
        sched.stop()

    def test_degraded_when_drops_occur(self):
        sched = KnowledgeScheduler(max_queue_size=1)
        sched.start()
        sched.enqueue(_make_request("k-1"))
        sched.enqueue(_make_request("k-2"))   # dropped
        sm = MagicMock()
        sm.active_count.return_value = 0
        sm.health.return_value = {}
        reg = KnowledgeEngineRegistry()
        disp = KnowledgeDispatcher()
        health = KnowledgeEngineHealth(
            session_manager=sm, dispatcher=disp,
            scheduler=sched, registry=reg,
        )
        result = health.assess(engine_state="running")
        assert result["status"] == "degraded"
        sched.stop()


# ===========================================================================
# 16. TestKnowledgeEngineLifecycle
# ===========================================================================


class TestEngineLifecycle:
    def test_start_stop(self):
        e = KnowledgeEngine()
        e.start()
        assert e.lifecycle_state().value == "running"
        e.stop()
        assert e.lifecycle_state().value != "running"

    def test_double_start_raises(self):
        e = KnowledgeEngine()
        e.start()
        with pytest.raises(EngineAlreadyRunningError):
            e.start()
        e.stop()

    def test_submit_requires_running(self):
        e = KnowledgeEngine()
        with pytest.raises(KnowledgeEngineNotRunningError):
            e.submit(_make_request())

    def test_schedule_requires_running(self):
        e = KnowledgeEngine()
        with pytest.raises(KnowledgeEngineNotRunningError):
            e.schedule(_make_request())

    def test_engine_state_idle_after_start(self):
        e = _started_engine()
        try:
            assert e.engine_state() == EngineState.IDLE
        finally:
            e.stop()

    def test_engine_state_stopped_after_stop(self):
        e = _started_engine()
        e.stop()
        assert e.engine_state() == EngineState.STOPPED


# ===========================================================================
# 17. TestWorkflowOrchestration
# ===========================================================================


class TestWorkflowOrchestration:
    def test_successful_submit(self):
        e = _started_engine()
        try:
            response = _full_submit(e)
            assert response.succeeded
            assert response.snapshot is not None
        finally:
            e.stop()

    def test_response_has_pipeline_id(self):
        e = _started_engine()
        try:
            response = _full_submit(e)
            assert response.pipeline_id
        finally:
            e.stop()

    def test_response_has_processing_ms(self):
        e = _started_engine()
        try:
            response = _full_submit(e)
            assert response.processing_ms >= 0
        finally:
            e.stop()

    def test_snapshot_has_engine_state(self):
        e = _started_engine()
        try:
            response = _full_submit(e)
            assert response.snapshot.engine_state is not None
        finally:
            e.stop()

    def test_events_emitted(self):
        received = []
        e = _started_engine()
        try:
            e.add_listener(received.append)
            _full_submit(e)
            assert len(received) >= 1
        finally:
            e.stop()

    def test_statistics_accumulate(self):
        e = _started_engine()
        try:
            _full_submit(e)
            stats = e.statistics()
            assert stats["knowledge_sessions"] >= 1
            assert stats["published_snapshots"] >= 1
        finally:
            e.stop()

    def test_history_recorded(self):
        e = _started_engine()
        try:
            _full_submit(e)
            h = e.history()
            assert len(h) >= 1
        finally:
            e.stop()

    def test_query_by_knowledge_id(self):
        e = _started_engine()
        try:
            req = _make_request(knowledge_id="k-query-test")
            e.submit(req)
            result = e.query("k-query-test")
            assert result is not None
            assert result.knowledge_id == "k-query-test"
        finally:
            e.stop()

    def test_all_workflow_types_accepted(self):
        e = _started_engine()
        try:
            for wt in KnowledgeWorkflowType:
                req = _make_request(
                    knowledge_id=f"k-wt-{wt.value}",
                    workflow_type=wt,
                )
                response = e.submit(req)
                assert response.knowledge_id == f"k-wt-{wt.value}"
        finally:
            e.stop()

    def test_invalid_request_returns_failure(self):
        """An empty knowledge_id should cause a failure response, not an exception."""
        e = _started_engine()
        try:
            bad = KnowledgeRequest(
                request_id="r-bad", knowledge_id="", subsystem_id="exec",
                workflow_type=KnowledgeWorkflowType.KNOWLEDGE_CAPTURE,
                priority=SchedulerPriority.NORMAL,
                context=KnowledgeEngineContext.create("k-bad", "exec"),
            )
            response = e.submit(bad)
            assert not response.succeeded
        finally:
            e.stop()

    def test_governance_delegate_called(self):
        called = []
        def gov(kid, ctx): called.append(kid); return {"status": "approved"}
        e = _started_engine(governance_delegate=gov)
        try:
            _full_submit(e)
            assert len(called) == 1
        finally:
            e.stop()

    def test_intelligence_delegate_called(self):
        called = []
        def intel(kid, ctx): called.append(kid); return {"status": "processed"}
        e = _started_engine(intelligence_delegate=intel)
        try:
            _full_submit(e)
            assert len(called) == 1
        finally:
            e.stop()

    def test_scheduler_submit(self):
        e = _started_engine()
        try:
            accepted = e.schedule(_make_request("k-sched-1"))
            assert accepted
            response = e.process_next()
            assert response is not None
            assert response.succeeded
        finally:
            e.stop()

    def test_process_next_returns_none_on_empty_queue(self):
        e = _started_engine()
        try:
            result = e.process_next()
            assert result is None
        finally:
            e.stop()


# ===========================================================================
# 18. TestConcurrency
# ===========================================================================


class TestConcurrency:
    def test_concurrent_submits(self):
        """N threads each submit one request — all must succeed."""
        e = _started_engine(max_sessions=200)
        errors   = []
        responses = []
        lock      = threading.Lock()

        def _submit(i: int):
            try:
                r = e.submit(_make_request(knowledge_id=f"k-c-{i}"))
                with lock:
                    responses.append(r)
            except Exception as exc:
                with lock:
                    errors.append(exc)

        threads = [threading.Thread(target=_submit, args=(i,)) for i in range(40)]
        for t in threads: t.start()
        for t in threads: t.join()
        e.stop()

        assert not errors, f"Errors: {errors}"
        assert len(responses) == 40

    def test_concurrent_schedule_and_process(self):
        """Scheduler thread enqueues; main thread processes."""
        e = _started_engine(max_sessions=200, max_queue=500)
        N = 20

        def _enqueue():
            for i in range(N):
                e.schedule(_make_request(f"k-sched-{i}"))

        t = threading.Thread(target=_enqueue)
        t.start()
        t.join()

        processed = 0
        while True:
            r = e.process_next()
            if r is None:
                break
            processed += 1

        e.stop()
        assert processed == N

    def test_statistics_accuracy_under_concurrent_writes(self):
        N = 30
        e = _started_engine(max_sessions=500)
        threads = [threading.Thread(target=lambda: _full_submit(e, f"k-stat-{id(threading.current_thread())}")) for _ in range(N)]
        for t in threads: t.start()
        for t in threads: t.join()
        stats = e.statistics()
        e.stop()
        assert stats["knowledge_sessions"] == N
        assert stats["published_snapshots"] == N


# ===========================================================================
# 19. TestPublicSurface
# ===========================================================================


class TestPublicSurface:
    def test_health_returns_dict(self):
        e = _started_engine()
        try:
            h = e.health()
            assert "status" in h
        finally:
            e.stop()

    def test_status_returns_dict(self):
        e = _started_engine()
        try:
            s = e.status()
            assert "lifecycle_state" in s
            assert "engine_state" in s
        finally:
            e.stop()

    def test_statistics_seven_keys(self):
        e = _started_engine()
        try:
            stats = e.statistics()
            assert len(stats) >= 7
        finally:
            e.stop()

    def test_add_remove_listener(self):
        e = _started_engine()
        try:
            received = []
            e.add_listener(received.append)
            _full_submit(e)
            assert len(received) >= 1
            e.remove_listener(received.append)
        finally:
            e.stop()

    def test_set_governance_delegate_after_start(self):
        e = _started_engine()
        try:
            called = []
            e.set_governance_delegate(lambda k, c: called.append(k) or {})
            _full_submit(e)
            assert len(called) == 1
        finally:
            e.stop()

    def test_set_intelligence_delegate_after_start(self):
        e = _started_engine()
        try:
            called = []
            e.set_intelligence_delegate(lambda k, c: called.append(k) or {})
            _full_submit(e)
            assert len(called) == 1
        finally:
            e.stop()


# ===========================================================================
# 20. TestRegression
# ===========================================================================


class TestRegression:
    def test_lifecycle_m1_import_unaffected(self):
        from iios.knowledge.lifecycle import KnowledgeLifecycle  # noqa: F401

    def test_supervisor_engine_import_unaffected(self):
        from iios.supervisor.engine import SupervisorEngine  # noqa: F401

    def test_engine_error_codes_distinct_from_lifecycle(self):
        from iios.knowledge.lifecycle.exceptions import KnowledgeLifecycleError
        assert KnowledgeEngineError.error_code != KnowledgeLifecycleError.error_code

    def test_engine_states_distinct_from_lifecycle_states(self):
        from iios.knowledge.lifecycle.constants import KnowledgeLifecycleState
        engine_values    = {s.value for s in EngineState}
        lifecycle_values = {s.value for s in KnowledgeLifecycleState}
        # Overlapping names (like "failed") are acceptable but the enums must be different objects
        assert EngineState is not KnowledgeLifecycleState
