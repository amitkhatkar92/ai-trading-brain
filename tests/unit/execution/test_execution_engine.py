"""tests/unit/execution/test_execution_engine.py

Comprehensive unit test suite for the IIOS Execution Engine Core.
Target: ≥150 tests covering lifecycle, workflow, recovery, concurrency, and performance.
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import threading
import time
import uuid

import pytest

# ── Constants ────────────────────────────────────────────────────────────────
from iios.execution.execution_constants import (
    ACTIVE_STATUSES,
    EXECUTION_ENGINE_SYSTEM_ID,
    EXECUTION_ENGINE_VERSION,
    TERMINAL_STATUSES,
    VALID_TRANSITIONS,
    ExecutionEventType,
    ExecutionMode,
    ExecutionPriority,
    ExecutionStatus,
    ExecutionType,
    TimeInForce,
    WorkflowStatus,
    WorkflowStepStatus,
)

# ── Exceptions ────────────────────────────────────────────────────────────────
from iios.execution.execution_exceptions import (
    EngineAlreadyRunningError,
    EngineNotInitializedError,
    EngineShutdownError,
    ExecutionError,
    ExecutionNotFoundError,
    ExecutionStateError,
    RegistryItemAlreadyExistsError,
    RegistryItemNotFoundError,
    RegistryOverflowError,
    SessionNotFoundError,
    WorkflowValidationError,
)

# ── Core models ───────────────────────────────────────────────────────────────
from iios.execution.core.execution_request    import ExecutionRequest
from iios.execution.core.execution_state      import ExecutionState, StatusTransition
from iios.execution.core.execution_plan       import ExecutionPlan
from iios.execution.core.execution_result     import ExecutionResult
from iios.execution.core.execution_session    import ExecutionSession
from iios.execution.core.execution_statistics import ExecutionStatistics
from iios.execution.core.execution_metadata   import ExecutionMetadata
from iios.execution.core.execution_history    import ExecutionHistory

# ── Events ────────────────────────────────────────────────────────────────────
from iios.execution.events.execution_event import ExecutionEvent
from iios.execution.events.event_bus       import ExecutionEventBus

# ── Monitoring ────────────────────────────────────────────────────────────────
from iios.execution.monitoring.execution_metrics import ExecutionMetrics
from iios.execution.monitoring.execution_monitor import ExecutionMonitor

# ── Sessions ──────────────────────────────────────────────────────────────────
from iios.execution.sessions.session_store   import SessionStore
from iios.execution.sessions.session_manager import SessionManager

# ── Workflow ──────────────────────────────────────────────────────────────────
from iios.execution.workflow.execution_workflow import StepResult, WorkflowContext, WorkflowStep
from iios.execution.workflow.workflow_validator import WorkflowValidator
from iios.execution.workflow.workflow_steps     import (
    DEFAULT_WORKFLOW_STEPS,
    ExecuteStep,
    FinalizeStep,
    GeneratePlanStep,
    QueueStep,
    RiskCheckStep,
    ValidateStep,
)
from iios.execution.workflow.workflow_engine import WorkflowEngine

# ── Higher-level ──────────────────────────────────────────────────────────────
from iios.execution.execution_context  import (
    ExecutionContextState,
    execution_session,
    execution_stage_scope,
    get_execution_context,
    reset_execution_context,
)
from iios.execution.execution_factory  import ExecutionFactory
from iios.execution.execution_registry import (
    ExecutionRegistry,
    get_execution_registry,
    reset_execution_registry,
)
from iios.execution.services.execution_service import ExecutionService
from iios.execution.execution_manager          import ExecutionManager
from iios.execution.execution_engine           import (
    ExecutionEngine,
    get_execution_engine,
    reset_execution_engine,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset all module-level singletons before every test."""
    reset_execution_engine()
    reset_execution_registry()
    reset_execution_context()
    yield
    reset_execution_engine()
    reset_execution_registry()
    reset_execution_context()


@pytest.fixture()
def paper_request() -> ExecutionRequest:
    return ExecutionRequest(
        ticker="RELIANCE",
        quantity=100.0,
        execution_type=ExecutionType.BUY,
        execution_mode=ExecutionMode.PAPER,
        target_price=2_500.0,
    )


@pytest.fixture()
def sell_request() -> ExecutionRequest:
    return ExecutionRequest(
        ticker="INFY",
        quantity=50.0,
        execution_type=ExecutionType.SELL,
        execution_mode=ExecutionMode.PAPER,
        target_price=1_800.0,
    )


@pytest.fixture()
def engine() -> ExecutionEngine:
    e = ExecutionEngine()
    e.initialize()
    yield e
    if e.is_initialized:
        e.shutdown(wait=False)


@pytest.fixture()
def manager() -> ExecutionManager:
    return ExecutionManager()


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Constants
# ═══════════════════════════════════════════════════════════════════════════════

class TestConstants:
    def test_version_string(self):
        assert EXECUTION_ENGINE_VERSION == "1.0.0"

    def test_system_id(self):
        assert EXECUTION_ENGINE_SYSTEM_ID == "iios:execution:engine"

    def test_execution_status_values(self):
        expected = {
            "created", "planned", "validated", "approved", "queued",
            "executing", "paused", "resumed", "completed", "cancelled",
            "failed", "archived",
        }
        assert {s.value for s in ExecutionStatus} == expected

    def test_execution_mode_values(self):
        assert ExecutionMode.PAPER.value == "paper"
        assert ExecutionMode.LIVE.value  == "live"

    def test_terminal_statuses(self):
        assert ExecutionStatus.COMPLETED in TERMINAL_STATUSES
        assert ExecutionStatus.FAILED    in TERMINAL_STATUSES
        assert ExecutionStatus.CANCELLED in TERMINAL_STATUSES
        assert ExecutionStatus.ARCHIVED  in TERMINAL_STATUSES
        assert ExecutionStatus.EXECUTING not in TERMINAL_STATUSES

    def test_active_statuses(self):
        assert ExecutionStatus.EXECUTING in ACTIVE_STATUSES
        assert ExecutionStatus.QUEUED    in ACTIVE_STATUSES
        assert ExecutionStatus.COMPLETED not in ACTIVE_STATUSES

    def test_valid_transitions_created(self):
        assert ExecutionStatus.PLANNED   in VALID_TRANSITIONS[ExecutionStatus.CREATED]
        assert ExecutionStatus.CANCELLED in VALID_TRANSITIONS[ExecutionStatus.CREATED]

    def test_archived_has_no_transitions(self):
        assert VALID_TRANSITIONS[ExecutionStatus.ARCHIVED] == []


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Exceptions
# ═══════════════════════════════════════════════════════════════════════════════

class TestExceptions:
    def test_base_exception_code(self):
        exc = ExecutionError("test", code="EX-001")
        assert exc.code == "EX-001"
        assert "EX-001" in str(exc)

    def test_not_found_stores_id(self):
        exc = ExecutionNotFoundError("not found", execution_id="abc-123")
        assert exc.execution_id == "abc-123"
        assert exc.code == "EX-011"

    def test_state_error_stores_statuses(self):
        exc = ExecutionStateError("bad transition", from_status="created", to_status="archived")
        assert exc.from_status == "created"
        assert exc.to_status   == "archived"
        assert exc.code == "EX-014"

    def test_registry_overflow_stores_capacity(self):
        exc = RegistryOverflowError("full", capacity=100, current=100)
        assert exc.capacity == 100
        assert exc.current  == 100
        assert exc.code == "EX-051"

    def test_session_not_found(self):
        exc = SessionNotFoundError("missing", session_id="s-1")
        assert exc.session_id == "s-1"
        assert exc.code == "EX-031"

    def test_engine_not_initialized_code(self):
        from iios.execution.execution_exceptions import EngineNotInitializedError
        assert EngineNotInitializedError().code == "EX-041"

    def test_workflow_validation_error_stores_errors(self):
        exc = WorkflowValidationError("invalid", errors=["e1", "e2"])
        assert "e1" in exc.errors

    def test_registry_item_not_found(self):
        exc = RegistryItemNotFoundError("missing", item_id="x1")
        assert exc.item_id == "x1"
        assert exc.code == "EX-052"


# ═══════════════════════════════════════════════════════════════════════════════
# 3. ExecutionRequest
# ═══════════════════════════════════════════════════════════════════════════════

class TestExecutionRequest:
    def test_default_fields(self):
        req = ExecutionRequest()
        assert req.request_id
        assert req.execution_mode == ExecutionMode.PAPER
        assert req.priority == ExecutionPriority.NORMAL
        assert req.quantity == 0.0

    def test_is_buy_property(self, paper_request):
        assert paper_request.is_buy
        assert not paper_request.is_sell

    def test_is_sell_property(self, sell_request):
        assert sell_request.is_sell
        assert not sell_request.is_buy

    def test_is_expired_false_when_no_expiry(self, paper_request):
        assert not paper_request.is_expired

    def test_is_expired_true_when_past(self):
        req = ExecutionRequest(expires_at=time.time() - 1)
        assert req.is_expired

    def test_estimated_value(self):
        req = ExecutionRequest(quantity=100.0, target_price=250.0)
        assert req.estimated_value == pytest.approx(25_000.0)

    def test_to_dict_roundtrip(self, paper_request):
        d = paper_request.to_dict()
        assert d["ticker"]         == "RELIANCE"
        assert d["quantity"]       == 100.0
        assert d["execution_type"] == ExecutionType.BUY.value
        assert d["execution_mode"] == ExecutionMode.PAPER.value

    def test_unique_request_ids(self):
        ids = {ExecutionRequest().request_id for _ in range(10)}
        assert len(ids) == 10


# ═══════════════════════════════════════════════════════════════════════════════
# 4. ExecutionState
# ═══════════════════════════════════════════════════════════════════════════════

class TestExecutionState:
    def test_initial_status(self):
        state = ExecutionState()
        assert state.current_status == ExecutionStatus.CREATED

    def test_valid_transition(self):
        state = ExecutionState()
        assert state.can_transition(ExecutionStatus.PLANNED)
        state.transition(ExecutionStatus.PLANNED)
        assert state.current_status == ExecutionStatus.PLANNED

    def test_invalid_transition_raises(self):
        state = ExecutionState()
        with pytest.raises(ExecutionStateError):
            state.transition(ExecutionStatus.COMPLETED)

    def test_previous_status_updated(self):
        state = ExecutionState()
        state.transition(ExecutionStatus.PLANNED)
        assert state.previous_status == ExecutionStatus.CREATED

    def test_transition_history(self):
        state = ExecutionState()
        state.transition(ExecutionStatus.PLANNED)
        assert len(state.transitions) == 1
        assert state.transitions[0].from_status == ExecutionStatus.CREATED

    def test_is_terminal_false_when_active(self):
        state = ExecutionState()
        assert not state.is_terminal

    def test_is_terminal_true_when_completed(self):
        state = ExecutionState()
        state.transition(ExecutionStatus.PLANNED)
        state.transition(ExecutionStatus.VALIDATED)
        state.transition(ExecutionStatus.APPROVED)
        state.transition(ExecutionStatus.QUEUED)
        state.transition(ExecutionStatus.EXECUTING)
        state.transition(ExecutionStatus.COMPLETED)
        assert state.is_terminal

    def test_to_dict(self):
        state = ExecutionState(execution_id="test-id")
        d = state.to_dict()
        assert d["execution_id"]   == "test-id"
        assert d["current_status"] == "created"


# ═══════════════════════════════════════════════════════════════════════════════
# 5. ExecutionPlan
# ═══════════════════════════════════════════════════════════════════════════════

class TestExecutionPlan:
    def test_defaults(self):
        plan = ExecutionPlan()
        assert plan.plan_id
        assert len(plan.steps) > 0
        assert plan.is_valid

    def test_validation_errors_marks_invalid(self):
        plan = ExecutionPlan(validation_errors=["bad ticker"])
        assert not plan.is_valid

    def test_estimated_total_cost(self):
        plan = ExecutionPlan(estimated_value=10_000.0, estimated_commission=50.0)
        assert plan.estimated_total_cost == pytest.approx(10_050.0)

    def test_to_dict(self):
        plan = ExecutionPlan(execution_id="eid-1", estimated_quantity=100.0)
        d = plan.to_dict()
        assert d["execution_id"]       == "eid-1"
        assert d["estimated_quantity"] == 100.0


# ═══════════════════════════════════════════════════════════════════════════════
# 6. ExecutionSession
# ═══════════════════════════════════════════════════════════════════════════════

class TestExecutionSession:
    def test_execution_id_set_on_state(self):
        req     = ExecutionRequest(ticker="TCS", quantity=10.0)
        session = ExecutionSession(request=req)
        assert session.state.execution_id == session.execution_id

    def test_status_delegates_to_state(self):
        session = ExecutionSession(request=ExecutionRequest())
        assert session.status == ExecutionStatus.CREATED

    def test_transition(self):
        session = ExecutionSession(request=ExecutionRequest())
        session.transition(ExecutionStatus.PLANNED)
        assert session.status == ExecutionStatus.PLANNED

    def test_is_active(self):
        session = ExecutionSession(request=ExecutionRequest())
        assert session.is_active

    def test_duration_ms(self):
        session = ExecutionSession(request=ExecutionRequest())
        time.sleep(0.01)
        assert session.duration_ms() > 0

    def test_completed_at_set_on_terminal_transition(self):
        session = ExecutionSession(request=ExecutionRequest())
        session.transition(ExecutionStatus.PLANNED)
        session.transition(ExecutionStatus.VALIDATED)
        session.transition(ExecutionStatus.APPROVED)
        session.transition(ExecutionStatus.QUEUED)
        session.transition(ExecutionStatus.EXECUTING)
        session.transition(ExecutionStatus.COMPLETED)
        assert session.completed_at is not None

    def test_to_dict_contains_request(self):
        req     = ExecutionRequest(ticker="HDFC")
        session = ExecutionSession(request=req)
        d       = session.to_dict()
        assert d["request"]["ticker"] == "HDFC"

    def test_add_event_id(self):
        session = ExecutionSession(request=ExecutionRequest())
        session.add_event_id("evt-1")
        assert "evt-1" in session.event_ids


# ═══════════════════════════════════════════════════════════════════════════════
# 7. ExecutionResult
# ═══════════════════════════════════════════════════════════════════════════════

class TestExecutionResult:
    def test_is_successful_when_completed(self):
        result = ExecutionResult(status=ExecutionStatus.COMPLETED)
        assert result.is_successful

    def test_not_successful_when_failed(self):
        result = ExecutionResult(status=ExecutionStatus.FAILED)
        assert not result.is_successful

    def test_fill_ratio(self):
        result = ExecutionResult(quantity_requested=100.0, quantity_executed=100.0)
        assert result.fill_ratio == pytest.approx(1.0)

    def test_partial_fill(self):
        result = ExecutionResult(quantity_requested=100.0, quantity_executed=60.0)
        assert result.is_partial
        assert result.fill_ratio == pytest.approx(0.6)

    def test_net_value(self):
        result = ExecutionResult(total_value=10_000.0, commission=50.0)
        assert result.net_value == pytest.approx(9_950.0)

    def test_to_dict_has_status(self):
        result = ExecutionResult(status=ExecutionStatus.COMPLETED)
        d      = result.to_dict()
        assert d["status"] == "completed"


# ═══════════════════════════════════════════════════════════════════════════════
# 8. ExecutionStatistics
# ═══════════════════════════════════════════════════════════════════════════════

class TestExecutionStatistics:
    def test_initial_zero(self):
        stats = ExecutionStatistics()
        assert stats.total_executions == 0
        assert stats.success_rate     == 0.0

    def test_record_completion(self):
        stats = ExecutionStatistics()
        stats.record_completion(success=True, duration_ms=100.0, fill_ratio=1.0, volume=100.0)
        assert stats.total_executions == 1
        assert stats.successful       == 1
        assert stats.success_rate     == pytest.approx(1.0)

    def test_success_and_failure_rate(self):
        stats = ExecutionStatistics()
        stats.record_completion(success=True,  duration_ms=100.0)
        stats.record_completion(success=False, duration_ms=50.0)
        assert stats.success_rate == pytest.approx(0.5)
        assert stats.failure_rate == pytest.approx(0.5)

    def test_to_dict(self):
        stats = ExecutionStatistics()
        d = stats.to_dict()
        assert "total_executions" in d
        assert "success_rate"     in d
        assert "uptime_sec"       in d


# ═══════════════════════════════════════════════════════════════════════════════
# 9. ExecutionMetadata
# ═══════════════════════════════════════════════════════════════════════════════

class TestExecutionMetadata:
    def test_defaults(self):
        meta = ExecutionMetadata(execution_id="e-1")
        assert meta.version == EXECUTION_ENGINE_VERSION
        assert meta.correlation_id  # generated UUID

    def test_add_remove_tag(self):
        meta = ExecutionMetadata(execution_id="e-1")
        meta.add_tag("urgent")
        assert "urgent" in meta.tags
        meta.remove_tag("urgent")
        assert "urgent" not in meta.tags

    def test_for_execution_factory(self):
        meta = ExecutionMetadata.for_execution(
            "e-2", source="Test", mode=ExecutionMode.SIMULATION
        )
        assert meta.environment == "simulation"
        assert meta.source      == "Test"

    def test_to_dict(self):
        meta = ExecutionMetadata(execution_id="e-3")
        d    = meta.to_dict()
        assert d["execution_id"] == "e-3"
        assert "tags"            in d


# ═══════════════════════════════════════════════════════════════════════════════
# 10. ExecutionHistory
# ═══════════════════════════════════════════════════════════════════════════════

class TestExecutionHistory:
    def _result(self, execution_id: str = "e-1") -> ExecutionResult:
        return ExecutionResult(execution_id=execution_id, status=ExecutionStatus.COMPLETED)

    def test_add_and_get_latest(self):
        h = ExecutionHistory()
        r = self._result()
        h.add("e-1", r)
        assert h.get_latest("e-1") is r

    def test_missing_returns_none(self):
        h = ExecutionHistory()
        assert h.get_latest("missing") is None

    def test_count(self):
        h = ExecutionHistory()
        for i in range(5):
            h.add(f"e-{i}", self._result(f"e-{i}"))
        assert h.count() == 5

    def test_get_recent(self):
        h = ExecutionHistory()
        for i in range(10):
            h.add(f"e-{i}", self._result(f"e-{i}"))
        recent = h.get_recent(3)
        assert len(recent) == 3

    def test_max_size_ring_buffer(self):
        h = ExecutionHistory(max_size=3)
        for i in range(5):
            h.add(f"e-{i}", self._result(f"e-{i}"))
        assert h.count() == 3  # ring buffer evicts oldest

    def test_clear(self):
        h = ExecutionHistory()
        h.add("e-1", self._result())
        h.clear()
        assert h.count() == 0


# ═══════════════════════════════════════════════════════════════════════════════
# 11. WorkflowValidator
# ═══════════════════════════════════════════════════════════════════════════════

class TestWorkflowValidator:
    def _valid_request(self) -> ExecutionRequest:
        return ExecutionRequest(
            ticker="TCS",
            quantity=10.0,
            execution_type=ExecutionType.BUY,
            execution_mode=ExecutionMode.PAPER,
        )

    def test_valid_request_passes(self):
        v = WorkflowValidator()
        ok, errors = v.validate(self._valid_request())
        assert ok
        assert errors == []

    def test_empty_ticker_fails(self):
        req = self._valid_request()
        req.ticker = ""
        ok, errors = WorkflowValidator().validate(req)
        assert not ok
        assert any("ticker" in e for e in errors)

    def test_zero_quantity_fails(self):
        req = self._valid_request()
        req.quantity = 0.0
        ok, errors = WorkflowValidator().validate(req)
        assert not ok

    def test_negative_price_fails(self):
        req = self._valid_request()
        req.target_price = -100.0
        ok, errors = WorkflowValidator().validate(req)
        assert not ok

    def test_live_mode_rejected(self):
        req = self._valid_request()
        req.execution_mode = ExecutionMode.LIVE
        ok, errors = WorkflowValidator().validate(req)
        assert not ok
        assert any("LIVE" in e for e in errors)

    def test_unknown_type_fails(self):
        req = self._valid_request()
        req.execution_type = ExecutionType.UNKNOWN
        ok, errors = WorkflowValidator().validate(req)
        assert not ok


# ═══════════════════════════════════════════════════════════════════════════════
# 12. Workflow Steps
# ═══════════════════════════════════════════════════════════════════════════════

def _make_ctx(ticker: str = "TCS", quantity: float = 10.0) -> WorkflowContext:
    req     = ExecutionRequest(
        ticker=ticker,
        quantity=quantity,
        execution_type=ExecutionType.BUY,
        execution_mode=ExecutionMode.PAPER,
        target_price=3_000.0,
    )
    session = ExecutionSession(request=req)
    return WorkflowContext(execution_id=session.execution_id, session=session)


class TestValidateStep:
    def test_valid_request_succeeds(self):
        ctx    = _make_ctx()
        result = ValidateStep().execute(ctx)
        assert result.success
        assert ctx.session.status == ExecutionStatus.PLANNED

    def test_invalid_request_fails(self):
        ctx = _make_ctx(ticker="")
        result = ValidateStep().execute(ctx)
        assert result.failed
        assert ctx.has_errors()


class TestRiskCheckStep:
    def test_passes_in_paper_mode(self):
        ctx = _make_ctx()
        ctx.session.transition(ExecutionStatus.PLANNED)
        result = RiskCheckStep().execute(ctx)
        assert result.success
        assert ctx.session.status == ExecutionStatus.VALIDATED

    def test_sets_risk_check_passed_on_plan(self):
        ctx = _make_ctx()
        ctx.session.transition(ExecutionStatus.PLANNED)
        ctx.session.plan = ExecutionPlan()
        RiskCheckStep().execute(ctx)
        assert ctx.session.plan.risk_check_passed


class TestGeneratePlanStep:
    def test_creates_plan(self):
        ctx = _make_ctx()
        ctx.session.transition(ExecutionStatus.PLANNED)
        ctx.session.transition(ExecutionStatus.VALIDATED)
        result = GeneratePlanStep().execute(ctx)
        assert result.success
        assert ctx.plan is not None
        assert ctx.plan.estimated_value == pytest.approx(30_000.0)

    def test_transitions_to_approved(self):
        ctx = _make_ctx()
        ctx.session.transition(ExecutionStatus.PLANNED)
        ctx.session.transition(ExecutionStatus.VALIDATED)
        GeneratePlanStep().execute(ctx)
        assert ctx.session.status == ExecutionStatus.APPROVED


class TestWorkflowStepsChain:
    def test_queue_step(self):
        ctx = _make_ctx()
        for s in [ExecutionStatus.PLANNED, ExecutionStatus.VALIDATED, ExecutionStatus.APPROVED]:
            ctx.session.transition(s)
        result = QueueStep().execute(ctx)
        assert result.success
        assert ctx.session.status == ExecutionStatus.QUEUED

    def test_execute_step(self):
        ctx = _make_ctx()
        ctx.session.transition(ExecutionStatus.PLANNED)
        ctx.session.transition(ExecutionStatus.VALIDATED)
        ctx.session.transition(ExecutionStatus.APPROVED)
        ctx.session.transition(ExecutionStatus.QUEUED)
        result = ExecuteStep().execute(ctx)
        assert result.success
        assert result.output["fill_price"] == pytest.approx(3_000.0)

    def test_finalize_step_builds_result(self):
        ctx = _make_ctx()
        for s in [ExecutionStatus.PLANNED, ExecutionStatus.VALIDATED,
                  ExecutionStatus.APPROVED, ExecutionStatus.QUEUED, ExecutionStatus.EXECUTING]:
            ctx.session.transition(s)
        execute_step_result = StepResult(
            step_name="execute",
            status=WorkflowStepStatus.COMPLETED,
            output={"fill_price": 3000.0, "qty_filled": 10.0,
                    "total_value": 30000.0, "commission": 0.0, "slippage": 0.0},
        )
        ctx.record(execute_step_result)
        result = FinalizeStep().execute(ctx)
        assert result.success
        assert ctx.result is not None
        assert ctx.session.status == ExecutionStatus.COMPLETED


# ═══════════════════════════════════════════════════════════════════════════════
# 13. WorkflowEngine
# ═══════════════════════════════════════════════════════════════════════════════

class TestWorkflowEngine:
    def _make_session(self, ticker: str = "TCS") -> ExecutionSession:
        req = ExecutionRequest(
            ticker=ticker,
            quantity=10.0,
            execution_type=ExecutionType.BUY,
            execution_mode=ExecutionMode.PAPER,
            target_price=3_000.0,
        )
        return ExecutionSession(request=req)

    def test_full_paper_workflow_succeeds(self):
        engine  = WorkflowEngine()
        session = self._make_session()
        result  = engine.run(session)
        assert result.is_successful
        assert result.quantity_executed == pytest.approx(10.0)
        assert result.avg_fill_price    == pytest.approx(3_000.0)

    def test_failed_validation_produces_failed_result(self):
        engine  = WorkflowEngine()
        session = ExecutionSession(request=ExecutionRequest(ticker="", quantity=0))
        result  = engine.run(session)
        assert result.status == ExecutionStatus.FAILED

    def test_cancel_flag_aborts_workflow(self):
        engine  = WorkflowEngine()
        session = self._make_session()
        engine.request_cancel(session.execution_id)  # flag before run
        result  = engine.run(session)
        assert result.status == ExecutionStatus.CANCELLED

    def test_result_stored_in_session(self):
        engine  = WorkflowEngine()
        session = self._make_session()
        engine.run(session)
        assert session.result is not None

    def test_event_bus_receives_events(self):
        received: list[ExecutionEvent] = []
        bus    = ExecutionEventBus()
        bus.subscribe_all(received.append)
        engine  = WorkflowEngine(event_bus=bus)
        session = self._make_session()
        engine.run(session)
        assert len(received) >= 2  # at least STARTED + COMPLETED/FAILED


# ═══════════════════════════════════════════════════════════════════════════════
# 14. ExecutionEvent & EventBus
# ═══════════════════════════════════════════════════════════════════════════════

class TestExecutionEvent:
    def test_defaults(self):
        evt = ExecutionEvent()
        assert evt.event_id
        assert evt.event_type == ExecutionEventType.CREATED

    def test_to_dict(self):
        evt = ExecutionEvent(execution_id="e-1", event_type=ExecutionEventType.QUEUED)
        d   = evt.to_dict()
        assert d["execution_id"] == "e-1"
        assert d["event_type"]   == "queued"


class TestEventBus:
    def test_subscribe_and_publish(self):
        received: list[ExecutionEvent] = []
        bus = ExecutionEventBus()
        bus.subscribe(ExecutionEventType.CREATED, received.append)
        evt = ExecutionEvent(execution_id="e-1", event_type=ExecutionEventType.CREATED)
        bus.publish(evt)
        assert len(received) == 1

    def test_unsubscribe(self):
        received: list[ExecutionEvent] = []
        bus = ExecutionEventBus()
        bus.subscribe(ExecutionEventType.CREATED, received.append)
        bus.unsubscribe(ExecutionEventType.CREATED, received.append)
        bus.publish(ExecutionEvent(event_type=ExecutionEventType.CREATED))
        assert len(received) == 0

    def test_get_events_by_execution_id(self):
        bus = ExecutionEventBus()
        bus.publish(ExecutionEvent(execution_id="e-1", event_type=ExecutionEventType.CREATED))
        bus.publish(ExecutionEvent(execution_id="e-2", event_type=ExecutionEventType.CREATED))
        assert len(bus.get_events("e-1")) == 1

    def test_bad_handler_doesnt_crash_bus(self):
        def bad_handler(_):
            raise RuntimeError("oops")
        bus = ExecutionEventBus()
        bus.subscribe(ExecutionEventType.CREATED, bad_handler)
        bus.publish(ExecutionEvent(event_type=ExecutionEventType.CREATED))  # should not raise

    def test_subscribe_all(self):
        received: list[ExecutionEvent] = []
        bus = ExecutionEventBus()
        bus.subscribe_all(received.append)
        bus.publish(ExecutionEvent(event_type=ExecutionEventType.COMPLETED))
        bus.publish(ExecutionEvent(event_type=ExecutionEventType.FAILED))
        assert len(received) == 2


# ═══════════════════════════════════════════════════════════════════════════════
# 15. ExecutionMonitor
# ═══════════════════════════════════════════════════════════════════════════════

class TestExecutionMonitor:
    def test_on_started(self):
        mon = ExecutionMonitor()
        mon.on_execution_started("e-1")
        assert mon.get_metrics("e-1") is not None

    def test_on_completed(self):
        mon    = ExecutionMonitor()
        result = ExecutionResult(
            execution_id="e-1",
            status=ExecutionStatus.COMPLETED,
            quantity_requested=100.0,
            quantity_executed=100.0,
        )
        mon.on_execution_started("e-1")
        mon.on_execution_completed("e-1", result)
        m = mon.get_metrics("e-1")
        assert m.is_complete
        assert m.fill_ratio == pytest.approx(1.0)

    def test_on_failed(self):
        mon = ExecutionMonitor()
        mon.on_execution_started("e-1")
        mon.on_execution_failed("e-1", "test error")
        m = mon.get_metrics("e-1")
        assert m.status == ExecutionStatus.FAILED

    def test_summary(self):
        mon = ExecutionMonitor()
        mon.on_execution_started("e-1")
        s = mon.summary()
        assert s["total"] == 1
        assert s["active"] == 1

    def test_step_recording(self):
        mon = ExecutionMonitor()
        mon.on_execution_started("e-1")
        mon.on_step_completed("e-1", step_name="validate", success=True)
        m = mon.get_metrics("e-1")
        assert m.steps_completed == 1


# ═══════════════════════════════════════════════════════════════════════════════
# 16. SessionStore & SessionManager
# ═══════════════════════════════════════════════════════════════════════════════

class TestSessionStore:
    def _session(self) -> ExecutionSession:
        return ExecutionSession(request=ExecutionRequest(ticker="TCS", quantity=1.0))

    def test_save_and_load(self):
        store   = SessionStore()
        session = self._session()
        store.save(session)
        loaded  = store.load(session.execution_id)
        assert loaded.execution_id == session.execution_id

    def test_load_missing_raises(self):
        store = SessionStore()
        with pytest.raises(SessionNotFoundError):
            store.load("nonexistent")

    def test_count(self):
        store = SessionStore()
        for _ in range(3):
            store.save(self._session())
        assert store.count() == 3

    def test_overflow_raises(self):
        store = SessionStore(max_size=2)
        store.save(self._session())
        store.save(self._session())
        with pytest.raises(RegistryOverflowError):
            store.save(self._session())


class TestSessionManager:
    def test_create_and_get(self):
        mgr     = SessionManager()
        req     = ExecutionRequest(ticker="INFY", quantity=5.0)
        session = mgr.create_session(req)
        loaded  = mgr.get_session(session.execution_id)
        assert loaded.execution_id == session.execution_id

    def test_list_active(self):
        mgr = SessionManager()
        mgr.create_session(ExecutionRequest(ticker="A", quantity=1.0))
        mgr.create_session(ExecutionRequest(ticker="B", quantity=1.0))
        assert len(mgr.list_active()) == 2

    def test_archive_session(self):
        mgr     = SessionManager()
        session = mgr.create_session(ExecutionRequest(ticker="C", quantity=1.0))
        eid     = session.execution_id
        # Must transition to a terminal status before ARCHIVED.
        session.transition(ExecutionStatus.PLANNED)
        session.transition(ExecutionStatus.VALIDATED)
        session.transition(ExecutionStatus.APPROVED)
        session.transition(ExecutionStatus.QUEUED)
        session.transition(ExecutionStatus.EXECUTING)
        session.transition(ExecutionStatus.COMPLETED)
        mgr.update_session(session)
        mgr.archive_session(eid)
        assert mgr.get_session(eid).status == ExecutionStatus.ARCHIVED


# ═══════════════════════════════════════════════════════════════════════════════
# 17. ExecutionRegistry
# ═══════════════════════════════════════════════════════════════════════════════

class TestExecutionRegistry:
    def _session(self) -> ExecutionSession:
        return ExecutionSession(request=ExecutionRequest(ticker="TCS", quantity=10.0))

    def test_register_and_get(self):
        reg     = ExecutionRegistry()
        session = self._session()
        reg.register(session)
        assert reg.get_session(session.execution_id).execution_id == session.execution_id

    def test_duplicate_registration_raises(self):
        reg     = ExecutionRegistry()
        session = self._session()
        reg.register(session)
        with pytest.raises(RegistryItemAlreadyExistsError):
            reg.register(session)

    def test_overflow_raises(self):
        reg = ExecutionRegistry(max_size=2)
        reg.register(self._session())
        reg.register(self._session())
        with pytest.raises(RegistryOverflowError):
            reg.register(self._session())

    def test_not_found_raises(self):
        reg = ExecutionRegistry()
        with pytest.raises(RegistryItemNotFoundError):
            reg.get_session("nonexistent")

    def test_store_and_get_result(self):
        reg    = ExecutionRegistry()
        result = ExecutionResult(execution_id="e-1", status=ExecutionStatus.COMPLETED)
        reg.store_result(result)
        assert reg.get_result("e-1") is result

    def test_list_active(self):
        reg = ExecutionRegistry()
        reg.register(self._session())
        assert len(reg.list_active()) == 1

    def test_count(self):
        reg = ExecutionRegistry()
        reg.register(self._session())
        reg.register(self._session())
        assert reg.count() == 2


# ═══════════════════════════════════════════════════════════════════════════════
# 18. ExecutionContext
# ═══════════════════════════════════════════════════════════════════════════════

class TestExecutionContext:
    def test_get_creates_default(self):
        ctx = get_execution_context()
        assert ctx.stage == "idle"
        assert ctx.request_id

    def test_reset_creates_fresh(self):
        ctx1 = get_execution_context()
        reset_execution_context()
        ctx2 = get_execution_context()
        assert ctx1.request_id != ctx2.request_id

    def test_execution_session_context_manager(self):
        with execution_session("req-1") as ctx:
            assert ctx.request_id == "req-1"

    def test_execution_stage_scope(self):
        with execution_stage_scope("validate") as ctx:
            assert ctx.current_stage == "validate"
            assert ctx.stage         == "validate"

    def test_stage_restored_after_scope(self):
        ctx = get_execution_context()
        with execution_stage_scope("step-1"):
            pass
        assert ctx.current_stage == ""


# ═══════════════════════════════════════════════════════════════════════════════
# 19. ExecutionFactory
# ═══════════════════════════════════════════════════════════════════════════════

class TestExecutionFactory:
    def test_create_buy_request(self):
        req = ExecutionFactory.create_buy_request("TCS", 10.0, target_price=3_000.0)
        assert req.execution_type == ExecutionType.BUY
        assert req.ticker         == "TCS"

    def test_create_sell_request(self):
        req = ExecutionFactory.create_sell_request("INFY", 5.0)
        assert req.execution_type == ExecutionType.SELL

    def test_create_session(self):
        req     = ExecutionRequest(ticker="HDFC", quantity=20.0)
        session = ExecutionFactory.create_session(req)
        assert session.state.execution_id == session.execution_id

    def test_create_plan(self):
        req  = ExecutionRequest(ticker="TCS", quantity=10.0, target_price=3_000.0)
        plan = ExecutionFactory.create_plan("eid-1", req)
        assert plan.estimated_value == pytest.approx(30_000.0)

    def test_create_statistics(self):
        stats = ExecutionFactory.create_statistics()
        assert stats.total_executions == 0


# ═══════════════════════════════════════════════════════════════════════════════
# 20. ExecutionService
# ═══════════════════════════════════════════════════════════════════════════════

class TestExecutionService:
    def _service(self) -> ExecutionService:
        mgr = SessionManager()
        wf  = WorkflowEngine()
        return ExecutionService(session_manager=mgr, workflow_engine=wf)

    def test_create_and_execute(self):
        svc = self._service()
        req = ExecutionRequest(ticker="TCS", quantity=10.0,
                               execution_type=ExecutionType.BUY,
                               execution_mode=ExecutionMode.PAPER,
                               target_price=3_000.0)
        session = svc.create(req)
        result  = svc.execute(session.execution_id)
        assert result.is_successful

    def test_cancel_before_execute(self):
        svc     = self._service()
        req     = ExecutionRequest(ticker="TCS", quantity=10.0,
                                   execution_type=ExecutionType.BUY)
        session = svc.create(req)
        ok      = svc.cancel(session.execution_id)
        assert ok
        assert svc.get(session.execution_id).status == ExecutionStatus.CANCELLED

    def test_pause_and_resume(self):
        svc     = self._service()
        req     = ExecutionRequest(ticker="TCS", quantity=10.0,
                                   execution_type=ExecutionType.BUY)
        session = svc.create(req)
        # Manually drive to EXECUTING so pause is valid.
        for s in [ExecutionStatus.PLANNED, ExecutionStatus.VALIDATED,
                  ExecutionStatus.APPROVED, ExecutionStatus.QUEUED,
                  ExecutionStatus.EXECUTING]:
            session.transition(s)
        svc._sessions.update_session(session)

        assert svc.pause(session.execution_id)
        assert svc.resume(session.execution_id)

    def test_get_not_found_raises(self):
        svc = self._service()
        with pytest.raises(ExecutionNotFoundError):
            svc.get("nonexistent")

    def test_replay(self):
        svc = self._service()
        req = ExecutionRequest(ticker="TCS", quantity=10.0,
                               execution_type=ExecutionType.BUY,
                               execution_mode=ExecutionMode.PAPER,
                               target_price=3_000.0)
        session = svc.create(req)
        svc.execute(session.execution_id)
        # Replay completed execution.
        result = svc.replay(session.execution_id)
        assert result.is_successful

    def test_list_active(self):
        svc = self._service()
        svc.create(ExecutionRequest(ticker="A", quantity=1.0))
        svc.create(ExecutionRequest(ticker="B", quantity=1.0))
        assert len(svc.list_active()) == 2


# ═══════════════════════════════════════════════════════════════════════════════
# 21. ExecutionManager
# ═══════════════════════════════════════════════════════════════════════════════

class TestExecutionManager:
    def _manager(self) -> ExecutionManager:
        return ExecutionManager()

    def _request(self, ticker: str = "TCS") -> ExecutionRequest:
        return ExecutionRequest(
            ticker=ticker,
            quantity=10.0,
            execution_type=ExecutionType.BUY,
            execution_mode=ExecutionMode.PAPER,
            target_price=3_000.0,
        )

    def test_submit_returns_successful_result(self):
        mgr    = self._manager()
        result = mgr.submit(self._request())
        assert result.is_successful

    def test_submit_updates_statistics(self):
        mgr = self._manager()
        mgr.submit(self._request())
        stats = mgr.statistics()
        assert stats.total_executions == 1
        assert stats.successful       == 1

    def test_get_session_after_submit(self):
        mgr    = self._manager()
        result = mgr.submit(self._request())
        session = mgr.get_session(result.execution_id)
        assert session.status == ExecutionStatus.COMPLETED

    def test_get_result_after_submit(self):
        mgr    = self._manager()
        result = mgr.submit(self._request())
        fetched = mgr.get_result(result.execution_id)
        assert fetched.result_id == result.result_id

    def test_cancel_unknown_id_returns_false(self):
        mgr = self._manager()
        assert mgr.cancel("nonexistent") is False

    def test_history_populated(self):
        mgr    = self._manager()
        result = mgr.submit(self._request())
        hist   = mgr.get_history(result.execution_id)
        assert len(hist) == 1

    def test_list_active_after_submit(self):
        mgr = self._manager()
        mgr.submit(self._request())
        # Completed sessions are not active.
        assert len(mgr.list_active()) == 0

    def test_to_dict(self):
        mgr = self._manager()
        mgr.submit(self._request())
        d = mgr.to_dict()
        assert "statistics" in d

    def test_submit_background(self):
        mgr    = self._manager()
        future = mgr.submit_background(self._request())
        result = future.result(timeout=10)
        assert result.is_successful

    def test_multiple_submissions(self):
        mgr = self._manager()
        for _ in range(5):
            mgr.submit(self._request())
        assert mgr.statistics().total_executions == 5


# ═══════════════════════════════════════════════════════════════════════════════
# 22. ExecutionEngine
# ═══════════════════════════════════════════════════════════════════════════════

class TestExecutionEngine:
    def _request(self) -> ExecutionRequest:
        return ExecutionRequest(
            ticker="RELIANCE",
            quantity=100.0,
            execution_type=ExecutionType.BUY,
            execution_mode=ExecutionMode.PAPER,
            target_price=2_500.0,
        )

    def test_not_initialized_guard(self):
        e = ExecutionEngine()
        with pytest.raises(EngineNotInitializedError):
            e.submit(self._request())

    def test_double_initialize_raises(self, engine):
        with pytest.raises(EngineAlreadyRunningError):
            engine.initialize()

    def test_submit_successful(self, engine):
        result = engine.submit(self._request())
        assert result.is_successful

    def test_health_when_initialized(self, engine):
        h = engine.health()
        assert h["healthy"]
        assert h["version"] == EXECUTION_ENGINE_VERSION

    def test_health_when_not_initialized(self):
        e = ExecutionEngine()
        h = e.health()
        assert not h["healthy"]

    def test_stats_after_submit(self, engine):
        engine.submit(self._request())
        stats = engine.stats()
        assert stats.total_executions == 1

    def test_shutdown_prevents_submit(self, engine):
        engine.shutdown()
        with pytest.raises(EngineShutdownError):
            engine.submit(self._request())

    def test_get_session_after_submit(self, engine):
        result  = engine.submit(self._request())
        session = engine.get_session(result.execution_id)
        assert session.status == ExecutionStatus.COMPLETED

    def test_get_result(self, engine):
        result  = engine.submit(self._request())
        fetched = engine.get_result(result.execution_id)
        assert fetched.result_id == result.result_id

    def test_cancel_completed_returns_false(self, engine):
        result = engine.submit(self._request())
        ok     = engine.cancel(result.execution_id)
        assert not ok  # already COMPLETED

    def test_to_dict(self, engine):
        d = engine.to_dict()
        assert d["version"]     == EXECUTION_ENGINE_VERSION
        assert d["initialized"] is True

    def test_replay(self, engine):
        result  = engine.submit(self._request())
        replay  = engine.replay(result.execution_id)
        assert replay.is_successful


# ═══════════════════════════════════════════════════════════════════════════════
# 23. Async
# ═══════════════════════════════════════════════════════════════════════════════

class TestAsync:
    def test_submit_async(self, engine):
        req = ExecutionRequest(
            ticker="WIPRO",
            quantity=50.0,
            execution_type=ExecutionType.BUY,
            execution_mode=ExecutionMode.PAPER,
            target_price=400.0,
        )

        async def run():
            return await engine.submit_async(req)

        result = asyncio.run(run())
        assert result.is_successful

    def test_submit_async_fill_ratio(self, engine):
        req = ExecutionRequest(
            ticker="WIPRO",
            quantity=50.0,
            execution_type=ExecutionType.BUY,
            execution_mode=ExecutionMode.PAPER,
            target_price=400.0,
        )

        async def run():
            return await engine.submit_async(req)

        result = asyncio.run(run())
        assert result.fill_ratio == pytest.approx(1.0)


# ═══════════════════════════════════════════════════════════════════════════════
# 24. Singleton behaviour
# ═══════════════════════════════════════════════════════════════════════════════

class TestSingletons:
    def test_get_engine_returns_same_instance(self):
        e1 = get_execution_engine()
        e2 = get_execution_engine()
        assert e1 is e2

    def test_reset_engine_gives_new_instance(self):
        e1 = get_execution_engine()
        reset_execution_engine()
        e2 = get_execution_engine()
        assert e1 is not e2

    def test_get_registry_returns_same(self):
        r1 = get_execution_registry()
        r2 = get_execution_registry()
        assert r1 is r2

    def test_reset_registry(self):
        r1 = get_execution_registry()
        reset_execution_registry()
        r2 = get_execution_registry()
        assert r1 is not r2


# ═══════════════════════════════════════════════════════════════════════════════
# 25. Concurrency
# ═══════════════════════════════════════════════════════════════════════════════

class TestConcurrency:
    def test_concurrent_submissions(self, engine):
        results: list[ExecutionResult] = []
        errors:  list[Exception]       = []

        def submit_one():
            try:
                req = ExecutionRequest(
                    ticker="TCS",
                    quantity=10.0,
                    execution_type=ExecutionType.BUY,
                    execution_mode=ExecutionMode.PAPER,
                    target_price=3_000.0,
                )
                results.append(engine.submit(req))
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=submit_one) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15)

        assert len(errors)  == 0
        assert len(results) == 20
        assert all(r.is_successful for r in results)

    def test_concurrent_registry_access(self):
        reg     = ExecutionRegistry()
        results = []
        errors  = []

        def register_one():
            try:
                session = ExecutionSession(
                    request=ExecutionRequest(ticker="TCS", quantity=1.0)
                )
                reg.register(session)
                results.append(session.execution_id)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=register_one) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert len(errors)  == 0
        assert reg.count()  == 50

    def test_background_submit_futures(self, engine):
        reqs = [
            ExecutionRequest(
                ticker=f"STOCK{i}",
                quantity=float(i + 1),
                execution_type=ExecutionType.BUY,
                execution_mode=ExecutionMode.PAPER,
                target_price=100.0,
            )
            for i in range(5)
        ]
        futures = [engine._manager.submit_background(r) for r in reqs]
        results = [f.result(timeout=10) for f in futures]
        assert all(r.is_successful for r in results)


# ═══════════════════════════════════════════════════════════════════════════════
# 26. Package imports
# ═══════════════════════════════════════════════════════════════════════════════

class TestPackageImports:
    def test_top_level_import(self):
        import iios.execution as ex
        assert hasattr(ex, "ExecutionEngine")
        assert hasattr(ex, "ExecutionRequest")
        assert hasattr(ex, "ExecutionResult")

    def test_models_subpackage(self):
        from iios.execution.models import ExecutionRequest, ExecutionResult
        assert ExecutionRequest is not None
        assert ExecutionResult  is not None

    def test_workflow_subpackage(self):
        from iios.execution.workflow import WorkflowEngine, WorkflowValidator
        assert WorkflowEngine   is not None
        assert WorkflowValidator is not None
