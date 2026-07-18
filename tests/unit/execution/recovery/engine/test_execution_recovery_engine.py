"""
tests/unit/execution/recovery/engine/test_execution_recovery_engine.py
=======================================================================
Comprehensive test suite for C7 Phase 1 M2 — Execution Recovery Engine.

Test classes
------------
TestConstants                — enums, limits, pipeline stage order
TestExceptions               — hierarchy, error codes, stored attributes
TestFailureContext           — factory, frozen, to_dict
TestExecutionSnapshots       — monitoring/gateway/risk frozen DTOs
TestRecoveryContext          — factory, frozen, properties, to_dict
TestRecoveryRequest          — factory, frozen, to_dict, priorities
TestRecoveryResponse         — factory helpers, status properties, to_dict
TestRecoveryEvents           — all 10 event types, immutability
TestRecoveryValidation       — request, failure, context, workflow, health
TestRecoveryStatistics       — accumulation, derived rates, thread safety
TestRecoveryHistory          — bounded deques, filtering, all item types
TestRecoverySnapshot         — factory, frozen, pipeline_progress, to_dict
TestRecoveryRegistry         — CRUD, bounded eviction, lifecycle guard
TestRecoveryPipeline         — stage lifecycle, complete/fail/skip, progress
TestRecoveryScheduler        — schedule, cancel, next, priority ordering
TestPolicyDecisionAndResult  — frozen DTOs, to_dict
TestRecoveryDispatcher       — null frameworks, port injection, dispatch
TestRecoverySessionManager   — create_session, lifecycle integration
TestRecoveryFactory          — create_request, create_context, create_snapshot
TestRecoveryManager          — full workflow, fail paths, port injection
TestExecutionRecoveryEngine  — start/stop, start_recovery, listeners, stats
TestWorkflowOrchestration    — complete end-to-end workflow
TestConcurrency              — concurrent start_recovery, statistics
TestStressTesting            — sequential high-volume requests
TestRegressionEdgeCases      — edge cases and boundary conditions
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Callable, Dict, List, Optional
from unittest.mock import MagicMock

import pytest

from iios.execution.recovery.engine import (
    ACTOR_MANAGER,
    ACTOR_SYSTEM,
    DEFAULT_MAX_CONCURRENT,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_REQUESTS,
    PIPELINE_STAGES_ORDERED,
    VERSION,
    DispatchResult,
    ExecutionGatewaySnapshot,
    ExecutionMonitoringSnapshot,
    ExecutionRecoveryEngine,
    ExecutionRiskSnapshot,
    FailoverFrameworkPort,
    FailoverResult,
    FailureContext,
    NullFailoverFramework,
    NullPolicyFramework,
    PipelineStage,
    PipelineStageRecord,
    PipelineStageStatus,
    PolicyDecision,
    PolicyFrameworkPort,
    RecoveryContext,
    RecoveryDispatchError,
    RecoveryDispatcher,
    RecoveryEngineError,
    RecoveryEngineEvent,
    RecoveryEngineEventType,
    RecoveryEngineNotRunningError,
    RecoveryEngineState,
    RecoveryEngineStatistics,
    RecoveryEngineValidationResult,
    RecoveryEngineValidator,
    RecoveryFactory,
    RecoveryEngineHistory,
    RecoveryManager,
    RecoveryOutcome,
    RecoveryPipeline,
    RecoveryPipelineError,
    RecoveryRegistry,
    RecoveryRequest,
    RecoveryRequestNotFoundError,
    RecoveryRequestPriority,
    RecoveryRequestType,
    RecoveryRequestValidationError,
    RecoveryResponse,
    RecoveryResponseStatus,
    RecoveryScheduler,
    RecoverySchedulerError,
    RecoverySessionManager,
    RecoverySnapshot,
    RecoverySnapshotError,
    SchedulerMode,
    make_engine_started,
    make_engine_stopped,
    make_failure_context,
    make_failure_detected,
    make_failure_response,
    make_recovery_completed,
    make_recovery_context,
    make_recovery_dispatched,
    make_recovery_failed,
    make_recovery_initialized,
    make_recovery_request,
    make_recovery_response,
    make_recovery_snapshot,
    make_recovery_started,
    make_recovery_stopped,
    make_recovery_verified,
    make_success_response,
)



# ── Helpers ───────────────────────────────────────────────────────────────────

def _sid() -> str:
    return f"exec-{uuid.uuid4().hex[:8]}"


def _sub() -> str:
    return f"sub-{uuid.uuid4().hex[:6]}"


def _fc(
    sub: Optional[str] = None,
    ftype: str = "GATEWAY_TIMEOUT",
    reason: str = "Connection lost",
) -> FailureContext:
    return make_failure_context(
        subsystem_id   = sub or _sub(),
        failure_type   = ftype,
        failure_reason = reason,
    )


def _req(
    sub: Optional[str] = None,
    priority: RecoveryRequestPriority = RecoveryRequestPriority.NORMAL,
    rtype: RecoveryRequestType = RecoveryRequestType.AUTOMATIC,
) -> RecoveryRequest:
    s = sub or _sub()
    return make_recovery_request(
        execution_session_id = _sid(),
        subsystem_id         = s,
        failure_context      = _fc(s),
        recovery_reason      = "test recovery",
        priority             = priority,
        request_type         = rtype,
    )


def _started_engine(**kwargs) -> ExecutionRecoveryEngine:
    eng = ExecutionRecoveryEngine(**kwargs)
    eng.start()
    return eng


# ─────────────────────────────────────────────────────────────────────────────
# 1  Constants
# ─────────────────────────────────────────────────────────────────────────────

class TestConstants:
    def test_version(self):
        assert isinstance(VERSION, str) and VERSION

    def test_engine_state_values(self):
        assert RecoveryEngineState.IDLE.value        == "idle"
        assert RecoveryEngineState.INITIALIZING.value == "initializing"
        assert RecoveryEngineState.COMPLETED.value    == "completed"
        assert RecoveryEngineState.FAILED.value       == "failed"
        assert RecoveryEngineState.STOPPED.value      == "stopped"

    def test_request_type_values(self):
        assert RecoveryRequestType.MANUAL.value       == "manual"
        assert RecoveryRequestType.AUTOMATIC.value    == "automatic"
        assert RecoveryRequestType.SCHEDULED.value    == "scheduled"
        assert RecoveryRequestType.EVENT_DRIVEN.value == "event_driven"
        assert RecoveryRequestType.PRIORITY.value     == "priority"

    def test_priority_ordering(self):
        assert RecoveryRequestPriority.LOW < RecoveryRequestPriority.NORMAL
        assert RecoveryRequestPriority.NORMAL < RecoveryRequestPriority.HIGH
        assert RecoveryRequestPriority.HIGH < RecoveryRequestPriority.CRITICAL
        assert RecoveryRequestPriority.CRITICAL < RecoveryRequestPriority.EMERGENCY

    def test_response_status_values(self):
        assert RecoveryResponseStatus.SUCCESS.value   == "success"
        assert RecoveryResponseStatus.FAILED.value    == "failed"
        assert RecoveryResponseStatus.CANCELLED.value == "cancelled"

    def test_outcome_values(self):
        assert RecoveryOutcome.RECOVERED.value         == "recovered"
        assert RecoveryOutcome.UNRECOVERABLE.value     == "unrecoverable"
        assert RecoveryOutcome.ABORTED.value           == "aborted"

    def test_event_type_values(self):
        assert RecoveryEngineEventType.RECOVERY_INITIALIZED.value == "recovery_initialized"
        assert RecoveryEngineEventType.RECOVERY_COMPLETED.value   == "recovery_completed"
        assert RecoveryEngineEventType.ENGINE_STARTED.value       == "engine_started"

    def test_pipeline_stages_ordered_coverage(self):
        assert len(PIPELINE_STAGES_ORDERED) == 10
        assert PIPELINE_STAGES_ORDERED[0]  == PipelineStage.VALIDATE_CONTEXT
        assert PIPELINE_STAGES_ORDERED[-1] == PipelineStage.FINALIZE

    def test_pipeline_stage_status_values(self):
        assert PipelineStageStatus.PENDING.value   == "pending"
        assert PipelineStageStatus.RUNNING.value   == "running"
        assert PipelineStageStatus.COMPLETED.value == "completed"
        assert PipelineStageStatus.FAILED.value    == "failed"
        assert PipelineStageStatus.SKIPPED.value   == "skipped"

    def test_scheduler_mode_values(self):
        assert SchedulerMode.AUTOMATIC.value    == "automatic"
        assert SchedulerMode.EVENT_DRIVEN.value == "event_driven"

    def test_default_limits_positive(self):
        assert DEFAULT_MAX_REQUESTS   >= 1
        assert DEFAULT_MAX_HISTORY    >= 1
        assert DEFAULT_MAX_CONCURRENT >= 1


# ─────────────────────────────────────────────────────────────────────────────
# 2  Exceptions
# ─────────────────────────────────────────────────────────────────────────────

class TestExceptions:
    def test_hierarchy(self):
        assert issubclass(RecoveryEngineNotRunningError,   RecoveryEngineError)
        assert issubclass(RecoveryRequestNotFoundError,    RecoveryEngineError)
        assert issubclass(RecoveryRequestValidationError,  RecoveryEngineError)
        assert issubclass(RecoveryDispatchError,           RecoveryEngineError)
        assert issubclass(RecoverySchedulerError,          RecoveryEngineError)
        assert issubclass(RecoveryPipelineError,           RecoveryEngineError)
        assert issubclass(RecoverySnapshotError,           RecoveryEngineError)

    def test_not_running(self):
        with pytest.raises(RecoveryEngineNotRunningError):
            raise RecoveryEngineNotRunningError()

    def test_request_not_found_stores_id(self):
        exc = RecoveryRequestNotFoundError("req-42")
        assert "req-42" in str(exc)
        assert exc.request_id == "req-42"

    def test_validation_error_stores_errors(self):
        exc = RecoveryRequestValidationError("bad", errors=("e1", "e2"))
        assert exc.errors == ("e1", "e2")

    def test_dispatch_error_stores_request_id(self):
        exc = RecoveryDispatchError("dispatch failed", request_id="r1")
        assert exc.request_id == "r1"

    def test_pipeline_error_stores_stage(self):
        exc = RecoveryPipelineError("stage failed", stage="assess_failure")
        assert exc.stage == "assess_failure"

    def test_error_codes_unique(self):
        classes = [
            RecoveryEngineError,
            RecoveryEngineNotRunningError,
            RecoveryRequestNotFoundError,
            RecoveryRequestValidationError,
            RecoveryDispatchError,
            RecoverySchedulerError,
            RecoveryPipelineError,
            RecoverySnapshotError,
        ]
        codes = [c.error_code for c in classes]
        assert len(codes) == len(set(codes))


# ─────────────────────────────────────────────────────────────────────────────
# 3  FailureContext
# ─────────────────────────────────────────────────────────────────────────────

class TestFailureContext:
    def test_factory(self):
        fc = make_failure_context("sub", "TIMEOUT", "connection lost")
        assert fc.subsystem_id   == "sub"
        assert fc.failure_type   == "TIMEOUT"
        assert fc.failure_reason == "connection lost"

    def test_frozen(self):
        fc = _fc()
        with pytest.raises((AttributeError, TypeError)):
            fc.failure_type = "x"  # type: ignore

    def test_auto_id(self):
        f1, f2 = _fc(), _fc()
        assert f1.failure_id != f2.failure_id

    def test_detected_at_auto(self):
        fc = _fc()
        assert fc.detected_at > 0

    def test_severity_default(self):
        fc = _fc()
        assert fc.severity == "MEDIUM"

    def test_affected_components(self):
        fc = make_failure_context("s", "T", "r", affected_components=("a", "b"))
        assert fc.affected_components == ("a", "b")

    def test_to_dict(self):
        fc = _fc()
        d = fc.to_dict()
        assert "failure_id"     in d
        assert "subsystem_id"   in d
        assert "failure_type"   in d
        assert "failure_reason" in d


# ─────────────────────────────────────────────────────────────────────────────
# 4  Execution Snapshots
# ─────────────────────────────────────────────────────────────────────────────

class TestExecutionSnapshots:
    def test_monitoring_snapshot_frozen(self):
        ms = ExecutionMonitoringSnapshot(
            snapshot_id="ms-1", captured_at=time.time(), is_healthy=True
        )
        with pytest.raises((AttributeError, TypeError)):
            ms.is_healthy = False  # type: ignore

    def test_monitoring_to_dict(self):
        ms = ExecutionMonitoringSnapshot(
            snapshot_id="ms-1", captured_at=time.time(), is_healthy=True,
            degraded_components=("comp-a",), error_count=2,
        )
        d = ms.to_dict()
        assert d["is_healthy"] is True
        assert d["error_count"] == 2
        assert "comp-a" in d["degraded_components"]

    def test_gateway_snapshot(self):
        gs = ExecutionGatewaySnapshot(
            snapshot_id="gs-1", captured_at=time.time(),
            is_connected=True, is_operational=True, latency_ms=5.0
        )
        assert gs.latency_ms == 5.0
        d = gs.to_dict()
        assert "is_connected" in d

    def test_risk_snapshot(self):
        rs = ExecutionRiskSnapshot(
            snapshot_id="rs-1", captured_at=time.time(),
            risk_level="HIGH", exposure=150_000.0, is_within_limits=False, breach_count=1,
        )
        assert not rs.is_within_limits
        d = rs.to_dict()
        assert d["risk_level"] == "HIGH"


# ─────────────────────────────────────────────────────────────────────────────
# 5  RecoveryContext
# ─────────────────────────────────────────────────────────────────────────────

class TestRecoveryContext:
    def test_factory(self):
        fc = _fc()
        ctx = make_recovery_context(_sid(), _sid(), _sub(), fc)
        assert ctx.failure_context is fc
        assert ctx.request_id

    def test_frozen(self):
        ctx = make_recovery_context(_sid(), _sid(), _sub(), _fc())
        with pytest.raises((AttributeError, TypeError)):
            ctx.subsystem_id = "x"  # type: ignore

    def test_has_monitoring_snapshot_false(self):
        ctx = make_recovery_context(_sid(), _sid(), _sub(), _fc())
        assert not ctx.has_monitoring_snapshot

    def test_has_monitoring_snapshot_true(self):
        ms = ExecutionMonitoringSnapshot(
            snapshot_id="ms", captured_at=time.time(), is_healthy=True
        )
        ctx = make_recovery_context(
            _sid(), _sid(), _sub(), _fc(), monitoring_snapshot=ms
        )
        assert ctx.has_monitoring_snapshot

    def test_failure_id_property(self):
        fc = _fc()
        ctx = make_recovery_context(_sid(), _sid(), fc.subsystem_id, fc)
        assert ctx.failure_id == fc.failure_id

    def test_failure_type_property(self):
        fc = make_failure_context("sub", "BROKER_DOWN", "broker offline")
        ctx = make_recovery_context(_sid(), _sid(), "sub", fc)
        assert ctx.failure_type == "BROKER_DOWN"

    def test_to_dict(self):
        ctx = make_recovery_context(_sid(), _sid(), _sub(), _fc())
        d = ctx.to_dict()
        assert "context_id"           in d
        assert "execution_session_id" in d
        assert "failure_context"      in d
        assert "framework_version"    in d

    def test_tags_and_metadata(self):
        ctx = make_recovery_context(
            _sid(), _sid(), _sub(), _fc(),
            tags=("tag1", "tag2"), metadata={"k": "v"},
        )
        assert ctx.tags == ("tag1", "tag2")
        assert ctx.metadata["k"] == "v"


# ─────────────────────────────────────────────────────────────────────────────
# 6  RecoveryRequest
# ─────────────────────────────────────────────────────────────────────────────

class TestRecoveryRequest:
    def test_factory(self):
        r = _req()
        assert r.request_id
        assert r.execution_session_id
        assert r.subsystem_id
        assert r.priority == RecoveryRequestPriority.NORMAL

    def test_frozen(self):
        r = _req()
        with pytest.raises((AttributeError, TypeError)):
            r.subsystem_id = "x"  # type: ignore

    def test_unique_ids(self):
        r1, r2 = _req(), _req()
        assert r1.request_id != r2.request_id

    def test_priority_levels(self):
        for prio in RecoveryRequestPriority:
            r = _req(priority=prio)
            assert r.priority == prio

    def test_request_types(self):
        for rtype in RecoveryRequestType:
            r = _req(rtype=rtype)
            assert r.request_type == rtype

    def test_to_dict(self):
        r = _req()
        d = r.to_dict()
        assert "request_id"           in d
        assert "request_type"         in d
        assert "priority"             in d
        assert "execution_session_id" in d
        assert "failure_context"      in d

    def test_requester_default(self):
        r = _req()
        assert r.requester == ACTOR_SYSTEM

    def test_custom_request_id(self):
        r = make_recovery_request(
            _sid(), _sub(), _fc(), "test", request_id="custom-id-1"
        )
        assert r.request_id == "custom-id-1"


# ─────────────────────────────────────────────────────────────────────────────
# 7  RecoveryResponse
# ─────────────────────────────────────────────────────────────────────────────

class TestRecoveryResponse:
    def test_success_factory(self):
        r = make_success_response("req-1", "sess-1", "sub-1", started_at=time.time() - 1.0)
        assert r.is_success
        assert r.duration_ms > 0
        assert r.outcome == RecoveryOutcome.RECOVERED

    def test_failure_factory(self):
        r = make_failure_response("req-1", "sess-1", "sub-1", "broker crashed")
        assert r.is_failure
        assert r.error_message == "broker crashed"
        assert r.outcome == RecoveryOutcome.UNRECOVERABLE

    def test_frozen(self):
        r = make_success_response("r", "s", "sub")
        with pytest.raises((AttributeError, TypeError)):
            r.status = RecoveryResponseStatus.FAILED  # type: ignore

    def test_pipeline_completion_rate_zero(self):
        r = make_success_response("r", "s", "sub")
        assert r.pipeline_completion_rate == 0.0

    def test_pipeline_completion_rate(self):
        r = make_recovery_response(
            "r", "s", RecoveryResponseStatus.SUCCESS, RecoveryOutcome.RECOVERED,
            "sub", pipeline_stages_completed=8, pipeline_stages_total=10,
        )
        assert abs(r.pipeline_completion_rate - 0.8) < 1e-9

    def test_to_dict(self):
        r = make_success_response("r", "s", "sub")
        d = r.to_dict()
        assert "response_id"   in d
        assert "request_id"    in d
        assert "status"        in d
        assert "outcome"       in d
        assert "duration_ms"   in d


# ─────────────────────────────────────────────────────────────────────────────
# 8  RecoveryEngineEvents
# ─────────────────────────────────────────────────────────────────────────────

class TestRecoveryEvents:
    def _assert_event(self, ev: RecoveryEngineEvent, etype: RecoveryEngineEventType):
        assert ev.event_type  == etype
        assert ev.event_id
        assert ev.occurred_at > 0
        assert ev.version     == VERSION

    def test_recovery_initialized(self):
        ev = make_recovery_initialized("r", "s")
        self._assert_event(ev, RecoveryEngineEventType.RECOVERY_INITIALIZED)

    def test_recovery_started(self):
        ev = make_recovery_started("r", "s")
        self._assert_event(ev, RecoveryEngineEventType.RECOVERY_STARTED)

    def test_failure_detected(self):
        ev = make_failure_detected("r", "s", reason="timeout")
        self._assert_event(ev, RecoveryEngineEventType.FAILURE_DETECTED)
        assert ev.reason == "timeout"

    def test_recovery_dispatched(self):
        ev = make_recovery_dispatched("r", "s")
        self._assert_event(ev, RecoveryEngineEventType.RECOVERY_DISPATCHED)

    def test_recovery_verified(self):
        ev = make_recovery_verified("r", "s")
        self._assert_event(ev, RecoveryEngineEventType.RECOVERY_VERIFIED)

    def test_recovery_completed(self):
        ev = make_recovery_completed("r", "s")
        self._assert_event(ev, RecoveryEngineEventType.RECOVERY_COMPLETED)

    def test_recovery_failed(self):
        ev = make_recovery_failed("r", "s", reason="crash")
        self._assert_event(ev, RecoveryEngineEventType.RECOVERY_FAILED)

    def test_recovery_stopped(self):
        ev = make_recovery_stopped("r", "s")
        self._assert_event(ev, RecoveryEngineEventType.RECOVERY_STOPPED)

    def test_engine_started(self):
        ev = make_engine_started(actor="test")
        self._assert_event(ev, RecoveryEngineEventType.ENGINE_STARTED)
        assert ev.actor == "test"

    def test_engine_stopped(self):
        ev = make_engine_stopped()
        self._assert_event(ev, RecoveryEngineEventType.ENGINE_STOPPED)

    def test_unique_event_ids(self):
        e1 = make_recovery_started("r", "s")
        e2 = make_recovery_started("r", "s")
        assert e1.event_id != e2.event_id

    def test_immutable(self):
        ev = make_recovery_started("r", "s")
        with pytest.raises((AttributeError, TypeError)):
            ev.event_id = "x"  # type: ignore

    def test_to_dict(self):
        ev = make_recovery_started("r", "s", actor="mgr", reason="init")
        d = ev.to_dict()
        assert d["actor"]  == "mgr"
        assert d["reason"] == "init"


# ─────────────────────────────────────────────────────────────────────────────
# 9  Validation
# ─────────────────────────────────────────────────────────────────────────────

class TestRecoveryValidation:
    def setup_method(self):
        self.v = RecoveryEngineValidator()

    def test_valid_request(self):
        r = self.v.validate_request(_req())
        assert r.is_valid

    def test_empty_exec_session_fails(self):
        m = MagicMock()
        m.request_id           = "r1"
        m.execution_session_id = ""
        m.subsystem_id         = "sub"
        m.recovery_reason      = "reason"
        m.failure_context      = _fc()
        r = self.v.validate_request(m)
        assert not r.is_valid

    def test_none_failure_context_fails(self):
        m = MagicMock()
        m.request_id           = "r1"
        m.execution_session_id = "e"
        m.subsystem_id         = "sub"
        m.recovery_reason      = "reason"
        m.failure_context      = None
        r = self.v.validate_request(m)
        assert not r.is_valid

    def test_empty_reason_warning(self):
        m = MagicMock()
        m.request_id           = "r1"
        m.execution_session_id = "e"
        m.subsystem_id         = "sub"
        m.recovery_reason      = ""
        m.failure_context      = _fc()
        r = self.v.validate_request(m)
        assert r.is_valid   # warning only
        assert r.warnings

    def test_valid_failure_context(self):
        r = self.v.validate_failure_context(_fc())
        assert r.is_valid

    def test_empty_failure_type_fails(self):
        fc = make_failure_context("sub", "", "reason")
        r = self.v.validate_failure_context(fc)
        assert not r.is_valid

    def test_valid_context(self):
        fc  = _fc()
        ctx = make_recovery_context(_sid(), _sid(), _sub(), fc)
        r = self.v.validate_context(ctx)
        assert r.is_valid

    def test_context_no_snapshots_warns(self):
        ctx = make_recovery_context(_sid(), _sid(), _sub(), _fc())
        r = self.v.validate_context(ctx)
        assert r.is_valid
        assert r.warnings   # no snapshots warning

    def test_valid_workflow_consistency(self):
        ordered = [s.value for s in PIPELINE_STAGES_ORDERED]
        completed = [ordered[0], ordered[1], ordered[2]]
        r = self.v.validate_workflow_consistency(ordered, completed)
        assert r.is_valid

    def test_out_of_order_workflow_fails(self):
        ordered = [s.value for s in PIPELINE_STAGES_ORDERED]
        # Reverse order — should fail
        completed = [ordered[2], ordered[0]]
        r = self.v.validate_workflow_consistency(ordered, completed)
        assert not r.is_valid

    def test_subsystem_health_valid(self):
        ms = ExecutionMonitoringSnapshot(
            snapshot_id="ms-1", captured_at=time.time(), is_healthy=True
        )
        r = self.v.validate_subsystem_health(ms)
        assert r.is_valid

    def test_subsystem_health_high_errors_warns(self):
        ms = ExecutionMonitoringSnapshot(
            snapshot_id="ms-1", captured_at=time.time(), is_healthy=False, error_count=200
        )
        r = self.v.validate_subsystem_health(ms)
        assert r.is_valid  # warning, not error
        assert r.warnings

    def test_lifecycle_consistency_valid(self):
        r = self.v.validate_lifecycle_consistency("req-1", "sess-1", "req-1")
        assert r.is_valid

    def test_lifecycle_consistency_mismatch_fails(self):
        r = self.v.validate_lifecycle_consistency("req-1", "sess-1", "req-DIFFERENT")
        assert not r.is_valid

    def test_result_add_error(self):
        vr = RecoveryEngineValidationResult()
        assert vr.is_valid
        vr.add_error("bad")
        assert not vr.is_valid

    def test_result_add_warning(self):
        vr = RecoveryEngineValidationResult()
        vr.add_warning("note")
        assert vr.is_valid
        assert "note" in vr.warnings

    def test_result_to_dict(self):
        vr = RecoveryEngineValidationResult()
        vr.add_error("e1")
        d = vr.to_dict()
        assert "is_valid" in d
        assert "errors"   in d
        assert "warnings" in d


# ─────────────────────────────────────────────────────────────────────────────
# 10  Statistics
# ─────────────────────────────────────────────────────────────────────────────

class TestRecoveryStatistics:
    def test_initial_zeros(self):
        s = RecoveryEngineStatistics()
        assert s.total_requests      == 0
        assert s.sessions_completed  == 0
        assert s.success_rate        == 0.0

    def test_record_request(self):
        s = RecoveryEngineStatistics()
        s.record_request()
        assert s.total_requests == 1

    def test_record_initiated(self):
        s = RecoveryEngineStatistics()
        s.record_initiated()
        assert s.sessions_initiated == 1

    def test_record_completed(self):
        s = RecoveryEngineStatistics()
        s.record_completed(200.0)
        assert s.sessions_completed   == 1
        assert s.average_recovery_time_ms == 200.0

    def test_success_rate(self):
        s = RecoveryEngineStatistics()
        s.record_completed(100.0)
        s.record_completed(100.0)
        s.record_failed()
        assert abs(s.success_rate - (2/3)) < 1e-9

    def test_failure_rate(self):
        s = RecoveryEngineStatistics()
        s.record_failed()
        assert s.failure_rate == 1.0

    def test_record_cancelled(self):
        s = RecoveryEngineStatistics()
        s.record_cancelled()
        assert s.sessions_cancelled == 1

    def test_record_transition(self):
        s = RecoveryEngineStatistics()
        s.record_transition()
        assert s.total_transitions == 1

    def test_record_verification(self):
        s = RecoveryEngineStatistics()
        s.record_verification(successful=True)
        s.record_verification(successful=False)
        assert s.total_verifications         == 2
        assert s.successful_verifications    == 1
        assert s.verification_success_rate   == 0.5

    def test_subsystem_availability(self):
        s = RecoveryEngineStatistics()
        s.record_initiated()
        s.record_initiated()
        s.record_completed(0.0)
        assert s.subsystem_availability == 0.5

    def test_reset(self):
        s = RecoveryEngineStatistics()
        s.record_request()
        s.record_completed(100.0)
        s.reset()
        assert s.total_requests     == 0
        assert s.sessions_completed == 0

    def test_copy_independent(self):
        s = RecoveryEngineStatistics()
        s.record_completed(100.0)
        c = s.copy()
        s.record_completed(200.0)
        assert c.sessions_completed == 1
        assert s.sessions_completed == 2

    def test_to_dict(self):
        s = RecoveryEngineStatistics()
        d = s.to_dict()
        assert "total_requests"            in d
        assert "sessions_completed"        in d
        assert "average_recovery_time_ms"  in d
        assert "verification_success_rate" in d

    def test_thread_safe_increments(self):
        s = RecoveryEngineStatistics()
        threads = [
            threading.Thread(target=lambda: [s.record_request() for _ in range(50)])
            for _ in range(10)
        ]
        for t in threads: t.start()
        for t in threads: t.join()
        assert s.total_requests == 500


# ─────────────────────────────────────────────────────────────────────────────
# 11  History
# ─────────────────────────────────────────────────────────────────────────────

class TestRecoveryHistory:
    def test_append_request(self):
        h = RecoveryEngineHistory()
        r = _req()
        h.append_request(r)
        assert h.request_count == 1
        assert h.latest_request() is r

    def test_bounded_requests(self):
        h = RecoveryEngineHistory(max_requests=3)
        for _ in range(5):
            h.append_request(_req())
        assert h.request_count == 3

    def test_requests_for_subsystem(self):
        h = RecoveryEngineHistory()
        sub = _sub()
        r1 = make_recovery_request(_sid(), sub, _fc(sub), "t")
        r2 = _req()
        h.append_request(r1)
        h.append_request(r2)
        assert len(h.requests_for_subsystem(sub)) == 1

    def test_append_response(self):
        h = RecoveryEngineHistory()
        r = make_success_response("r", "s", "sub")
        h.append_response(r)
        assert h.response_count == 1

    def test_successful_responses(self):
        h = RecoveryEngineHistory()
        h.append_response(make_success_response("r1", "s", "sub"))
        h.append_response(make_failure_response("r2", "s", "sub", "err"))
        assert len(h.successful_responses()) == 1
        assert len(h.failed_responses())     == 1

    def test_append_event(self):
        h = RecoveryEngineHistory()
        ev = make_recovery_started("r", "s")
        h.append_event(ev)
        assert h.event_count == 1

    def test_events_for_request(self):
        h = RecoveryEngineHistory()
        h.append_event(make_recovery_started("r1", "s"))
        h.append_event(make_recovery_started("r2", "s"))
        assert len(h.events_for_request("r1")) == 1

    def test_events_matching(self):
        h = RecoveryEngineHistory()
        h.append_event(make_recovery_started("r", "s"))
        h.append_event(make_recovery_completed("r", "s"))
        found = h.events_matching(
            lambda e: e.event_type == RecoveryEngineEventType.RECOVERY_COMPLETED
        )
        assert len(found) == 1

    def test_append_snapshot(self):
        h = RecoveryEngineHistory()
        snap = make_recovery_snapshot(
            "s", "r", "sub", RecoveryEngineState.COMPLETED, None,
            10, 10, "T", "MEDIUM", "r", RecoveryOutcome.RECOVERED, is_complete=True
        )
        h.append_snapshot(snap)
        assert h.snapshot_count == 1

    def test_snapshots_for_session(self):
        h = RecoveryEngineHistory()
        snap = make_recovery_snapshot(
            "sess-1", "r", "sub", RecoveryEngineState.COMPLETED, None,
            10, 10, "T", "M", "r", RecoveryOutcome.RECOVERED
        )
        h.append_snapshot(snap)
        h.append_snapshot(make_recovery_snapshot(
            "sess-2", "r", "sub", RecoveryEngineState.COMPLETED, None,
            10, 10, "T", "M", "r", RecoveryOutcome.RECOVERED
        ))
        assert len(h.snapshots_for_session("sess-1")) == 1

    def test_clear(self):
        h = RecoveryEngineHistory()
        h.append_request(_req())
        h.append_event(make_recovery_started("r", "s"))
        h.clear()
        assert h.request_count == 0
        assert h.event_count   == 0

    def test_latest_none_when_empty(self):
        h = RecoveryEngineHistory()
        assert h.latest_request()  is None
        assert h.latest_response() is None
        assert h.latest_event()    is None
        assert h.latest_snapshot() is None


# ─────────────────────────────────────────────────────────────────────────────
# 12  RecoverySnapshot
# ─────────────────────────────────────────────────────────────────────────────

class TestRecoverySnapshot:
    def test_factory(self):
        snap = make_recovery_snapshot(
            "sess", "req", "sub", RecoveryEngineState.COMPLETED,
            PipelineStage.FINALIZE, 10, 10, "TIMEOUT", "MEDIUM", "lost",
            RecoveryOutcome.RECOVERED, is_complete=True,
        )
        assert snap.is_complete
        assert snap.pipeline_progress == 1.0

    def test_frozen(self):
        snap = make_recovery_snapshot(
            "s", "r", "sub", RecoveryEngineState.IDLE, None,
            5, 10, "T", "M", "r", RecoveryOutcome.UNKNOWN
        )
        with pytest.raises((AttributeError, TypeError)):
            snap.is_complete = True  # type: ignore

    def test_pipeline_progress_partial(self):
        snap = make_recovery_snapshot(
            "s", "r", "sub", RecoveryEngineState.RECOVERING, None,
            6, 10, "T", "M", "r", RecoveryOutcome.UNKNOWN
        )
        assert abs(snap.pipeline_progress - 0.6) < 1e-9

    def test_pipeline_progress_zero_total(self):
        snap = make_recovery_snapshot(
            "s", "r", "sub", RecoveryEngineState.IDLE, None,
            0, 0, "T", "M", "r", RecoveryOutcome.UNKNOWN
        )
        assert snap.pipeline_progress == 0.0

    def test_to_dict(self):
        snap = make_recovery_snapshot(
            "s", "r", "sub", RecoveryEngineState.COMPLETED, PipelineStage.FINALIZE,
            10, 10, "T", "HIGH", "r", RecoveryOutcome.RECOVERED, is_complete=True,
        )
        d = snap.to_dict()
        assert d["engine_state"]     == "completed"
        assert d["failure_severity"] == "HIGH"
        assert d["is_complete"] is True

    def test_unique_snapshot_ids(self):
        def _s():
            return make_recovery_snapshot(
                "s", "r", "sub", RecoveryEngineState.IDLE, None,
                0, 0, "T", "M", "r", RecoveryOutcome.UNKNOWN
            )
        assert _s().snapshot_id != _s().snapshot_id


# ─────────────────────────────────────────────────────────────────────────────
# 13  RecoveryRegistry
# ─────────────────────────────────────────────────────────────────────────────

class TestRecoveryRegistry:
    def _started(self) -> RecoveryRegistry:
        reg = RecoveryRegistry()
        reg.start()
        return reg

    def test_store_and_get(self):
        reg = self._started()
        r = _req()
        reg.store(r)
        assert reg.get(r.request_id) is r
        reg.stop()

    def test_get_missing_raises(self):
        reg = self._started()
        with pytest.raises(RecoveryRequestNotFoundError):
            reg.get("nonexistent")
        reg.stop()

    def test_find_returns_none(self):
        reg = self._started()
        assert reg.find("x") is None
        reg.stop()

    def test_archive_moves(self):
        reg = self._started()
        r = _req()
        reg.store(r)
        reg.archive(r.request_id)
        assert reg.find(r.request_id) is None
        assert reg.find_archived(r.request_id) is r
        reg.stop()

    def test_archive_missing_raises(self):
        reg = self._started()
        with pytest.raises(RecoveryRequestNotFoundError):
            reg.archive("nonexistent")
        reg.stop()

    def test_for_subsystem(self):
        reg = self._started()
        sub = _sub()
        r1 = make_recovery_request(_sid(), sub, _fc(sub), "t")
        r2 = _req()
        reg.store(r1)
        reg.store(r2)
        results = reg.for_subsystem(sub)
        assert len(results) == 1
        reg.stop()

    def test_contains(self):
        reg = self._started()
        r = _req()
        reg.store(r)
        assert reg.contains(r.request_id)
        assert not reg.contains("x")
        reg.stop()

    def test_bounded_eviction(self):
        reg = RecoveryRegistry(max_requests=2)
        reg.start()
        for _ in range(5):
            reg.store(_req())
        assert reg.count == 2
        reg.stop()

    def test_not_started_raises(self):
        reg = RecoveryRegistry()
        with pytest.raises(RecoveryEngineNotRunningError):
            reg.store(_req())

    def test_clear(self):
        reg = self._started()
        reg.store(_req())
        reg.clear()
        assert reg.count == 0
        reg.stop()


# ─────────────────────────────────────────────────────────────────────────────
# 14  RecoveryPipeline
# ─────────────────────────────────────────────────────────────────────────────

class TestRecoveryPipeline:
    def _pipeline(self) -> RecoveryPipeline:
        return RecoveryPipeline("req-1", "sess-1")

    def test_initial_state(self):
        p = self._pipeline()
        assert not p.is_complete
        assert not p.is_failed
        assert p.stages_completed == 0
        assert p.stages_total     == 10

    def test_current_stage_initial(self):
        p = self._pipeline()
        assert p.current_stage == PipelineStage.VALIDATE_CONTEXT

    def test_complete_stage_advances(self):
        p = self._pipeline()
        p.start_stage(PipelineStage.VALIDATE_CONTEXT)
        p.complete_stage(PipelineStage.VALIDATE_CONTEXT)
        assert p.stages_completed == 1
        assert p.current_stage == PipelineStage.INITIALIZE_SESSION

    def test_fail_stage(self):
        p = self._pipeline()
        p.start_stage(PipelineStage.VALIDATE_CONTEXT)
        p.fail_stage(PipelineStage.VALIDATE_CONTEXT, "invalid request")
        assert p.is_failed
        assert p.failed_stage == PipelineStage.VALIDATE_CONTEXT

    def test_skip_stage(self):
        p = self._pipeline()
        p.skip_stage(PipelineStage.COORDINATE_FAILOVER)
        assert p.stages_completed == 1

    def test_complete_all_stages(self):
        p = self._pipeline()
        for stage in PIPELINE_STAGES_ORDERED:
            p.start_stage(stage)
            p.complete_stage(stage)
        assert p.is_complete
        assert not p.is_failed

    def test_start_completed_stage_raises(self):
        """Starting an already-completed stage raises RecoveryPipelineError."""
        p = self._pipeline()
        p.start_stage(PipelineStage.VALIDATE_CONTEXT)
        p.complete_stage(PipelineStage.VALIDATE_CONTEXT)
        with pytest.raises(RecoveryPipelineError):
            p.start_stage(PipelineStage.VALIDATE_CONTEXT)  # already COMPLETED

    def test_get_stage_record(self):
        p = self._pipeline()
        rec = p.get_stage_record(PipelineStage.ASSESS_FAILURE)
        assert rec is not None
        assert rec.status == PipelineStageStatus.PENDING

    def test_to_dict(self):
        p = self._pipeline()
        d = p.to_dict()
        assert "request_id"       in d
        assert "is_complete"      in d
        assert "stages_completed" in d
        assert "stages"           in d

    def test_stage_record_duration(self):
        p = self._pipeline()
        p.start_stage(PipelineStage.VALIDATE_CONTEXT)
        time.sleep(0.01)
        p.complete_stage(PipelineStage.VALIDATE_CONTEXT)
        rec = p.get_stage_record(PipelineStage.VALIDATE_CONTEXT)
        assert rec.duration_ms > 0


# ─────────────────────────────────────────────────────────────────────────────
# 15  RecoveryScheduler
# ─────────────────────────────────────────────────────────────────────────────

class TestRecoveryScheduler:
    def _started(self, **kwargs) -> RecoveryScheduler:
        s = RecoveryScheduler(**kwargs)
        s.start()
        return s

    def test_schedule_and_next(self):
        sch = self._started()
        r = _req()
        sch.schedule(r)
        assert sch.queue_size == 1
        out = sch.next()
        assert out is r
        assert sch.is_empty
        sch.stop()

    def test_priority_ordering(self):
        sch = self._started()
        r_low    = _req(priority=RecoveryRequestPriority.LOW)
        r_high   = _req(priority=RecoveryRequestPriority.HIGH)
        r_normal = _req(priority=RecoveryRequestPriority.NORMAL)
        sch.schedule(r_low)
        sch.schedule(r_normal)
        sch.schedule(r_high)
        assert sch.next().priority == RecoveryRequestPriority.HIGH
        assert sch.next().priority == RecoveryRequestPriority.NORMAL
        assert sch.next().priority == RecoveryRequestPriority.LOW
        sch.stop()

    def test_cancel(self):
        sch = self._started()
        r = _req()
        sch.schedule(r)
        result = sch.cancel(r.request_id)
        assert result is True
        assert sch.next() is None  # cancelled — skipped
        sch.stop()

    def test_cancel_nonexistent_returns_false(self):
        sch = self._started()
        assert sch.cancel("nonexistent") is False
        sch.stop()

    def test_peek_does_not_remove(self):
        sch = self._started()
        r = _req()
        sch.schedule(r)
        assert sch.peek() is r
        assert sch.queue_size == 1
        sch.stop()

    def test_drain(self):
        sch = self._started()
        for _ in range(5):
            sch.schedule(_req())
        items = sch.drain()
        assert len(items) == 5
        assert sch.is_empty
        sch.stop()

    def test_queue_full_raises(self):
        sch = self._started(max_queue_size=2)
        sch.schedule(_req())
        sch.schedule(_req())
        with pytest.raises(RecoverySchedulerError):
            sch.schedule(_req())
        sch.stop()

    def test_fifo_same_priority(self):
        sch = self._started()
        r1 = _req()
        r2 = _req()
        sch.schedule(r1)
        sch.schedule(r2)
        assert sch.next() is r1   # FIFO within same priority
        assert sch.next() is r2
        sch.stop()

    def test_not_started_raises(self):
        sch = RecoveryScheduler()
        with pytest.raises(RecoveryEngineNotRunningError):
            sch.schedule(_req())

    def test_mode(self):
        sch = self._started(mode=SchedulerMode.MANUAL)
        assert sch.mode == SchedulerMode.MANUAL
        sch.mode = SchedulerMode.AUTOMATIC
        assert sch.mode == SchedulerMode.AUTOMATIC
        sch.stop()


# ─────────────────────────────────────────────────────────────────────────────
# 16  PolicyDecision and FailoverResult
# ─────────────────────────────────────────────────────────────────────────────

class TestPolicyDecisionAndResult:
    def test_policy_decision_frozen(self):
        pd = PolicyDecision(approved=True, plan_id="p1")
        with pytest.raises((AttributeError, TypeError)):
            pd.approved = False  # type: ignore

    def test_policy_decision_to_dict(self):
        pd = PolicyDecision(approved=True, requires_failover=True, plan_id="p1")
        d = pd.to_dict()
        assert d["approved"] is True
        assert d["requires_failover"] is True

    def test_failover_result_frozen(self):
        fr = FailoverResult(triggered=True, result="ok")
        with pytest.raises((AttributeError, TypeError)):
            fr.triggered = False  # type: ignore

    def test_failover_result_to_dict(self):
        fr = FailoverResult(triggered=False, result="none")
        d = fr.to_dict()
        assert d["triggered"] is False


# ─────────────────────────────────────────────────────────────────────────────
# 17  RecoveryDispatcher
# ─────────────────────────────────────────────────────────────────────────────

class TestRecoveryDispatcher:
    def _started(self, policy=None, failover=None) -> RecoveryDispatcher:
        d = RecoveryDispatcher(policy_framework=policy, failover_framework=failover)
        d.start()
        return d

    def test_dispatch_null_frameworks(self):
        d = self._started()
        req = _req()
        ctx = make_recovery_context(req.request_id, req.execution_session_id,
                                    req.subsystem_id, req.failure_context)
        result = d.dispatch(req, ctx)
        assert result.dispatched
        assert result.policy_decision.approved
        assert result.failover_result is None
        d.stop()

    def test_dispatch_with_failover_required(self):
        class _PolicyWithFailover(PolicyFrameworkPort):
            def invoke(self, req, ctx):
                return PolicyDecision(approved=True, requires_failover=True)

        d = self._started(policy=_PolicyWithFailover())
        req = _req()
        ctx = make_recovery_context(req.request_id, req.execution_session_id,
                                    req.subsystem_id, req.failure_context)
        result = d.dispatch(req, ctx)
        assert result.dispatched
        assert result.failover_result is not None
        assert not result.failover_result.triggered  # NullFailoverFramework
        d.stop()

    def test_dispatch_policy_rejection(self):
        class _RejectingPolicy(PolicyFrameworkPort):
            def invoke(self, req, ctx):
                return PolicyDecision(approved=False)

        d = self._started(policy=_RejectingPolicy())
        req = _req()
        ctx = make_recovery_context(req.request_id, req.execution_session_id,
                                    req.subsystem_id, req.failure_context)
        result = d.dispatch(req, ctx)
        assert not result.dispatched
        d.stop()

    def test_dispatch_policy_error_raises(self):
        class _BrokenPolicy(PolicyFrameworkPort):
            def invoke(self, req, ctx):
                raise RuntimeError("policy crashed")

        d = self._started(policy=_BrokenPolicy())
        req = _req()
        ctx = make_recovery_context(req.request_id, req.execution_session_id,
                                    req.subsystem_id, req.failure_context)
        with pytest.raises(RecoveryDispatchError):
            d.dispatch(req, ctx)
        d.stop()

    def test_port_injection_at_runtime(self):
        d = self._started()
        class _CustomPolicy(PolicyFrameworkPort):
            def invoke(self, req, ctx):
                return PolicyDecision(approved=True, plan_id="custom-plan")
        d.set_policy_framework(_CustomPolicy())
        req = _req()
        ctx = make_recovery_context(req.request_id, req.execution_session_id,
                                    req.subsystem_id, req.failure_context)
        result = d.dispatch(req, ctx)
        assert result.policy_decision.plan_id == "custom-plan"
        d.stop()

    def test_not_started_raises(self):
        d = RecoveryDispatcher()
        with pytest.raises(RecoveryEngineNotRunningError):
            d.dispatch(_req(), MagicMock())

    def test_dispatch_result_immutable(self):
        d = self._started()
        req = _req()
        ctx = make_recovery_context(req.request_id, req.execution_session_id,
                                    req.subsystem_id, req.failure_context)
        result = d.dispatch(req, ctx)
        with pytest.raises((AttributeError, TypeError)):
            result.dispatched = False  # type: ignore
        d.stop()


# ─────────────────────────────────────────────────────────────────────────────
# 18  RecoverySessionManager
# ─────────────────────────────────────────────────────────────────────────────

class TestRecoverySessionManager:
    def _started(self) -> RecoverySessionManager:
        mgr = RecoverySessionManager()
        mgr.start()
        return mgr

    def test_create_session(self):
        mgr = self._started()
        req = _req()
        ctx = make_recovery_context(req.request_id, req.execution_session_id,
                                    req.subsystem_id, req.failure_context)
        session = mgr.create_session(req, ctx)
        assert session is not None
        assert session.execution_session_id == req.execution_session_id
        mgr.stop()

    def test_get_session_for_request(self):
        mgr = self._started()
        req = _req()
        ctx = make_recovery_context(req.request_id, req.execution_session_id,
                                    req.subsystem_id, req.failure_context)
        mgr.create_session(req, ctx)
        s = mgr.get_session_for_request(req.request_id)
        assert s is not None
        mgr.stop()

    def test_get_session_for_unknown_request(self):
        mgr = self._started()
        assert mgr.get_session_for_request("unknown") is None
        mgr.stop()

    def test_initialize(self):
        from iios.execution.recovery.lifecycle import RecoveryState
        mgr = self._started()
        req = _req()
        ctx = make_recovery_context(req.request_id, req.execution_session_id,
                                    req.subsystem_id, req.failure_context)
        mgr.create_session(req, ctx)
        mgr.initialize(req.request_id)
        s = mgr.get_session_for_request(req.request_id)
        assert s.state == RecoveryState.INITIALIZING
        mgr.stop()

    def test_full_happy_path(self):
        from iios.execution.recovery.lifecycle import RecoveryState
        mgr = self._started()
        req = _req()
        ctx = make_recovery_context(req.request_id, req.execution_session_id,
                                    req.subsystem_id, req.failure_context)
        mgr.create_session(req, ctx)
        mgr.initialize(req.request_id)
        mgr.detect(req.request_id)
        mgr.assess(req.request_id)
        mgr.ready(req.request_id)
        mgr.begin_recovery(req.request_id)
        mgr.verify(req.request_id)
        mgr.complete(req.request_id)
        s = mgr.get_session_for_request(req.request_id)
        assert s.is_completed
        mgr.stop()

    def test_fail_gracefully_if_no_session(self):
        mgr = self._started()
        mgr.fail("nonexistent", "reason")  # should not raise
        mgr.stop()

    def test_not_started_raises(self):
        mgr = RecoverySessionManager()
        with pytest.raises(RecoveryEngineNotRunningError):
            mgr.create_session(_req(), MagicMock())


# ─────────────────────────────────────────────────────────────────────────────
# 19  RecoveryFactory
# ─────────────────────────────────────────────────────────────────────────────

class TestRecoveryFactory:
    def _started(self) -> RecoveryFactory:
        f = RecoveryFactory()
        f.start()
        return f

    def test_create_failure_context(self):
        f = self._started()
        fc = f.create_failure_context("sub", "TIMEOUT", "conn lost")
        assert fc.failure_type == "TIMEOUT"
        f.stop()

    def test_create_request(self):
        f = self._started()
        fc = f.create_failure_context("sub", "T", "r")
        req = f.create_request(_sid(), "sub", fc, "test")
        assert req.subsystem_id == "sub"
        f.stop()

    def test_create_context(self):
        f = self._started()
        req = _req()
        ctx = f.create_context(req)
        assert ctx.request_id           == req.request_id
        assert ctx.execution_session_id == req.execution_session_id
        f.stop()

    def test_create_snapshot(self):
        f = self._started()
        snap = f.create_snapshot(
            "sess", "req", "sub",
            RecoveryEngineState.COMPLETED, PipelineStage.FINALIZE,
            10, 10, "T", "M", "r", RecoveryOutcome.RECOVERED,
            is_complete=True,
        )
        assert snap.is_complete
        f.stop()

    def test_create_success_response(self):
        f = self._started()
        r = f.create_success_response("req", "sess", "sub")
        assert r.is_success
        f.stop()

    def test_create_failure_response(self):
        f = self._started()
        r = f.create_failure_response("req", "sess", "sub", "error")
        assert r.is_failure
        f.stop()

    def test_not_started_raises(self):
        f = RecoveryFactory()
        with pytest.raises(RecoveryEngineNotRunningError):
            f.create_failure_context("sub", "T", "r")


# ─────────────────────────────────────────────────────────────────────────────
# 20  RecoveryManager
# ─────────────────────────────────────────────────────────────────────────────

class TestRecoveryManager:
    def _started(self, **kwargs) -> RecoveryManager:
        mgr = RecoveryManager(**kwargs)
        mgr.start()
        return mgr

    def test_start_recovery_success(self):
        mgr = self._started()
        response = mgr.start_recovery(_req())
        assert response.is_success
        mgr.stop()

    def test_start_recovery_invalid_request(self):
        mgr = self._started()
        bad_req = MagicMock()
        bad_req.request_id           = ""  # empty — will fail validation
        bad_req.execution_session_id = ""
        bad_req.subsystem_id         = ""
        bad_req.recovery_reason      = ""
        bad_req.failure_context      = None
        bad_req.priority             = RecoveryRequestPriority.NORMAL
        bad_req.request_type         = RecoveryRequestType.AUTOMATIC
        bad_req.requester            = ACTOR_SYSTEM
        bad_req.workflow_id          = ""
        bad_req.tags                 = ()
        bad_req.metadata             = {}
        response = mgr.start_recovery(bad_req)
        assert response.is_failure
        mgr.stop()

    def test_statistics_updated(self):
        mgr = self._started()
        mgr.start_recovery(_req())
        stats = mgr.statistics()
        assert stats.total_requests    >= 1
        assert stats.sessions_completed >= 1
        mgr.stop()

    def test_history_populated(self):
        mgr = self._started()
        mgr.start_recovery(_req())
        h = mgr.history()
        assert h.request_count  >= 1
        assert h.response_count >= 1
        assert h.event_count    >= 1
        mgr.stop()

    def test_event_listener(self):
        received: List[RecoveryEngineEvent] = []
        mgr = self._started()
        mgr.add_event_listener(received.append)
        mgr.start_recovery(_req())
        mgr.remove_event_listener(received.append)
        assert len(received) >= 1
        mgr.stop()

    def test_stop_recovery(self):
        mgr = self._started()
        req = _req()
        # start async recovery in a thread just to have an active request
        # stop_recovery aborts by request_id — best effort
        mgr.stop_recovery(req.request_id, "test abort")
        stats = mgr.statistics()
        assert stats.sessions_cancelled >= 1
        mgr.stop()

    def test_port_injection(self):
        class _Tracking(PolicyFrameworkPort):
            called = False
            def invoke(self, req, ctx):
                _Tracking.called = True
                return PolicyDecision(approved=True)

        mgr = self._started()
        mgr.set_policy_framework(_Tracking())
        mgr.start_recovery(_req())
        assert _Tracking.called
        mgr.stop()

    def test_not_started_raises(self):
        mgr = RecoveryManager()
        with pytest.raises(RecoveryEngineNotRunningError):
            mgr.start_recovery(_req())


# ─────────────────────────────────────────────────────────────────────────────
# 21  ExecutionRecoveryEngine
# ─────────────────────────────────────────────────────────────────────────────

class TestExecutionRecoveryEngine:
    def test_start_and_stop(self):
        eng = ExecutionRecoveryEngine()
        eng.start()
        assert eng.is_running()
        eng.stop()
        assert not eng.is_running()

    def test_start_recovery(self):
        eng = _started_engine()
        response = eng.start_recovery(_req())
        assert response.is_success
        eng.stop()

    def test_before_start_raises(self):
        eng = ExecutionRecoveryEngine()
        with pytest.raises(RecoveryEngineNotRunningError):
            eng.start_recovery(_req())

    def test_get_statistics(self):
        eng = _started_engine()
        eng.start_recovery(_req())
        stats = eng.get_statistics()
        assert stats.total_requests >= 1
        eng.stop()

    def test_get_history(self):
        eng = _started_engine()
        eng.start_recovery(_req())
        h = eng.get_history()
        assert h.request_count >= 1
        eng.stop()

    def test_active_sessions(self):
        eng = _started_engine()
        # All sessions finish synchronously so active may be 0
        sessions = eng.active_sessions()
        assert isinstance(sessions, list)
        eng.stop()

    def test_event_listener_receives_events(self):
        received: List[RecoveryEngineEvent] = []
        eng = _started_engine()
        eng.add_event_listener(received.append)
        eng.start_recovery(_req())
        eng.remove_event_listener(received.append)
        assert any(e.event_type == RecoveryEngineEventType.RECOVERY_COMPLETED for e in received)
        eng.stop()

    def test_remove_listener_bound_method(self):
        """Bound-method identity regression — must use == not is."""
        received: List[RecoveryEngineEvent] = []

        class _Recv:
            def on_event(self, ev: RecoveryEngineEvent):
                received.append(ev)

        eng = _started_engine()
        obj = _Recv()
        eng.add_event_listener(obj.on_event)
        eng.remove_event_listener(obj.on_event)
        eng.start_recovery(_req())
        assert len(received) == 0
        eng.stop()

    def test_set_policy_framework(self):
        class _Tracking(PolicyFrameworkPort):
            called = False
            def invoke(self, req, ctx):
                _Tracking.called = True
                return PolicyDecision(approved=True)

        eng = _started_engine()
        eng.set_policy_framework(_Tracking())
        eng.start_recovery(_req())
        assert _Tracking.called
        eng.stop()

    def test_set_failover_framework(self):
        class _TrackingPolicy(PolicyFrameworkPort):
            def invoke(self, req, ctx):
                return PolicyDecision(approved=True, requires_failover=True)

        class _TrackingFailover(FailoverFrameworkPort):
            called = False
            def trigger_failover(self, req, ctx):
                _TrackingFailover.called = True
                return FailoverResult(triggered=True, result="ok")

        eng = _started_engine()
        eng.set_policy_framework(_TrackingPolicy())
        eng.set_failover_framework(_TrackingFailover())
        eng.start_recovery(_req())
        assert _TrackingFailover.called
        eng.stop()

    def test_stop_recovery_before_start_raises(self):
        eng = ExecutionRecoveryEngine()
        with pytest.raises(RecoveryEngineNotRunningError):
            eng.stop_recovery("r1", "reason")

    def test_snapshot_in_history(self):
        eng = _started_engine()
        eng.start_recovery(_req())
        h = eng.get_history()
        assert h.snapshot_count >= 1
        eng.stop()


# ─────────────────────────────────────────────────────────────────────────────
# 22  Full workflow orchestration
# ─────────────────────────────────────────────────────────────────────────────

class TestWorkflowOrchestration:
    def test_complete_end_to_end(self):
        eng = _started_engine()
        req = make_recovery_request(
            execution_session_id = _sid(),
            subsystem_id         = "execution_gateway",
            failure_context      = make_failure_context(
                "execution_gateway", "GATEWAY_TIMEOUT",
                "Connection timed out after 30s",
                severity="HIGH",
                affected_components=("gateway", "order_router"),
            ),
            recovery_reason = "Automatic recovery triggered by health monitor",
            priority        = RecoveryRequestPriority.HIGH,
            request_type    = RecoveryRequestType.AUTOMATIC,
        )
        response = eng.start_recovery(req)
        assert response.is_success
        assert response.request_id  == req.request_id
        assert response.subsystem_id == "execution_gateway"
        assert response.snapshot_id
        assert response.pipeline_stages_completed > 0
        assert response.pipeline_completion_rate  > 0.0
        assert response.duration_ms > 0.0
        eng.stop()

    def test_response_references_correct_request(self):
        eng = _started_engine()
        r1 = _req()
        r2 = _req()
        resp1 = eng.start_recovery(r1)
        resp2 = eng.start_recovery(r2)
        assert resp1.request_id == r1.request_id
        assert resp2.request_id == r2.request_id
        assert resp1.request_id != resp2.request_id
        eng.stop()

    def test_multiple_requests_independent(self):
        eng = _started_engine()
        responses = [eng.start_recovery(_req()) for _ in range(5)]
        assert all(r.is_success for r in responses)
        assert len({r.request_id for r in responses}) == 5
        eng.stop()

    def test_policy_rejection_returns_cancelled(self):
        class _RejectingPolicy(PolicyFrameworkPort):
            def invoke(self, req, ctx):
                return PolicyDecision(approved=False)

        eng = _started_engine(policy_framework=_RejectingPolicy())
        response = eng.start_recovery(_req())
        # Should not be success (policy rejected)
        assert not response.is_success
        eng.stop()

    def test_statistics_accurate_after_multiple(self):
        eng = _started_engine()
        n = 5
        for _ in range(n):
            eng.start_recovery(_req())
        stats = eng.get_statistics()
        assert stats.total_requests    == n
        assert stats.sessions_completed == n
        assert abs(stats.success_rate - 1.0) < 1e-9
        eng.stop()

    def test_history_accurate_after_multiple(self):
        eng = _started_engine()
        n = 3
        for _ in range(n):
            eng.start_recovery(_req())
        h = eng.get_history()
        assert h.request_count  == n
        assert h.response_count == n
        assert h.snapshot_count == n
        eng.stop()


# ─────────────────────────────────────────────────────────────────────────────
# 23  Concurrency
# ─────────────────────────────────────────────────────────────────────────────

class TestConcurrency:
    def test_concurrent_start_recovery(self):
        eng = _started_engine(max_concurrent=20)
        errors: List[Exception] = []
        responses: List[RecoveryResponse] = []
        lock = threading.Lock()

        def _recover():
            try:
                r = eng.start_recovery(_req())
                with lock:
                    responses.append(r)
            except Exception as exc:
                with lock:
                    errors.append(exc)

        threads = [threading.Thread(target=_recover) for _ in range(20)]
        for t in threads: t.start()
        for t in threads: t.join()

        assert not errors, f"Errors: {errors}"
        assert len(responses) == 20
        eng.stop()

    def test_concurrent_statistics(self):
        s = RecoveryEngineStatistics()
        threads = [
            threading.Thread(target=lambda: [s.record_request() for _ in range(100)])
            for _ in range(10)
        ]
        for t in threads: t.start()
        for t in threads: t.join()
        assert s.total_requests == 1_000

    def test_concurrent_history_appends(self):
        h = RecoveryEngineHistory()
        threads = [
            threading.Thread(target=lambda: h.append_request(_req()))
            for _ in range(50)
        ]
        for t in threads: t.start()
        for t in threads: t.join()
        assert h.request_count == 50

    def test_concurrent_registry_operations(self):
        reg = RecoveryRegistry()
        reg.start()
        errors: List[Exception] = []

        def _store():
            try:
                reg.store(_req())
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_store) for _ in range(30)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert not errors
        reg.stop()

    def test_concurrent_event_listeners(self):
        eng = _started_engine()
        counts: Dict[str, int] = {"n": 0}
        lock = threading.Lock()

        def listener(ev: RecoveryEngineEvent):
            with lock:
                counts["n"] += 1

        eng.add_event_listener(listener)
        threads = [
            threading.Thread(target=lambda: eng.start_recovery(_req()))
            for _ in range(5)
        ]
        for t in threads: t.start()
        for t in threads: t.join()
        eng.remove_event_listener(listener)
        assert counts["n"] >= 5
        eng.stop()


# ─────────────────────────────────────────────────────────────────────────────
# 24  Stress testing
# ─────────────────────────────────────────────────────────────────────────────

class TestStressTesting:
    def test_sequential_high_volume(self):
        eng = _started_engine()
        n = 50
        success_count = 0
        for _ in range(n):
            r = eng.start_recovery(_req())
            if r.is_success:
                success_count += 1
        stats = eng.get_statistics()
        assert stats.total_requests == n
        assert success_count == n
        eng.stop()

    def test_history_bounded_under_load(self):
        eng = _started_engine(max_history=10)
        for _ in range(30):
            eng.start_recovery(_req())
        h = eng.get_history()
        assert h.request_count  <= 10
        assert h.response_count <= 10
        eng.stop()

    def test_scheduler_high_volume(self):
        sch = RecoveryScheduler(max_queue_size=200)
        sch.start()
        for _ in range(100):
            sch.schedule(_req())
        assert sch.queue_size == 100
        drained = sch.drain()
        assert len(drained) == 100
        assert sch.is_empty
        sch.stop()


# ─────────────────────────────────────────────────────────────────────────────
# 25  Regression / edge cases
# ─────────────────────────────────────────────────────────────────────────────

class TestRegressionEdgeCases:
    def test_statistics_zero_division_safe(self):
        s = RecoveryEngineStatistics()
        assert s.success_rate               == 0.0
        assert s.failure_rate               == 0.0
        assert s.verification_success_rate  == 0.0
        assert s.average_recovery_time_ms   == 0.0
        assert s.subsystem_availability     == 0.0

    def test_history_bounded_at_one(self):
        h = RecoveryEngineHistory(max_requests=1)
        h.append_request(_req())
        h.append_request(_req())
        assert h.request_count == 1

    def test_pipeline_complete_all_stages(self):
        p = RecoveryPipeline("r", "s")
        for stage in PIPELINE_STAGES_ORDERED:
            p.start_stage(stage)
            p.complete_stage(stage)
        assert p.is_complete
        assert p.current_stage is None

    def test_engine_stopped_get_history_raises(self):
        eng = ExecutionRecoveryEngine()
        with pytest.raises(RecoveryEngineNotRunningError):
            eng.get_history()

    def test_response_to_dict_complete(self):
        r = make_success_response("req", "sess", "sub", started_at=time.time()-1)
        d = r.to_dict()
        assert d["pipeline_completion_rate"] == 0.0

    def test_dispatcher_result_is_success(self):
        pd = PolicyDecision(approved=True)
        result = DispatchResult(
            dispatch_id="d", dispatched=True,
            policy_decision=pd, failover_result=None,
            dispatched_at=time.time(),
        )
        assert result.is_success

    def test_dispatcher_result_not_success_when_error(self):
        pd = PolicyDecision(approved=True)
        result = DispatchResult(
            dispatch_id="d", dispatched=True,
            policy_decision=pd, failover_result=None,
            dispatched_at=time.time(),
            error_message="something went wrong",
        )
        assert not result.is_success

    def test_recovery_request_tags(self):
        r = make_recovery_request(
            _sid(), _sub(), _fc(), "test",
            tags=("critical", "gateway"),
        )
        assert r.tags == ("critical", "gateway")

    def test_multiple_listeners(self):
        received_a: List[RecoveryEngineEvent] = []
        received_b: List[RecoveryEngineEvent] = []
        eng = _started_engine()
        eng.add_event_listener(received_a.append)
        eng.add_event_listener(received_b.append)
        eng.start_recovery(_req())
        eng.remove_event_listener(received_a.append)
        eng.remove_event_listener(received_b.append)
        assert len(received_a) > 0
        assert len(received_b) > 0
        assert len(received_a) == len(received_b)
        eng.stop()

    def test_emergency_priority_goes_first(self):
        sch = RecoveryScheduler()
        sch.start()
        sch.schedule(_req(priority=RecoveryRequestPriority.NORMAL))
        sch.schedule(_req(priority=RecoveryRequestPriority.EMERGENCY))
        sch.schedule(_req(priority=RecoveryRequestPriority.LOW))
        assert sch.next().priority == RecoveryRequestPriority.EMERGENCY
        assert sch.next().priority == RecoveryRequestPriority.NORMAL
        assert sch.next().priority == RecoveryRequestPriority.LOW
        sch.stop()
