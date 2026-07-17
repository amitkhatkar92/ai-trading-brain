"""tests/unit/execution/gateway/engine/test_execution_gateway_engine.py
==================================================
Unit tests for C6 Phase 5 Module 2: Execution Gateway Engine.

Coverage areas
--------------
TestConstants               — enums, sentinels, defaults
TestExceptions              — all EGE-* exception classes
TestEngineGatewayContext    — EngineGatewayContext dataclass
TestEngineGatewayRequest    — EngineGatewayRequest state management
TestGatewayResponse         — GatewayResponse dataclass
TestGatewayOperation        — GatewayOperation, make_gateway_operation
TestGatewayEngineStatistics — counters and derived properties
TestGatewayEngineHistory    — bounded history store
TestGatewaySession          — GatewaySession lifecycle
TestGatewaySessionManager   — session creation and expiry
TestFifoQueue               — FIFO queue behaviour
TestPriorityQueue           — priority ordering
TestRetryQueue              — delay-based dequeue
TestCancellationQueue       — idempotent cancel
TestGatewayOperationQueue   — facade operations
TestGatewayEngineRegistry   — lifecycle-aware registry
TestGatewayStateManager     — state transition history
TestDispatchResult          — DispatchResult dataclass
TestGatewayDispatcher       — SimulatedDispatch + pluggable broker
TestEngineGatewayValidator  — context and capacity validation
TestGatewayEngineFactory    — factory methods
TestGatewayEvents           — event factory functions
TestGatewayManager          — workflow orchestration
TestExecutionGatewayEngine  — public API
TestStatisticsIntegration   — end-to-end stat accumulation
TestEventsIntegration       — end-to-end event firing
TestConcurrency             — thread-safety under load
TestRegression              — edge cases and guard rails
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import List
from unittest.mock import MagicMock, patch

import pytest

from iios.execution.gateway.engine import (
    ACTIVE_ENGINE_STATES,
    ACTIVE_REQUEST_STATUSES,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_QUEUE_SIZE,
    DEFAULT_MAX_REQUESTS,
    DEFAULT_MAX_RETRIES,
    DEFAULT_MAX_SESSIONS,
    DEFAULT_RETRY_DELAY_SECS,
    DEFAULT_SESSION_TIMEOUT_SECS,
    TERMINAL_ENGINE_STATES,
    TERMINAL_REQUEST_STATUSES,
    VERSION,
    BrokerAbstractionProtocol,
    CancellationQueue,
    DispatchOutcome,
    DispatchResult,
    DuplicateEngineRequestError,
    ENGINE_SYSTEM_ID,
    EngineGatewayContext,
    EngineGatewayValidator,
    EngineState,
    EngineValidationResult,
    EnginePriorityQueue,
    EngineEventType,
    ExecutionGatewayEngine,
    ExecutionGatewayEngineError,
    FifoQueue,
    GatewayDispatcher,
    GatewayEngineEvent,
    GatewayEngineFactory,
    GatewayEngineHistory,
    GatewayEngineNotRunningError,
    GatewayEngineRegistry,
    GatewayEngineRequestNotFoundError,
    GatewayEngineStatistics,
    GatewayEngineSnapshot,
    GatewayManager,
    GatewayOperation,
    GatewayOperationQueue,
    GatewayRegistryCapacityError,
    GatewayRequestSubmissionError,
    GatewayRequestSummary,
    GatewayResponse,
    GatewaySession,
    GatewaySessionManager,
    GatewaySessionNotFoundError,
    GatewayStateManager,
    GatewayValidationFailedError,
    OperationType,
    QueueStatistics,
    QueueType,
    RequestStatus,
    RetryQueue,
    RouteDecision,
    RoutingFrameworkProtocol,
    SessionStatus,
    SimulatedDispatch,
    make_dispatch_completed_event,
    make_dispatch_failed_event,
    make_engine_gateway_context,
    make_gateway_operation,
    make_gateway_started_event,
    make_gateway_stopped_event,
    make_request_dispatched_event,
    make_request_queued_event,
    make_request_received_event,
)
from iios.execution.gateway.engine.gateway_request import EngineGatewayRequest


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _ctx(**kwargs) -> EngineGatewayContext:
    """Build a minimal valid EngineGatewayContext."""
    defaults = dict(
        execution_id="EX-001",
        order_id="ORD-001",
        portfolio_id="PORT-A",
        strategy_id="STRAT-1",
        symbol="NIFTY",
        side="BUY",
        quantity=50.0,
        price=200.0,
        order_type="MARKET",
        asset_class="OPTION",
    )
    defaults.update(kwargs)
    return make_engine_gateway_context(**defaults)


def _request(ctx=None, **kwargs) -> EngineGatewayRequest:
    """Build a minimal EngineGatewayRequest."""
    return EngineGatewayRequest(ctx or _ctx(), **kwargs)


def _engine(**kwargs) -> ExecutionGatewayEngine:
    """Return a started ExecutionGatewayEngine."""
    engine = ExecutionGatewayEngine(**kwargs)
    engine.start()
    return engine


# ═══════════════════════════════════════════════════════════════════════════════
# TestConstants
# ═══════════════════════════════════════════════════════════════════════════════

class TestConstants:
    def test_engine_system_id(self):
        assert ENGINE_SYSTEM_ID == "iios:execution:gateway:engine"

    def test_version(self):
        assert VERSION == "1.0.0"

    def test_engine_states_complete(self):
        values = {s.value for s in EngineState}
        assert "IDLE" in values
        assert "DISPATCHING" in values
        assert "STOPPED" in values

    def test_active_engine_states_do_not_include_stopped(self):
        assert EngineState.STOPPED not in ACTIVE_ENGINE_STATES

    def test_terminal_engine_states_contains_failed_and_stopped(self):
        assert EngineState.FAILED in TERMINAL_ENGINE_STATES
        assert EngineState.STOPPED in TERMINAL_ENGINE_STATES

    def test_request_status_values(self):
        values = {s.value for s in RequestStatus}
        for expected in ("PENDING", "QUEUED", "DISPATCHING", "COMPLETED", "FAILED",
                         "CANCELLED", "RETRYING"):
            assert expected in values

    def test_dispatch_outcome_values(self):
        values = {d.value for d in DispatchOutcome}
        assert "ACCEPTED" in values
        assert "REJECTED" in values
        assert "DEFERRED" in values

    def test_queue_type_values(self):
        values = {q.value for q in QueueType}
        for expected in ("FIFO", "PRIORITY", "RETRY", "CANCELLATION"):
            assert expected in values

    def test_defaults_are_positive(self):
        assert DEFAULT_MAX_REQUESTS > 0
        assert DEFAULT_MAX_QUEUE_SIZE > 0
        assert DEFAULT_MAX_SESSIONS > 0
        assert DEFAULT_MAX_HISTORY > 0
        assert DEFAULT_MAX_RETRIES >= 0
        assert DEFAULT_SESSION_TIMEOUT_SECS > 0
        assert DEFAULT_RETRY_DELAY_SECS >= 0


# ═══════════════════════════════════════════════════════════════════════════════
# TestExceptions
# ═══════════════════════════════════════════════════════════════════════════════

class TestExceptions:
    def test_base_exception(self):
        exc = ExecutionGatewayEngineError("test")
        assert "test" in str(exc)

    def test_not_running(self):
        exc = GatewayEngineNotRunningError()
        assert "not running" in str(exc).lower()

    def test_submission_error(self):
        exc = GatewayRequestSubmissionError(reason="too busy")
        assert "too busy" in str(exc)

    def test_request_not_found(self):
        exc = GatewayEngineRequestNotFoundError("REQ-1")
        assert "REQ-1" in str(exc)

    def test_duplicate_error(self):
        exc = DuplicateEngineRequestError("REQ-1")
        assert "REQ-1" in str(exc)

    def test_registry_capacity_error(self):
        exc = GatewayRegistryCapacityError(100)
        assert "100" in str(exc)

    def test_session_not_found(self):
        exc = GatewaySessionNotFoundError("SES-1")
        assert "SES-1" in str(exc)

    def test_validation_failed(self):
        exc = GatewayValidationFailedError("bad", errors=("e1", "e2"))
        assert "e1" in str(exc)

    def test_exception_hierarchy(self):
        from iios.common.errors.exceptions import IIOSError
        assert issubclass(ExecutionGatewayEngineError, IIOSError)
        assert issubclass(GatewayEngineNotRunningError, ExecutionGatewayEngineError)


# ═══════════════════════════════════════════════════════════════════════════════
# TestEngineGatewayContext
# ═══════════════════════════════════════════════════════════════════════════════

class TestEngineGatewayContext:
    def test_required_fields(self):
        ctx = _ctx()
        assert ctx.execution_id == "EX-001"
        assert ctx.order_id     == "ORD-001"
        assert ctx.portfolio_id == "PORT-A"
        assert ctx.strategy_id  == "STRAT-1"

    def test_auto_request_id(self):
        ctx = _ctx()
        assert ctx.request_id and len(ctx.request_id) == 36  # UUID

    def test_explicit_request_id(self):
        rid = "CUSTOM-001"
        ctx = make_engine_gateway_context("EX", "ORD", "PORT", "STRAT",
                                          request_id=rid)
        assert ctx.request_id == rid

    def test_is_frozen(self):
        ctx = _ctx()
        with pytest.raises((AttributeError, TypeError)):
            ctx.execution_id = "X"  # type: ignore[misc]

    def test_has_risk_data_false(self):
        ctx = _ctx()
        assert not ctx.has_risk_data

    def test_has_risk_data_true(self):
        ctx = _ctx(risk_snapshot_id="RISK-1")
        assert ctx.has_risk_data

    def test_is_high_priority_false(self):
        ctx = _ctx(priority=0)
        assert not ctx.is_high_priority

    def test_is_high_priority_true(self):
        ctx = _ctx(priority=10)
        assert ctx.is_high_priority

    def test_age_ms_non_negative(self):
        ctx = _ctx()
        time.sleep(0.01)
        assert ctx.age_ms >= 0.0

    def test_to_dict_keys(self):
        d = _ctx().to_dict()
        assert "request_id"   in d
        assert "execution_id" in d
        assert "portfolio_id" in d


# ═══════════════════════════════════════════════════════════════════════════════
# TestEngineGatewayRequest
# ═══════════════════════════════════════════════════════════════════════════════

class TestEngineGatewayRequest:
    def test_initial_status_is_pending(self):
        r = _request()
        assert r.status == RequestStatus.PENDING

    def test_identity_delegation(self):
        r = _request()
        assert r.execution_id == "EX-001"
        assert r.portfolio_id == "PORT-A"
        assert r.order_id     == "ORD-001"
        assert r.symbol       == "NIFTY"

    def test_set_status(self):
        r = _request()
        r.set_status(RequestStatus.QUEUED)
        assert r.status == RequestStatus.QUEUED

    def test_lifecycle_request_id_default_empty(self):
        r = _request()
        assert r.lifecycle_request_id == ""

    def test_set_lifecycle_request_id(self):
        r = _request()
        r.set_lifecycle_request_id("LCR-1")
        assert r.lifecycle_request_id == "LCR-1"

    def test_mark_queued_stamps_queued_at(self):
        r = _request()
        assert r.queued_at is None
        r.mark_queued()
        assert r.queued_at is not None

    def test_mark_dispatched_stamps_dispatched_at(self):
        r = _request()
        r.mark_dispatched()
        assert r.dispatched_at is not None

    def test_mark_completed_stamps_completed_at(self):
        r = _request()
        r.mark_completed()
        assert r.completed_at is not None

    def test_set_dispatch_result(self):
        r = _request()
        r.set_dispatch_result(DispatchOutcome.ACCEPTED, {"external_id": "EXT-1"})
        assert r.dispatch_outcome == DispatchOutcome.ACCEPTED
        assert r.dispatch_result["external_id"] == "EXT-1"

    def test_set_error(self):
        r = _request()
        r.set_error("EGE-003", "dispatch failed")
        assert r.error_code    == "EGE-003"
        assert r.error_message == "dispatch failed"

    def test_can_retry_true_initially(self):
        r = _request(max_retries=3)
        assert r.can_retry

    def test_can_retry_false_when_exhausted(self):
        r = _request(max_retries=1)
        r.increment_retry()
        assert not r.can_retry

    def test_is_terminal_completed(self):
        r = _request()
        r.set_status(RequestStatus.COMPLETED)
        assert r.is_terminal

    def test_is_active_pending(self):
        r = _request()
        assert r.is_active

    def test_to_dict_keys(self):
        d = _request().to_dict()
        assert "request_id"   in d
        assert "status"       in d
        assert "retry_count"  in d


# ═══════════════════════════════════════════════════════════════════════════════
# TestGatewayResponse
# ═══════════════════════════════════════════════════════════════════════════════

class TestGatewayResponse:
    def _resp(self, outcome=DispatchOutcome.ACCEPTED, status=RequestStatus.COMPLETED):
        return GatewayResponse(
            response_id=str(uuid.uuid4()),
            request_id="REQ-1",
            lifecycle_request_id="LCR-1",
            session_id="SES-1",
            status=status.value,
            outcome=outcome.value,
            dispatch_result={},
            error_code="",
            error_message="",
            portfolio_id="PORT-A",
            strategy_id="STRAT-1",
            execution_id="EX-001",
            order_id="ORD-001",
            symbol="NIFTY",
            created_at=time.time() - 0.1,
            elapsed_ms=100.0,
        )

    def test_is_accepted_true(self):
        assert self._resp().is_accepted

    def test_is_rejected_false(self):
        assert not self._resp().is_rejected

    def test_is_completed_true(self):
        assert self._resp().is_completed

    def test_is_failed_false(self):
        assert not self._resp().is_failed

    def test_to_dict_keys(self):
        d = self._resp().to_dict()
        assert "response_id"  in d
        assert "request_id"   in d
        assert "status"       in d
        assert "outcome"      in d
        assert "elapsed_ms"   in d


# ═══════════════════════════════════════════════════════════════════════════════
# TestGatewayOperation
# ═══════════════════════════════════════════════════════════════════════════════

class TestGatewayOperation:
    def _op(self, is_success=True):
        return make_gateway_operation(
            OperationType.SUBMIT_REQUEST,
            request_id="REQ-1",
            session_id="SES-1",
            started_at=time.time() - 0.05,
            is_success=is_success,
        )

    def test_operation_type(self):
        op = self._op()
        assert op.operation_type == OperationType.SUBMIT_REQUEST

    def test_is_success_true(self):
        assert self._op(is_success=True).is_success

    def test_is_failure_false(self):
        assert not self._op(is_success=True).is_failure

    def test_elapsed_ms_non_negative(self):
        op = self._op()
        assert op.elapsed_ms >= 0.0

    def test_to_dict_keys(self):
        d = self._op().to_dict()
        assert "operation_id"   in d
        assert "operation_type" in d
        assert "elapsed_ms"     in d


# ═══════════════════════════════════════════════════════════════════════════════
# TestGatewayEngineStatistics
# ═══════════════════════════════════════════════════════════════════════════════

class TestGatewayEngineStatistics:
    def test_initial_zeros(self):
        s = GatewayEngineStatistics()
        assert s.requests_received == 0
        assert s.requests_completed == 0

    def test_record_received(self):
        s = GatewayEngineStatistics()
        s.record_received()
        assert s.requests_received == 1

    def test_record_queued(self):
        s = GatewayEngineStatistics()
        s.record_queued(50.0)
        assert s.requests_queued == 1
        assert s.total_queue_time_ms == 50.0

    def test_record_dispatched(self):
        s = GatewayEngineStatistics()
        s.record_dispatched(30.0)
        assert s.requests_dispatched == 1

    def test_record_completed(self):
        s = GatewayEngineStatistics()
        s.record_completed(100.0)
        assert s.requests_completed == 1

    def test_record_failed(self):
        s = GatewayEngineStatistics()
        s.record_failed(80.0)
        assert s.requests_failed == 1

    def test_completion_rate(self):
        s = GatewayEngineStatistics()
        s.record_completed(100.0)
        s.record_failed(80.0)
        assert abs(s.completion_rate - 0.5) < 1e-9

    def test_average_queue_time(self):
        s = GatewayEngineStatistics()
        s.record_queued(100.0)
        s.record_queued(200.0)
        assert abs(s.average_queue_time_ms - 150.0) < 1e-9

    def test_reset(self):
        s = GatewayEngineStatistics()
        s.record_received()
        s.reset()
        assert s.requests_received == 0

    def test_copy_is_independent(self):
        s = GatewayEngineStatistics()
        s.record_received()
        c = s.copy()
        s.record_received()
        assert c.requests_received == 1
        assert s.requests_received == 2

    def test_to_dict_keys(self):
        d = GatewayEngineStatistics().to_dict()
        assert "requests_received"   in d
        assert "completion_rate"     in d
        assert "gateway_throughput"  in d


# ═══════════════════════════════════════════════════════════════════════════════
# TestGatewayEngineHistory
# ═══════════════════════════════════════════════════════════════════════════════

class TestGatewayEngineHistory:
    def _op(self):
        return make_gateway_operation(
            OperationType.SUBMIT_REQUEST, "REQ-1", "SES-1", time.time()
        )

    def test_append_operation(self):
        h = GatewayEngineHistory()
        h.append_operation(self._op())
        assert h.operation_count == 1

    def test_latest_operation(self):
        h = GatewayEngineHistory()
        op = self._op()
        h.append_operation(op)
        assert h.latest_operation() is op

    def test_bounded_eviction(self):
        h = GatewayEngineHistory(max_size=2)
        for _ in range(5):
            h.append_operation(self._op())
        assert h.operation_count == 2

    def test_operations_for_request(self):
        h = GatewayEngineHistory()
        op = make_gateway_operation(
            OperationType.SUBMIT_REQUEST, "REQ-X", "SES-1", time.time()
        )
        h.append_operation(op)
        results = h.operations_for_request("REQ-X")
        assert len(results) == 1 and results[0] is op

    def test_empty_latest_returns_none(self):
        h = GatewayEngineHistory()
        assert h.latest_operation() is None


# ═══════════════════════════════════════════════════════════════════════════════
# TestGatewaySession
# ═══════════════════════════════════════════════════════════════════════════════

class TestGatewaySession:
    def _session(self, timeout=3600.0):
        return GatewaySession(
            session_id=str(uuid.uuid4()),
            portfolio_id="PORT-A",
            strategy_id="STRAT-1",
            execution_id="EX-001",
            timeout_secs=timeout,
        )

    def test_initial_active(self):
        s = self._session()
        assert s.status == SessionStatus.ACTIVE
        assert s.is_active
        assert not s.is_expired

    def test_add_request(self):
        s = self._session()
        s.add_request("REQ-1")
        assert "REQ-1" in s.request_ids
        assert s.request_count == 1

    def test_add_request_idempotent(self):
        s = self._session()
        s.add_request("REQ-1")
        s.add_request("REQ-1")
        assert s.request_count == 1

    def test_expire(self):
        s = self._session()
        s.expire()
        assert s.status == SessionStatus.EXPIRED
        assert s.is_expired

    def test_close(self):
        s = self._session()
        s.close()
        assert s.status == SessionStatus.CLOSED
        assert s.is_closed

    def test_extend(self):
        s = self._session(timeout=1.0)
        old_expires = s.expires_at
        s.extend(100.0)
        assert s.expires_at > old_expires

    def test_to_dict_keys(self):
        d = self._session().to_dict()
        assert "session_id"   in d
        assert "status"       in d
        assert "request_count" in d


# ═══════════════════════════════════════════════════════════════════════════════
# TestGatewaySessionManager
# ═══════════════════════════════════════════════════════════════════════════════

class TestGatewaySessionManager:
    def test_create_session(self):
        mgr = GatewaySessionManager()
        s   = mgr.create_session("PORT-A", "STRAT-1", "EX-001")
        assert s.is_active
        assert mgr.exists(s.session_id)

    def test_get_session(self):
        mgr = GatewaySessionManager()
        s   = mgr.create_session("PORT-A", "STRAT-1", "EX-001")
        got = mgr.get_session(s.session_id)
        assert got is s

    def test_get_session_not_found(self):
        mgr = GatewaySessionManager()
        with pytest.raises(GatewaySessionNotFoundError):
            mgr.get_session("nonexistent")

    def test_add_request_to_session(self):
        mgr = GatewaySessionManager()
        s   = mgr.create_session("PORT-A", "STRAT-1", "EX-001")
        mgr.add_request_to_session(s.session_id, "REQ-1")
        assert "REQ-1" in mgr.get_session(s.session_id).request_ids

    def test_expire_stale_sessions(self):
        mgr = GatewaySessionManager(timeout_secs=0.01)
        s   = mgr.create_session("PORT-A", "STRAT-1", "EX-001")
        time.sleep(0.05)
        expired = mgr.expire_stale_sessions()
        assert expired >= 1

    def test_active_sessions_filter(self):
        mgr = GatewaySessionManager()
        s1  = mgr.create_session("P", "S", "E")
        s2  = mgr.create_session("P", "S", "E")
        s1.expire()
        active = mgr.active_sessions()
        assert s2 in active
        assert s1 not in active


# ═══════════════════════════════════════════════════════════════════════════════
# TestFifoQueue
# ═══════════════════════════════════════════════════════════════════════════════

class TestFifoQueue:
    def test_enqueue_dequeue(self):
        q = FifoQueue()
        r = _request()
        q.enqueue(r)
        assert q.dequeue() is r

    def test_fifo_order(self):
        q  = FifoQueue()
        r1 = _request()
        r2 = _request()
        q.enqueue(r1)
        q.enqueue(r2)
        assert q.dequeue() is r1
        assert q.dequeue() is r2

    def test_empty_dequeue_returns_none(self):
        assert FifoQueue().dequeue() is None

    def test_full_raises(self):
        q = FifoQueue(max_size=1)
        q.enqueue(_request())
        with pytest.raises(Exception):
            q.enqueue(_request())

    def test_size(self):
        q = FifoQueue()
        q.enqueue(_request())
        assert q.size == 1


# ═══════════════════════════════════════════════════════════════════════════════
# TestPriorityQueue
# ═══════════════════════════════════════════════════════════════════════════════

class TestPriorityQueue:
    def test_higher_priority_dequeued_first(self):
        q   = EnginePriorityQueue()
        low = _request(_ctx(priority=1))
        hi  = _request(_ctx(priority=10))
        q.enqueue(low)
        q.enqueue(hi)
        assert q.dequeue() is hi
        assert q.dequeue() is low

    def test_empty_returns_none(self):
        assert EnginePriorityQueue().dequeue() is None


# ═══════════════════════════════════════════════════════════════════════════════
# TestRetryQueue
# ═══════════════════════════════════════════════════════════════════════════════

class TestRetryQueue:
    def test_not_ready_before_delay(self):
        q = RetryQueue()
        q.enqueue(_request(), delay_secs=9999.0)
        assert q.dequeue_ready() == []

    def test_ready_after_zero_delay(self):
        q = RetryQueue()
        r = _request()
        q.enqueue(r, delay_secs=0.0)
        ready = q.dequeue_ready()
        assert r in ready

    def test_size(self):
        q = RetryQueue()
        q.enqueue(_request(), delay_secs=9999.0)
        assert q.size == 1


# ═══════════════════════════════════════════════════════════════════════════════
# TestCancellationQueue
# ═══════════════════════════════════════════════════════════════════════════════

class TestCancellationQueue:
    def test_enqueue_and_contains(self):
        q = CancellationQueue()
        q.enqueue("REQ-1")
        assert q.contains("REQ-1")

    def test_dequeue(self):
        q = CancellationQueue()
        q.enqueue("REQ-1")
        assert q.dequeue() == "REQ-1"
        assert not q.contains("REQ-1")

    def test_idempotent_enqueue(self):
        q = CancellationQueue()
        q.enqueue("REQ-1")
        q.enqueue("REQ-1")
        assert q.size == 1

    def test_remove(self):
        q = CancellationQueue()
        q.enqueue("REQ-1")
        assert q.remove("REQ-1")
        assert not q.contains("REQ-1")


# ═══════════════════════════════════════════════════════════════════════════════
# TestGatewayOperationQueue
# ═══════════════════════════════════════════════════════════════════════════════

class TestGatewayOperationQueue:
    def test_fifo_enqueue_dequeue(self):
        q = GatewayOperationQueue()
        r = _request()
        q.enqueue_fifo(r)
        assert q.dequeue_next() is r

    def test_priority_first(self):
        q   = GatewayOperationQueue()
        low = _request()
        hi  = _request(_ctx(priority=20))
        q.enqueue_fifo(low)
        q.enqueue_priority(hi)
        assert q.dequeue_next() is hi

    def test_cancellation_pending(self):
        q = GatewayOperationQueue()
        q.enqueue_cancellation("REQ-1")
        assert q.is_cancellation_pending("REQ-1")

    def test_remove_cancellation(self):
        q = GatewayOperationQueue()
        q.enqueue_cancellation("REQ-1")
        q.remove_cancellation("REQ-1")
        assert not q.is_cancellation_pending("REQ-1")

    def test_sizes_dict(self):
        q = GatewayOperationQueue()
        q.enqueue_fifo(_request())
        sizes = q.sizes()
        assert sizes[QueueType.FIFO.value] == 1

    def test_total_pending(self):
        q = GatewayOperationQueue()
        q.enqueue_fifo(_request())
        q.enqueue_priority(_request())
        assert q.total_pending == 2

    def test_is_empty(self):
        q = GatewayOperationQueue()
        assert q.is_empty
        q.enqueue_fifo(_request())
        assert not q.is_empty

    def test_statistics(self):
        q  = GatewayOperationQueue()
        q.enqueue_fifo(_request())
        q.dequeue_next()
        s = q.statistics
        assert s.fifo_enqueued == 1
        assert s.fifo_dequeued == 1


# ═══════════════════════════════════════════════════════════════════════════════
# TestGatewayEngineRegistry
# ═══════════════════════════════════════════════════════════════════════════════

class TestGatewayEngineRegistry:
    def _reg(self, max_requests=100):
        r = GatewayEngineRegistry(max_requests=max_requests)
        r.start()
        return r

    def test_register_and_get(self):
        reg = self._reg()
        req = _request()
        reg.register(req)
        assert reg.get(req.request_id) is req
        reg.stop()

    def test_duplicate_raises(self):
        reg = self._reg()
        req = _request()
        reg.register(req)
        with pytest.raises(DuplicateEngineRequestError):
            reg.register(req)
        reg.stop()

    def test_not_found_raises(self):
        reg = self._reg()
        with pytest.raises(GatewayEngineRequestNotFoundError):
            reg.get("nonexistent")
        reg.stop()

    def test_capacity_raises(self):
        reg = self._reg(max_requests=1)
        reg.register(_request())
        with pytest.raises(GatewayRegistryCapacityError):
            reg.register(_request())
        reg.stop()

    def test_unregister(self):
        reg = self._reg()
        req = _request()
        reg.register(req)
        reg.unregister(req.request_id)
        assert not reg.exists(req.request_id)
        reg.stop()

    def test_active_filter(self):
        reg = self._reg()
        req = _request()
        reg.register(req)
        assert req in reg.active()
        req.set_status(RequestStatus.COMPLETED)
        assert req not in reg.active()
        reg.stop()

    def test_count(self):
        reg = self._reg()
        reg.register(_request())
        reg.register(_request())
        assert reg.count == 2
        reg.stop()

    def test_not_running_raises(self):
        reg = GatewayEngineRegistry()
        with pytest.raises(GatewayEngineNotRunningError):
            reg.register(_request())


# ═══════════════════════════════════════════════════════════════════════════════
# TestGatewayStateManager
# ═══════════════════════════════════════════════════════════════════════════════

class TestGatewayStateManager:
    def test_initial_stopped(self):
        m = GatewayStateManager()
        assert m.current() == EngineState.STOPPED
        assert m.is_stopped()

    def test_transition(self):
        m = GatewayStateManager()
        m.transition(EngineState.IDLE)
        assert m.current() == EngineState.IDLE
        assert m.is_idle()

    def test_history_grows(self):
        m = GatewayStateManager()
        m.transition(EngineState.IDLE)
        assert m.transition_count >= 2

    def test_is_active(self):
        m = GatewayStateManager()
        m.transition(EngineState.IDLE)
        assert m.is_active()

    def test_is_terminal(self):
        m = GatewayStateManager()
        m.transition(EngineState.STOPPED)
        assert m.is_terminal()


# ═══════════════════════════════════════════════════════════════════════════════
# TestDispatchResult
# ═══════════════════════════════════════════════════════════════════════════════

class TestDispatchResult:
    def _result(self, accepted=True, outcome=DispatchOutcome.ACCEPTED):
        return DispatchResult(
            accepted=accepted,
            outcome=outcome,
            external_id="EXT-1",
            result_metadata={},
            error_code="",
            error_message="",
            dispatched_at=time.time(),
        )

    def test_accepted(self):
        r = self._result(accepted=True)
        assert r.accepted

    def test_to_dict_keys(self):
        d = self._result().to_dict()
        assert "accepted"      in d
        assert "outcome"       in d
        assert "external_id"   in d
        assert "dispatched_at" in d


# ═══════════════════════════════════════════════════════════════════════════════
# TestGatewayDispatcher
# ═══════════════════════════════════════════════════════════════════════════════

class TestGatewayDispatcher:
    def test_simulated_accepts(self):
        d   = GatewayDispatcher()
        req = _request()
        res = d.dispatch(req)
        assert res.accepted
        assert res.outcome == DispatchOutcome.ACCEPTED

    def test_has_broker_false_by_default(self):
        assert not GatewayDispatcher().has_broker

    def test_dispatch_count_increments(self):
        d = GatewayDispatcher()
        d.dispatch(_request())
        assert d.dispatch_count == 1

    def test_cancel_count_increments(self):
        d = GatewayDispatcher()
        d.cancel("REQ-1")
        assert d.cancel_count == 1

    def test_register_broker_replaces(self):
        class FakeBroker:
            is_available = True
            def dispatch(self, req):
                return DispatchResult(
                    accepted=False,
                    outcome=DispatchOutcome.REJECTED,
                    external_id="",
                    result_metadata={},
                    error_code="FAKE",
                    error_message="rejected",
                    dispatched_at=time.time(),
                )
            def cancel(self, req_id, reason=""):
                return False

        d = GatewayDispatcher()
        d.register_broker(FakeBroker())
        assert d.has_broker

    def test_route_decision_passthrough(self):
        d = GatewayDispatcher()
        req = _request()
        res = d.dispatch(req)
        assert res is not None


# ═══════════════════════════════════════════════════════════════════════════════
# TestEngineGatewayValidator
# ═══════════════════════════════════════════════════════════════════════════════

class TestEngineGatewayValidator:
    def test_valid_context(self):
        v   = EngineGatewayValidator()
        res = v.validate_context(_ctx())
        assert res.is_valid

    def test_missing_execution_id(self):
        v   = EngineGatewayValidator()
        ctx = make_engine_gateway_context("", "ORD", "PORT", "STRAT")
        res = v.validate_context(ctx)
        assert not res.is_valid

    def test_missing_order_id(self):
        v   = EngineGatewayValidator()
        ctx = make_engine_gateway_context("EX", "", "PORT", "STRAT")
        res = v.validate_context(ctx)
        assert not res.is_valid

    def test_validation_result_bool(self):
        result = EngineValidationResult(
            is_valid=True, errors=(), warnings=(), validated_at=time.time()
        )
        assert bool(result)

    def test_validation_result_invalid(self):
        result = EngineValidationResult(
            is_valid=False, errors=("bad",), warnings=(), validated_at=time.time()
        )
        assert not bool(result)

    def test_raise_if_invalid(self):
        v  = EngineGatewayValidator()
        r  = EngineValidationResult(
            is_valid=False, errors=("error1",), warnings=(), validated_at=time.time()
        )
        with pytest.raises(GatewayValidationFailedError):
            v.raise_if_invalid(r, "REQ-1")

    def test_to_dict_keys(self):
        r = EngineValidationResult(
            is_valid=True, errors=(), warnings=(), validated_at=time.time()
        )
        d = r.to_dict()
        assert "is_valid" in d
        assert "errors"   in d


# ═══════════════════════════════════════════════════════════════════════════════
# TestGatewayEngineFactory
# ═══════════════════════════════════════════════════════════════════════════════

class TestGatewayEngineFactory:
    def test_create_context(self):
        ctx = GatewayEngineFactory.create_context("EX", "ORD", "PORT", "STRAT")
        assert ctx.execution_id == "EX"
        assert ctx.request_id

    def test_create_request(self):
        ctx = GatewayEngineFactory.create_context("EX", "ORD", "PORT", "STRAT")
        req = GatewayEngineFactory.create_request(ctx)
        assert req.status == RequestStatus.PENDING

    def test_create_session(self):
        s = GatewayEngineFactory.create_session("PORT", "STRAT", "EX")
        assert s.is_active
        assert s.portfolio_id == "PORT"

    def test_create_snapshot_empty(self):
        snap = GatewayEngineFactory.create_snapshot(
            engine_state=EngineState.IDLE,
            requests=[],
            queue_sizes={},
            statistics=GatewayEngineStatistics(),
            active_sessions=0,
        )
        assert snap.total_requests == 0
        assert snap.engine_state == EngineState.IDLE.value

    def test_create_snapshot_with_requests(self):
        ctx = GatewayEngineFactory.create_context("EX", "ORD", "PORT", "STRAT")
        req = GatewayEngineFactory.create_request(ctx)
        snap = GatewayEngineFactory.create_snapshot(
            engine_state=EngineState.IDLE,
            requests=[req],
            queue_sizes={},
            statistics=GatewayEngineStatistics(),
            active_sessions=1,
        )
        assert snap.total_requests == 1
        assert snap.pending_count  == 1

    def test_create_response_success(self):
        ctx = GatewayEngineFactory.create_context("EX", "ORD", "PORT", "STRAT")
        req = GatewayEngineFactory.create_request(ctx)
        req.set_dispatch_result(DispatchOutcome.ACCEPTED, {})
        resp = GatewayEngineFactory.create_response(req, is_success=True)
        assert resp.is_accepted
        assert resp.is_completed

    def test_create_response_failure(self):
        ctx = GatewayEngineFactory.create_context("EX", "ORD", "PORT", "STRAT")
        req = GatewayEngineFactory.create_request(ctx)
        resp = GatewayEngineFactory.create_response(
            req, is_success=False, error_code="EGE-003", error_message="fail"
        )
        assert resp.is_failed
        assert resp.error_code == "EGE-003"


# ═══════════════════════════════════════════════════════════════════════════════
# TestGatewayEvents
# ═══════════════════════════════════════════════════════════════════════════════

class TestGatewayEvents:
    def test_gateway_started_event(self):
        e = make_gateway_started_event()
        assert e.event_type == EngineEventType.GATEWAY_STARTED
        assert e.is_engine_event
        assert e.event_id

    def test_request_received_event(self):
        e = make_request_received_event("REQ-1", "EX-1", "PORT-A", "STRAT-1")
        assert e.event_type == EngineEventType.REQUEST_RECEIVED
        assert e.request_id == "REQ-1"

    def test_request_queued_event(self):
        e = make_request_queued_event("REQ-1", "EX-1", "PORT-A", "STRAT-1")
        assert e.event_type == EngineEventType.REQUEST_QUEUED

    def test_request_dispatched_event(self):
        e = make_request_dispatched_event("REQ-1", "EX-1", "PORT-A", "STRAT-1")
        assert e.event_type == EngineEventType.REQUEST_DISPATCHED

    def test_dispatch_completed_event(self):
        e = make_dispatch_completed_event("REQ-1", "EX-1", "PORT-A", "STRAT-1")
        assert e.event_type == EngineEventType.DISPATCH_COMPLETED
        assert e.is_success_event

    def test_dispatch_failed_event(self):
        e = make_dispatch_failed_event("REQ-1", "EX-1", "PORT-A", "STRAT-1")
        assert e.event_type == EngineEventType.DISPATCH_FAILED
        assert e.is_failure_event

    def test_gateway_stopped_event(self):
        e = make_gateway_stopped_event()
        assert e.event_type == EngineEventType.GATEWAY_STOPPED

    def test_event_to_dict(self):
        e = make_request_received_event("REQ-1", "EX-1", "PORT-A", "STRAT-1")
        d = e.to_dict()
        assert "event_id"   in d
        assert "event_type" in d
        assert "occurred_at" in d

    def test_event_is_frozen(self):
        e = make_gateway_started_event()
        with pytest.raises((AttributeError, TypeError)):
            e.event_id = "X"  # type: ignore[misc]


# ═══════════════════════════════════════════════════════════════════════════════
# TestGatewayManager
# ═══════════════════════════════════════════════════════════════════════════════

class TestGatewayManager:
    def _mgr(self) -> GatewayManager:
        m = GatewayManager()
        m.start()
        return m

    def test_start_stop(self):
        m = self._mgr()
        assert m.is_running
        m.stop()
        assert not m.is_running

    def test_not_running_raises(self):
        m = GatewayManager()
        with pytest.raises(GatewayEngineNotRunningError):
            m.process_request(_ctx())

    def test_process_request_returns_response(self):
        m = self._mgr()
        r = m.process_request(_ctx())
        assert isinstance(r, GatewayResponse)
        m.stop()

    def test_process_request_accepted(self):
        m = self._mgr()
        r = m.process_request(_ctx())
        assert r.is_accepted
        m.stop()

    def test_process_request_registers_request(self):
        m = self._mgr()
        m.process_request(_ctx())
        assert m.request_count >= 1
        m.stop()

    def test_cancel_unknown_returns_false(self):
        m = self._mgr()
        assert not m.cancel_request("nonexistent")
        m.stop()

    def test_cancel_completed_returns_false(self):
        m = self._mgr()
        resp = m.process_request(_ctx())
        result = m.cancel_request(resp.request_id)
        # completed requests are terminal — cancel is a no-op
        assert result is False
        m.stop()

    def test_retry_non_failed_raises(self):
        m = self._mgr()
        resp = m.process_request(_ctx())
        with pytest.raises(GatewayRequestSubmissionError):
            m.retry_request(resp.request_id)
        m.stop()

    def test_statistics_increments(self):
        m = self._mgr()
        m.process_request(_ctx())
        s = m.statistics()
        assert s.requests_received >= 1
        assert s.requests_completed >= 1
        m.stop()

    def test_snapshot_contains_request(self):
        m    = self._mgr()
        m.process_request(_ctx())
        snap = m.snapshot()
        assert snap.total_requests >= 1
        m.stop()

    def test_query_all_requests(self):
        m = self._mgr()
        m.process_request(_ctx())
        assert len(m.all_requests()) >= 1
        m.stop()

    def test_query_by_portfolio_id(self):
        m = self._mgr()
        m.process_request(_ctx(portfolio_id="MY-PORT"))
        results = m.by_portfolio_id("MY-PORT")
        assert len(results) >= 1
        m.stop()

    def test_query_by_execution_id(self):
        m = self._mgr()
        m.process_request(_ctx(execution_id="EX-999"))
        results = m.by_execution_id("EX-999")
        assert len(results) >= 1
        m.stop()

    def test_invalid_context_raises(self):
        m   = self._mgr()
        ctx = make_engine_gateway_context("", "ORD", "PORT", "STRAT")
        with pytest.raises(GatewayRequestSubmissionError):
            m.process_request(ctx)
        m.stop()

    def test_double_stop_raises(self):
        from iios.investment.workflow.engine_lifecycle import EngineNotRunningError
        m = self._mgr()
        m.stop()
        with pytest.raises(EngineNotRunningError):
            m.stop()


# ═══════════════════════════════════════════════════════════════════════════════
# TestExecutionGatewayEngine
# ═══════════════════════════════════════════════════════════════════════════════

class TestExecutionGatewayEngine:
    def test_start_stop(self):
        e = ExecutionGatewayEngine()
        e.start()
        assert e.is_running
        e.stop()
        assert not e.is_running

    def test_not_running_raises(self):
        e = ExecutionGatewayEngine()
        ctx = e.make_context("EX", "ORD", "PORT", "STRAT")
        with pytest.raises(GatewayEngineNotRunningError):
            e.submit_request(ctx)

    def test_make_context(self):
        e   = ExecutionGatewayEngine()
        ctx = e.make_context("EX", "ORD", "PORT", "STRAT", symbol="NIFTY")
        assert ctx.execution_id == "EX"
        assert ctx.symbol       == "NIFTY"

    def test_submit_request_accepted(self):
        e    = _engine()
        ctx  = e.make_context("EX", "ORD", "PORT", "STRAT")
        resp = e.submit_request(ctx)
        assert resp.is_accepted
        e.stop()

    def test_cancel_request_unknown(self):
        e = _engine()
        assert not e.cancel_request("nonexistent")
        e.stop()

    def test_retry_raises_for_completed(self):
        e    = _engine()
        ctx  = e.make_context("EX", "ORD", "PORT", "STRAT")
        resp = e.submit_request(ctx)
        with pytest.raises(GatewayRequestSubmissionError):
            e.retry_request(resp.request_id)
        e.stop()

    def test_snapshot(self):
        e    = _engine()
        e.submit_request(e.make_context("EX", "ORD", "PORT", "STRAT"))
        snap = e.snapshot()
        assert isinstance(snap, GatewayEngineSnapshot)
        assert snap.total_requests >= 1
        e.stop()

    def test_statistics(self):
        e = _engine()
        e.submit_request(e.make_context("EX", "ORD", "PORT", "STRAT"))
        s = e.statistics()
        assert isinstance(s, GatewayEngineStatistics)
        assert s.requests_received >= 1
        e.stop()

    def test_all_requests(self):
        e = _engine()
        e.submit_request(e.make_context("EX", "ORD", "PORT", "STRAT"))
        assert len(e.all_requests()) >= 1
        e.stop()

    def test_completed_requests(self):
        e = _engine()
        e.submit_request(e.make_context("EX", "ORD", "PORT", "STRAT"))
        assert len(e.completed_requests()) >= 1
        e.stop()

    def test_request_count(self):
        e = _engine()
        e.submit_request(e.make_context("EX", "ORD", "PORT", "STRAT"))
        assert e.request_count >= 1
        e.stop()

    def test_has_live_broker_false(self):
        e = _engine()
        assert not e.has_live_broker
        e.stop()

    def test_repr(self):
        e = _engine()
        assert "ExecutionGatewayEngine" in repr(e)
        e.stop()

    def test_event_listener_receives_events(self):
        events: List[GatewayEngineEvent] = []
        e = ExecutionGatewayEngine()
        e.add_event_listener(events.append)
        e.start()
        e.submit_request(e.make_context("EX", "ORD", "PORT", "STRAT"))
        e.stop()
        types = {ev.event_type for ev in events}
        assert EngineEventType.GATEWAY_STARTED  in types
        assert EngineEventType.REQUEST_RECEIVED in types
        assert EngineEventType.DISPATCH_COMPLETED in types

    def test_remove_event_listener(self):
        events: List[GatewayEngineEvent] = []
        e = _engine()
        e.add_event_listener(events.append)
        e.remove_event_listener(events.append)
        e.submit_request(e.make_context("EX", "ORD", "PORT", "STRAT"))
        e.stop()
        # After removal, only engine-stop event should have been received
        # (none fired after removal since listener was removed before submit)
        req_events = [ev for ev in events if ev.event_type == EngineEventType.REQUEST_RECEIVED]
        assert len(req_events) == 0

    def test_by_portfolio_id(self):
        e = _engine()
        e.submit_request(e.make_context("EX", "ORD", "MY-PORT", "STRAT"))
        assert len(e.by_portfolio_id("MY-PORT")) >= 1
        e.stop()

    def test_by_strategy_id(self):
        e = _engine()
        e.submit_request(e.make_context("EX", "ORD", "PORT", "MY-STRAT"))
        assert len(e.by_strategy_id("MY-STRAT")) >= 1
        e.stop()

    def test_by_execution_id(self):
        e = _engine()
        e.submit_request(e.make_context("EX-999", "ORD", "PORT", "STRAT"))
        assert len(e.by_execution_id("EX-999")) >= 1
        e.stop()

    def test_double_stop_raises(self):
        from iios.investment.workflow.engine_lifecycle import EngineNotRunningError
        e = _engine()
        e.stop()
        with pytest.raises(EngineNotRunningError):
            e.stop()


# ═══════════════════════════════════════════════════════════════════════════════
# TestStatisticsIntegration
# ═══════════════════════════════════════════════════════════════════════════════

class TestStatisticsIntegration:
    def test_multiple_requests_accumulate(self):
        e = _engine()
        for i in range(5):
            e.submit_request(e.make_context(f"EX-{i}", "ORD", "PORT", "STRAT"))
        s = e.statistics()
        assert s.requests_received  >= 5
        assert s.requests_completed >= 5
        e.stop()

    def test_failure_rate_zero_when_all_succeed(self):
        e = _engine()
        e.submit_request(e.make_context("EX", "ORD", "PORT", "STRAT"))
        s = e.statistics()
        assert s.failure_rate == 0.0
        e.stop()

    def test_snapshot_stats_match_statistics(self):
        e    = _engine()
        e.submit_request(e.make_context("EX", "ORD", "PORT", "STRAT"))
        snap = e.snapshot()
        s    = e.statistics()
        assert snap.statistics.requests_completed == s.requests_completed
        e.stop()


# ═══════════════════════════════════════════════════════════════════════════════
# TestEventsIntegration
# ═══════════════════════════════════════════════════════════════════════════════

class TestEventsIntegration:
    def test_full_workflow_events(self):
        events: List[GatewayEngineEvent] = []
        e = ExecutionGatewayEngine()
        e.add_event_listener(events.append)
        e.start()
        e.submit_request(e.make_context("EX", "ORD", "PORT", "STRAT"))
        e.stop()

        event_types = [ev.event_type for ev in events]
        assert EngineEventType.GATEWAY_STARTED    in event_types
        assert EngineEventType.REQUEST_RECEIVED   in event_types
        assert EngineEventType.REQUEST_QUEUED     in event_types
        assert EngineEventType.REQUEST_DISPATCHED in event_types
        assert EngineEventType.DISPATCH_COMPLETED in event_types
        assert EngineEventType.GATEWAY_STOPPED    in event_types

    def test_events_have_valid_ids(self):
        events: List[GatewayEngineEvent] = []
        e = _engine()
        e.add_event_listener(events.append)
        e.submit_request(e.make_context("EX", "ORD", "PORT", "STRAT"))
        e.stop()
        for ev in events:
            assert ev.event_id and len(ev.event_id) == 36

    def test_events_have_occurred_at(self):
        events: List[GatewayEngineEvent] = []
        e = _engine()
        e.add_event_listener(events.append)
        e.submit_request(e.make_context("EX", "ORD", "PORT", "STRAT"))
        e.stop()
        for ev in events:
            assert ev.occurred_at > 0.0

    def test_listener_exception_does_not_break_workflow(self):
        def bad_listener(ev):
            raise RuntimeError("listener error")

        e    = _engine()
        e.add_event_listener(bad_listener)
        resp = e.submit_request(e.make_context("EX", "ORD", "PORT", "STRAT"))
        # Should still return a valid response
        assert resp.is_accepted
        e.stop()


# ═══════════════════════════════════════════════════════════════════════════════
# TestConcurrency
# ═══════════════════════════════════════════════════════════════════════════════

class TestConcurrency:
    def test_concurrent_submissions(self):
        e       = _engine()
        results = []
        errors  = []

        def submit(i):
            try:
                r = e.submit_request(
                    e.make_context(f"EX-{i}", f"ORD-{i}", "PORT", "STRAT")
                )
                results.append(r)
            except Exception as ex:
                errors.append(ex)

        threads = [threading.Thread(target=submit, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        e.stop()
        assert len(errors) == 0
        assert len(results) == 20
        for r in results:
            assert r.is_accepted

    def test_concurrent_event_listeners(self):
        e      = _engine()
        events = []
        lock   = threading.Lock()

        def listener(ev):
            with lock:
                events.append(ev)

        e.add_event_listener(listener)

        threads = [
            threading.Thread(
                target=lambda i=i: e.submit_request(
                    e.make_context(f"EX-{i}", f"ORD-{i}", "PORT", "STRAT")
                )
            )
            for i in range(10)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        e.stop()
        assert len(events) > 0

    def test_registry_thread_safety(self):
        reg  = GatewayEngineRegistry(max_requests=1000)
        reg.start()
        errors: List[Exception] = []

        def register():
            try:
                reg.register(_request())
            except Exception as ex:
                errors.append(ex)

        threads = [threading.Thread(target=register) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        reg.stop()
        assert len(errors) == 0
        assert reg.count == 50

    def test_fifo_queue_thread_safety(self):
        q       = FifoQueue(max_size=200)
        enqueued = []
        lock     = threading.Lock()

        def enqueue():
            r = _request()
            q.enqueue(r)
            with lock:
                enqueued.append(r)

        threads = [threading.Thread(target=enqueue) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert q.size == 50


# ═══════════════════════════════════════════════════════════════════════════════
# TestRegression
# ═══════════════════════════════════════════════════════════════════════════════

class TestRegression:
    def test_engine_state_idle_after_submit(self):
        e = _engine()
        e.submit_request(e.make_context("EX", "ORD", "PORT", "STRAT"))
        assert e.engine_state == EngineState.IDLE
        e.stop()

    def test_response_lifecycle_request_id_set(self):
        e    = _engine()
        resp = e.submit_request(e.make_context("EX", "ORD", "PORT", "STRAT"))
        assert resp.lifecycle_request_id
        e.stop()

    def test_response_elapsed_ms_positive(self):
        e    = _engine()
        resp = e.submit_request(e.make_context("EX", "ORD", "PORT", "STRAT"))
        assert resp.elapsed_ms >= 0.0
        e.stop()

    def test_multiple_start_raises(self):
        from iios.investment.workflow.engine_lifecycle import EngineAlreadyRunningError
        e = ExecutionGatewayEngine()
        e.start()
        with pytest.raises(EngineAlreadyRunningError):
            e.start()
        e.stop()

    def test_empty_snapshot(self):
        e    = _engine()
        snap = e.snapshot()
        assert snap.total_requests == 0
        assert snap.completed_count == 0
        e.stop()

    def test_statistics_zero_on_fresh_engine(self):
        e = _engine()
        s = e.statistics()
        assert s.requests_received == 0
        e.stop()

    def test_context_to_dict_is_serialisable(self):
        import json
        ctx = _ctx()
        d   = ctx.to_dict()
        json.dumps(d)  # must not raise

    def test_response_to_dict_is_serialisable(self):
        import json
        e    = _engine()
        resp = e.submit_request(e.make_context("EX", "ORD", "PORT", "STRAT"))
        json.dumps(resp.to_dict())  # must not raise
        e.stop()

    def test_snapshot_to_dict(self):
        e    = _engine()
        e.submit_request(e.make_context("EX", "ORD", "PORT", "STRAT"))
        snap = e.snapshot()
        d    = snap.to_dict()
        assert "snapshot_id"    in d
        assert "engine_state"   in d
        assert "total_requests" in d
        e.stop()

    def test_gateway_history_persists_after_stop(self):
        """History should remain readable after engine stops."""
        from iios.execution.gateway.engine.gateway_history import GatewayEngineHistory
        h  = GatewayEngineHistory()
        op = make_gateway_operation(
            OperationType.SUBMIT_REQUEST, "REQ-1", "SES-1", time.time()
        )
        h.append_operation(op)
        assert h.operation_count == 1

    def test_submit_after_stop_raises(self):
        e = _engine()
        e.stop()
        with pytest.raises(GatewayEngineNotRunningError):
            e.submit_request(e.make_context("EX", "ORD", "PORT", "STRAT"))
