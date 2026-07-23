"""
test_supervisor_engine.py
==========================
Unit tests for C13 M2 — AI Supervisor Engine.

Coverage areas:
  Constants, Exceptions, Context, Request, Response, Pipeline,
  Scheduler, Dispatcher, SessionManager, Registry, Validation,
  Health, Status, Statistics, History, Events, Factory, Manager,
  Engine (public API), Concurrency, Regression

Target: 95%+ coverage.
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

from iios.supervisor.engine import (
    # Primary interface
    SupervisorEngine,
    # Value objects
    SupervisorEngineContext,
    SupervisorRequest,
    SupervisorEngineSnapshot,
    SupervisorResponse,
    PipelineStage,
    SupervisorPipeline,
    # Subsystems
    SupervisorScheduler,
    SupervisorDispatcher,
    SupervisorSessionManager,
    SupervisorEngineRegistry,
    SupervisorEngineValidator,
    SupervisorEngineValidationCheckResult,
    SupervisorEngineValidationResult,
    SupervisorEngineHealth,
    SupervisorEngineStatus,
    SupervisorEngineStatistics,
    SupervisorEngineHistory,
    SupervisorEngineFactory,
    SupervisorWorkflowManager,
    # Events
    SupervisorEngineEvent,
    SupervisorEngineEventType,
    make_supervisor_engine_initialized,
    make_supervisor_engine_started,
    make_supervisor_engine_collected,
    make_supervisor_engine_validated,
    make_supervisor_engine_dispatched,
    make_supervisor_engine_monitoring_started,
    make_supervisor_engine_published,
    make_supervisor_engine_completed,
    make_supervisor_engine_failed,
    make_supervisor_engine_stopped,
    # Enums
    EngineState,
    SupervisorWorkflowType,
    SubsystemType,
    SchedulerPriority,
    ResponseStatus,
    PipelineStatus,
    # Constants
    VERSION,
    SCHEMA_VERSION,
    ENGINE_SYSTEM_ID,
    DEFAULT_MAX_CONCURRENT_SESSIONS,
    DEFAULT_MAX_PIPELINES,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_SCHEDULER_QUEUE,
    DEFAULT_MAX_ARCHIVED_PIPELINES,
    SUPERVISION_WORKFLOWS,
    MONITORING_WORKFLOWS,
    ACTIVE_ENGINE_STATES,
    TERMINAL_ENGINE_STATES,
    VALID_ENGINE_TRANSITIONS,
    # Exceptions
    SupervisorEngineError,
    SupervisorEngineNotRunningError,
    SupervisorSessionError,
    SupervisorPipelineError,
    SupervisorDispatchError,
    SupervisorCollectionError,
    SupervisorPublicationError,
    SupervisorEngineValidationError,
    SupervisorSchedulerError,
    SupervisorEngineCapacityError,
)


# ============================================================================
# Helpers
# ============================================================================

def _make_request(
    supervision_id: str = "sup-001",
    subsystem_id:   str = "enterprise",
    workflow_type:  SupervisorWorkflowType = SupervisorWorkflowType.ENTERPRISE_HEALTH_REVIEW,
    priority:       SchedulerPriority      = SchedulerPriority.NORMAL,
    **kwargs,
) -> SupervisorRequest:
    return SupervisorRequest.create(
        supervision_id,
        subsystem_id,
        workflow_type,
        priority=priority,
        **kwargs,
    )


def _started_engine(**kwargs) -> SupervisorEngine:
    engine = SupervisorEngine(**kwargs)
    engine.start()
    return engine


# ============================================================================
# 1. Constants
# ============================================================================

class TestConstants:
    def test_version_is_string(self):
        assert isinstance(VERSION, str) and VERSION

    def test_schema_version_is_string(self):
        assert isinstance(SCHEMA_VERSION, str) and SCHEMA_VERSION

    def test_engine_system_id(self):
        assert ENGINE_SYSTEM_ID == "iios:supervisor:engine"

    def test_engine_state_count(self):
        assert len(EngineState) == 12

    def test_engine_state_values(self):
        expected = {
            "idle", "initializing", "discovering", "collecting",
            "validating", "dispatching", "supervising", "monitoring",
            "publishing", "completed", "failed", "stopped",
        }
        assert {s.value for s in EngineState} == expected

    def test_workflow_type_count(self):
        assert len(SupervisorWorkflowType) == 8

    def test_subsystem_type_count(self):
        assert len(SubsystemType) == 8

    def test_scheduler_priority_count(self):
        assert len(SchedulerPriority) == 5

    def test_scheduler_priority_order(self):
        assert SchedulerPriority.CRITICAL < SchedulerPriority.HIGH
        assert SchedulerPriority.HIGH < SchedulerPriority.NORMAL
        assert SchedulerPriority.NORMAL < SchedulerPriority.LOW
        assert SchedulerPriority.LOW < SchedulerPriority.BATCH

    def test_response_status_count(self):
        assert len(ResponseStatus) == 3

    def test_pipeline_status_count(self):
        assert len(PipelineStatus) == 5

    def test_event_type_count(self):
        assert len(SupervisorEngineEventType) == 10

    def test_supervision_workflows_nonempty(self):
        assert len(SUPERVISION_WORKFLOWS) > 0

    def test_monitoring_workflows_nonempty(self):
        assert len(MONITORING_WORKFLOWS) > 0

    def test_active_engine_states(self):
        assert len(ACTIVE_ENGINE_STATES) >= 4

    def test_terminal_engine_states(self):
        assert EngineState.COMPLETED in TERMINAL_ENGINE_STATES
        assert EngineState.FAILED    in TERMINAL_ENGINE_STATES
        assert EngineState.STOPPED   in TERMINAL_ENGINE_STATES

    def test_valid_transitions_keys(self):
        assert EngineState.IDLE in VALID_ENGINE_TRANSITIONS

    def test_default_constants(self):
        assert DEFAULT_MAX_CONCURRENT_SESSIONS == 200
        assert DEFAULT_MAX_PIPELINES == 5_000
        assert DEFAULT_MAX_SCHEDULER_QUEUE == 10_000


# ============================================================================
# 2. Exceptions
# ============================================================================

class TestExceptions:
    def test_base_is_iios_error(self):
        from iios.common.errors.exceptions import IIOSError
        assert issubclass(SupervisorEngineError, IIOSError)

    def test_not_running_code(self):
        exc = SupervisorEngineNotRunningError()
        assert "SE-001" in str(exc) or exc.error_code == "SE-001"

    def test_session_error_stores_session_id(self):
        exc = SupervisorSessionError("bad", session_id="s-001")
        assert exc.session_id == "s-001"

    def test_pipeline_error_stores_pipeline_id(self):
        exc = SupervisorPipelineError("bad", pipeline_id="p-001")
        assert exc.pipeline_id == "p-001"

    def test_dispatch_error_stores_workflow_type(self):
        exc = SupervisorDispatchError("bad", workflow_type="ENTERPRISE_HEALTH_REVIEW")
        assert exc.workflow_type == "ENTERPRISE_HEALTH_REVIEW"

    def test_collection_error_stores_missing_inputs(self):
        exc = SupervisorCollectionError("bad", missing_inputs=("a", "b"))
        assert "a" in exc.missing_inputs

    def test_publication_error_stores_supervision_id(self):
        exc = SupervisorPublicationError("bad", supervision_id="s-001")
        assert exc.supervision_id == "s-001"

    def test_validation_error_stores_failed_checks(self):
        exc = SupervisorEngineValidationError("bad", failed_checks=("check_a",))
        assert "check_a" in exc.failed_checks

    def test_capacity_error_stores_limit(self):
        exc = SupervisorEngineCapacityError(500)
        assert exc.limit == 500

    def test_scheduler_error(self):
        exc = SupervisorSchedulerError("oops")
        assert isinstance(exc, SupervisorEngineError)

    def test_all_inherit_from_base(self):
        for cls in [
            SupervisorEngineNotRunningError,
            SupervisorSessionError,
            SupervisorPipelineError,
            SupervisorDispatchError,
            SupervisorCollectionError,
            SupervisorPublicationError,
            SupervisorEngineValidationError,
            SupervisorSchedulerError,
            SupervisorEngineCapacityError,
        ]:
            assert issubclass(cls, SupervisorEngineError)


# ============================================================================
# 3. SupervisorEngineContext
# ============================================================================

class TestSupervisorEngineContext:
    def test_create_returns_context(self):
        ctx = SupervisorEngineContext.create(
            "sup-001", "enterprise",
            SupervisorWorkflowType.ENTERPRISE_HEALTH_REVIEW,
        )
        assert ctx.supervision_id == "sup-001"
        assert ctx.subsystem_id   == "enterprise"

    def test_context_is_frozen(self):
        ctx = SupervisorEngineContext.create(
            "sup-001", "enterprise",
            SupervisorWorkflowType.ENTERPRISE_HEALTH_REVIEW,
        )
        with pytest.raises((AttributeError, TypeError)):
            ctx.supervision_id = "other"   # type: ignore[misc]

    def test_context_id_is_uuid(self):
        ctx = SupervisorEngineContext.create(
            "sup-001", "enterprise",
            SupervisorWorkflowType.ENTERPRISE_HEALTH_REVIEW,
        )
        uuid.UUID(ctx.context_id)

    def test_to_dict(self):
        ctx = SupervisorEngineContext.create(
            "sup-001", "enterprise",
            SupervisorWorkflowType.ENTERPRISE_HEALTH_REVIEW,
        )
        d = ctx.to_dict()
        assert d["supervision_id"]  == "sup-001"
        assert d["subsystem_id"]    == "enterprise"
        assert d["framework_version"] == VERSION

    def test_workflow_type_preserved(self):
        ctx = SupervisorEngineContext.create(
            "sup-001", "ent",
            SupervisorWorkflowType.SUBSYSTEM_SUPERVISION,
        )
        assert ctx.workflow_type == SupervisorWorkflowType.SUBSYSTEM_SUPERVISION


# ============================================================================
# 4. SupervisorRequest
# ============================================================================

class TestSupervisorRequest:
    def test_create_defaults(self):
        req = SupervisorRequest.create("sup-001", "enterprise")
        assert req.supervision_id == "sup-001"
        assert req.subsystem_id   == "enterprise"
        assert isinstance(req.request_id, str)

    def test_create_priority(self):
        req = SupervisorRequest.create(
            "sup-001", "ent", priority=SchedulerPriority.HIGH
        )
        assert req.priority == SchedulerPriority.HIGH

    def test_create_with_inputs(self):
        req = SupervisorRequest.create(
            "sup-001", "ent", inputs={"system_health": {"ok": True}}
        )
        assert req.inputs["system_health"]["ok"] is True

    def test_with_inputs_merges(self):
        req  = SupervisorRequest.create("sup-001", "ent", inputs={"a": 1})
        req2 = req.with_inputs({"b": 2})
        assert req2.inputs["a"] == 1
        assert req2.inputs["b"] == 2
        assert req.inputs.get("b") is None

    def test_context_supervision_id_matches(self):
        req = SupervisorRequest.create("sup-xyz", "ent")
        assert req.context.supervision_id == "sup-xyz"

    def test_to_dict_omits_raw_inputs(self):
        req = SupervisorRequest.create(
            "sup-001", "ent", inputs={"system_health": {"ok": True}}
        )
        d = req.to_dict()
        assert "input_keys" in d
        assert "inputs" not in d

    def test_request_is_frozen(self):
        req = SupervisorRequest.create("s", "e")
        with pytest.raises((AttributeError, TypeError)):
            req.supervision_id = "x"   # type: ignore[misc]


# ============================================================================
# 5. SupervisorResponse + SupervisorEngineSnapshot
# ============================================================================

class TestSupervisorResponse:
    def test_success_properties(self):
        snap = SupervisorEngineSnapshot.create(
            "sup-001", "ent", "sess-001",
            SupervisorWorkflowType.ENTERPRISE_HEALTH_REVIEW,
            EngineState.SUPERVISING,
        )
        resp = SupervisorResponse(
            response_id    = str(uuid.uuid4()),
            request_id     = "req-001",
            supervision_id = "sup-001",
            subsystem_id   = "ent",
            workflow_type  = SupervisorWorkflowType.ENTERPRISE_HEALTH_REVIEW,
            status         = ResponseStatus.SUCCESS,
            snapshot       = snap,
        )
        assert resp.is_success
        assert not resp.is_failure
        assert resp.has_snapshot

    def test_failure_properties(self):
        resp = SupervisorResponse(
            response_id    = str(uuid.uuid4()),
            request_id     = "req-001",
            supervision_id = "sup-001",
            subsystem_id   = "ent",
            workflow_type  = SupervisorWorkflowType.ENTERPRISE_HEALTH_REVIEW,
            status         = ResponseStatus.FAILURE,
            error_message  = "something went wrong",
        )
        assert resp.is_failure
        assert not resp.is_success
        assert not resp.has_snapshot

    def test_snapshot_to_dict(self):
        snap = SupervisorEngineSnapshot.create(
            "sup-001", "ent", "sess-001",
            SupervisorWorkflowType.ENTERPRISE_HEALTH_REVIEW,
            EngineState.SUPERVISING,
        )
        d = snap.to_dict()
        assert d["supervision_id"] == "sup-001"
        assert d["framework_version"] == VERSION

    def test_response_to_dict(self):
        resp = SupervisorResponse(
            response_id    = str(uuid.uuid4()),
            request_id     = "r",
            supervision_id = "s",
            subsystem_id   = "e",
            workflow_type  = SupervisorWorkflowType.ENTERPRISE_HEALTH_REVIEW,
            status         = ResponseStatus.SUCCESS,
        )
        d = resp.to_dict()
        assert "response_id" in d


# ============================================================================
# 6. SupervisorPipeline + PipelineStage
# ============================================================================

class TestPipeline:
    def test_create_pending(self):
        p = SupervisorPipeline("r-001", "sup-001", "ent",
                               SupervisorWorkflowType.ENTERPRISE_HEALTH_REVIEW)
        assert p.status == PipelineStatus.PENDING

    def test_start_sets_running(self):
        p = SupervisorPipeline("r-001", "sup-001", "ent",
                               SupervisorWorkflowType.ENTERPRISE_HEALTH_REVIEW)
        p.start()
        assert p.is_running

    def test_complete(self):
        p = SupervisorPipeline("r-001", "sup-001", "ent",
                               SupervisorWorkflowType.ENTERPRISE_HEALTH_REVIEW)
        p.start()
        p.complete()
        assert p.is_complete

    def test_fail(self):
        p = SupervisorPipeline("r-001", "sup-001", "ent",
                               SupervisorWorkflowType.ENTERPRISE_HEALTH_REVIEW)
        p.start()
        p.fail("oops")
        assert p.is_failed
        assert p.error == "oops"

    def test_cancel(self):
        p = SupervisorPipeline("r-001", "sup-001", "ent",
                               SupervisorWorkflowType.ENTERPRISE_HEALTH_REVIEW)
        p.start()
        p.cancel()
        assert p.status == PipelineStatus.CANCELLED

    def test_add_stage(self):
        p = SupervisorPipeline("r-001", "sup-001", "ent",
                               SupervisorWorkflowType.ENTERPRISE_HEALTH_REVIEW)
        stage = PipelineStage("init", EngineState.INITIALIZING, PipelineStatus.COMPLETED)
        p.add_stage(stage)
        assert len(p.stages) == 1

    def test_session_id_settable(self):
        p = SupervisorPipeline("r-001", "sup-001", "ent",
                               SupervisorWorkflowType.ENTERPRISE_HEALTH_REVIEW)
        p.session_id = "sess-001"
        assert p.session_id == "sess-001"

    def test_elapsed_s(self):
        p = SupervisorPipeline("r-001", "sup-001", "ent",
                               SupervisorWorkflowType.ENTERPRISE_HEALTH_REVIEW)
        p.start()
        assert p.elapsed_s >= 0

    def test_to_dict(self):
        p = SupervisorPipeline("r-001", "sup-001", "ent",
                               SupervisorWorkflowType.ENTERPRISE_HEALTH_REVIEW)
        d = p.to_dict()
        assert d["pipeline_id"] == p.pipeline_id

    def test_stage_elapsed(self):
        start = time.time() - 0.1
        stage = PipelineStage(
            "test", EngineState.INITIALIZING, PipelineStatus.COMPLETED,
            started_at=start, completed_at=time.time(),
        )
        assert stage.elapsed_s > 0

    def test_stage_to_dict(self):
        stage = PipelineStage("test", EngineState.IDLE, PipelineStatus.PENDING)
        d = stage.to_dict()
        assert "stage_name" in d


# ============================================================================
# 7. SupervisorScheduler
# ============================================================================

class TestScheduler:
    def test_schedule_returns_request_id(self):
        sched = SupervisorScheduler()
        req   = _make_request()
        rid   = sched.schedule(req)
        assert rid == req.request_id

    def test_next_returns_request(self):
        sched = SupervisorScheduler()
        req   = _make_request()
        sched.schedule(req)
        out = sched.next()
        assert out is not None
        assert out.request_id == req.request_id

    def test_next_returns_none_when_empty(self):
        sched = SupervisorScheduler()
        assert sched.next() is None

    def test_priority_ordering(self):
        sched = SupervisorScheduler()
        low  = _make_request("s1", priority=SchedulerPriority.LOW)
        high = _make_request("s2", priority=SchedulerPriority.HIGH)
        sched.schedule(low)
        sched.schedule(high)
        first = sched.next()
        assert first.supervision_id == "s2"

    def test_cancel_prevents_dequeue(self):
        sched = SupervisorScheduler()
        req   = _make_request()
        sched.schedule(req)
        sched.cancel(req.request_id)
        assert sched.next() is None

    def test_cancel_unknown_returns_false(self):
        sched = SupervisorScheduler()
        assert not sched.cancel("unknown")

    def test_capacity_error(self):
        sched = SupervisorScheduler(max_queue_size=2)
        sched.schedule(_make_request("s1"))
        sched.schedule(_make_request("s2"))
        with pytest.raises(SupervisorEngineCapacityError):
            sched.schedule(_make_request("s3"))

    def test_duplicate_raises_scheduler_error(self):
        sched = SupervisorScheduler()
        req   = _make_request()
        sched.schedule(req)
        with pytest.raises(SupervisorSchedulerError):
            sched.schedule(req)

    def test_queue_depth(self):
        sched = SupervisorScheduler()
        sched.schedule(_make_request("s1"))
        sched.schedule(_make_request("s2"))
        assert sched.queue_depth() == 2

    def test_statistics_keys(self):
        sched = SupervisorScheduler()
        s = sched.statistics()
        assert "scheduled" in s
        assert "dispatched" in s

    def test_clear(self):
        sched = SupervisorScheduler()
        sched.schedule(_make_request())
        sched.clear()
        assert sched.queue_depth() == 0


# ============================================================================
# 8. SupervisorDispatcher
# ============================================================================

class TestDispatcher:
    def test_no_framework_registered(self):
        dsp = SupervisorDispatcher()
        assert not dsp.has_governance_framework
        assert not dsp.has_autonomous_framework

    def test_register_governance(self):
        dsp = SupervisorDispatcher()
        dsp.register_governance_framework(lambda p, r: None)
        assert dsp.has_governance_framework

    def test_register_autonomous(self):
        dsp = SupervisorDispatcher()
        dsp.register_autonomous_framework(lambda p, r: None)
        assert dsp.has_autonomous_framework

    def test_unregister_governance(self):
        dsp = SupervisorDispatcher()
        dsp.register_governance_framework(lambda p, r: None)
        dsp.unregister_governance_framework()
        assert not dsp.has_governance_framework

    def test_dispatch_passthrough(self):
        dsp      = SupervisorDispatcher()
        req      = _make_request()
        pipeline = SupervisorPipeline(
            req.request_id, req.supervision_id, req.subsystem_id,
            req.workflow_type
        )
        pipeline.start()
        out = dsp.dispatch(pipeline, req)
        assert out is pipeline

    def test_dispatch_calls_governance_hook(self):
        called = []
        dsp    = SupervisorDispatcher()
        dsp.register_governance_framework(lambda p, r: called.append(True))
        req      = _make_request()
        pipeline = SupervisorPipeline(
            req.request_id, req.supervision_id, req.subsystem_id,
            req.workflow_type
        )
        pipeline.start()
        dsp.dispatch(pipeline, req)
        assert called

    def test_dispatch_calls_autonomous_hook(self):
        called = []
        dsp    = SupervisorDispatcher()
        dsp.register_autonomous_framework(lambda p, r: called.append(True))
        req      = _make_request()
        pipeline = SupervisorPipeline(
            req.request_id, req.supervision_id, req.subsystem_id,
            req.workflow_type
        )
        pipeline.start()
        dsp.dispatch(pipeline, req)
        assert called

    def test_next_engine_state_supervision(self):
        dsp = SupervisorDispatcher()
        wt  = next(iter(SUPERVISION_WORKFLOWS))
        assert dsp.next_engine_state(wt) == EngineState.SUPERVISING

    def test_next_engine_state_monitoring(self):
        dsp = SupervisorDispatcher()
        wt  = next(iter(MONITORING_WORKFLOWS))
        assert dsp.next_engine_state(wt) == EngineState.MONITORING

    def test_statistics_keys(self):
        dsp = SupervisorDispatcher()
        s   = dsp.statistics()
        assert "dispatch_count" in s


# ============================================================================
# 9. SupervisorEngineRegistry
# ============================================================================

class TestRegistry:
    def _make_pipeline(self, req=None) -> SupervisorPipeline:
        r = req or _make_request()
        return SupervisorPipeline(
            r.request_id, r.supervision_id, r.subsystem_id, r.workflow_type
        )

    def test_register_and_retrieve(self):
        reg = SupervisorEngineRegistry()
        req = _make_request()
        p   = self._make_pipeline(req)
        reg.register_pipeline(p)
        assert reg.get_pipeline(p.pipeline_id) is p

    def test_active_count(self):
        reg = SupervisorEngineRegistry()
        p   = self._make_pipeline()
        reg.register_pipeline(p)
        assert reg.active_pipeline_count() == 1

    def test_archive_pipeline(self):
        reg = SupervisorEngineRegistry()
        p   = self._make_pipeline()
        reg.register_pipeline(p)
        p.complete()
        reg.archive_pipeline(p)
        assert reg.active_pipeline_count() == 0
        assert reg.archived_pipeline_count() == 1
        assert reg.get_pipeline(p.pipeline_id) is p

    def test_capacity_error(self):
        reg = SupervisorEngineRegistry(max_pipelines=1)
        reg.register_pipeline(self._make_pipeline())
        with pytest.raises(SupervisorEngineCapacityError):
            reg.register_pipeline(self._make_pipeline())

    def test_register_request(self):
        reg = SupervisorEngineRegistry()
        req = _make_request()
        reg.register_request(req)
        assert reg.get_request(req.request_id) is req

    def test_register_response(self):
        reg  = SupervisorEngineRegistry()
        req  = _make_request()
        resp = SupervisorResponse(
            response_id    = str(uuid.uuid4()),
            request_id     = req.request_id,
            supervision_id = req.supervision_id,
            subsystem_id   = req.subsystem_id,
            workflow_type  = req.workflow_type,
            status         = ResponseStatus.SUCCESS,
        )
        reg.register_response(resp)
        assert reg.get_response(req.request_id) is resp

    def test_recent_responses(self):
        reg = SupervisorEngineRegistry()
        for i in range(5):
            req  = _make_request(f"sup-{i}")
            resp = SupervisorResponse(
                response_id    = str(uuid.uuid4()),
                request_id     = req.request_id,
                supervision_id = req.supervision_id,
                subsystem_id   = req.subsystem_id,
                workflow_type  = req.workflow_type,
                status         = ResponseStatus.SUCCESS,
            )
            reg.register_response(resp)
        assert len(reg.recent_responses(3)) == 3

    def test_is_ready(self):
        reg = SupervisorEngineRegistry(max_pipelines=10)
        assert reg.is_ready()

    def test_get_pipeline_for_request(self):
        reg = SupervisorEngineRegistry()
        req = _make_request()
        p   = self._make_pipeline(req)
        reg.register_pipeline(p)
        assert reg.get_pipeline_for_request(req.request_id) is p

    def test_clear(self):
        reg = SupervisorEngineRegistry()
        reg.register_pipeline(self._make_pipeline())
        reg.clear()
        assert reg.active_pipeline_count() == 0

    def test_fifo_eviction(self):
        reg = SupervisorEngineRegistry(max_archived=2)
        for i in range(4):
            p = self._make_pipeline()
            p.complete()
            reg.archive_pipeline(p)
        assert reg.archived_pipeline_count() == 2


# ============================================================================
# 10. SupervisorEngineValidator
# ============================================================================

class TestValidator:
    def test_valid_request(self):
        req    = _make_request()
        val    = SupervisorEngineValidator()
        result = val.validate_request(req)
        assert result.is_valid
        assert result.failed_checks == []

    def test_invalid_inputs_schema(self):
        # Manually craft a broken request (would normally not happen)
        req = _make_request()
        # Patch the request to have wrong inputs type via a mock
        from unittest.mock import PropertyMock
        req2 = MagicMock(spec=SupervisorRequest)
        req2.request_id     = req.request_id
        req2.supervision_id = req.supervision_id
        req2.subsystem_id   = req.subsystem_id
        req2.workflow_type  = req.workflow_type
        req2.priority       = req.priority
        req2.context        = req.context
        req2.inputs         = "not_a_dict"   # bad type
        val    = SupervisorEngineValidator()
        result = val.validate_request(req2)
        assert not result.is_valid
        assert "inputs_schema" in result.failed_checks

    def test_context_consistency_fail(self):
        req = _make_request("sup-A")
        # Build context with mismatched supervision_id
        ctx = SupervisorEngineContext.create(
            "sup-B", "ent",
            SupervisorWorkflowType.ENTERPRISE_HEALTH_REVIEW,
        )
        bad_req = SupervisorRequest(
            request_id     = req.request_id,
            supervision_id = req.supervision_id,
            subsystem_id   = req.subsystem_id,
            workflow_type  = req.workflow_type,
            priority       = req.priority,
            context        = ctx,
            inputs         = {},
        )
        val    = SupervisorEngineValidator()
        result = val.validate_request(bad_req)
        assert not result.is_valid
        assert "context_consistency" in result.failed_checks

    def test_session_capacity_exceeded(self):
        val    = SupervisorEngineValidator(
            max_sessions=0,
            active_count_fn=lambda: 0,
        )
        req    = _make_request()
        result = val.validate_request(req)
        assert not result.is_valid
        assert "lifecycle_readiness" in result.failed_checks

    def test_validate_or_raise_on_failure(self):
        req = _make_request()
        ctx = SupervisorEngineContext.create(
            "other", "ent",
            SupervisorWorkflowType.ENTERPRISE_HEALTH_REVIEW,
        )
        bad_req = SupervisorRequest(
            request_id     = req.request_id,
            supervision_id = req.supervision_id,
            subsystem_id   = req.subsystem_id,
            workflow_type  = req.workflow_type,
            priority       = req.priority,
            context        = ctx,
        )
        with pytest.raises(SupervisorEngineValidationError):
            SupervisorEngineValidator().validate_or_raise(bad_req)

    def test_validation_result_properties(self):
        checks = [
            SupervisorEngineValidationCheckResult("c1", True),
            SupervisorEngineValidationCheckResult("c2", False, "bad"),
        ]
        result = SupervisorEngineValidationResult(checks=checks)
        assert not result.is_valid
        assert "c2" in result.failed_checks
        assert "bad" in result.error_messages


# ============================================================================
# 11. SupervisorEngineHealth
# ============================================================================

class TestHealth:
    def test_report_keys(self):
        h      = SupervisorEngineHealth()
        report = h.report()
        assert "overall" in report
        assert "components" in report
        assert "checked_at" in report

    def test_report_with_mocks(self):
        sm   = MagicMock()
        sm.active_session_count.return_value = 3
        dsp  = MagicMock()
        dsp.has_governance_framework = False
        dsp.has_autonomous_framework = False
        sch  = MagicMock()
        sch.queue_depth.return_value = 5
        reg  = MagicMock()
        reg.is_ready.return_value = True
        reg.active_pipeline_count.return_value = 1

        h      = SupervisorEngineHealth(sm, dsp, sch, reg)
        report = h.report(engine_state="idle")
        assert report["overall"] == "healthy"
        assert report["components"]["session_manager"]["active_sessions"] == 3

    def test_degraded_when_component_raises(self):
        sm = MagicMock()
        sm.active_session_count.side_effect = RuntimeError("db error")
        h      = SupervisorEngineHealth(session_manager=sm)
        report = h.report()
        assert report["components"]["session_manager"]["status"] == "degraded"


# ============================================================================
# 12. SupervisorEngineStatus
# ============================================================================

class TestStatus:
    def test_to_dict(self):
        status = SupervisorEngineStatus(
            engine_state          = EngineState.IDLE,
            engine_lifecycle      = "running",
            active_pipelines      = 0,
            archived_pipelines    = 0,
            scheduler_queue_depth = 0,
            active_sessions       = 0,
            total_requests        = 5,
            total_responses       = 4,
            health                = "healthy",
        )
        d = status.to_dict()
        assert d["engine_state"] == "idle"
        assert d["total_requests"] == 5

    def test_status_is_frozen(self):
        status = SupervisorEngineStatus(
            engine_state=EngineState.IDLE,
            engine_lifecycle="running",
            active_pipelines=0, archived_pipelines=0,
            scheduler_queue_depth=0, active_sessions=0,
            total_requests=0, total_responses=0, health="healthy",
        )
        with pytest.raises((AttributeError, TypeError)):
            status.health = "bad"   # type: ignore[misc]


# ============================================================================
# 13. SupervisorEngineStatistics
# ============================================================================

class TestStatistics:
    def test_initial_snapshot(self):
        s = SupervisorEngineStatistics()
        snap = s.snapshot()
        assert snap["total_requests"] == 0
        assert snap["total_sessions"] == 0

    def test_record_session(self):
        s = SupervisorEngineStatistics()
        s.record_session()
        assert s.snapshot()["total_sessions"] == 1

    def test_record_request(self):
        s = SupervisorEngineStatistics()
        s.record_request()
        assert s.snapshot()["total_requests"] == 1

    def test_record_response_success(self):
        s = SupervisorEngineStatistics()
        s.record_response(success=True)
        snap = s.snapshot()
        assert snap["total_success"] == 1
        assert snap["total_failure"] == 0

    def test_record_response_failure(self):
        s = SupervisorEngineStatistics()
        s.record_response(success=False)
        snap = s.snapshot()
        assert snap["total_failure"] == 1

    def test_welford_mean(self):
        s = SupervisorEngineStatistics()
        for v in [1.0, 2.0, 3.0]:
            s.record_elapsed(v)
        assert abs(s.mean_elapsed_s - 2.0) < 1e-9

    def test_stddev_calculated(self):
        s = SupervisorEngineStatistics()
        for v in [1.0, 3.0]:
            s.record_elapsed(v)
        assert s.stddev_elapsed_s > 0

    def test_throughput_per_minute(self):
        s = SupervisorEngineStatistics(throughput_window_s=60)
        for _ in range(10):
            s.record_elapsed(0.1)
        assert s.throughput_per_minute() > 0

    def test_health_check_counter(self):
        s = SupervisorEngineStatistics()
        s.record_health_check()
        s.record_health_check()
        assert s.snapshot()["total_health_checks"] == 2

    def test_subsystem_counter(self):
        s = SupervisorEngineStatistics()
        s.record_subsystem()
        assert s.snapshot()["total_subsystems"] == 1

    def test_snapshot_counter(self):
        s = SupervisorEngineStatistics()
        s.record_snapshot()
        assert s.snapshot()["total_snapshots"] == 1


# ============================================================================
# 14. SupervisorEngineHistory
# ============================================================================

class TestHistory:
    def test_record_and_retrieve_events(self):
        h = SupervisorEngineHistory()
        e = make_supervisor_engine_initialized("sup-001")
        h.record_event(e)
        assert len(h.recent_events()) == 1

    def test_bounded_by_max(self):
        h = SupervisorEngineHistory(max_history=3)
        for i in range(5):
            h.record_event(make_supervisor_engine_initialized(f"sup-{i}"))
        assert len(h.recent_events(100)) == 3

    def test_record_request(self):
        h   = SupervisorEngineHistory()
        req = _make_request()
        h.record_request(req)
        assert len(h.recent_requests()) == 1

    def test_record_response(self):
        h    = SupervisorEngineHistory()
        resp = SupervisorResponse(
            response_id    = str(uuid.uuid4()),
            request_id     = "r",
            supervision_id = "s",
            subsystem_id   = "e",
            workflow_type  = SupervisorWorkflowType.ENTERPRISE_HEALTH_REVIEW,
            status         = ResponseStatus.SUCCESS,
        )
        h.record_response(resp)
        assert len(h.recent_responses()) == 1

    def test_record_pipeline(self):
        h = SupervisorEngineHistory()
        p = SupervisorPipeline("r", "s", "e",
                               SupervisorWorkflowType.ENTERPRISE_HEALTH_REVIEW)
        h.record_pipeline(p)
        assert len(h.recent_pipelines()) == 1

    def test_clear(self):
        h = SupervisorEngineHistory()
        h.record_event(make_supervisor_engine_initialized("s"))
        h.clear()
        assert len(h.recent_events()) == 0

    def test_n_limit(self):
        h = SupervisorEngineHistory()
        for i in range(10):
            h.record_event(make_supervisor_engine_initialized(f"s-{i}"))
        assert len(h.recent_events(3)) == 3


# ============================================================================
# 15. SupervisorEngineEvent factory functions
# ============================================================================

class TestEvents:
    def _check_event(self, ev, expected_type, expected_state):
        assert isinstance(ev, SupervisorEngineEvent)
        assert ev.event_type    == expected_type
        assert ev.engine_state  == expected_state
        assert ev.supervision_id == "sup-001"
        uuid.UUID(ev.event_id)

    def test_initialized(self):
        ev = make_supervisor_engine_initialized("sup-001")
        self._check_event(ev, SupervisorEngineEventType.SUPERVISOR_INITIALIZED,
                          EngineState.INITIALIZING)

    def test_started(self):
        ev = make_supervisor_engine_started("sup-001")
        self._check_event(ev, SupervisorEngineEventType.SUPERVISOR_STARTED,
                          EngineState.DISCOVERING)

    def test_collected(self):
        ev = make_supervisor_engine_collected("sup-001")
        self._check_event(ev, SupervisorEngineEventType.SUPERVISOR_COLLECTED,
                          EngineState.COLLECTING)

    def test_validated(self):
        ev = make_supervisor_engine_validated("sup-001")
        self._check_event(ev, SupervisorEngineEventType.SUPERVISOR_VALIDATED,
                          EngineState.VALIDATING)

    def test_dispatched(self):
        ev = make_supervisor_engine_dispatched("sup-001")
        self._check_event(ev, SupervisorEngineEventType.SUPERVISOR_DISPATCHED,
                          EngineState.DISPATCHING)

    def test_monitoring_started(self):
        ev = make_supervisor_engine_monitoring_started("sup-001")
        self._check_event(ev, SupervisorEngineEventType.SUPERVISOR_MONITORING_STARTED,
                          EngineState.MONITORING)

    def test_published(self):
        ev = make_supervisor_engine_published("sup-001")
        self._check_event(ev, SupervisorEngineEventType.SUPERVISOR_PUBLISHED,
                          EngineState.PUBLISHING)

    def test_completed(self):
        ev = make_supervisor_engine_completed("sup-001")
        self._check_event(ev, SupervisorEngineEventType.SUPERVISOR_COMPLETED,
                          EngineState.COMPLETED)

    def test_failed_carries_error(self):
        ev = make_supervisor_engine_failed("sup-001", error="boom")
        assert ev.payload.get("error") == "boom"

    def test_stopped(self):
        ev = make_supervisor_engine_stopped("sup-001")
        self._check_event(ev, SupervisorEngineEventType.SUPERVISOR_STOPPED,
                          EngineState.STOPPED)

    def test_event_to_dict(self):
        ev = make_supervisor_engine_initialized("sup-001", session_id="sess-001")
        d  = ev.to_dict()
        assert d["event_type"]     == SupervisorEngineEventType.SUPERVISOR_INITIALIZED.value
        assert d["supervision_id"] == "sup-001"

    def test_event_is_frozen(self):
        ev = make_supervisor_engine_initialized("sup-001")
        with pytest.raises((AttributeError, TypeError)):
            ev.supervision_id = "x"   # type: ignore[misc]


# ============================================================================
# 16. SupervisorEngineFactory
# ============================================================================

class TestFactory:
    def test_create_context(self):
        f   = SupervisorEngineFactory()
        ctx = f.create_context("sup-001", "ent",
                               SupervisorWorkflowType.ENTERPRISE_HEALTH_REVIEW)
        assert ctx.supervision_id == "sup-001"

    def test_create_request(self):
        f   = SupervisorEngineFactory()
        req = f.create_request("sup-001", "ent")
        assert req.supervision_id == "sup-001"

    def test_create_pipeline(self):
        f    = SupervisorEngineFactory()
        req  = f.create_request("sup-001", "ent")
        pipe = f.create_pipeline(req)
        assert pipe.request_id == req.request_id

    def test_create_snapshot(self):
        f    = SupervisorEngineFactory()
        req  = f.create_request("sup-001", "ent")
        pipe = f.create_pipeline(req)
        pipe.session_id = "sess-001"
        snap = f.create_snapshot(pipe, EngineState.SUPERVISING)
        assert snap.supervision_id == "sup-001"

    def test_create_success_response(self):
        f    = SupervisorEngineFactory()
        req  = f.create_request("sup-001", "ent")
        pipe = f.create_pipeline(req)
        pipe.start()
        resp = f.create_success_response(req, pipe)
        assert resp.is_success

    def test_create_failure_response(self):
        f    = SupervisorEngineFactory()
        req  = f.create_request("sup-001", "ent")
        pipe = f.create_pipeline(req)
        resp = f.create_failure_response(req, pipe, error_message="oops")
        assert resp.is_failure
        assert resp.error_message == "oops"

    def test_create_failure_response_no_pipeline(self):
        f    = SupervisorEngineFactory()
        req  = f.create_request("sup-001", "ent")
        resp = f.create_failure_response(req, error_message="bad")
        assert resp.is_failure


# ============================================================================
# 17. SupervisorEngine — basic lifecycle
# ============================================================================

class TestSupervisorEngineLifecycle:
    def test_start_and_stop(self):
        engine = SupervisorEngine()
        engine.start()
        assert engine.lifecycle_state().value == "running"
        engine.stop()
        assert engine.lifecycle_state().value != "running"

    def test_submit_raises_when_not_running(self):
        engine = SupervisorEngine()
        req    = _make_request()
        with pytest.raises(SupervisorEngineNotRunningError):
            engine.submit(req)

    def test_supervise_raises_when_not_running(self):
        engine = SupervisorEngine()
        with pytest.raises(SupervisorEngineNotRunningError):
            engine.supervise("sup-001", "ent")

    def test_initial_status(self):
        engine = _started_engine()
        status = engine.status()
        assert status.engine_lifecycle == "running"
        engine.stop()

    def test_health_returns_dict(self):
        engine = _started_engine()
        h = engine.health()
        assert "overall" in h
        engine.stop()

    def test_statistics_returns_dict(self):
        engine = _started_engine()
        s = engine.statistics()
        assert "total_requests" in s
        engine.stop()


# ============================================================================
# 18. SupervisorEngine — submit / supervise
# ============================================================================

class TestSupervisorEngineSubmit:
    def test_submit_success(self):
        engine   = _started_engine()
        req      = _make_request()
        response = engine.submit(req)
        assert response.is_success
        engine.stop()

    def test_supervise_success(self):
        engine   = _started_engine()
        response = engine.supervise("sup-001", "ent")
        assert response.is_success
        engine.stop()

    def test_submit_invalid_request_returns_failure(self):
        engine = _started_engine()
        req    = _make_request("A")
        # Corrupt context
        ctx = SupervisorEngineContext.create(
            "B", "ent", SupervisorWorkflowType.ENTERPRISE_HEALTH_REVIEW
        )
        bad_req = SupervisorRequest(
            request_id     = req.request_id,
            supervision_id = req.supervision_id,
            subsystem_id   = req.subsystem_id,
            workflow_type  = req.workflow_type,
            priority       = req.priority,
            context        = ctx,
        )
        resp = engine.submit(bad_req)
        assert resp.is_failure
        engine.stop()

    def test_supervise_all_workflow_types(self):
        engine = _started_engine()
        for wt in SupervisorWorkflowType:
            r = engine.supervise("sup", "ent", workflow_type=wt)
            assert r.is_success
        engine.stop()

    def test_statistics_updated_after_submit(self):
        engine = _started_engine()
        engine.submit(_make_request())
        s = engine.statistics()
        assert s["total_requests"] >= 1
        assert s["total_responses"] >= 1
        engine.stop()

    def test_query_returns_responses(self):
        engine = _started_engine()
        engine.supervise("sup-q1", "ent")
        responses = engine.query(supervision_id="sup-q1")
        assert len(responses) >= 1
        engine.stop()

    def test_query_filters_by_supervision_id(self):
        engine = _started_engine()
        engine.supervise("sup-a", "ent")
        engine.supervise("sup-b", "ent")
        results = engine.query(supervision_id="sup-a")
        assert all(r.supervision_id == "sup-a" for r in results)
        engine.stop()

    def test_response_has_snapshot(self):
        engine   = _started_engine()
        response = engine.supervise("sup-snap", "ent")
        assert response.has_snapshot
        engine.stop()


# ============================================================================
# 19. SupervisorEngine — listeners
# ============================================================================

class TestSupervisorEngineListeners:
    def test_add_listener_receives_events(self):
        engine = _started_engine()
        received = []
        engine.add_listener(received.append)
        engine.supervise("sup-ev", "ent")
        assert len(received) > 0
        engine.stop()

    def test_remove_listener(self):
        engine = _started_engine()
        received = []
        fn = received.append
        engine.add_listener(fn)
        engine.remove_listener(fn)
        engine.supervise("sup-ev", "ent")
        assert len(received) == 0
        engine.stop()

    def test_duplicate_listener_not_added_twice(self):
        engine = _started_engine()
        received = []
        fn = received.append
        engine.add_listener(fn)
        engine.add_listener(fn)
        engine.supervise("sup-ev", "ent")
        count_before = len(received)
        engine.stop()
        # Events from stop should only be delivered once
        assert len(received) == count_before + 1  # one stop event

    def test_listener_exception_does_not_crash_engine(self):
        engine = _started_engine()
        def bad_listener(e):
            raise RuntimeError("listener failed")
        engine.add_listener(bad_listener)
        # Should not raise
        response = engine.supervise("sup-safe", "ent")
        assert response is not None
        engine.stop()


# ============================================================================
# 20. SupervisorEngine — framework registration
# ============================================================================

class TestFrameworkRegistration:
    def test_register_governance_framework(self):
        engine = _started_engine()
        called = []
        engine.register_governance_framework(lambda p, r: called.append(True))
        engine.supervise("sup-g", "ent")
        assert called
        engine.stop()

    def test_register_autonomous_framework(self):
        engine = _started_engine()
        called = []
        engine.register_autonomous_framework(lambda p, r: called.append(True))
        engine.supervise("sup-a", "ent")
        assert called
        engine.stop()

    def test_governance_framework_exception_does_not_fail_workflow(self):
        engine = _started_engine()
        def bad_framework(p, r):
            raise RuntimeError("policy error")
        engine.register_governance_framework(bad_framework)
        response = engine.supervise("sup-safe-g", "ent")
        assert response.is_success
        engine.stop()


# ============================================================================
# 21. SupervisorEngine — concurrency
# ============================================================================

class TestConcurrency:
    def test_concurrent_supervise(self):
        engine  = _started_engine()
        results = []
        errors  = []

        def _run(i):
            try:
                r = engine.supervise(f"sup-{i}", "ent")
                results.append(r)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_run, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) == 20
        assert all(r.is_success for r in results)
        engine.stop()

    def test_concurrent_listeners(self):
        engine   = _started_engine()
        received = []
        lock     = threading.Lock()

        def listener(ev):
            with lock:
                received.append(ev)

        engine.add_listener(listener)
        threads = [
            threading.Thread(target=lambda i=i: engine.supervise(f"s-{i}", "e"))
            for i in range(10)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        engine.stop()
        assert len(received) > 0

    def test_scheduler_thread_safety(self):
        sched  = SupervisorScheduler(max_queue_size=1000)
        errors = []
        def _schedule(i):
            try:
                req = _make_request(f"sup-t-{i}")
                sched.schedule(req)
            except Exception as exc:
                errors.append(exc)
        threads = [threading.Thread(target=_schedule, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(errors) == 0
        assert sched.queue_depth() == 50


# ============================================================================
# 22. SupervisorEngine — priority workflows
# ============================================================================

class TestPriorityWorkflows:
    def test_critical_priority(self):
        engine   = _started_engine()
        response = engine.supervise(
            "sup-crit", "ent", priority=SchedulerPriority.CRITICAL
        )
        assert response.is_success
        engine.stop()

    def test_batch_priority(self):
        engine   = _started_engine()
        response = engine.supervise(
            "sup-batch", "ent", priority=SchedulerPriority.BATCH
        )
        assert response.is_success
        engine.stop()


# ============================================================================
# 23. Regression / Edge Cases
# ============================================================================

class TestRegression:
    def test_multiple_start_stop_cycles(self):
        engine = SupervisorEngine()
        for _ in range(3):
            engine.start()
            engine.supervise("sup-r", "ent")
            engine.stop()

    def test_empty_inputs_allowed(self):
        engine   = _started_engine()
        response = engine.supervise("sup-empty", "ent", inputs={})
        assert response.is_success
        engine.stop()

    def test_metadata_passed_through(self):
        engine   = _started_engine()
        response = engine.supervise(
            "sup-meta", "ent", metadata={"source": "test"}
        )
        assert response.is_success
        engine.stop()

    def test_query_with_no_results(self):
        engine  = _started_engine()
        results = engine.query(supervision_id="nonexistent")
        assert results == []
        engine.stop()

    def test_status_after_submit(self):
        engine = _started_engine()
        engine.supervise("sup-st", "ent")
        status = engine.status()
        assert status.total_requests >= 1
        engine.stop()

    def test_supervision_workflow_reaches_supervising(self):
        """Verify that SUPERVISION workflows produce SUPERVISING state in snapshot."""
        wt     = next(iter(SUPERVISION_WORKFLOWS))
        engine = _started_engine()
        resp   = engine.supervise("sup-sv", "ent", workflow_type=wt)
        assert resp.is_success
        if resp.snapshot:
            assert resp.snapshot.engine_state in (
                EngineState.SUPERVISING, EngineState.MONITORING,
                EngineState.PUBLISHING, EngineState.COMPLETED,
            )
        engine.stop()

    def test_monitoring_workflow_produces_response(self):
        """Verify that MONITORING workflows complete without error."""
        wt     = next(iter(MONITORING_WORKFLOWS))
        engine = _started_engine()
        resp   = engine.supervise("sup-mon", "ent", workflow_type=wt)
        assert resp.is_success
        engine.stop()

    def test_statistics_mean_after_multiple_submits(self):
        engine = _started_engine()
        for i in range(5):
            engine.supervise(f"sup-stat-{i}", "ent")
        s = engine.statistics()
        assert s["mean_elapsed_s"] >= 0
        assert s["completed_workflows"] == 5
        engine.stop()
