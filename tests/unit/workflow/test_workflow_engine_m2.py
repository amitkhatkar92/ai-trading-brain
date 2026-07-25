"""
test_workflow_engine_m2.py — C16 M2: Workflow Engine

Comprehensive test suite for iios.workflow.engine.
Coverage target: 95%+

Test groups:
  - Engine lifecycle (initialize, stop, restart)
  - Request / Response / Context
  - Priority and Queue
  - Scheduler
  - Pipeline orchestration
  - Dispatcher
  - Session manager
  - Validation
  - Statistics
  - History
  - Registry
  - Monitor
  - Events
  - Health / Status
  - Factory
  - Manager (top-level API)
  - Batch execution
  - Concurrency
  - Edge cases
  - Regression
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import List, Optional

import pytest

from iios.workflow.engine import (
    ACTOR_ENGINE,
    ACTOR_MONITOR,
    ACTOR_SCHEDULER,
    ACTOR_SYSTEM,
    BUILD_VERSION,
    DEFAULT_ENGINE_ID,
    DEFAULT_MAX_HISTORY,
    DEFAULT_PRIORITY,
    DEFAULT_QUEUE_SIZE,
    PIPELINE_STAGE_ORDER,
    VERSION,
    ActiveWorkflowRecord,
    PipelineExecution,
    PriorityWorkflowItem,
    ScheduledWorkflowJob,
    WorkflowDispatchMode,
    WorkflowDispatcher,
    WorkflowEngine,
    WorkflowEngineContext,
    WorkflowEngineEvent,
    WorkflowEngineEventBus,
    WorkflowEngineEventType,
    WorkflowEngineFactory,
    WorkflowEngineHealth,
    WorkflowEngineHistory,
    WorkflowEngineNotReadyError,
    WorkflowEngineOperation,
    WorkflowEngineRegistry,
    WorkflowEngineResponseStatus,
    WorkflowEngineState,
    WorkflowEngineStatistics,
    WorkflowEngineStatusTracker,
    WorkflowEngineValidationCheck,
    WorkflowEngineValidator,
    WorkflowManager,
    WorkflowMonitor,
    WorkflowPipeline,
    WorkflowPipelineError,
    WorkflowPipelineStage,
    WorkflowQueue,
    WorkflowQueueCapacityError,
    WorkflowQueuePriority,
    WorkflowRequestValidationError,
    WorkflowScheduler,
    WorkflowSessionManager,
    priority_label,
)
from iios.workflow.engine.exceptions import (
    WorkflowEngineError,
    WorkflowGovernanceError,
    WorkflowMonitorError,
    WorkflowOrchestrationError,
    WorkflowSchedulerError,
    WorkflowSessionError,
)
from iios.workflow.engine.workflow_engine import WorkflowEngine
from iios.workflow.engine.workflow_request import WorkflowEngineRequest
from iios.workflow.engine.workflow_response import WorkflowEngineResponse
from iios.workflow.lifecycle import WorkflowType


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def make_request(
    workflow_id:   str                         = "wf-test-001",
    workflow_type: WorkflowType                = WorkflowType.SEQUENTIAL,
    dispatch_mode: WorkflowDispatchMode        = WorkflowDispatchMode.IMMEDIATE,
    priority:      int                         = DEFAULT_PRIORITY,
    correlation_id: Optional[str]              = None,
    trace_id:       Optional[str]              = None,
) -> WorkflowEngineRequest:
    return WorkflowEngineRequest.create(
        workflow_id    = workflow_id,
        workflow_type  = workflow_type,
        dispatch_mode  = dispatch_mode,
        priority       = priority,
        correlation_id = correlation_id,
        trace_id       = trace_id,
    )


def make_manager(engine_id: str = DEFAULT_ENGINE_ID) -> WorkflowManager:
    m = WorkflowManager(engine_id=engine_id)
    m.start()
    return m


# ─────────────────────────────────────────────────────────────────────────────
# 1. Constants
# ─────────────────────────────────────────────────────────────────────────────

class TestConstants:
    def test_version(self):
        assert VERSION == "1.0.0"

    def test_build_version(self):
        assert BUILD_VERSION == "c16-m2"

    def test_default_engine_id(self):
        assert DEFAULT_ENGINE_ID == "iios-workflow-engine"

    def test_default_queue_size(self):
        assert DEFAULT_QUEUE_SIZE == 10_000

    def test_pipeline_stage_order_length(self):
        assert len(PIPELINE_STAGE_ORDER) == 8

    def test_actor_names(self):
        assert ACTOR_ENGINE == "workflow-engine"
        assert ACTOR_SCHEDULER == "workflow-scheduler"
        assert ACTOR_SYSTEM == "workflow-system"
        assert ACTOR_MONITOR == "workflow-monitor"

    def test_engine_states(self):
        states = [s.value for s in WorkflowEngineState]
        assert "idle" in states
        assert "stopped" in states
        assert "failed" in states

    def test_event_types(self):
        assert len(WorkflowEngineEventType) == 9

    def test_dispatch_modes(self):
        assert len(WorkflowDispatchMode) == 6

    def test_queue_priority_ordering(self):
        assert WorkflowQueuePriority.CRITICAL < WorkflowQueuePriority.HIGH
        assert WorkflowQueuePriority.HIGH < WorkflowQueuePriority.NORMAL
        assert WorkflowQueuePriority.NORMAL < WorkflowQueuePriority.LOW

    def test_validation_checks(self):
        assert len(WorkflowEngineValidationCheck) == 6


# ─────────────────────────────────────────────────────────────────────────────
# 2. Exceptions
# ─────────────────────────────────────────────────────────────────────────────

class TestExceptions:
    def test_base_error(self):
        e = WorkflowEngineError("boom")
        assert "WEN-000" in str(e)

    def test_not_ready(self):
        e = WorkflowEngineNotReadyError("engine stopped")
        assert "WEN-001" in str(e)

    def test_validation_error_with_checks(self):
        e = WorkflowRequestValidationError("bad", failed_checks=["QUEUE_CONSISTENCY"])
        assert "WEN-002" in str(e)
        assert e.failed_checks == ["QUEUE_CONSISTENCY"]

    def test_session_error(self):
        e = WorkflowSessionError("sess fail")
        assert "WEN-003" in str(e)

    def test_capacity_error(self):
        e = WorkflowQueueCapacityError("full", limit=100)
        assert "WEN-004" in str(e)
        assert e.limit == 100

    def test_dispatch_error(self):
        from iios.workflow.engine.exceptions import WorkflowDispatchError
        e = WorkflowDispatchError("dispatch fail")
        assert "WEN-005" in str(e)

    def test_scheduler_error(self):
        e = WorkflowSchedulerError("sched fail")
        assert "WEN-006" in str(e)

    def test_pipeline_error(self):
        e = WorkflowPipelineError("pipe fail")
        assert "WEN-007" in str(e)

    def test_monitor_error(self):
        e = WorkflowMonitorError("mon fail")
        assert "WEN-008" in str(e)

    def test_governance_error(self):
        e = WorkflowGovernanceError("gov fail")
        assert "WEN-009" in str(e)

    def test_orchestration_error(self):
        e = WorkflowOrchestrationError("orch fail")
        assert "WEN-010" in str(e)

    def test_inheritance(self):
        from iios.common.errors.exceptions import IIOSError
        assert issubclass(WorkflowEngineError, IIOSError)


# ─────────────────────────────────────────────────────────────────────────────
# 3. WorkflowEngineRequest
# ─────────────────────────────────────────────────────────────────────────────

class TestWorkflowEngineRequest:
    def test_create_defaults(self):
        req = make_request()
        assert req.request_id.startswith("wenreq-")
        assert req.workflow_id == "wf-test-001"
        assert req.priority == DEFAULT_PRIORITY
        assert req.enterprise_id == "iios"

    def test_frozen(self):
        req = make_request()
        with pytest.raises((AttributeError, TypeError)):
            req.workflow_id = "x"  # type: ignore

    def test_priority_clamped(self):
        req = WorkflowEngineRequest.create(
            workflow_id="x", workflow_type=WorkflowType.SEQUENTIAL,
            dispatch_mode=WorkflowDispatchMode.IMMEDIATE,
            priority=99,
        )
        assert req.priority == 3

    def test_priority_negative_clamped(self):
        req = WorkflowEngineRequest.create(
            workflow_id="x", workflow_type=WorkflowType.SEQUENTIAL,
            dispatch_mode=WorkflowDispatchMode.IMMEDIATE,
            priority=-5,
        )
        assert req.priority == 0

    def test_dispatch_properties_immediate(self):
        req = make_request(dispatch_mode=WorkflowDispatchMode.IMMEDIATE)
        assert req.is_immediate
        assert not req.is_scheduled

    def test_dispatch_properties_scheduled(self):
        req = make_request(dispatch_mode=WorkflowDispatchMode.SCHEDULED)
        assert req.is_scheduled
        assert not req.is_immediate

    def test_dispatch_properties_batch(self):
        req = make_request(dispatch_mode=WorkflowDispatchMode.BATCH)
        assert req.is_batch

    def test_dispatch_properties_retry(self):
        req = make_request(dispatch_mode=WorkflowDispatchMode.RETRY)
        assert req.is_retry

    def test_dispatch_properties_event_driven(self):
        req = make_request(dispatch_mode=WorkflowDispatchMode.EVENT_DRIVEN)
        assert req.is_event_driven

    def test_to_dict(self):
        req = make_request()
        d = req.to_dict()
        assert "request_id" in d
        assert d["workflow_id"] == "wf-test-001"

    def test_from_dict_roundtrip(self):
        req = make_request()
        d = req.to_dict()
        req2 = WorkflowEngineRequest.from_dict(d)
        assert req2.request_id == req.request_id
        assert req2.workflow_id == req.workflow_id

    def test_unique_ids(self):
        ids = {make_request().request_id for _ in range(100)}
        assert len(ids) == 100


# ─────────────────────────────────────────────────────────────────────────────
# 4. WorkflowEngineResponse
# ─────────────────────────────────────────────────────────────────────────────

class TestWorkflowEngineResponse:
    def test_success_response(self):
        req = make_request()
        resp = WorkflowEngineResponse.success_for(req, "sess-1")
        assert resp.is_success
        assert not resp.is_failure
        assert resp.response_id.startswith("wenresp-")
        assert resp.request_id == req.request_id

    def test_failure_response(self):
        req = make_request()
        resp = WorkflowEngineResponse.failure_for(req, "sess-1", "boom")
        assert resp.is_failure
        assert resp.error_message == "boom"

    def test_cancelled_response(self):
        req = make_request()
        resp = WorkflowEngineResponse.cancelled_for(req, "sess-1")
        assert resp.is_cancelled

    def test_has_snapshot(self):
        req = make_request()
        resp = WorkflowEngineResponse.success_for(req, "s", snapshot_id="snap-1")
        assert resp.has_snapshot

    def test_frozen(self):
        req = make_request()
        resp = WorkflowEngineResponse.success_for(req, "s")
        with pytest.raises((AttributeError, TypeError)):
            resp.status = WorkflowEngineResponseStatus.FAILED  # type: ignore

    def test_to_dict(self):
        req = make_request()
        resp = WorkflowEngineResponse.success_for(req, "s")
        d = resp.to_dict()
        assert d["is_success"] is True


# ─────────────────────────────────────────────────────────────────────────────
# 5. WorkflowEngineContext
# ─────────────────────────────────────────────────────────────────────────────

class TestWorkflowEngineContext:
    def test_create(self):
        req = make_request()
        ctx = WorkflowEngineContext.create(req, "sess-42", engine_id="eng-1")
        assert ctx.context_id.startswith("wenctx-")
        assert ctx.request_id == req.request_id
        assert ctx.session_id == "sess-42"
        assert ctx.engine_id == "eng-1"
        assert ctx.workflow_id == req.workflow_id

    def test_frozen(self):
        req = make_request()
        ctx = WorkflowEngineContext.create(req, "s", engine_id="e")
        with pytest.raises((AttributeError, TypeError)):
            ctx.engine_id = "x"  # type: ignore


# ─────────────────────────────────────────────────────────────────────────────
# 6. WorkflowEngineEvent and EventBus
# ─────────────────────────────────────────────────────────────────────────────

class TestEventBus:
    def test_emit_and_receive(self):
        bus = WorkflowEngineEventBus()
        received: List[WorkflowEngineEvent] = []
        bus.add_listener(WorkflowEngineEventType.WORKFLOW_COMPLETED, received.append)
        bus.emit(WorkflowEngineEventType.WORKFLOW_COMPLETED, "eng", "req", "sess")
        assert len(received) == 1
        assert received[0].event_type == WorkflowEngineEventType.WORKFLOW_COMPLETED
        assert received[0].engine_id == "eng"

    def test_listener_count(self):
        bus = WorkflowEngineEventBus()
        f = lambda e: None
        bus.add_listener(WorkflowEngineEventType.WORKFLOW_FAILED, f)
        assert bus.listener_count(WorkflowEngineEventType.WORKFLOW_FAILED) == 1

    def test_remove_listener(self):
        bus = WorkflowEngineEventBus()
        f = lambda e: None
        bus.add_listener(WorkflowEngineEventType.WORKFLOW_COMPLETED, f)
        bus.remove_listener(WorkflowEngineEventType.WORKFLOW_COMPLETED, f)
        assert bus.listener_count(WorkflowEngineEventType.WORKFLOW_COMPLETED) == 0

    def test_clear_listeners(self):
        bus = WorkflowEngineEventBus()
        bus.add_listener(WorkflowEngineEventType.WORKFLOW_FAILED, lambda e: None)
        bus.clear()
        assert bus.listener_count(WorkflowEngineEventType.WORKFLOW_FAILED) == 0

    def test_event_id_prefix(self):
        bus = WorkflowEngineEventBus()
        received: List[WorkflowEngineEvent] = []
        bus.add_listener(WorkflowEngineEventType.WORKFLOW_STARTED, received.append)
        bus.emit(WorkflowEngineEventType.WORKFLOW_STARTED, "e", "r", "s")
        assert received[0].event_id.startswith("wevt-")

    def test_listener_exception_does_not_propagate(self):
        bus = WorkflowEngineEventBus()
        def bad(e): raise RuntimeError("crash")
        bus.add_listener(WorkflowEngineEventType.WORKFLOW_COMPLETED, bad)
        bus.emit(WorkflowEngineEventType.WORKFLOW_COMPLETED, "e", "r", "s")  # should not raise

    def test_multiple_listeners(self):
        bus = WorkflowEngineEventBus()
        hits: List[str] = []
        bus.add_listener(WorkflowEngineEventType.WORKFLOW_COMPLETED, lambda e: hits.append("a"))
        bus.add_listener(WorkflowEngineEventType.WORKFLOW_COMPLETED, lambda e: hits.append("b"))
        bus.emit(WorkflowEngineEventType.WORKFLOW_COMPLETED, "e", "r", "s")
        assert set(hits) == {"a", "b"}


# ─────────────────────────────────────────────────────────────────────────────
# 7. Priority helpers
# ─────────────────────────────────────────────────────────────────────────────

class TestPriority:
    def test_priority_label_critical(self):
        assert priority_label(0) == "CRITICAL"

    def test_priority_label_high(self):
        assert priority_label(1) == "HIGH"

    def test_priority_label_normal(self):
        assert priority_label(2) == "NORMAL"

    def test_priority_label_low(self):
        assert priority_label(3) == "LOW"

    def test_priority_label_unknown(self):
        assert priority_label(99) == "UNKNOWN"

    def test_priority_item_ordering(self):
        req_a = make_request(priority=1)
        req_b = make_request(priority=3)
        a = PriorityWorkflowItem.create(req_a, 0, priority=1)
        b = PriorityWorkflowItem.create(req_b, 1, priority=3)
        assert a < b   # CRITICAL/HIGH < LOW

    def test_priority_item_id_prefix(self):
        req = make_request()
        item = PriorityWorkflowItem.create(req, 0, priority=2)
        assert item.item_id.startswith("wqi-")


# ─────────────────────────────────────────────────────────────────────────────
# 8. WorkflowQueue
# ─────────────────────────────────────────────────────────────────────────────

class TestWorkflowQueue:
    def test_enqueue_dequeue(self):
        q = WorkflowQueue(max_size=10)
        req = make_request()
        item = PriorityWorkflowItem.create(req, 0, priority=2)
        q.enqueue(item)
        assert q.size() == 1
        out = q.dequeue()
        assert out is not None
        assert out.request.request_id == req.request_id

    def test_capacity_error(self):
        q = WorkflowQueue(max_size=2)
        for i in range(2):
            req = make_request(workflow_id=f"wf-{i}")
            q.enqueue(PriorityWorkflowItem.create(req, i, priority=2))
        with pytest.raises(WorkflowQueueCapacityError):
            req = make_request(workflow_id="wf-extra")
            q.enqueue(PriorityWorkflowItem.create(req, 99, priority=2))

    def test_empty_dequeue_returns_none(self):
        q = WorkflowQueue()
        assert q.dequeue() is None

    def test_priority_ordering(self):
        q = WorkflowQueue()
        req_low  = make_request(workflow_id="wf-low",  priority=3)
        req_high = make_request(workflow_id="wf-high", priority=0)
        q.enqueue(PriorityWorkflowItem.create(req_low,  0, priority=3))
        q.enqueue(PriorityWorkflowItem.create(req_high, 1, priority=0))
        out = q.dequeue()
        assert out.request.priority == 0   # CRITICAL first

    def test_cancel(self):
        q = WorkflowQueue()
        req = make_request()
        item = PriorityWorkflowItem.create(req, 0, priority=2)
        q.enqueue(item)
        assert q.cancel(item.item_id)
        out = q.dequeue()
        assert out is None   # cancelled item skipped

    def test_cancel_nonexistent(self):
        q = WorkflowQueue()
        assert not q.cancel("nonexistent-id")

    def test_peek(self):
        q = WorkflowQueue()
        req = make_request()
        item = PriorityWorkflowItem.create(req, 0, priority=2)
        q.enqueue(item)
        peeked = q.peek()
        assert peeked.item_id == item.item_id
        assert q.size() == 1   # still in queue

    def test_is_empty(self):
        q = WorkflowQueue()
        assert q.is_empty()
        req = make_request()
        q.enqueue(PriorityWorkflowItem.create(req, 0, priority=2))
        assert not q.is_empty()

    def test_clear(self):
        q = WorkflowQueue()
        for i in range(5):
            req = make_request(workflow_id=f"wf-{i}")
            q.enqueue(PriorityWorkflowItem.create(req, i, priority=2))
        q.clear()
        assert q.size() == 0
        assert q.is_empty()

    def test_max_size_property(self):
        q = WorkflowQueue(max_size=500)
        assert q.max_size == 500


# ─────────────────────────────────────────────────────────────────────────────
# 9. WorkflowScheduler
# ─────────────────────────────────────────────────────────────────────────────

class TestWorkflowScheduler:
    def test_schedule_returns_job(self):
        s = WorkflowScheduler()
        req = make_request()
        job = s.schedule(req)
        assert isinstance(job, ScheduledWorkflowJob)
        assert job.job_id.startswith("wsj-")

    def test_next_returns_job(self):
        s = WorkflowScheduler()
        req = make_request()
        s.schedule(req)
        job = s.next()
        assert job is not None
        assert isinstance(job, ScheduledWorkflowJob)
        assert job.request.request_id == req.request_id

    def test_next_empty_returns_none(self):
        s = WorkflowScheduler()
        assert s.next() is None

    def test_cancel_job(self):
        s = WorkflowScheduler()
        req = make_request()
        job = s.schedule(req)
        assert s.cancel_job(job.job_id)
        assert s.next() is None

    def test_queue_size(self):
        s = WorkflowScheduler()
        for i in range(3):
            s.schedule(make_request(workflow_id=f"wf-{i}"))
        assert s.queue_size() == 3

    def test_is_empty(self):
        s = WorkflowScheduler()
        assert s.is_empty()
        s.schedule(make_request())
        assert not s.is_empty()

    def test_list_jobs(self):
        s = WorkflowScheduler()
        s.schedule(make_request(workflow_id="wf-a"))
        s.schedule(make_request(workflow_id="wf-b"))
        jobs = s.list_jobs()
        assert len(jobs) == 2
        assert all(isinstance(j, ScheduledWorkflowJob) for j in jobs)


# ─────────────────────────────────────────────────────────────────────────────
# 10. WorkflowPipeline
# ─────────────────────────────────────────────────────────────────────────────

class TestWorkflowPipeline:
    def test_execute_empty_handlers(self):
        pipeline = WorkflowPipeline()
        req = make_request()
        ctx = WorkflowEngineContext.create(req, "sess", engine_id="e")
        result = pipeline.execute(req, ctx)
        assert isinstance(result, PipelineExecution)
        assert result.success
        assert len(result.completed_stages) == 8

    def test_register_and_invoke_handler(self):
        pipeline = WorkflowPipeline()
        calls: List[str] = []
        def my_handler(req, ctx, exec):
            calls.append("invoked")
            return "ok"
        pipeline.register_handler(WorkflowPipelineStage.DISPATCH, my_handler)
        req = make_request()
        ctx = WorkflowEngineContext.create(req, "s", engine_id="e")
        result = pipeline.execute(req, ctx)
        assert "invoked" in calls
        assert result.stage_results.get("dispatch") == "ok"

    def test_stage_failure_stops_pipeline(self):
        pipeline = WorkflowPipeline()
        def bad_handler(req, ctx, exec):
            raise RuntimeError("stage boom")
        pipeline.register_handler(WorkflowPipelineStage.INITIALIZE, bad_handler)
        req = make_request()
        ctx = WorkflowEngineContext.create(req, "s", engine_id="e")
        result = pipeline.execute(req, ctx)
        assert not result.success
        assert result.failed_stage == "initialize"

    def test_registered_stages(self):
        pipeline = WorkflowPipeline()
        pipeline.register_handler(WorkflowPipelineStage.GOVERN, lambda r, c, e: None)
        assert WorkflowPipelineStage.GOVERN in pipeline.registered_stages()

    def test_stage_count(self):
        pipeline = WorkflowPipeline()
        assert pipeline.stage_count() == 0
        pipeline.register_handler(WorkflowPipelineStage.DISPATCH, lambda r, c, e: None)
        assert pipeline.stage_count() == 1

    def test_pipeline_execution_to_dict(self):
        pipeline = WorkflowPipeline()
        req = make_request()
        ctx = WorkflowEngineContext.create(req, "s", engine_id="e")
        result = pipeline.execute(req, ctx)
        d = result.to_dict()
        assert "execution_id" in d
        assert d["success"] is True


# ─────────────────────────────────────────────────────────────────────────────
# 11. WorkflowDispatcher
# ─────────────────────────────────────────────────────────────────────────────

class TestWorkflowDispatcher:
    def test_dispatch_returns_execution(self):
        d = WorkflowDispatcher()
        req = make_request()
        ctx = WorkflowEngineContext.create(req, "s", engine_id="e")
        result = d.dispatch(req, ctx)
        assert result.success

    def test_dispatch_batch(self):
        d = WorkflowDispatcher()
        results = []
        for i in range(3):
            req = make_request(workflow_id=f"wf-{i}")
            ctx = WorkflowEngineContext.create(req, f"sess-{i}", engine_id="e")
            results.append(d.dispatch(req, ctx))
        assert all(r.success for r in results)

    def test_pipeline_accessible(self):
        d = WorkflowDispatcher()
        assert isinstance(d.pipeline(), WorkflowPipeline)


# ─────────────────────────────────────────────────────────────────────────────
# 12. WorkflowSessionManager
# ─────────────────────────────────────────────────────────────────────────────

class TestWorkflowSessionManager:
    def test_create_session(self):
        mgr = WorkflowSessionManager(engine_id="test-eng")
        session_id = mgr.create_session("wf-001")
        assert session_id is not None
        assert len(session_id) > 0

    def test_lifecycle_walk(self):
        mgr = WorkflowSessionManager(engine_id="test-eng")
        session_id = mgr.create_session("wf-001")
        mgr.initialize_session(session_id)
        mgr.validate_session(session_id)
        mgr.mark_ready(session_id)
        mgr.start_session(session_id)
        mgr.complete_session(session_id)
        assert session_id not in mgr.active_session_ids()

    def test_fail_session(self):
        mgr = WorkflowSessionManager(engine_id="test-eng")
        session_id = mgr.create_session("wf-001")
        mgr.initialize_session(session_id)
        mgr.validate_session(session_id)
        mgr.mark_ready(session_id)
        mgr.start_session(session_id)
        mgr.fail_session(session_id, reason="boom")
        assert session_id not in mgr.active_session_ids()

    def test_cancel_session(self):
        mgr = WorkflowSessionManager(engine_id="test-eng")
        session_id = mgr.create_session("wf-001")
        mgr.initialize_session(session_id)
        mgr.cancel_session(session_id, reason="user cancelled")
        # should not raise

    def test_active_count(self):
        mgr = WorkflowSessionManager(engine_id="test-eng")
        assert mgr.active_count() == 0
        sess = mgr.create_session("wf-001")
        mgr.initialize_session(sess)
        mgr.validate_session(sess)
        mgr.mark_ready(sess)
        mgr.start_session(sess)
        assert mgr.active_count() == 1


# ─────────────────────────────────────────────────────────────────────────────
# 13. WorkflowEngineRegistry
# ─────────────────────────────────────────────────────────────────────────────

class TestWorkflowEngineRegistry:
    def test_register_and_lookup(self):
        reg = WorkflowEngineRegistry()
        req = make_request()
        reg.register(req, "sess-1")
        assert reg.exists(req.request_id)
        assert reg.get_session_id(req.request_id) == "sess-1"

    def test_record_response(self):
        reg = WorkflowEngineRegistry()
        req = make_request()
        reg.register(req, "sess-1")
        resp = WorkflowEngineResponse.success_for(req, "sess-1")
        reg.record_response(req.request_id, resp)
        assert reg.get_response(req.request_id) is not None

    def test_deregister(self):
        reg = WorkflowEngineRegistry()
        req = make_request()
        reg.register(req, "sess-1")
        reg.deregister(req.request_id)
        assert not reg.exists(req.request_id)

    def test_active_count(self):
        reg = WorkflowEngineRegistry()
        for i in range(5):
            reg.register(make_request(workflow_id=f"wf-{i}"), f"sess-{i}")
        assert reg.active_count() == 5

    def test_clear(self):
        reg = WorkflowEngineRegistry()
        reg.register(make_request(), "s")
        reg.clear()
        assert reg.active_count() == 0


# ─────────────────────────────────────────────────────────────────────────────
# 14. WorkflowEngineValidator
# ─────────────────────────────────────────────────────────────────────────────

class TestWorkflowEngineValidator:
    def test_valid_request(self):
        v = WorkflowEngineValidator()
        req = make_request()
        report = v.validate(req)
        assert report.passed
        assert report.failed_checks == []

    def test_empty_workflow_id_fails(self):
        v = WorkflowEngineValidator()
        req = WorkflowEngineRequest.create(
            workflow_id="",
            workflow_type=WorkflowType.SEQUENTIAL,
            dispatch_mode=WorkflowDispatchMode.IMMEDIATE,
        )
        report = v.validate(req)
        assert not report.passed
        assert WorkflowEngineValidationCheck.WORKFLOW_CONFIGURATION.value in report.failed_checks

    def test_empty_correlation_fails(self):
        import dataclasses
        v = WorkflowEngineValidator()
        # Direct construction bypasses create()'s auto-generation
        base = make_request()
        req = dataclasses.replace(base, correlation_id="")
        report = v.validate(req)
        assert not report.passed
        assert WorkflowEngineValidationCheck.INPUT_COMPLETENESS.value in report.failed_checks

    def test_to_dict(self):
        v = WorkflowEngineValidator()
        report = v.validate(make_request())
        d = report.to_dict()
        assert "passed" in d
        assert "failed_checks" in d
        assert "results" in d


# ─────────────────────────────────────────────────────────────────────────────
# 15. WorkflowEngineHealth
# ─────────────────────────────────────────────────────────────────────────────

class TestWorkflowEngineHealth:
    def test_healthy_state(self):
        h = WorkflowEngineHealth()
        report = h.report(
            WorkflowEngineState.IDLE,
            active_requests=0,
            queue_size=0,
            started_at=time.monotonic() - 10,
        )
        assert report.is_healthy
        assert report.uptime_seconds >= 10

    def test_unhealthy_stopped(self):
        h = WorkflowEngineHealth()
        report = h.report(
            WorkflowEngineState.STOPPED,
            active_requests=0,
            queue_size=0,
            started_at=time.monotonic(),
        )
        assert report.is_unhealthy

    def test_unhealthy_failed(self):
        h = WorkflowEngineHealth()
        report = h.report(
            WorkflowEngineState.FAILED,
            active_requests=0,
            queue_size=0,
            started_at=time.monotonic(),
        )
        assert report.is_unhealthy

    def test_degraded_near_capacity(self):
        h = WorkflowEngineHealth()
        report = h.report(
            WorkflowEngineState.IDLE,
            active_requests=0,
            queue_size=int(DEFAULT_QUEUE_SIZE * 0.95),
            started_at=time.monotonic(),
        )
        assert report.is_degraded

    def test_to_dict(self):
        h = WorkflowEngineHealth()
        report = h.report(WorkflowEngineState.IDLE, 0, 0, time.monotonic())
        d = report.to_dict()
        assert "status" in d
        assert "engine_state" in d


# ─────────────────────────────────────────────────────────────────────────────
# 16. WorkflowEngineStatusTracker
# ─────────────────────────────────────────────────────────────────────────────

class TestWorkflowEngineStatusTracker:
    def test_capture(self):
        tracker = WorkflowEngineStatusTracker()
        status = tracker.capture(
            engine_id       = "test",
            state           = WorkflowEngineState.IDLE,
            active_requests = 2,
            queue_size      = 5,
            sessions_active = 3,
            started_at      = time.monotonic() - 60,
        )
        assert status.engine_id == "test"
        assert status.state == WorkflowEngineState.IDLE
        assert status.active_requests == 2
        assert status.uptime_seconds >= 60

    def test_to_dict(self):
        tracker = WorkflowEngineStatusTracker()
        status = tracker.capture("e", WorkflowEngineState.IDLE, 0, 0, 0, time.monotonic())
        d = status.to_dict()
        assert "engine_id" in d
        assert "state" in d


# ─────────────────────────────────────────────────────────────────────────────
# 17. WorkflowEngineStatistics
# ─────────────────────────────────────────────────────────────────────────────

class TestWorkflowEngineStatistics:
    def test_initial_report(self):
        stats = WorkflowEngineStatistics()
        report = stats.report()
        assert report.workflows_executed == 0
        assert report.workflow_availability == 1.0

    def test_record_executed(self):
        stats = WorkflowEngineStatistics()
        stats.record_executed()
        assert stats.report().workflows_executed == 1

    def test_record_completed(self):
        stats = WorkflowEngineStatistics()
        stats.record_completed(runtime_ms=100)
        report = stats.report()
        assert report.workflows_completed == 1
        assert report.average_runtime_ms == 100

    def test_record_failed(self):
        stats = WorkflowEngineStatistics()
        stats.record_failed()
        assert stats.report().workflows_failed == 1

    def test_availability_calculation(self):
        stats = WorkflowEngineStatistics()
        stats.record_completed()
        stats.record_completed()
        stats.record_failed()
        report = stats.report()
        assert abs(report.workflow_availability - 2/3) < 0.001

    def test_record_queue_time(self):
        stats = WorkflowEngineStatistics()
        stats.record_queue_time(50)
        stats.record_queue_time(100)
        assert stats.report().average_queue_time_ms == 75

    def test_record_processing_time(self):
        stats = WorkflowEngineStatistics()
        stats.record_processing_time(200)
        assert stats.report().average_processing_time_ms == 200

    def test_reset(self):
        stats = WorkflowEngineStatistics()
        stats.record_executed()
        stats.record_completed()
        stats.reset()
        report = stats.report()
        assert report.workflows_executed == 0
        assert report.workflows_completed == 0

    def test_queue_size_in_report(self):
        stats = WorkflowEngineStatistics()
        report = stats.report(current_queue_size=42)
        assert report.queued_workflows == 42

    def test_to_dict(self):
        stats = WorkflowEngineStatistics()
        d = stats.report().to_dict()
        assert "workflows_executed" in d
        assert "workflow_availability" in d


# ─────────────────────────────────────────────────────────────────────────────
# 18. WorkflowEngineHistory
# ─────────────────────────────────────────────────────────────────────────────

class TestWorkflowEngineHistory:
    def test_record_and_get_request(self):
        h = WorkflowEngineHistory()
        req = make_request()
        h.record_request(req)
        found = h.get_request(req.request_id)
        assert found is not None
        assert found.request_id == req.request_id

    def test_record_and_get_response(self):
        h = WorkflowEngineHistory()
        req = make_request()
        resp = WorkflowEngineResponse.success_for(req, "s")
        h.record_response(resp)
        found = h.get_response(resp.response_id)
        assert found is not None

    def test_response_for_request(self):
        h = WorkflowEngineHistory()
        req = make_request()
        resp = WorkflowEngineResponse.success_for(req, "s")
        h.record_request(req)
        h.record_response(resp)
        found = h.response_for_request(req.request_id)
        assert found is not None
        assert found.response_id == resp.response_id

    def test_recent_requests(self):
        h = WorkflowEngineHistory()
        for i in range(10):
            h.record_request(make_request(workflow_id=f"wf-{i}"))
        recent = h.recent_requests(5)
        assert len(recent) == 5

    def test_by_session(self):
        h = WorkflowEngineHistory()
        req = make_request()
        resp1 = WorkflowEngineResponse.success_for(req, "session-X")
        resp2 = WorkflowEngineResponse.success_for(req, "session-X")
        h.record_response(resp1)
        h.record_response(resp2)
        results = h.by_session("session-X")
        assert len(results) == 2

    def test_count(self):
        h = WorkflowEngineHistory()
        assert h.request_count() == 0
        h.record_request(make_request())
        assert h.request_count() == 1

    def test_clear(self):
        h = WorkflowEngineHistory()
        h.record_request(make_request())
        h.clear()
        assert h.request_count() == 0

    def test_bounded(self):
        h = WorkflowEngineHistory(max_history=5)
        for i in range(10):
            h.record_request(make_request(workflow_id=f"wf-{i}"))
        assert h.request_count() == 5


# ─────────────────────────────────────────────────────────────────────────────
# 19. WorkflowMonitor
# ─────────────────────────────────────────────────────────────────────────────

class TestWorkflowMonitor:
    def test_register_and_active_count(self):
        m = WorkflowMonitor()
        m.register("req-1", "sess-1", "wf-1")
        assert m.active_count() == 1

    def test_deregister(self):
        m = WorkflowMonitor()
        m.register("req-1", "sess-1", "wf-1")
        record = m.deregister("req-1")
        assert record is not None
        assert m.active_count() == 0

    def test_get(self):
        m = WorkflowMonitor()
        m.register("req-1", "sess-1", "wf-1")
        record = m.get("req-1")
        assert record is not None
        assert record.request_id == "req-1"

    def test_all_active(self):
        m = WorkflowMonitor()
        m.register("req-1", "sess-1", "wf-1")
        m.register("req-2", "sess-2", "wf-2")
        records = m.all_active()
        assert len(records) == 2

    def test_elapsed_ms_positive(self):
        m = WorkflowMonitor()
        m.register("req-1", "sess-1", "wf-1")
        record = m.get("req-1")
        time.sleep(0.01)
        assert record.elapsed_ms() > 0

    def test_clear(self):
        m = WorkflowMonitor()
        m.register("req-1", "sess-1", "wf-1")
        m.clear()
        assert m.active_count() == 0

    def test_stall_detection(self):
        stalled: List[str] = []
        def on_stall(req_id, sess_id, elapsed_ms):
            stalled.append(req_id)

        m = WorkflowMonitor(stall_threshold_ms=1, on_stall=on_stall)
        m.register("req-slow", "sess-1", "wf-1")
        time.sleep(0.01)
        found = m.check_stalls()
        assert len(found) == 1
        assert "req-slow" in stalled

    def test_to_dict(self):
        m = WorkflowMonitor()
        m.register("req-1", "sess-1", "wf-1")
        record = m.get("req-1")
        d = record.to_dict()
        assert "request_id" in d
        assert "elapsed_ms" in d


# ─────────────────────────────────────────────────────────────────────────────
# 20. WorkflowEngineFactory
# ─────────────────────────────────────────────────────────────────────────────

class TestWorkflowEngineFactory:
    def test_create_request(self):
        f = WorkflowEngineFactory()
        req = f.create_request("wf-001")
        assert req.workflow_id == "wf-001"
        assert req.dispatch_mode == WorkflowDispatchMode.IMMEDIATE

    def test_create_immediate_request(self):
        f = WorkflowEngineFactory()
        req = f.create_immediate_request("wf-001")
        assert req.is_immediate

    def test_create_scheduled_request(self):
        f = WorkflowEngineFactory()
        req = f.create_scheduled_request("wf-001")
        assert req.is_scheduled

    def test_create_batch_request(self):
        f = WorkflowEngineFactory()
        req = f.create_batch_request("wf-001")
        assert req.is_batch

    def test_create_context(self):
        f = WorkflowEngineFactory()
        req = f.create_request("wf-001")
        ctx = f.create_context(req, "sess-1", engine_id="test-eng")
        assert ctx.session_id == "sess-1"
        assert ctx.engine_id == "test-eng"

    def test_create_success_response(self):
        f = WorkflowEngineFactory()
        req = f.create_request("wf-001")
        resp = f.create_success_response(req, "sess-1")
        assert resp.is_success

    def test_create_failure_response(self):
        f = WorkflowEngineFactory()
        req = f.create_request("wf-001")
        resp = f.create_failure_response(req, "sess-1", "oops")
        assert resp.is_failure
        assert resp.error_message == "oops"


# ─────────────────────────────────────────────────────────────────────────────
# 21. WorkflowEngine — core coordinator
# ─────────────────────────────────────────────────────────────────────────────

class TestWorkflowEngine:
    def test_initialize(self):
        engine = WorkflowEngine()
        engine.initialize()
        assert engine.state == WorkflowEngineState.IDLE

    def test_stop(self):
        engine = WorkflowEngine()
        engine.initialize()
        engine.stop()
        assert engine.state == WorkflowEngineState.STOPPED

    def test_stopped_raises_not_ready(self):
        engine = WorkflowEngine()
        engine.initialize()
        engine.stop()
        with pytest.raises(WorkflowEngineNotReadyError):
            engine.execute(make_request())

    def test_execute_returns_response(self):
        engine = WorkflowEngine()
        engine.initialize()
        resp = engine.execute(make_request())
        assert isinstance(resp, WorkflowEngineResponse)
        assert resp.is_success

    def test_execute_invalid_request_returns_failure(self):
        engine = WorkflowEngine()
        engine.initialize()
        req = WorkflowEngineRequest.create(
            workflow_id="",
            workflow_type=WorkflowType.SEQUENTIAL,
            dispatch_mode=WorkflowDispatchMode.IMMEDIATE,
        )
        resp = engine.execute(req)
        assert resp.is_failure

    def test_execute_records_history(self):
        engine = WorkflowEngine()
        engine.initialize()
        req = make_request()
        engine.execute(req)
        hist = engine.history()
        assert hist.get_request(req.request_id) is not None

    def test_execute_updates_statistics(self):
        engine = WorkflowEngine()
        engine.initialize()
        engine.execute(make_request())
        report = engine.statistics()
        assert report.workflows_executed == 1
        assert report.workflows_completed == 1

    def test_validate(self):
        engine = WorkflowEngine()
        engine.initialize()
        report = engine.validate(make_request())
        assert report.passed

    def test_cancel_nonexistent_returns_false(self):
        engine = WorkflowEngine()
        engine.initialize()
        assert not engine.cancel("nonexistent-req")

    def test_health(self):
        engine = WorkflowEngine()
        engine.initialize()
        h = engine.health()
        assert h.is_healthy

    def test_status(self):
        engine = WorkflowEngine()
        engine.initialize()
        s = engine.status()
        assert s.state == WorkflowEngineState.IDLE

    def test_event_bus_events_emitted(self):
        engine = WorkflowEngine()
        engine.initialize()
        events: List[WorkflowEngineEvent] = []
        engine.event_bus().add_listener(
            WorkflowEngineEventType.WORKFLOW_COMPLETED, events.append
        )
        engine.execute(make_request())
        assert len(events) >= 1

    def test_batch_execute(self):
        engine = WorkflowEngine()
        engine.initialize()
        requests = [make_request(workflow_id=f"wf-{i}") for i in range(5)]
        responses = engine.execute_batch(requests)
        assert len(responses) == 5
        assert all(r.is_success for r in responses)

    def test_engine_id_property(self):
        engine = WorkflowEngine(engine_id="custom-engine")
        assert engine.engine_id == "custom-engine"

    def test_reinitialize_after_stop_raises(self):
        engine = WorkflowEngine()
        engine.initialize()
        engine.stop()
        with pytest.raises(WorkflowEngineNotReadyError):
            engine.initialize()


# ─────────────────────────────────────────────────────────────────────────────
# 22. WorkflowManager — public API
# ─────────────────────────────────────────────────────────────────────────────

class TestWorkflowManager:
    def test_start_and_stop(self):
        m = WorkflowManager()
        m.start()
        assert m.is_started()
        m.stop()
        assert not m.is_started()

    def test_idempotent_start(self):
        m = WorkflowManager()
        m.start()
        m.start()  # should not raise
        assert m.is_started()
        m.stop()

    def test_idempotent_stop(self):
        m = WorkflowManager()
        m.start()
        m.stop()
        m.stop()  # should not raise
        assert not m.is_started()

    def test_execute_before_start_raises(self):
        m = WorkflowManager()
        with pytest.raises(WorkflowEngineNotReadyError):
            m.execute(make_request())

    def test_execute_after_start(self):
        m = make_manager()
        resp = m.execute(make_request())
        assert resp.is_success
        m.stop()

    def test_execute_batch(self):
        m = make_manager()
        reqs = [make_request(workflow_id=f"wf-{i}") for i in range(5)]
        responses = m.execute_batch(reqs)
        assert len(responses) == 5
        assert all(r.is_success for r in responses)
        m.stop()

    def test_validate(self):
        m = WorkflowManager()
        report = m.validate(make_request())
        assert report.passed

    def test_health(self):
        m = make_manager()
        h = m.health()
        assert h.is_healthy
        m.stop()

    def test_status(self):
        m = make_manager()
        s = m.status()
        assert s.engine_id is not None
        m.stop()

    def test_statistics(self):
        m = make_manager()
        m.execute(make_request())
        report = m.statistics()
        assert report.workflows_executed == 1
        m.stop()

    def test_event_bus(self):
        m = make_manager()
        bus = m.event_bus()
        assert isinstance(bus, WorkflowEngineEventBus)
        m.stop()

    def test_engine_id(self):
        m = WorkflowManager(engine_id="my-engine")
        assert m.engine_id == "my-engine"

    def test_cancel_nonexistent(self):
        m = make_manager()
        assert not m.cancel("nope")
        m.stop()


# ─────────────────────────────────────────────────────────────────────────────
# 23. Concurrency
# ─────────────────────────────────────────────────────────────────────────────

class TestConcurrency:
    def test_concurrent_execute(self):
        m = make_manager()
        results: List[WorkflowEngineResponse] = []
        errors:  List[Exception]              = []
        lock = threading.Lock()

        def run():
            try:
                resp = m.execute(make_request())
                with lock:
                    results.append(resp)
            except Exception as e:
                with lock:
                    errors.append(e)

        threads = [threading.Thread(target=run) for _ in range(20)]
        for t in threads: t.start()
        for t in threads: t.join()

        assert not errors
        assert len(results) == 20
        assert all(r.is_success for r in results)
        m.stop()

    def test_concurrent_queue_operations(self):
        q = WorkflowQueue(max_size=1000)
        errors: List[Exception] = []

        def enqueue_n(n: int):
            for i in range(n):
                try:
                    req = make_request(workflow_id=f"wf-t-{threading.current_thread().ident}-{i}")
                    q.enqueue(PriorityWorkflowItem.create(req, i, priority=2))
                except Exception as e:
                    errors.append(e)

        threads = [threading.Thread(target=enqueue_n, args=(50,)) for _ in range(5)]
        for t in threads: t.start()
        for t in threads: t.join()

        assert not errors
        assert q.size() == 250

    def test_concurrent_statistics(self):
        stats = WorkflowEngineStatistics()
        lock  = threading.Lock()

        def record():
            for _ in range(100):
                stats.record_executed()
                stats.record_completed(runtime_ms=1)

        threads = [threading.Thread(target=record) for _ in range(10)]
        for t in threads: t.start()
        for t in threads: t.join()

        report = stats.report()
        assert report.workflows_executed == 1000
        assert report.workflows_completed == 1000


# ─────────────────────────────────────────────────────────────────────────────
# 24. Edge cases
# ─────────────────────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_empty_batch(self):
        m = make_manager()
        results = m.execute_batch([])
        assert results == []
        m.stop()

    def test_request_with_payload(self):
        m = make_manager()
        req = make_request()
        req2 = WorkflowEngineRequest.create(
            workflow_id="wf-001",
            workflow_type=WorkflowType.SEQUENTIAL,
            dispatch_mode=WorkflowDispatchMode.IMMEDIATE,
            payload={"key": "value"},
        )
        resp = m.execute(req2)
        assert resp.is_success
        m.stop()

    def test_statistics_availability_no_ticks(self):
        stats = WorkflowEngineStatistics()
        report = stats.report()
        assert report.workflow_availability == 1.0

    def test_history_missing_request(self):
        h = WorkflowEngineHistory()
        assert h.get_request("nonexistent") is None

    def test_history_missing_response(self):
        h = WorkflowEngineHistory()
        assert h.get_response("nonexistent") is None

    def test_history_response_for_missing_request(self):
        h = WorkflowEngineHistory()
        assert h.response_for_request("nonexistent") is None

    def test_queue_cancel_already_dequeued(self):
        q = WorkflowQueue()
        req = make_request()
        item = PriorityWorkflowItem.create(req, 0, priority=2)
        q.enqueue(item)
        q.dequeue()  # removes it
        assert not q.cancel(item.item_id)  # nothing to cancel

    def test_scheduler_cancel_nonexistent(self):
        s = WorkflowScheduler()
        assert not s.cancel_job("nonexistent-job")

    def test_monitor_deregister_nonexistent(self):
        m = WorkflowMonitor()
        record = m.deregister("nonexistent")
        assert record is None

    def test_registry_get_nonexistent_session(self):
        r = WorkflowEngineRegistry()
        assert r.get_session_id("nope") is None

    def test_validation_report_to_dict(self):
        v = WorkflowEngineValidator()
        report = v.validate(make_request())
        d = report.to_dict()
        assert d["passed"] is True
        assert isinstance(d["results"], list)


# ─────────────────────────────────────────────────────────────────────────────
# 25. Regression — ensure M1 bridge is intact
# ─────────────────────────────────────────────────────────────────────────────

class TestRegression:
    def test_m1_session_lifecycle_via_engine(self):
        """Engine should walk through M1 lifecycle without errors."""
        engine = WorkflowEngine()
        engine.initialize()
        for _ in range(5):
            resp = engine.execute(make_request())
            assert resp.is_success

    def test_multiple_start_stop_cycles(self):
        for _ in range(3):
            m = WorkflowManager()   # fresh manager each cycle
            m.start()
            m.execute(make_request())
            m.stop()
        # each cycle should work cleanly

    def test_event_count_per_execution(self):
        engine = WorkflowEngine()
        engine.initialize()
        events: List[WorkflowEngineEvent] = []
        for et in WorkflowEngineEventType:
            engine.event_bus().add_listener(et, events.append)
        engine.execute(make_request())
        # At minimum: VALIDATED, INITIALIZED, QUEUED, DISPATCHED, STARTED, COMPLETED, SNAPSHOT
        assert len(events) >= 7

    def test_batch_statistics_accuracy(self):
        engine = WorkflowEngine()
        engine.initialize()
        requests = [make_request(workflow_id=f"wf-{i}") for i in range(10)]
        engine.execute_batch(requests)
        report = engine.statistics()
        assert report.workflows_executed == 10
        assert report.workflows_completed == 10
        assert report.workflows_failed == 0
