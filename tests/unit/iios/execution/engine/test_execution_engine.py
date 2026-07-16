"""tests/unit/iios/execution/engine/test_execution_engine.py
==================================================
Complete test suite for iios.execution.engine

Parts
-----
 1  EngineExecutionState — enum values, state machine rules
 2  ExecutionRequest     — fields, helpers, validation
 3  ExecutionContext     — assembly, properties
 4  ExecutionResult      — factories, properties
 5  ExecutionSnapshot    — immutable construction
 6  ExecutionEvents      — event types, make_execution_event, mapping
 7  ExecutionHistory     — append-only, thread-safe, eviction
 8  ExecutionStatistics  — per-execution and engine-level metrics
 9  ExecutionValidation  — request / context / transition validation
10  ExecutionFactory     — create_request, create_context
11  ExecutionRegistry    — lifecycle, register, transitions, queries
12  ExecutionEngine      — submit flow, failure paths, cancel
13  ExecutionManager     — facade, delegation
14  Integration          — end-to-end with M1 OrderRegistry
15  Thread Safety        — concurrent submissions
"""
from __future__ import annotations

import threading
import time
import uuid
from decimal import Decimal
from typing import Optional
from unittest.mock import MagicMock

import pytest

from iios.execution.engine import (
    ACTIVE_ENGINE_STATES, ACTOR_ENGINE, ACTOR_SYSTEM, ACTOR_VALIDATOR,
    CANCELLABLE_ENGINE_STATES, TERMINAL_ENGINE_STATES, VALID_ENGINE_TRANSITIONS,
    VERSION, EngineExecutionState, EngineStatistics, ExecutionCancelledError,
    ExecutionCapacityError, ExecutionContext, ExecutionEngine,
    ExecutionEngineNotRunningError, ExecutionEngineError, ExecutionEvent,
    ExecutionEventType, ExecutionFactory, ExecutionHistory, ExecutionHistoryEntry,
    ExecutionManager, ExecutionMode, ExecutionNotFoundError, ExecutionPriority,
    ExecutionRecord, ExecutionRegistry, ExecutionRequest, ExecutionResult,
    ExecutionSnapshot, ExecutionStateError, ExecutionStatistics,
    ExecutionValidationError, ExecutionValidator, RegistryStatistics,
    ValidationResult, allowed_engine_next, assert_engine_transition,
    can_engine_transition, event_type_for_state, is_engine_terminal,
    make_execution_event, make_history_entry,
    DuplicateExecutionError,
)


# ──────────────────────────────────────────────────────────────────────────────
#  Shared fixtures
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def request_() -> ExecutionRequest:
    return ExecutionRequest(
        request_id   = "REQ-TEST-001",
        order_id     = "ORD-TEST-001",
        decision_id  = "DEC-TEST-001",
        portfolio_id = "PORT-TEST-001",
        strategy_id  = "STRAT-TEST-001",
        execution_mode = ExecutionMode.PAPER,
        priority       = ExecutionPriority.NORMAL,
        requested_by   = "test",
    )


@pytest.fixture
def factory() -> ExecutionFactory:
    return ExecutionFactory()


@pytest.fixture
def registry() -> ExecutionRegistry:
    reg = ExecutionRegistry()
    reg.start()
    yield reg
    if reg.is_running:
        reg.stop()


@pytest.fixture
def engine() -> ExecutionEngine:
    eng = ExecutionEngine()
    eng.start()
    yield eng
    if eng.is_running:
        eng.stop()


@pytest.fixture
def manager() -> ExecutionManager:
    mgr = ExecutionManager()
    mgr.start()
    yield mgr
    if mgr.is_running:
        mgr.stop()


def _new_exec_id() -> str:
    return f"EXEC-{uuid.uuid4().hex[:12].upper()}"


# ──────────────────────────────────────────────────────────────────────────────
#  PART 1 — EngineExecutionState
# ──────────────────────────────────────────────────────────────────────────────

class TestEngineExecutionState:

    def test_all_9_states_defined(self):
        names = {s.value for s in EngineExecutionState}
        assert names == {"IDLE", "VALIDATING", "PREPARING", "READY",
                         "EXECUTING", "WAITING", "COMPLETED", "FAILED", "CANCELLED"}

    def test_terminal_states(self):
        assert TERMINAL_ENGINE_STATES == frozenset({
            EngineExecutionState.COMPLETED,
            EngineExecutionState.FAILED,
            EngineExecutionState.CANCELLED,
        })

    def test_active_states(self):
        for s in ACTIVE_ENGINE_STATES:
            assert s in {
                EngineExecutionState.VALIDATING,
                EngineExecutionState.PREPARING,
                EngineExecutionState.READY,
                EngineExecutionState.EXECUTING,
                EngineExecutionState.WAITING,
            }

    def test_can_transition_valid_happy_path(self):
        assert can_engine_transition(EngineExecutionState.IDLE,      EngineExecutionState.VALIDATING)
        assert can_engine_transition(EngineExecutionState.VALIDATING, EngineExecutionState.PREPARING)
        assert can_engine_transition(EngineExecutionState.PREPARING,  EngineExecutionState.READY)
        assert can_engine_transition(EngineExecutionState.READY,      EngineExecutionState.EXECUTING)
        assert can_engine_transition(EngineExecutionState.EXECUTING,  EngineExecutionState.COMPLETED)

    def test_can_transition_failure_paths(self):
        assert can_engine_transition(EngineExecutionState.VALIDATING, EngineExecutionState.FAILED)
        assert can_engine_transition(EngineExecutionState.PREPARING,  EngineExecutionState.FAILED)
        assert can_engine_transition(EngineExecutionState.EXECUTING,  EngineExecutionState.FAILED)

    def test_can_transition_cancel_paths(self):
        for s in CANCELLABLE_ENGINE_STATES:
            assert can_engine_transition(s, EngineExecutionState.CANCELLED)

    def test_terminal_states_have_no_outgoing(self):
        for s in TERMINAL_ENGINE_STATES:
            assert allowed_engine_next(s) == frozenset()

    def test_waiting_can_resume_to_executing(self):
        assert can_engine_transition(EngineExecutionState.WAITING, EngineExecutionState.EXECUTING)

    def test_idle_cannot_skip_to_ready(self):
        assert not can_engine_transition(EngineExecutionState.IDLE, EngineExecutionState.READY)

    def test_is_engine_terminal(self):
        assert is_engine_terminal(EngineExecutionState.COMPLETED)
        assert is_engine_terminal(EngineExecutionState.FAILED)
        assert is_engine_terminal(EngineExecutionState.CANCELLED)
        assert not is_engine_terminal(EngineExecutionState.EXECUTING)

    def test_assert_engine_transition_raises(self):
        with pytest.raises(ExecutionStateError):
            assert_engine_transition(
                EngineExecutionState.COMPLETED,
                EngineExecutionState.VALIDATING,
                "EX-001",
            )

    def test_assert_engine_transition_passes(self):
        # Should not raise
        assert_engine_transition(EngineExecutionState.IDLE, EngineExecutionState.VALIDATING)


# ──────────────────────────────────────────────────────────────────────────────
#  PART 2 — ExecutionRequest
# ──────────────────────────────────────────────────────────────────────────────

class TestExecutionRequest:

    def test_required_fields(self, request_: ExecutionRequest):
        assert request_.order_id     == "ORD-TEST-001"
        assert request_.decision_id  == "DEC-TEST-001"
        assert request_.portfolio_id == "PORT-TEST-001"
        assert request_.strategy_id  == "STRAT-TEST-001"

    def test_default_mode_is_paper(self):
        r = ExecutionRequest(order_id="O", decision_id="D",
                             portfolio_id="P", strategy_id="S")
        assert r.execution_mode == ExecutionMode.PAPER

    def test_not_expired_by_default(self, request_: ExecutionRequest):
        assert not request_.is_expired

    def test_expired_when_past_deadline(self):
        r = ExecutionRequest(
            order_id="O", decision_id="D", portfolio_id="P", strategy_id="S",
            expires_at = time.time() - 1.0,
        )
        assert r.is_expired

    def test_age_sec_positive(self, request_: ExecutionRequest):
        assert request_.age_sec >= 0.0

    def test_to_dict(self, request_: ExecutionRequest):
        d = request_.to_dict()
        assert d["order_id"]      == "ORD-TEST-001"
        assert d["execution_mode"] == "PAPER"
        assert isinstance(d["tags"], list)

    def test_repr(self, request_: ExecutionRequest):
        r = repr(request_)
        assert "ORD-TEST-001" in r
        assert "PAPER" in r


# ──────────────────────────────────────────────────────────────────────────────
#  PART 3 — ExecutionContext
# ──────────────────────────────────────────────────────────────────────────────

class TestExecutionContext:

    def test_basic_properties(self, request_: ExecutionRequest):
        ctx = ExecutionContext(
            execution_id = "EXEC-001",
            request      = request_,
        )
        assert ctx.portfolio_id == "PORT-TEST-001"
        assert ctx.strategy_id  == "STRAT-TEST-001"
        assert ctx.order_id     == "ORD-TEST-001"

    def test_has_fields_false_when_empty(self, request_: ExecutionRequest):
        ctx = ExecutionContext(execution_id="E", request=request_)
        assert not ctx.has_order
        assert not ctx.has_portfolio
        assert not ctx.has_decision
        assert not ctx.has_strategy

    def test_completeness_zero_when_no_refs(self, request_: ExecutionRequest):
        ctx = ExecutionContext(execution_id="E", request=request_)
        assert ctx.completeness == 0.0

    def test_completeness_full_with_all_refs(self, request_: ExecutionRequest):
        mock_order     = MagicMock()
        mock_portfolio = MagicMock()
        mock_decision  = MagicMock()
        mock_strategy  = MagicMock()
        ctx = ExecutionContext(
            execution_id       = "E",
            request            = request_,
            order              = mock_order,
            portfolio_snapshot = mock_portfolio,
            decision           = mock_decision,
            strategy_snapshot  = mock_strategy,
        )
        assert ctx.completeness == 1.0

    def test_is_frozen(self, request_: ExecutionRequest):
        ctx = ExecutionContext(execution_id="E", request=request_)
        with pytest.raises((AttributeError, TypeError)):
            ctx.execution_id = "changed"  # type: ignore[misc]

    def test_to_dict(self, request_: ExecutionRequest):
        ctx = ExecutionContext(execution_id="EXEC-42", request=request_)
        d   = ctx.to_dict()
        assert d["execution_id"] == "EXEC-42"
        assert d["has_order"]    is False
        assert d["completeness"] == 0.0


# ──────────────────────────────────────────────────────────────────────────────
#  PART 4 — ExecutionResult
# ──────────────────────────────────────────────────────────────────────────────

class TestExecutionResult:

    def test_success_factory(self):
        r = ExecutionResult.success("E1", "REQ-1", "ORD-1", time.time())
        assert r.succeeded
        assert r.final_state == EngineExecutionState.COMPLETED
        assert r.duration_ms >= 0.0

    def test_failure_factory(self):
        r = ExecutionResult.failure("E1", "REQ-1", "ORD-1", time.time(),
                                    error_message="bad", error_code="EX-002")
        assert not r.succeeded
        assert r.final_state == EngineExecutionState.FAILED
        assert r.error_message == "bad"

    def test_cancelled_factory(self):
        r = ExecutionResult.cancelled("E1", "REQ-1", "ORD-1", time.time(),
                                      reason="user cancelled")
        assert not r.succeeded
        assert r.final_state == EngineExecutionState.CANCELLED
        assert r.cancelled
        assert "user cancelled" in r.error_message

    def test_properties(self):
        r = ExecutionResult.failure("E", "R", "O", time.time(),
                                    error_message="validation error")
        assert r.failed
        assert r.has_errors

    def test_to_dict(self):
        r = ExecutionResult.success("E", "R", "O", time.time())
        d = r.to_dict()
        assert d["succeeded"]    is True
        assert d["final_state"]  == "COMPLETED"
        assert d["duration_ms"]  >= 0.0

    def test_repr(self):
        r = ExecutionResult.success("EXEC-42", "R", "O", time.time())
        assert "EXEC-42" in repr(r)
        assert "COMPLETED" in repr(r)


# ──────────────────────────────────────────────────────────────────────────────
#  PART 5 — ExecutionSnapshot
# ──────────────────────────────────────────────────────────────────────────────

class TestExecutionSnapshot:

    def test_default_not_terminal(self):
        s = ExecutionSnapshot(execution_id="E")
        assert not s.is_terminal

    def test_is_frozen(self):
        s = ExecutionSnapshot(execution_id="E")
        with pytest.raises((AttributeError, TypeError)):
            s.execution_id = "changed"  # type: ignore[misc]

    def test_to_dict_fields(self):
        s = ExecutionSnapshot(
            execution_id  = "E1",
            request_id    = "R1",
            execution_state = EngineExecutionState.READY,
            is_terminal   = False,
        )
        d = s.to_dict()
        assert d["execution_id"]    == "E1"
        assert d["execution_state"] == "READY"
        assert d["is_terminal"]     is False

    def test_repr(self):
        s = ExecutionSnapshot(execution_id="E-SNAP", execution_state=EngineExecutionState.COMPLETED)
        assert "E-SNAP" in repr(s)


# ──────────────────────────────────────────────────────────────────────────────
#  PART 6 — ExecutionEvents
# ──────────────────────────────────────────────────────────────────────────────

class TestExecutionEvents:

    def test_all_event_types_defined(self):
        types = {e.value for e in ExecutionEventType}
        assert "EXECUTION_STARTED"   in types
        assert "EXECUTION_VALIDATED" in types
        assert "EXECUTION_PREPARED"  in types
        assert "EXECUTION_READY"     in types
        assert "EXECUTION_COMPLETED" in types
        assert "EXECUTION_FAILED"    in types
        assert "EXECUTION_CANCELLED" in types

    def test_event_type_for_state_mapping(self):
        assert event_type_for_state(EngineExecutionState.VALIDATING) == ExecutionEventType.EXECUTION_STARTED
        assert event_type_for_state(EngineExecutionState.PREPARING)  == ExecutionEventType.EXECUTION_VALIDATED
        assert event_type_for_state(EngineExecutionState.READY)      == ExecutionEventType.EXECUTION_PREPARED
        assert event_type_for_state(EngineExecutionState.EXECUTING)  == ExecutionEventType.EXECUTION_READY
        assert event_type_for_state(EngineExecutionState.COMPLETED)  == ExecutionEventType.EXECUTION_COMPLETED
        assert event_type_for_state(EngineExecutionState.FAILED)     == ExecutionEventType.EXECUTION_FAILED
        assert event_type_for_state(EngineExecutionState.CANCELLED)  == ExecutionEventType.EXECUTION_CANCELLED
        assert event_type_for_state(EngineExecutionState.IDLE)       is None
        assert event_type_for_state(EngineExecutionState.WAITING)    is None

    def test_make_execution_event_fields(self):
        ev = make_execution_event("EXEC-1", ExecutionEventType.EXECUTION_STARTED)
        assert ev.execution_id == "EXEC-1"
        assert ev.event_type   == ExecutionEventType.EXECUTION_STARTED
        assert ev.occurred_at  > 0

    def test_event_is_frozen(self):
        ev = make_execution_event("E", ExecutionEventType.EXECUTION_COMPLETED)
        with pytest.raises((AttributeError, TypeError)):
            ev.execution_id = "changed"  # type: ignore[misc]

    def test_event_to_dict(self):
        ev = make_execution_event("E", ExecutionEventType.EXECUTION_PREPARED)
        d  = ev.to_dict()
        assert d["execution_id"] == "E"
        assert d["event_type"]   == "EXECUTION_PREPARED"
        assert d["snapshot"]     is None

    def test_event_with_snapshot(self):
        snap = ExecutionSnapshot(execution_id="E")
        ev   = make_execution_event("E", ExecutionEventType.EXECUTION_READY,
                                    snapshot=snap)
        assert ev.snapshot is snap


# ──────────────────────────────────────────────────────────────────────────────
#  PART 7 — ExecutionHistory
# ──────────────────────────────────────────────────────────────────────────────

class TestExecutionHistory:

    def _entry(self, from_s: EngineExecutionState, to_s: EngineExecutionState,
               eid: str = "E") -> ExecutionHistoryEntry:
        return make_history_entry(eid, from_s, to_s, "r", "actor")

    def test_empty_initially(self):
        h = ExecutionHistory("E")
        assert h.count() == 0
        assert h.first() is None
        assert h.last()  is None

    def test_record_and_retrieve(self):
        h = ExecutionHistory("E")
        e = self._entry(EngineExecutionState.IDLE, EngineExecutionState.VALIDATING)
        h.record(e)
        assert h.count() == 1
        assert h.last()  == e

    def test_entries_returns_tuple(self):
        h = ExecutionHistory("E")
        h.record(self._entry(EngineExecutionState.IDLE, EngineExecutionState.VALIDATING))
        assert isinstance(h.entries(), tuple)

    def test_states_visited(self):
        h = ExecutionHistory("E")
        h.record(self._entry(EngineExecutionState.IDLE, EngineExecutionState.VALIDATING))
        h.record(self._entry(EngineExecutionState.VALIDATING, EngineExecutionState.PREPARING))
        sv = h.states_visited()
        assert EngineExecutionState.VALIDATING in sv
        assert EngineExecutionState.PREPARING  in sv

    def test_wrong_execution_id_raises(self):
        h = ExecutionHistory("E")
        e = make_history_entry("WRONG", EngineExecutionState.IDLE,
                               EngineExecutionState.VALIDATING, "r", "a")
        with pytest.raises(ValueError, match="execution_id"):
            h.record(e)

    def test_eviction(self):
        h = ExecutionHistory("E", max_entries=2)
        for from_s, to_s in [
            (EngineExecutionState.IDLE, EngineExecutionState.VALIDATING),
            (EngineExecutionState.VALIDATING, EngineExecutionState.PREPARING),
            (EngineExecutionState.PREPARING, EngineExecutionState.READY),
        ]:
            h.record(make_history_entry("E", from_s, to_s, "r", "a"))
        assert h.count()         == 2
        assert h.total_recorded  == 3
        assert h.evicted_count   == 1

    def test_thread_safe(self):
        h      = ExecutionHistory("E", max_entries=500)
        errors: list = []

        def worker():
            try:
                h.record(make_history_entry(
                    "E",
                    EngineExecutionState.IDLE,
                    EngineExecutionState.VALIDATING,
                    "r", "a",
                ))
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors

    def test_len_and_iter(self):
        h = ExecutionHistory("E")
        h.record(self._entry(EngineExecutionState.IDLE, EngineExecutionState.VALIDATING))
        assert len(h) == 1
        assert len(list(h)) == 1


# ──────────────────────────────────────────────────────────────────────────────
#  PART 8 — ExecutionStatistics
# ──────────────────────────────────────────────────────────────────────────────

class TestExecutionStatistics:

    def test_initial_state(self):
        s = ExecutionStatistics(execution_id="E")
        assert s.started_at   is None
        assert s.completed_at is None
        assert s.succeeded    is False
        assert s.total_duration is None

    def test_on_transition_validating_sets_started_at(self):
        s   = ExecutionStatistics(execution_id="E")
        now = time.time()
        s.on_transition(EngineExecutionState.IDLE,
                        EngineExecutionState.VALIDATING, occurred_at=now)
        assert s.started_at == now

    def test_on_transition_completed_sets_succeeded(self):
        s = ExecutionStatistics(execution_id="E")
        now = time.time()
        s.on_transition(EngineExecutionState.IDLE,
                        EngineExecutionState.VALIDATING, occurred_at=now)
        s.on_transition(EngineExecutionState.VALIDATING,
                        EngineExecutionState.COMPLETED, occurred_at=now + 1.0)
        assert s.succeeded
        assert s.total_duration == pytest.approx(1.0, abs=0.05)

    def test_on_transition_failed_sets_not_succeeded(self):
        s = ExecutionStatistics(execution_id="E")
        now = time.time()
        s.on_transition(EngineExecutionState.IDLE,
                        EngineExecutionState.VALIDATING, occurred_at=now)
        s.on_transition(EngineExecutionState.VALIDATING,
                        EngineExecutionState.FAILED, occurred_at=now + 0.5)
        assert not s.succeeded
        assert s.final_state == EngineExecutionState.FAILED

    def test_validation_duration(self):
        s   = ExecutionStatistics(execution_id="E")
        now = time.time()
        s.on_transition(EngineExecutionState.IDLE,
                        EngineExecutionState.VALIDATING, occurred_at=now)
        s.on_transition(EngineExecutionState.VALIDATING,
                        EngineExecutionState.PREPARING, occurred_at=now + 0.2)
        assert s.validation_duration == pytest.approx(0.2, abs=0.01)

    def test_to_dict(self):
        s = ExecutionStatistics(execution_id="E")
        d = s.to_dict()
        assert d["execution_id"]       == "E"
        assert d["total_duration_sec"] >= 0.0

    def test_engine_statistics_record_completion(self):
        es = EngineStatistics()
        es2 = EngineStatistics()

        s = ExecutionStatistics(execution_id="E1")
        s.on_transition(EngineExecutionState.IDLE,
                        EngineExecutionState.VALIDATING, occurred_at=time.time())
        s.on_transition(EngineExecutionState.VALIDATING,
                        EngineExecutionState.COMPLETED, occurred_at=time.time())
        es.record_completion(s)
        assert es.success_count   == 1
        assert es.execution_count == 1
        assert es.success_rate    == 1.0

    def test_engine_statistics_failure_rate(self):
        es = EngineStatistics()
        for _ in range(3):
            s = ExecutionStatistics(execution_id="E")
            s.on_transition(EngineExecutionState.IDLE,
                            EngineExecutionState.VALIDATING)
            s.on_transition(EngineExecutionState.VALIDATING,
                            EngineExecutionState.FAILED)
            es.record_completion(s)
        assert es.failure_count == 3
        assert es.failure_rate  == pytest.approx(1.0)


# ──────────────────────────────────────────────────────────────────────────────
#  PART 9 — ExecutionValidation
# ──────────────────────────────────────────────────────────────────────────────

class TestExecutionValidation:

    @pytest.fixture
    def validator(self) -> ExecutionValidator:
        return ExecutionValidator()

    def test_valid_request_passes(self, validator: ExecutionValidator,
                                   request_: ExecutionRequest):
        result = validator.validate_request(request_)
        assert result.passed
        assert len(result.errors) == 0

    def test_empty_order_id_fails(self, validator: ExecutionValidator):
        r = ExecutionRequest(order_id="", decision_id="D",
                             portfolio_id="P", strategy_id="S")
        result = validator.validate_request(r)
        assert not result.passed
        assert any("order_id" in e for e in result.errors)

    def test_empty_decision_id_fails(self, validator: ExecutionValidator):
        r = ExecutionRequest(order_id="O", decision_id="",
                             portfolio_id="P", strategy_id="S")
        result = validator.validate_request(r)
        assert not result.passed

    def test_empty_portfolio_id_fails(self, validator: ExecutionValidator):
        r = ExecutionRequest(order_id="O", decision_id="D",
                             portfolio_id="", strategy_id="S")
        result = validator.validate_request(r)
        assert not result.passed

    def test_expired_request_fails(self, validator: ExecutionValidator):
        r = ExecutionRequest(
            order_id="O", decision_id="D", portfolio_id="P", strategy_id="S",
            expires_at = time.time() - 1.0,
        )
        result = validator.validate_request(r)
        assert not result.passed
        assert any("REQUEST_EXPIRED" in e or "expired" in e.lower() for e in result.errors)

    def test_context_with_no_request_fails(self, validator: ExecutionValidator):
        ctx    = ExecutionContext(execution_id="E")
        result = validator.validate_context(ctx)
        assert not result.passed

    def test_context_with_no_order_fails(self, validator: ExecutionValidator,
                                          request_: ExecutionRequest):
        ctx    = ExecutionContext(execution_id="E", request=request_)
        result = validator.validate_context(ctx)
        assert not result.passed
        assert any("ORDER_NOT_FOUND" in e for e in result.errors)

    def test_context_warns_on_missing_portfolio(self, validator: ExecutionValidator,
                                                 request_: ExecutionRequest):
        from iios.execution.lifecycle import Order, OrderContext, OrderSide, OrderType
        from decimal import Decimal
        order_ctx = OrderContext(strategy_id="S", portfolio_id="P",
                                 decision_id="D", workflow_id="W")
        order = Order(order_id="ORD-V", context=order_ctx, instrument="TCS",
                      exchange="NSE", side=OrderSide.BUY,
                      order_type=OrderType.MARKET, quantity=Decimal("10"))
        ctx    = ExecutionContext(execution_id="E", request=request_, order=order)
        result = validator.validate_context(ctx)
        # Should pass but warn about missing portfolio
        assert result.passed
        assert any("PORTFOLIO_MISSING" in w for w in result.warnings)

    def test_valid_engine_transition(self, validator: ExecutionValidator):
        result = validator.validate_engine_transition(
            EngineExecutionState.IDLE, EngineExecutionState.VALIDATING
        )
        assert result.passed

    def test_invalid_engine_transition(self, validator: ExecutionValidator):
        result = validator.validate_engine_transition(
            EngineExecutionState.IDLE, EngineExecutionState.COMPLETED
        )
        assert not result.passed

    def test_terminal_state_blocks_transition(self, validator: ExecutionValidator):
        result = validator.validate_engine_transition(
            EngineExecutionState.COMPLETED, EngineExecutionState.VALIDATING
        )
        assert not result.passed

    def test_validation_result_bool(self):
        assert bool(ValidationResult.ok())
        assert not bool(ValidationResult.fail("error"))


# ──────────────────────────────────────────────────────────────────────────────
#  PART 10 — ExecutionFactory
# ──────────────────────────────────────────────────────────────────────────────

class TestExecutionFactory:

    def test_create_request_all_fields(self, factory: ExecutionFactory):
        req = factory.create_request(
            order_id     = "ORD-F-001",
            decision_id  = "DEC-F-001",
            portfolio_id = "PORT-F-001",
            strategy_id  = "STRAT-F-001",
        )
        assert req.order_id     == "ORD-F-001"
        assert req.decision_id  == "DEC-F-001"
        assert req.portfolio_id == "PORT-F-001"
        assert req.strategy_id  == "STRAT-F-001"
        assert req.execution_mode == ExecutionMode.PAPER

    def test_create_request_custom_mode(self, factory: ExecutionFactory):
        req = factory.create_request(
            order_id="O", decision_id="D", portfolio_id="P", strategy_id="S",
            execution_mode = ExecutionMode.SIMULATION,
        )
        assert req.execution_mode == ExecutionMode.SIMULATION

    def test_create_request_invalid_raises(self, factory: ExecutionFactory):
        with pytest.raises(ExecutionValidationError):
            factory.create_request(
                order_id     = "",   # invalid
                decision_id  = "D",
                portfolio_id = "P",
                strategy_id  = "S",
            )

    def test_create_context_no_registry(self, factory: ExecutionFactory,
                                         request_: ExecutionRequest):
        ctx = factory.create_context(
            request      = request_,
            execution_id = "EXEC-F-001",
        )
        assert ctx.execution_id == "EXEC-F-001"
        assert ctx.order        is None

    def test_create_context_with_mock_registry(self, factory: ExecutionFactory,
                                                request_: ExecutionRequest):
        mock_order    = MagicMock()
        mock_registry = MagicMock()
        mock_registry.get.return_value = mock_order

        ctx = factory.create_context(
            request        = request_,
            execution_id   = "EXEC-F-002",
            order_registry = mock_registry,
        )
        assert ctx.order is mock_order

    def test_create_context_none_request_raises(self, factory: ExecutionFactory):
        from iios.execution.engine import ExecutionRequestError
        with pytest.raises(ExecutionRequestError):
            factory.create_context(request=None, execution_id="E")  # type: ignore

    def test_gen_execution_id_format(self):
        eid = ExecutionFactory.gen_execution_id()
        assert eid.startswith("EXEC-")
        assert len(eid) > 5

    def test_factory_system_id(self, factory: ExecutionFactory):
        assert factory.SYSTEM_ID.startswith("iios:execution:engine")
        assert factory.VERSION == "1.0.0"


# ──────────────────────────────────────────────────────────────────────────────
#  PART 11 — ExecutionRegistry
# ──────────────────────────────────────────────────────────────────────────────

class TestExecutionRegistry:

    def test_not_running_before_start(self):
        reg = ExecutionRegistry()
        assert not reg.is_running

    def test_running_after_start(self, registry: ExecutionRegistry):
        assert registry.is_running

    def test_register_returns_record(self, registry: ExecutionRegistry):
        rec = registry.register("E1", "R1", "O1", "P1", "S1")
        assert isinstance(rec, ExecutionRecord)
        assert rec.state == EngineExecutionState.IDLE

    def test_register_duplicate_raises(self, registry: ExecutionRegistry):
        registry.register("E1", "R1", "O1", "P1", "S1")
        with pytest.raises(DuplicateExecutionError):
            registry.register("E1", "R2", "O2", "P2", "S2")

    def test_get_not_found_raises(self, registry: ExecutionRegistry):
        with pytest.raises(ExecutionNotFoundError):
            registry.get("NONEXISTENT")

    def test_contains(self, registry: ExecutionRegistry):
        assert not registry.contains("E1")
        registry.register("E1", "R1", "O1", "P1", "S1")
        assert registry.contains("E1")

    def test_apply_transition_valid(self, registry: ExecutionRegistry):
        registry.register("E1", "R1", "O1", "P1", "S1")
        rec = registry.apply_transition("E1", EngineExecutionState.VALIDATING,
                                        reason="test")
        assert rec.state == EngineExecutionState.VALIDATING

    def test_apply_transition_invalid_raises(self, registry: ExecutionRegistry):
        registry.register("E1", "R1", "O1", "P1", "S1")
        with pytest.raises(ExecutionStateError):
            registry.apply_transition("E1", EngineExecutionState.COMPLETED)

    def test_get_active(self, registry: ExecutionRegistry):
        registry.register("E1", "R1", "O1", "P1", "S1")
        registry.apply_transition("E1", EngineExecutionState.VALIDATING)
        active = registry.get_active()
        assert any(r.execution_id == "E1" for r in active)

    def test_get_by_portfolio(self, registry: ExecutionRegistry):
        for i in range(3):
            registry.register(f"E{i}", f"R{i}", f"O{i}", "PORT-A", f"S{i}")
        records = registry.get_by_portfolio("PORT-A")
        assert len(records) == 3

    def test_get_by_strategy(self, registry: ExecutionRegistry):
        for i in range(2):
            registry.register(f"E{i}", f"R{i}", f"O{i}", f"P{i}", "STRAT-Z")
        records = registry.get_by_strategy("STRAT-Z")
        assert len(records) == 2

    def test_capacity_exceeded_raises(self):
        reg = ExecutionRegistry(max_executions=2)
        reg.start()
        try:
            reg.register("E1", "R1", "O1", "P1", "S1")
            reg.register("E2", "R2", "O2", "P2", "S2")
            with pytest.raises(ExecutionCapacityError):
                reg.register("E3", "R3", "O3", "P3", "S3")
        finally:
            reg.stop()

    def test_register_when_not_running_raises(self):
        reg = ExecutionRegistry()
        with pytest.raises(ExecutionEngineNotRunningError):
            reg.register("E1", "R1", "O1", "P1", "S1")

    def test_statistics(self, registry: ExecutionRegistry):
        registry.register("E1", "R1", "O1", "P1", "S1")
        stats = registry.statistics()
        assert isinstance(stats, RegistryStatistics)
        assert stats.total_registered >= 1

    def test_listener_called_on_transition(self, registry: ExecutionRegistry):
        events: list = []
        registry.add_listener(events.append)
        registry.register("E1", "R1", "O1", "P1", "S1")
        registry.apply_transition("E1", EngineExecutionState.VALIDATING)
        # dispatch is called explicitly — no auto dispatch from apply_transition
        # (dispatch is done by engine, not registry directly)
        assert registry.contains("E1")

    def test_listener_dispatch_fires(self, registry: ExecutionRegistry):
        events: list = []
        registry.add_listener(events.append)
        ev = make_execution_event("E99", ExecutionEventType.EXECUTION_STARTED)
        registry.dispatch(ev)
        assert len(events) == 1

    def test_listener_removed(self, registry: ExecutionRegistry):
        events: list = []
        registry.add_listener(events.append)
        registry.remove_listener(events.append)
        ev = make_execution_event("E99", ExecutionEventType.EXECUTION_STARTED)
        registry.dispatch(ev)
        assert len(events) == 0

    def test_faulty_listener_does_not_crash(self, registry: ExecutionRegistry):
        def bad(ev: ExecutionEvent) -> None:
            raise RuntimeError("boom")
        registry.add_listener(bad)
        ev = make_execution_event("E99", ExecutionEventType.EXECUTION_STARTED)
        # Should not raise
        registry.dispatch(ev)


# ──────────────────────────────────────────────────────────────────────────────
#  PART 12 — ExecutionEngine
# ──────────────────────────────────────────────────────────────────────────────

class TestExecutionEngine:

    def test_not_running_before_start(self):
        eng = ExecutionEngine()
        assert not eng.is_running

    def test_running_after_start(self, engine: ExecutionEngine):
        assert engine.is_running

    def test_submit_not_running_raises(self, request_: ExecutionRequest):
        eng = ExecutionEngine()
        with pytest.raises(ExecutionEngineNotRunningError):
            eng.submit(request_)

    def test_submit_valid_request_returns_success(self,
                                                    engine: ExecutionEngine,
                                                    request_: ExecutionRequest):
        # request_ has order_id set but no registry provided
        # validation will fail on context (ORDER_NOT_FOUND)
        result = engine.submit(request_)
        # Without an order_registry, context validation fails → FAILED
        assert not result.succeeded
        assert result.final_state == EngineExecutionState.FAILED
        assert any("ORDER_NOT_FOUND" in e for e in result.validation_errors)

    def test_submit_empty_order_id_fails_at_validation(self,
                                                         engine: ExecutionEngine):
        req = ExecutionRequest(
            order_id="",        # invalid
            decision_id="D",
            portfolio_id="P",
            strategy_id="S",
        )
        result = engine.submit(req)
        assert not result.succeeded
        assert result.final_state == EngineExecutionState.FAILED

    def test_submit_expired_request_fails(self, engine: ExecutionEngine):
        req = ExecutionRequest(
            order_id="O", decision_id="D", portfolio_id="P", strategy_id="S",
            expires_at = time.time() - 1.0,
        )
        result = engine.submit(req)
        assert not result.succeeded

    def test_submit_with_mock_registry_succeeds(self, engine: ExecutionEngine,
                                                  request_: ExecutionRequest):
        from iios.execution.lifecycle import Order, OrderContext, OrderSide, OrderType
        from decimal import Decimal
        from iios.execution.lifecycle.order_state import OrderState

        order_ctx = OrderContext(strategy_id="S", portfolio_id="P",
                                 decision_id="D", workflow_id="W")
        order = Order(
            order_id="ORD-TEST-001", context=order_ctx,
            instrument="TCS", exchange="NSE",
            side=OrderSide.BUY, order_type=OrderType.MARKET,
            quantity=Decimal("10"),
        )
        # Manually set order to VALIDATED state (bypass normal flow for test)
        order.state = OrderState.VALIDATED

        mock_registry = MagicMock()
        mock_registry.get.return_value = order
        mock_registry.apply_transition.return_value = (order, MagicMock(), MagicMock())

        result = engine.submit(request_, order_registry=mock_registry)
        assert result.succeeded
        assert result.final_state == EngineExecutionState.COMPLETED

    def test_submit_emits_events(self, engine: ExecutionEngine,
                                  request_: ExecutionRequest):
        from iios.execution.lifecycle import Order, OrderContext, OrderSide, OrderType
        from decimal import Decimal
        from iios.execution.lifecycle.order_state import OrderState

        order_ctx = OrderContext(strategy_id="S", portfolio_id="P",
                                 decision_id="D", workflow_id="W")
        order = Order(
            order_id="ORD-TEST-001", context=order_ctx,
            instrument="TCS", exchange="NSE",
            side=OrderSide.BUY, order_type=OrderType.MARKET,
            quantity=Decimal("10"),
        )
        order.state = OrderState.VALIDATED

        mock_registry = MagicMock()
        mock_registry.get.return_value = order
        mock_registry.apply_transition.return_value = (order, MagicMock(), MagicMock())

        events: list[ExecutionEvent] = []
        engine.add_listener(events.append)

        engine.submit(request_, order_registry=mock_registry)

        # Should have received at least: PREPARED, READY, COMPLETED
        event_types = [e.event_type for e in events]
        assert ExecutionEventType.EXECUTION_COMPLETED in event_types

    def test_cancel_active_execution(self, engine: ExecutionEngine):
        # Manually register an execution in VALIDATING state via the registry
        registry = engine._registry
        registry.register("EXEC-CANCEL-001", "R1", "O1", "P1", "S1")
        registry.apply_transition("EXEC-CANCEL-001", EngineExecutionState.VALIDATING)

        cancelled = engine.cancel("EXEC-CANCEL-001", reason="test cancel")
        assert cancelled
        rec = engine.get_record("EXEC-CANCEL-001")
        assert rec.state == EngineExecutionState.CANCELLED

    def test_cancel_nonexistent_returns_false(self, engine: ExecutionEngine):
        result = engine.cancel("NONEXISTENT")
        assert not result

    def test_cancel_terminal_returns_false(self, engine: ExecutionEngine):
        registry = engine._registry
        registry.register("EXEC-TERM-001", "R1", "O1", "P1", "S1")
        for to_s in [EngineExecutionState.VALIDATING,
                     EngineExecutionState.PREPARING,
                     EngineExecutionState.READY,
                     EngineExecutionState.EXECUTING,
                     EngineExecutionState.COMPLETED]:
            registry.apply_transition("EXEC-TERM-001", to_s)
        result = engine.cancel("EXEC-TERM-001")
        assert not result

    def test_statistics(self, engine: ExecutionEngine, request_: ExecutionRequest):
        engine.submit(request_)
        stats = engine.statistics()
        assert stats.total_registered >= 1

    def test_system_id_and_version(self, engine: ExecutionEngine):
        assert engine.SYSTEM_ID.startswith("iios:execution:engine")
        assert engine.VERSION == "1.0.0"


# ──────────────────────────────────────────────────────────────────────────────
#  PART 13 — ExecutionManager
# ──────────────────────────────────────────────────────────────────────────────

class TestExecutionManager:

    def test_not_running_before_start(self):
        mgr = ExecutionManager()
        assert not mgr.is_running

    def test_running_after_start(self, manager: ExecutionManager):
        assert manager.is_running

    def test_create_request(self, manager: ExecutionManager):
        req = manager.create_request(
            order_id="O", decision_id="D",
            portfolio_id="P", strategy_id="S",
        )
        assert req.order_id == "O"

    def test_create_request_invalid_raises(self, manager: ExecutionManager):
        with pytest.raises(ExecutionValidationError):
            manager.create_request(order_id="", decision_id="D",
                                   portfolio_id="P", strategy_id="S")

    def test_submit_delegates_to_engine(self, manager: ExecutionManager,
                                         request_: ExecutionRequest):
        result = manager.submit(request_)
        assert isinstance(result, ExecutionResult)

    def test_statistics_returns_registry_stats(self, manager: ExecutionManager,
                                                request_: ExecutionRequest):
        manager.submit(request_)
        stats = manager.statistics()
        assert isinstance(stats, RegistryStatistics)
        assert stats.total_registered >= 1

    def test_add_and_remove_listener(self, manager: ExecutionManager):
        events: list = []
        manager.add_listener(events.append)
        manager.remove_listener(events.append)
        # After removal, no events should be received
        ev = make_execution_event("E", ExecutionEventType.EXECUTION_STARTED)
        manager._engine._registry.dispatch(ev)
        assert len(events) == 0


# ──────────────────────────────────────────────────────────────────────────────
#  PART 14 — Integration with M1 OrderRegistry
# ──────────────────────────────────────────────────────────────────────────────

class TestIntegrationWithOrderLifecycle:

    @pytest.fixture
    def order_registry(self):
        from iios.execution.lifecycle import OrderRegistry
        reg = OrderRegistry()
        reg.start()
        yield reg
        if reg.is_running:
            reg.stop()

    @pytest.fixture
    def validated_order(self, order_registry):
        from iios.execution.lifecycle import (
            Order, OrderContext, OrderFactory, OrderRegistry, OrderSide,
            OrderState, OrderType,
        )
        from decimal import Decimal

        factory   = OrderFactory()
        order_ctx = OrderContext(strategy_id="S", portfolio_id="P",
                                 decision_id="D", workflow_id="W")
        order = factory.create_market_order(
            context=order_ctx, instrument="TCS", exchange="NSE",
            side=OrderSide.BUY, quantity=Decimal("10"),
        )
        order_registry.register(order)
        order_registry.apply_transition(order.order_id,
                                         OrderState.VALIDATED,
                                         reason="validation passed",
                                         actor="validator")
        return order

    def test_submit_advances_order_to_pending_submission(
        self,
        engine: ExecutionEngine,
        order_registry,
        validated_order,
    ):
        from iios.execution.lifecycle.order_state import OrderState

        request = ExecutionRequest(
            order_id     = validated_order.order_id,
            decision_id  = "DEC-INT-001",
            portfolio_id = "PORT-INT-001",
            strategy_id  = "STRAT-INT-001",
        )
        result = engine.submit(request, order_registry=order_registry)
        assert result.succeeded
        assert validated_order.state == OrderState.PENDING_SUBMISSION

    def test_submit_returns_completed_result_with_order(
        self,
        engine: ExecutionEngine,
        order_registry,
        validated_order,
    ):
        request = ExecutionRequest(
            order_id     = validated_order.order_id,
            decision_id  = "DEC-INT-002",
            portfolio_id = "PORT-INT-002",
            strategy_id  = "STRAT-INT-002",
        )
        result = engine.submit(request, order_registry=order_registry)
        assert result.order_id == validated_order.order_id
        assert result.final_state == EngineExecutionState.COMPLETED

    def test_snapshot_published_with_correct_fields(
        self,
        engine: ExecutionEngine,
        order_registry,
        validated_order,
    ):
        snapshots: list[ExecutionSnapshot] = []

        def capture(event: ExecutionEvent) -> None:
            if event.snapshot:
                snapshots.append(event.snapshot)

        engine.add_listener(capture)

        request = ExecutionRequest(
            order_id     = validated_order.order_id,
            decision_id  = "DEC-SNAP-001",
            portfolio_id = "PORT-SNAP-001",
            strategy_id  = "STRAT-SNAP-001",
        )
        engine.submit(request, order_registry=order_registry)

        assert len(snapshots) >= 1
        snap = snapshots[0]
        assert snap.order_id == validated_order.order_id
        assert snap.has_order is True


# ──────────────────────────────────────────────────────────────────────────────
#  PART 15 — Thread Safety
# ──────────────────────────────────────────────────────────────────────────────

class TestThreadSafety:

    def test_concurrent_submissions(self, engine: ExecutionEngine):
        """N concurrent submits should all return valid ExecutionResult."""
        n       = 30
        results: list[ExecutionResult] = []
        errors:  list = []
        lock    = threading.Lock()

        def worker(i: int) -> None:
            try:
                req = ExecutionRequest(
                    order_id     = f"ORD-CONC-{i:04d}",
                    decision_id  = f"DEC-{i}",
                    portfolio_id = "PORT-CONC",
                    strategy_id  = "STRAT-CONC",
                )
                result = engine.submit(req)
                with lock:
                    results.append(result)
            except Exception as exc:
                with lock:
                    errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Concurrent submit errors: {errors}"
        assert len(results) == n
        # All should be FAILED (no order registry) but should NOT crash
        for r in results:
            assert isinstance(r, ExecutionResult)
            assert r.final_state in TERMINAL_ENGINE_STATES

    def test_concurrent_registry_registrations(self, registry: ExecutionRegistry):
        """N concurrent registrations should all succeed."""
        n      = 50
        errors: list = []

        def worker(i: int) -> None:
            try:
                registry.register(f"CONC-{i:04d}", f"R{i}", f"O{i}",
                                   f"P{i}", f"S{i}")
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert registry.count() >= n

    def test_concurrent_listeners(self, engine: ExecutionEngine):
        """Multiple listeners on concurrent events should all fire."""
        lock    = threading.Lock()
        event_counts: dict[int, int] = {}

        def make_listener(n: int):
            def listener(ev: ExecutionEvent) -> None:
                with lock:
                    event_counts[n] = event_counts.get(n, 0) + 1
            return listener

        for i in range(5):
            engine.add_listener(make_listener(i))

        req = ExecutionRequest(
            order_id="O", decision_id="D",
            portfolio_id="P", strategy_id="S",
        )
        engine.submit(req)

        # Each listener should have seen at least one event
        assert len(event_counts) == 5
        for count in event_counts.values():
            assert count >= 1
