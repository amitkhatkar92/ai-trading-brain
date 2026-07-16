"""tests/unit/execution/positions/test_position_engine.py
==================================================
Test suite for C6 Phase 3 M2 — IIOS Position Engine.

Coverage targets (95%+):
  * Constants, enums, EngineState, OperationType, EngineEventType
  * Exceptions — hierarchy, error codes, fields
  * EngineStateRecord — duration, terminal, with_exit
  * EngineContext — make_engine_context, properties
  * ExecutionSnapshot — quantities, is_fully_closed
  * Request types — CreatePositionRequest, UpdatePositionRequest,
      ClosePositionRequest, SyncPositionRequest, ArchivePositionRequest,
      QueryPositionRequest
  * PositionResult — succeeded/failed, to_dict, factories
  * EngineStatistics — all counters, averages, rates
  * EngineHistory — append, filters, eviction, concurrency
  * PositionSummary and EngineSnapshot — factories, properties, to_dict
  * EngineStateRecord — immutability and derived fields
  * EngineEvents — all 7 factory functions
  * EngineValidator — validate_create, validate_update, validate_close,
      validate_sync, validate_archive, validate_query, raise_if_invalid
  * EngineFactory — create_from_request, bad inputs, make_created_event
  * EngineRegistry — lifecycle guard, CRUD, filtering, statistics passthrough
  * PositionManager — all 6 operations, not-found, validation failures,
      statistics increments, event emission, concurrency
  * PositionEngine — facade delegation, lifecycle guard, all 6 ops,
      position access helpers, snapshot/history/events/statistics

C6 Execution Intelligence — Phase 3, Module 2
"""
from __future__ import annotations

import threading
import time
import uuid
from decimal import Decimal
from typing import List

import pytest

from iios.execution.positions.lifecycle import (
    Position,
    PositionDirection,
    PositionProduct,
    PositionState,
)

from iios.execution.positions.engine import (
    # constants
    ENGINE_SYSTEM_ID,
    EngineEventType,
    EngineState,
    OperationType,
    VERSION,
    TERMINAL_ENGINE_STATES,
    # exceptions
    PositionEngineError,
    PositionEngineNotRunningError,
    PositionEngineValidationError,
    PositionCreationError,
    PositionOperationError,
    PositionUpdateError,
    PositionCloseError,
    PositionSyncError,
    PositionArchiveError,
    PositionQueryError,
    PositionEngineStateError,
    # value types
    EngineContext, make_engine_context,
    EngineEvent,
    make_engine_started_event, make_engine_stopped_event,
    make_position_created_event, make_position_updated_event,
    make_position_closed_event, make_position_synchronized_event,
    make_position_archived_event,
    EngineHistory,
    ExecutionSnapshot,
    CreatePositionRequest, UpdatePositionRequest, ClosePositionRequest,
    SyncPositionRequest, ArchivePositionRequest, QueryPositionRequest,
    PositionResult, make_success_result, make_failure_result,
    EngineSnapshot, PositionSummary, make_engine_snapshot,
    EngineStateRecord,
    EngineStatistics,
    ValidationResult, EngineValidator,
    # services
    EngineFactory, EngineRegistry, PositionManager, PositionEngine,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _create_req(
    instrument: str = "NIFTY50",
    quantity: Decimal = Decimal("100"),
    direction: PositionDirection = PositionDirection.LONG,
    **kwargs,
) -> CreatePositionRequest:
    return CreatePositionRequest(
        instrument=instrument,
        exchange="NSE",
        product=PositionProduct.FUTURES,
        direction=direction,
        quantity=quantity,
        portfolio_id=kwargs.get("portfolio_id", "port-1"),
        strategy_id=kwargs.get("strategy_id", "strat-1"),
        decision_id=kwargs.get("decision_id", "dec-1"),
        workflow_id=kwargs.get("workflow_id", "wf-1"),
        execution_id=kwargs.get("execution_id", "exec-1"),
        auto_open=kwargs.get("auto_open", True),
    )


def _started_engine(**kwargs) -> PositionEngine:
    e = PositionEngine(**kwargs)
    e.start()
    return e


def _create_and_open_position(engine: PositionEngine) -> Position:
    """Create a position and advance it to OPEN state."""
    req = _create_req(auto_open=True)
    result = engine.create_position(req)
    assert result.succeeded
    pos = result.position
    assert pos is not None
    pos.transition_to(PositionState.OPEN)
    return pos


# ══════════════════════════════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════════════════════════════

class TestConstants:
    def test_all_engine_states(self):
        states = [s.value for s in EngineState]
        for s in ("IDLE", "VALIDATING", "CREATING", "UPDATING",
                  "SYNCHRONIZING", "CLOSING", "COMPLETED", "FAILED"):
            assert s in states

    def test_all_operation_types(self):
        ops = [o.value for o in OperationType]
        for o in ("CREATE_POSITION", "UPDATE_POSITION", "CLOSE_POSITION",
                  "SYNC_POSITION", "ARCHIVE_POSITION", "QUERY_POSITION"):
            assert o in ops

    def test_all_event_types(self):
        evts = [e.value for e in EngineEventType]
        assert len(evts) == 7

    def test_terminal_engine_states(self):
        assert EngineState.COMPLETED in TERMINAL_ENGINE_STATES
        assert EngineState.FAILED    in TERMINAL_ENGINE_STATES
        assert EngineState.IDLE  not in TERMINAL_ENGINE_STATES

    def test_version_string(self):
        assert VERSION == "1.0.0"


# ══════════════════════════════════════════════════════════════════════════════
# Exceptions
# ══════════════════════════════════════════════════════════════════════════════

class TestExceptions:
    def test_all_inherit_engine_error(self):
        for exc_class in (
            PositionEngineNotRunningError, PositionOperationError,
            PositionCreationError, PositionUpdateError, PositionCloseError,
            PositionSyncError, PositionArchiveError, PositionQueryError,
            PositionEngineValidationError, PositionEngineStateError,
        ):
            assert issubclass(exc_class, PositionEngineError)

    def test_not_running_error_code(self):
        e = PositionEngineNotRunningError()
        assert "PE2-001" in str(e.code)

    def test_creation_error_code(self):
        e = PositionCreationError("bad request")
        assert "PE2-003" in str(e.code)

    def test_validation_error_has_errors_tuple(self):
        e = PositionEngineValidationError("fail", errors=("e1", "e2"))
        assert "e1" in e.errors

    def test_update_error_has_position_id(self):
        e = PositionUpdateError("pos-1")
        assert e.position_id == "pos-1"

    def test_close_error_has_position_id(self):
        e = PositionCloseError("pos-2", "already closed")
        assert e.position_id == "pos-2"

    def test_archive_error_code(self):
        e = PositionArchiveError("p", "not closed")
        assert "PE2-007" in str(e.code)

    def test_query_error_code(self):
        e = PositionQueryError("bad query")
        assert "PE2-008" in str(e.code)


# ══════════════════════════════════════════════════════════════════════════════
# EngineStateRecord
# ══════════════════════════════════════════════════════════════════════════════

class TestEngineStateRecord:
    def _rec(self, state: EngineState = EngineState.CREATING) -> EngineStateRecord:
        return EngineStateRecord(
            state=state,
            operation_id=str(uuid.uuid4()),
            operation_type=OperationType.CREATE_POSITION,
            entered_at=time.time(),
        )

    def test_is_current_no_exit(self):
        r = self._rec()
        assert r.is_current is True
        assert r.duration_ms is None

    def test_is_not_current_after_exit(self):
        t = time.time()
        r = EngineStateRecord(
            state=EngineState.CREATING, operation_id="x",
            operation_type=OperationType.CREATE_POSITION,
            entered_at=t, exited_at=t + 1.0,
        )
        assert r.is_current is False
        assert r.duration_ms == pytest.approx(1000.0, abs=1.0)

    def test_is_terminal_for_completed(self):
        r = EngineStateRecord(
            state=EngineState.COMPLETED, operation_id="x",
            operation_type=OperationType.CREATE_POSITION,
            entered_at=time.time(),
        )
        assert r.is_terminal is True

    def test_is_not_terminal_for_creating(self):
        assert self._rec(EngineState.CREATING).is_terminal is False

    def test_with_exit(self):
        t = time.time()
        r   = self._rec()
        r2  = r.with_exit(t + 3.0)
        assert r2.exited_at == pytest.approx(t + 3.0)
        assert r.is_current          # original unchanged

    def test_to_dict_keys(self):
        d = self._rec().to_dict()
        for k in ("state", "operation_id", "operation_type", "entered_at",
                  "exited_at", "duration_ms", "is_current", "is_terminal"):
            assert k in d


# ══════════════════════════════════════════════════════════════════════════════
# EngineContext
# ══════════════════════════════════════════════════════════════════════════════

class TestEngineContext:
    def test_make_context_creates_uuid(self):
        ctx = make_engine_context(OperationType.CREATE_POSITION, portfolio_id="p")
        assert uuid.UUID(ctx.context_id)
        assert ctx.portfolio_id == "p"

    def test_has_workflow_true(self):
        ctx = make_engine_context(OperationType.QUERY_POSITION, workflow_id="wf")
        assert ctx.has_workflow is True

    def test_has_workflow_false(self):
        ctx = make_engine_context(OperationType.QUERY_POSITION)
        assert ctx.has_workflow is False

    def test_has_execution_true(self):
        ctx = make_engine_context(OperationType.SYNC_POSITION, execution_id="ex-1")
        assert ctx.has_execution is True

    def test_age_ms_positive(self):
        ctx = make_engine_context(OperationType.CREATE_POSITION)
        time.sleep(0.01)
        assert ctx.age_ms > 0

    def test_to_dict_keys(self):
        d = make_engine_context(OperationType.CREATE_POSITION).to_dict()
        for k in ("context_id", "operation_type", "portfolio_id", "correlation_id"):
            assert k in d


# ══════════════════════════════════════════════════════════════════════════════
# ExecutionSnapshot
# ══════════════════════════════════════════════════════════════════════════════

class TestExecutionSnapshot:
    def _snap(self, oq=Decimal("80"), cq=Decimal("20")) -> ExecutionSnapshot:
        return ExecutionSnapshot(
            execution_id="ex-1",
            position_id="pos-1",
            instrument="NIFTY50",
            exchange="NSE",
            open_quantity=oq,
            closed_quantity=cq,
            avg_entry_price=Decimal("22500"),
            avg_exit_price=Decimal("22700"),
            realized_pnl=Decimal("400"),
            unrealized_pnl=Decimal("1600"),
        )

    def test_total_quantity(self):
        s = self._snap(Decimal("80"), Decimal("20"))
        assert s.total_quantity == Decimal("100")

    def test_is_fully_closed_false(self):
        s = self._snap(Decimal("80"), Decimal("20"))
        assert s.is_fully_closed is False

    def test_is_fully_closed_true(self):
        s = self._snap(Decimal("0"), Decimal("100"))
        assert s.is_fully_closed is True

    def test_to_dict_has_keys(self):
        d = self._snap().to_dict()
        for k in ("execution_id", "position_id", "open_quantity", "realized_pnl"):
            assert k in d


# ══════════════════════════════════════════════════════════════════════════════
# Request types
# ══════════════════════════════════════════════════════════════════════════════

class TestRequests:
    def test_create_request_operation_type(self):
        r = _create_req()
        assert r.operation_type == OperationType.CREATE_POSITION

    def test_create_request_has_uuid(self):
        r = _create_req()
        assert uuid.UUID(r.request_id)

    def test_update_request_has_field_updates_false(self):
        r = UpdatePositionRequest(position_id="p")
        assert r.has_field_updates is False

    def test_update_request_has_field_updates_true(self):
        r = UpdatePositionRequest(position_id="p", open_quantity=Decimal("50"))
        assert r.has_field_updates is True

    def test_update_request_operation_type(self):
        r = UpdatePositionRequest(position_id="p")
        assert r.operation_type == OperationType.UPDATE_POSITION

    def test_close_request_operation_type(self):
        r = ClosePositionRequest(position_id="p")
        assert r.operation_type == OperationType.CLOSE_POSITION

    def test_sync_request_operation_type(self):
        r = SyncPositionRequest(position_id="p")
        assert r.operation_type == OperationType.SYNC_POSITION

    def test_archive_request_operation_type(self):
        r = ArchivePositionRequest(position_id="p")
        assert r.operation_type == OperationType.ARCHIVE_POSITION

    def test_query_request_is_single_lookup(self):
        r = QueryPositionRequest(position_id="p")
        assert r.is_single_lookup is True

    def test_query_request_is_not_single_lookup(self):
        r = QueryPositionRequest()
        assert r.is_single_lookup is False

    def test_query_request_default_limit(self):
        r = QueryPositionRequest()
        assert r.limit > 0


# ══════════════════════════════════════════════════════════════════════════════
# PositionResult
# ══════════════════════════════════════════════════════════════════════════════

class TestPositionResult:
    def test_make_success_result(self):
        r = make_success_result("req-1", OperationType.CREATE_POSITION, "pos-1", 5.0)
        assert r.succeeded is True
        assert r.failed    is False
        assert r.error_code == ""
        assert r.result_count == 1

    def test_make_failure_result(self):
        r = make_failure_result("req-1", OperationType.UPDATE_POSITION, "PE2-009", "bad", 3.0)
        assert r.succeeded is False
        assert r.failed    is True
        assert r.error_code == "PE2-009"

    def test_has_position_true(self):
        pos = object()
        r = make_success_result("r", OperationType.CREATE_POSITION, "p", 1.0, position=pos)
        assert r.has_position is True

    def test_has_position_false(self):
        r = make_success_result("r", OperationType.CREATE_POSITION, "p", 1.0)
        assert r.has_position is False

    def test_to_dict_keys(self):
        r = make_success_result("r", OperationType.CREATE_POSITION, "p", 1.0)
        d = r.to_dict()
        for k in ("result_id", "request_id", "operation_type", "succeeded",
                  "position_id", "elapsed_ms", "error_code", "error_message"):
            assert k in d


# ══════════════════════════════════════════════════════════════════════════════
# EngineStatistics
# ══════════════════════════════════════════════════════════════════════════════

class TestEngineStatistics:
    def test_initial_all_zero(self):
        s = EngineStatistics()
        assert s.positions_created   == 0
        assert s.total_operations    == 0
        assert s.failed_operations   == 0

    def test_record_created(self):
        s = EngineStatistics()
        s.record_created(elapsed_ms=10.0)
        assert s.positions_created == 1
        assert s.total_operations  == 1

    def test_record_failed(self):
        s = EngineStatistics()
        s.record_failed()
        assert s.failed_operations == 1
        assert s.total_operations  == 1

    def test_average_update_time(self):
        s = EngineStatistics()
        s.record_created(elapsed_ms=10.0)
        s.record_updated(elapsed_ms=30.0)
        assert s.average_update_time_ms == pytest.approx(20.0)

    def test_success_rate_full(self):
        s = EngineStatistics()
        s.record_created(5.0)
        assert s.success_rate == 1.0

    def test_success_rate_with_failure(self):
        s = EngineStatistics()
        s.record_created(5.0)
        s.record_failed()
        assert s.success_rate == pytest.approx(0.5)

    def test_success_rate_no_ops(self):
        assert EngineStatistics().success_rate == 1.0

    def test_failure_count_property(self):
        s = EngineStatistics()
        s.record_failed()
        assert s.failure_count == 1

    def test_all_operation_types_counted(self):
        s = EngineStatistics()
        s.record_created(1.0)
        s.record_updated(1.0)
        s.record_closed(1.0)
        s.record_synchronized(1.0)
        s.record_archived(1.0)
        s.record_queried(1.0)
        assert s.positions_created      == 1
        assert s.positions_updated      == 1
        assert s.positions_closed       == 1
        assert s.positions_synchronized == 1
        assert s.positions_archived     == 1
        assert s.positions_queried      == 1
        assert s.total_operations       == 6

    def test_to_dict_keys(self):
        d = EngineStatistics().to_dict()
        for k in ("positions_created", "total_operations", "failed_operations",
                  "average_update_time_ms", "success_rate"):
            assert k in d


# ══════════════════════════════════════════════════════════════════════════════
# EngineHistory
# ══════════════════════════════════════════════════════════════════════════════

class TestEngineHistory:
    def _r(self, op: OperationType = OperationType.CREATE_POSITION,
           succeeded: bool = True, position_id: str = "p1") -> PositionResult:
        if succeeded:
            return make_success_result(str(uuid.uuid4()), op, position_id, 1.0)
        return make_failure_result(str(uuid.uuid4()), op, "E", "fail", 1.0, position_id=position_id)

    def test_empty_on_init(self):
        h = EngineHistory()
        assert len(h) == 0
        assert h.total == 0

    def test_append_and_all(self):
        h = EngineHistory()
        r = self._r()
        h.append(r)
        assert len(h) == 1
        assert h.all()[0] is r

    def test_latest(self):
        h = EngineHistory()
        r1 = self._r()
        r2 = self._r()
        h.append(r1)
        h.append(r2)
        assert h.latest(1)[0] is r2

    def test_by_operation(self):
        h = EngineHistory()
        h.append(self._r(OperationType.CREATE_POSITION))
        h.append(self._r(OperationType.UPDATE_POSITION))
        assert len(h.by_operation(OperationType.CREATE_POSITION)) == 1

    def test_by_position(self):
        h = EngineHistory()
        h.append(self._r(position_id="pos-A"))
        h.append(self._r(position_id="pos-B"))
        assert len(h.by_position("pos-A")) == 1

    def test_failed_filter(self):
        h = EngineHistory()
        h.append(self._r(succeeded=True))
        h.append(self._r(succeeded=False))
        assert len(h.failed()) == 1

    def test_successful_filter(self):
        h = EngineHistory()
        h.append(self._r(succeeded=True))
        h.append(self._r(succeeded=False))
        assert len(h.successful()) == 1

    def test_eviction_at_capacity(self):
        h = EngineHistory(max_size=2)
        h.append(self._r())
        h.append(self._r())
        h.append(self._r())
        assert len(h)    == 2
        assert h.evicted == 1
        assert h.total   == 3

    def test_iter(self):
        h = EngineHistory()
        r = self._r()
        h.append(r)
        assert list(h)[0] is r


# ══════════════════════════════════════════════════════════════════════════════
# PositionSummary and EngineSnapshot
# ══════════════════════════════════════════════════════════════════════════════

class TestSnapshotTypes:
    def _make_open_position(self) -> Position:
        from iios.execution.positions.lifecycle import PositionFactory
        f = PositionFactory()
        p = f.create_long("NIFTY50", "NSE", PositionProduct.FUTURES, Decimal("100"))
        p.transition_to(PositionState.OPENING)
        p.transition_to(PositionState.OPEN)
        return p

    def test_position_summary_from_position(self):
        pos = self._make_open_position()
        s   = PositionSummary.from_position(pos)
        assert s.position_id == pos.position_id
        assert s.state       == "OPEN"

    def test_position_summary_to_dict(self):
        pos = self._make_open_position()
        d   = PositionSummary.from_position(pos).to_dict()
        assert "position_id" in d and "state" in d

    def test_make_engine_snapshot_empty(self):
        snap = make_engine_snapshot([], EngineStatistics())
        assert snap.total_positions == 0
        assert snap.is_empty is True

    def test_make_engine_snapshot_with_positions(self):
        pos  = self._make_open_position()
        snap = make_engine_snapshot([pos], EngineStatistics())
        assert snap.total_positions == 1
        assert snap.active_count    == 1

    def test_snapshot_is_healthy_no_failures(self):
        snap = make_engine_snapshot([], EngineStatistics())
        assert snap.is_healthy is True

    def test_snapshot_is_not_healthy_with_failures(self):
        stats = EngineStatistics()
        stats.record_failed()
        snap = make_engine_snapshot([], stats)
        assert snap.is_healthy is False

    def test_snapshot_to_dict_keys(self):
        snap = make_engine_snapshot([], EngineStatistics())
        d = snap.to_dict()
        for k in ("snapshot_id", "total_positions", "active_count",
                  "statistics", "taken_at", "is_healthy"):
            assert k in d


# ══════════════════════════════════════════════════════════════════════════════
# EngineEvents
# ══════════════════════════════════════════════════════════════════════════════

class TestEngineEvents:
    def _check(self, event: EngineEvent, expected: EngineEventType):
        assert event.event_type == expected
        assert uuid.UUID(event.event_id)
        assert event.occurred_at > 0

    def test_make_position_created_event(self):
        e = make_position_created_event("p1", portfolio_id="port")
        self._check(e, EngineEventType.POSITION_CREATED)
        assert e.position_id == "p1"

    def test_make_position_updated_event(self):
        self._check(make_position_updated_event("p"), EngineEventType.POSITION_UPDATED)

    def test_make_position_closed_event(self):
        self._check(make_position_closed_event("p"), EngineEventType.POSITION_CLOSED)

    def test_make_position_synchronized_event(self):
        self._check(make_position_synchronized_event("p"), EngineEventType.POSITION_SYNCHRONIZED)

    def test_make_position_archived_event(self):
        self._check(make_position_archived_event("p"), EngineEventType.POSITION_ARCHIVED)

    def test_make_engine_started_event(self):
        self._check(make_engine_started_event(), EngineEventType.ENGINE_STARTED)

    def test_make_engine_stopped_event(self):
        self._check(make_engine_stopped_event(), EngineEventType.ENGINE_STOPPED)

    def test_all_seven_types_covered(self):
        assert len(list(EngineEventType)) == 7

    def test_to_dict_keys(self):
        e = make_position_created_event("p")
        d = e.to_dict()
        for k in ("event_id", "event_type", "position_id", "actor", "occurred_at"):
            assert k in d


# ══════════════════════════════════════════════════════════════════════════════
# EngineValidator
# ══════════════════════════════════════════════════════════════════════════════

class TestEngineValidator:
    def _open_pos(self) -> Position:
        from iios.execution.positions.lifecycle import PositionFactory
        f = PositionFactory()
        p = f.create_long("NIFTY50", "NSE", PositionProduct.FUTURES, Decimal("100"),
                          portfolio_id="port", strategy_id="strat")
        p.transition_to(PositionState.OPENING)
        p.transition_to(PositionState.OPEN)
        return p

    def _closed_pos(self) -> Position:
        pos = self._open_pos()
        pos.transition_to(PositionState.CLOSING)
        pos.transition_to(PositionState.CLOSED)
        return pos

    # validate_create
    def test_valid_create_request(self):
        v = EngineValidator()
        r = v.validate_create(_create_req())
        assert r.is_valid

    def test_create_missing_instrument(self):
        v = EngineValidator()
        req = _create_req()
        req.instrument = ""
        r = v.validate_create(req)
        assert not r.is_valid

    def test_create_missing_product(self):
        v = EngineValidator()
        req = _create_req()
        req.product = None
        r = v.validate_create(req)
        assert not r.is_valid

    def test_create_zero_quantity(self):
        v = EngineValidator()
        req = _create_req(quantity=Decimal("0"))
        r = v.validate_create(req)
        assert not r.is_valid

    def test_create_negative_quantity(self):
        v = EngineValidator()
        req = _create_req(quantity=Decimal("-1"))
        r = v.validate_create(req)
        assert not r.is_valid

    def test_create_warns_empty_portfolio(self):
        v = EngineValidator()
        req = _create_req(portfolio_id="")
        r = v.validate_create(req)
        assert r.is_valid
        assert r.warning_count > 0

    # validate_update
    def test_valid_update(self):
        v   = EngineValidator()
        pos = self._open_pos()
        req = UpdatePositionRequest(
            position_id=pos.position_id,
            open_quantity=Decimal("60"),
        )
        r = v.validate_update(pos, req)
        assert r.is_valid

    def test_update_rejects_closed_position(self):
        v   = EngineValidator()
        pos = self._closed_pos()
        req = UpdatePositionRequest(position_id=pos.position_id, open_quantity=Decimal("10"))
        r = v.validate_update(pos, req)
        assert not r.is_valid

    def test_update_rejects_invalid_transition(self):
        v   = EngineValidator()
        pos = self._open_pos()
        req = UpdatePositionRequest(position_id=pos.position_id, new_state=PositionState.ARCHIVED)
        r = v.validate_update(pos, req)
        assert not r.is_valid

    def test_update_warns_no_changes(self):
        v   = EngineValidator()
        pos = self._open_pos()
        req = UpdatePositionRequest(position_id=pos.position_id)
        r = v.validate_update(pos, req)
        assert r.is_valid
        assert r.warning_count > 0

    # validate_close
    def test_valid_close(self):
        v   = EngineValidator()
        pos = self._open_pos()
        r   = v.validate_close(pos, ClosePositionRequest(position_id=pos.position_id))
        assert r.is_valid

    def test_close_rejects_archived_position(self):
        v = EngineValidator()
        from iios.execution.positions.lifecycle import PositionFactory
        f = PositionFactory()
        p = f.create_long("X", "NSE", PositionProduct.EQUITY, Decimal("10"))
        for s in (PositionState.OPENING, PositionState.OPEN,
                  PositionState.CLOSING, PositionState.CLOSED, PositionState.ARCHIVED):
            p.transition_to(s)
        r = v.validate_close(p, ClosePositionRequest(position_id=p.position_id))
        assert not r.is_valid

    def test_close_warns_no_exit_price(self):
        v   = EngineValidator()
        pos = self._open_pos()
        r   = v.validate_close(pos, ClosePositionRequest(position_id=pos.position_id))
        assert r.warning_count > 0  # no exit price provided

    # validate_sync
    def test_valid_sync_no_data(self):
        v   = EngineValidator()
        pos = self._open_pos()
        r   = v.validate_sync(pos, SyncPositionRequest(position_id=pos.position_id))
        assert r.is_valid

    def test_sync_rejects_closed_position(self):
        v   = EngineValidator()
        pos = self._closed_pos()
        r   = v.validate_sync(pos, SyncPositionRequest(position_id=pos.position_id))
        assert not r.is_valid

    def test_sync_rejects_snapshot_id_mismatch(self):
        v    = EngineValidator()
        pos  = self._open_pos()
        snap = ExecutionSnapshot(
            execution_id="ex", position_id="WRONG",
            instrument="X", exchange="NSE",
            open_quantity=Decimal("50"), closed_quantity=Decimal("50"),
            avg_entry_price=Decimal("100"), avg_exit_price=Decimal("110"),
            realized_pnl=Decimal("500"), unrealized_pnl=Decimal("0"),
        )
        r = v.validate_sync(pos, SyncPositionRequest(
            position_id=pos.position_id, execution_snapshot=snap
        ))
        assert not r.is_valid

    # validate_archive
    def test_valid_archive(self):
        v   = EngineValidator()
        pos = self._closed_pos()
        r   = v.validate_archive(pos, ArchivePositionRequest(position_id=pos.position_id))
        assert r.is_valid

    def test_archive_rejects_open_position(self):
        v   = EngineValidator()
        pos = self._open_pos()
        r   = v.validate_archive(pos, ArchivePositionRequest(position_id=pos.position_id))
        assert not r.is_valid

    # validate_query
    def test_valid_query(self):
        v = EngineValidator()
        r = v.validate_query(QueryPositionRequest())
        assert r.is_valid

    def test_query_rejects_zero_limit(self):
        v = EngineValidator()
        r = v.validate_query(QueryPositionRequest(limit=0))
        assert not r.is_valid

    # raise_if_invalid
    def test_raise_if_invalid_raises(self):
        v = EngineValidator()
        res = ValidationResult(is_valid=False, errors=("bad",), warnings=())
        with pytest.raises(PositionEngineValidationError):
            v.raise_if_invalid(res)

    def test_raise_if_invalid_passes(self):
        v = EngineValidator()
        res = ValidationResult(is_valid=True, errors=(), warnings=())
        v.raise_if_invalid(res)  # must not raise


# ══════════════════════════════════════════════════════════════════════════════
# EngineFactory
# ══════════════════════════════════════════════════════════════════════════════

class TestEngineFactory:
    def test_create_from_request(self):
        f = EngineFactory()
        r = f.create_from_request(_create_req())
        assert isinstance(r, Position)
        assert r.state == PositionState.CREATED

    def test_create_raises_on_missing_product(self):
        f   = EngineFactory()
        req = _create_req()
        req.product = None
        with pytest.raises(PositionCreationError):
            f.create_from_request(req)

    def test_create_raises_on_missing_direction(self):
        f   = EngineFactory()
        req = _create_req()
        req.direction = None
        with pytest.raises(PositionCreationError):
            f.create_from_request(req)

    def test_create_raises_on_bad_quantity(self):
        f   = EngineFactory()
        req = _create_req(quantity=Decimal("-1"))
        with pytest.raises(PositionCreationError):
            f.create_from_request(req)

    def test_make_created_event(self):
        f   = EngineFactory()
        pos = f.create_from_request(_create_req())
        evt = f.make_created_event(pos)
        assert evt.event_type == EngineEventType.POSITION_CREATED
        assert evt.position_id == pos.position_id


# ══════════════════════════════════════════════════════════════════════════════
# EngineRegistry
# ══════════════════════════════════════════════════════════════════════════════

class TestEngineRegistry:
    def _reg(self) -> EngineRegistry:
        r = EngineRegistry()
        r.start()
        return r

    def _pos(self) -> Position:
        return EngineFactory().create_from_request(_create_req())

    def test_register_before_start_raises(self):
        reg = EngineRegistry()
        with pytest.raises(PositionEngineNotRunningError):
            reg.register(self._pos())

    def test_register_after_start(self):
        reg = self._reg()
        reg.register(self._pos())
        assert reg.count == 1

    def test_get_returns_position(self):
        reg = self._reg()
        p   = self._pos()
        reg.register(p)
        assert reg.get(p.position_id) is p

    def test_get_returns_none_for_unknown(self):
        reg = self._reg()
        assert reg.get("ghost") is None

    def test_require_raises_for_unknown(self):
        from iios.execution.positions.lifecycle import PositionNotFoundError
        reg = self._reg()
        with pytest.raises(PositionNotFoundError):
            reg.require("ghost")

    def test_contains(self):
        reg = self._reg()
        p   = self._pos()
        reg.register(p)
        assert reg.contains(p.position_id) is True

    def test_deregister(self):
        reg = self._reg()
        p   = self._pos()
        reg.register(p)
        reg.deregister(p.position_id)
        assert reg.get(p.position_id) is None

    def test_active_filter(self):
        reg = self._reg()
        p   = self._pos()
        reg.register(p)
        p.transition_to(PositionState.OPENING)
        assert p in reg.active()

    def test_all(self):
        reg = self._reg()
        p1  = self._pos()
        p2  = self._pos()
        reg.register(p1)
        reg.register(p2)
        assert len(reg.all()) == 2

    def test_is_empty(self):
        reg = self._reg()
        assert reg.is_empty is True
        reg.register(self._pos())
        assert reg.is_empty is False

    def test_lifecycle_statistics_returns_stats(self):
        reg = self._reg()
        s   = reg.lifecycle_statistics()
        assert s is not None

    def test_notify_transition_delegates(self):
        reg = self._reg()
        p   = self._pos()
        reg.register(p)
        reg.notify_transition(PositionState.OPENING)   # must not raise


# ══════════════════════════════════════════════════════════════════════════════
# PositionManager — operations
# ══════════════════════════════════════════════════════════════════════════════

class TestPositionManagerOperations:
    def _manager(self) -> PositionManager:
        m = PositionManager()
        m.start()
        return m

    # ── create_position ───────────────────────────────────────────────────────

    def test_create_position_success(self):
        m   = self._manager()
        r   = m.create_position(_create_req())
        assert r.succeeded
        assert r.operation_type == OperationType.CREATE_POSITION
        assert r.position is not None
        assert r.position.state == PositionState.OPENING

    def test_create_auto_open_false(self):
        m   = self._manager()
        req = _create_req(auto_open=False)
        r   = m.create_position(req)
        assert r.succeeded
        assert r.position.state == PositionState.CREATED

    def test_create_validation_failure(self):
        m   = self._manager()
        req = _create_req(quantity=Decimal("-1"))
        r   = m.create_position(req)
        assert r.failed
        assert r.error_code == "PE2-009"

    def test_create_missing_instrument_fails(self):
        m   = self._manager()
        req = _create_req()
        req.instrument = ""
        r   = m.create_position(req)
        assert r.failed

    def test_create_records_in_history(self):
        m = self._manager()
        m.create_position(_create_req())
        assert len(m.history()) >= 1

    def test_create_increments_statistics(self):
        m = self._manager()
        m.create_position(_create_req())
        s = m.statistics()
        assert s.positions_created == 1

    def test_create_emits_event(self):
        m = self._manager()
        m.create_position(_create_req())
        evts = [e for e in m.events() if e.event_type == EngineEventType.POSITION_CREATED]
        assert len(evts) == 1

    # ── update_position ───────────────────────────────────────────────────────

    def test_update_position_success(self):
        m   = self._manager()
        cr  = m.create_position(_create_req())
        pos = cr.position
        pos.transition_to(PositionState.OPEN)

        req = UpdatePositionRequest(
            position_id=pos.position_id,
            open_quantity=Decimal("80"),
            closed_quantity=Decimal("20"),
        )
        r   = m.update_position(req)
        assert r.succeeded
        assert pos.open_quantity   == Decimal("80")
        assert pos.closed_quantity == Decimal("20")

    def test_update_applies_state_transition(self):
        m   = self._manager()
        cr  = m.create_position(_create_req())
        pos = cr.position
        pos.transition_to(PositionState.OPEN)

        req = UpdatePositionRequest(
            position_id=pos.position_id,
            new_state=PositionState.PARTIALLY_CLOSED,
        )
        r = m.update_position(req)
        assert r.succeeded
        assert pos.state == PositionState.PARTIALLY_CLOSED

    def test_update_position_not_found(self):
        m   = self._manager()
        req = UpdatePositionRequest(position_id="ghost")
        r   = m.update_position(req)
        assert r.failed

    def test_update_position_validation_failure(self):
        m   = self._manager()
        cr  = m.create_position(_create_req())
        pos = cr.position
        pos.transition_to(PositionState.OPEN)
        # Try invalid transition
        req = UpdatePositionRequest(
            position_id=pos.position_id,
            new_state=PositionState.ARCHIVED,
        )
        r = m.update_position(req)
        assert r.failed

    def test_update_applies_prices_and_pnl(self):
        m   = self._manager()
        cr  = m.create_position(_create_req())
        pos = cr.position
        pos.transition_to(PositionState.OPEN)
        req = UpdatePositionRequest(
            position_id=pos.position_id,
            avg_entry_price=Decimal("22500"),
            realized_pnl=Decimal("1000"),
            unrealized_pnl=Decimal("500"),
        )
        r = m.update_position(req)
        assert r.succeeded
        assert pos.average_entry_price == Decimal("22500")
        assert pos.realized_pnl        == Decimal("1000")

    # ── close_position ────────────────────────────────────────────────────────

    def test_close_position_success(self):
        m   = self._manager()
        cr  = m.create_position(_create_req())
        pos = cr.position
        pos.transition_to(PositionState.OPEN)
        req = ClosePositionRequest(
            position_id=pos.position_id,
            avg_exit_price=Decimal("22700"),
            realized_pnl=Decimal("200"),
        )
        r = m.close_position(req)
        assert r.succeeded
        assert pos.state             == PositionState.CLOSED
        assert pos.average_exit_price == Decimal("22700")

    def test_close_not_found(self):
        m = self._manager()
        r = m.close_position(ClosePositionRequest(position_id="ghost"))
        assert r.failed

    def test_close_already_closed_fails_validation(self):
        m   = self._manager()
        cr  = m.create_position(_create_req())
        pos = cr.position
        pos.transition_to(PositionState.OPEN)
        req = ClosePositionRequest(position_id=pos.position_id)
        m.close_position(req)
        # Close again — should fail
        r = m.close_position(ClosePositionRequest(position_id=pos.position_id))
        assert r.failed

    def test_close_increments_statistics(self):
        m   = self._manager()
        cr  = m.create_position(_create_req())
        pos = cr.position
        pos.transition_to(PositionState.OPEN)
        m.close_position(ClosePositionRequest(position_id=pos.position_id))
        assert m.statistics().positions_closed == 1

    def test_close_emits_event(self):
        m   = self._manager()
        cr  = m.create_position(_create_req())
        pos = cr.position
        pos.transition_to(PositionState.OPEN)
        m.close_position(ClosePositionRequest(position_id=pos.position_id))
        evts = [e for e in m.events() if e.event_type == EngineEventType.POSITION_CLOSED]
        assert len(evts) == 1

    # ── sync_position ─────────────────────────────────────────────────────────

    def test_sync_with_snapshot(self):
        m   = self._manager()
        cr  = m.create_position(_create_req(quantity=Decimal("100")))
        pos = cr.position
        pos.transition_to(PositionState.OPEN)
        snap = ExecutionSnapshot(
            execution_id="ex-1",
            position_id=pos.position_id,
            instrument="NIFTY50", exchange="NSE",
            open_quantity=Decimal("80"),
            closed_quantity=Decimal("20"),
            avg_entry_price=Decimal("22500"),
            avg_exit_price=Decimal("0"),
            realized_pnl=Decimal("0"),
            unrealized_pnl=Decimal("200"),
        )
        req = SyncPositionRequest(position_id=pos.position_id, execution_snapshot=snap)
        r   = m.sync_position(req)
        assert r.succeeded
        assert pos.open_quantity        == Decimal("80")
        assert pos.average_entry_price  == Decimal("22500")

    def test_sync_field_overrides_win_over_snapshot(self):
        m   = self._manager()
        cr  = m.create_position(_create_req())
        pos = cr.position
        pos.transition_to(PositionState.OPEN)
        snap = ExecutionSnapshot(
            execution_id="ex", position_id=pos.position_id,
            instrument="X", exchange="NSE",
            open_quantity=Decimal("50"), closed_quantity=Decimal("50"),
            avg_entry_price=Decimal("100"), avg_exit_price=Decimal("0"),
            realized_pnl=Decimal("0"), unrealized_pnl=Decimal("0"),
        )
        # Override open_quantity with explicit value
        req = SyncPositionRequest(
            position_id=pos.position_id,
            execution_snapshot=snap,
            open_quantity=Decimal("90"),
        )
        r = m.sync_position(req)
        assert r.succeeded
        assert pos.open_quantity == Decimal("90")

    def test_sync_with_state_transition(self):
        m   = self._manager()
        cr  = m.create_position(_create_req())
        pos = cr.position
        pos.transition_to(PositionState.OPEN)
        req = SyncPositionRequest(
            position_id=pos.position_id,
            open_quantity=Decimal("60"),
            new_state=PositionState.PARTIALLY_CLOSED,
        )
        r = m.sync_position(req)
        assert r.succeeded
        assert pos.state == PositionState.PARTIALLY_CLOSED

    def test_sync_not_found(self):
        m = self._manager()
        r = m.sync_position(SyncPositionRequest(position_id="ghost"))
        assert r.failed

    def test_sync_emits_event(self):
        m   = self._manager()
        cr  = m.create_position(_create_req())
        pos = cr.position
        pos.transition_to(PositionState.OPEN)
        m.sync_position(SyncPositionRequest(position_id=pos.position_id, open_quantity=Decimal("90")))
        evts = [e for e in m.events() if e.event_type == EngineEventType.POSITION_SYNCHRONIZED]
        assert len(evts) == 1

    # ── archive_position ──────────────────────────────────────────────────────

    def test_archive_position_success(self):
        m   = self._manager()
        cr  = m.create_position(_create_req())
        pos = cr.position
        pos.transition_to(PositionState.OPEN)
        m.close_position(ClosePositionRequest(position_id=pos.position_id))
        r = m.archive_position(ArchivePositionRequest(position_id=pos.position_id))
        assert r.succeeded
        assert pos.state == PositionState.ARCHIVED

    def test_archive_not_closed_fails(self):
        m   = self._manager()
        cr  = m.create_position(_create_req())
        pos = cr.position
        pos.transition_to(PositionState.OPEN)
        # Position is OPEN, not CLOSED
        r = m.archive_position(ArchivePositionRequest(position_id=pos.position_id))
        assert r.failed

    def test_archive_not_found(self):
        m = self._manager()
        r = m.archive_position(ArchivePositionRequest(position_id="ghost"))
        assert r.failed

    def test_archive_emits_event(self):
        m   = self._manager()
        cr  = m.create_position(_create_req())
        pos = cr.position
        pos.transition_to(PositionState.OPEN)
        m.close_position(ClosePositionRequest(position_id=pos.position_id))
        m.archive_position(ArchivePositionRequest(position_id=pos.position_id))
        evts = [e for e in m.events() if e.event_type == EngineEventType.POSITION_ARCHIVED]
        assert len(evts) == 1

    # ── query_position ────────────────────────────────────────────────────────

    def test_query_single_found(self):
        m   = self._manager()
        cr  = m.create_position(_create_req())
        pos = cr.position
        req = QueryPositionRequest(position_id=pos.position_id)
        r   = m.query_position(req)
        assert r.succeeded
        assert r.result_count == 1
        assert r.data["count"] == 1

    def test_query_single_not_found(self):
        m   = self._manager()
        req = QueryPositionRequest(position_id="ghost")
        r   = m.query_position(req)
        assert r.succeeded
        assert r.result_count == 0

    def test_query_all(self):
        m = self._manager()
        m.create_position(_create_req())
        m.create_position(_create_req())
        r = m.query_position(QueryPositionRequest())
        assert r.result_count == 2

    def test_query_by_portfolio(self):
        m = self._manager()
        req1 = _create_req(portfolio_id="A")
        req2 = _create_req(portfolio_id="B")
        m.create_position(req1)
        m.create_position(req2)
        r = m.query_position(QueryPositionRequest(portfolio_id="A"))
        assert r.result_count == 1

    def test_query_by_state(self):
        m   = self._manager()
        cr  = m.create_position(_create_req())
        pos = cr.position
        pos.transition_to(PositionState.OPEN)
        r   = m.query_position(QueryPositionRequest(state=PositionState.OPEN))
        assert r.result_count == 1

    def test_query_invalid_limit_fails(self):
        m = self._manager()
        r = m.query_position(QueryPositionRequest(limit=0))
        assert r.failed

    # ── snapshot / statistics / history ──────────────────────────────────────

    def test_snapshot_returns_engine_snapshot(self):
        m   = self._manager()
        m.create_position(_create_req())
        s   = m.snapshot()
        assert isinstance(s, EngineSnapshot)
        assert s.total_positions == 1

    def test_statistics_returns_copy(self):
        m  = self._manager()
        s1 = m.statistics()
        s2 = m.statistics()
        assert s1 is not s2

    def test_history_is_engine_history(self):
        m = self._manager()
        assert isinstance(m.history(), EngineHistory)

    # ── not running guard ─────────────────────────────────────────────────────

    def test_operations_raise_when_not_started(self):
        m = PositionManager()
        with pytest.raises(PositionEngineNotRunningError):
            m.create_position(_create_req())


# ══════════════════════════════════════════════════════════════════════════════
# PositionEngine — facade
# ══════════════════════════════════════════════════════════════════════════════

class TestPositionEngine:
    def test_lifecycle_running_after_start(self):
        e = _started_engine()
        assert e.lifecycle_state().value == "running"
        e.stop()

    def test_operations_fail_before_start(self):
        e = PositionEngine()
        with pytest.raises(PositionEngineNotRunningError):
            e.create_position(_create_req())

    def test_create_position(self):
        e = _started_engine()
        r = e.create_position(_create_req())
        assert r.succeeded
        assert e.position_count == 1
        e.stop()

    def test_update_position(self):
        e   = _started_engine()
        cr  = e.create_position(_create_req())
        pos = cr.position
        pos.transition_to(PositionState.OPEN)
        req = UpdatePositionRequest(
            position_id=pos.position_id,
            avg_entry_price=Decimal("22500"),
        )
        r = e.update_position(req)
        assert r.succeeded
        assert pos.average_entry_price == Decimal("22500")
        e.stop()

    def test_close_position(self):
        e   = _started_engine()
        pos = _create_and_open_position(e)
        r   = e.close_position(ClosePositionRequest(
            position_id=pos.position_id,
            avg_exit_price=Decimal("22750"),
        ))
        assert r.succeeded
        assert pos.state == PositionState.CLOSED
        e.stop()

    def test_sync_position(self):
        e   = _started_engine()
        pos = _create_and_open_position(e)
        r   = e.sync_position(SyncPositionRequest(
            position_id=pos.position_id,
            open_quantity=Decimal("50"),
            closed_quantity=Decimal("50"),
        ))
        assert r.succeeded
        assert pos.open_quantity == Decimal("50")
        e.stop()

    def test_archive_position(self):
        e   = _started_engine()
        pos = _create_and_open_position(e)
        e.close_position(ClosePositionRequest(position_id=pos.position_id))
        r = e.archive_position(ArchivePositionRequest(position_id=pos.position_id))
        assert r.succeeded
        assert pos.state == PositionState.ARCHIVED
        e.stop()

    def test_query_position(self):
        e   = _started_engine()
        _create_and_open_position(e)
        r   = e.query_position(QueryPositionRequest())
        assert r.succeeded
        assert r.result_count == 1
        e.stop()

    def test_get_position(self):
        e   = _started_engine()
        pos = _create_and_open_position(e)
        assert e.get_position(pos.position_id) is pos
        assert e.get_position("ghost") is None
        e.stop()

    def test_require_position(self):
        from iios.execution.positions.lifecycle import PositionNotFoundError
        e = _started_engine()
        with pytest.raises(PositionNotFoundError):
            e.require_position("ghost")
        e.stop()

    def test_active_positions(self):
        e   = _started_engine()
        pos = _create_and_open_position(e)
        assert pos in e.active_positions()
        e.stop()

    def test_closed_positions(self):
        e   = _started_engine()
        pos = _create_and_open_position(e)
        e.close_position(ClosePositionRequest(position_id=pos.position_id))
        assert pos in e.closed_positions()
        e.stop()

    def test_archived_positions(self):
        e   = _started_engine()
        pos = _create_and_open_position(e)
        e.close_position(ClosePositionRequest(position_id=pos.position_id))
        e.archive_position(ArchivePositionRequest(position_id=pos.position_id))
        assert pos in e.archived_positions()
        e.stop()

    def test_all_positions(self):
        e = _started_engine()
        _create_and_open_position(e)
        _create_and_open_position(e)
        assert len(e.all_positions()) == 2
        e.stop()

    def test_positions_by_portfolio(self):
        e   = _started_engine()
        req = _create_req(portfolio_id="MY-PORT")
        e.create_position(req)
        result = e.positions_by_portfolio("MY-PORT")
        assert len(result) == 1
        e.stop()

    def test_positions_by_strategy(self):
        e   = _started_engine()
        req = _create_req(strategy_id="MY-STRAT")
        e.create_position(req)
        result = e.positions_by_strategy("MY-STRAT")
        assert len(result) == 1
        e.stop()

    def test_snapshot(self):
        e    = _started_engine()
        _create_and_open_position(e)
        snap = e.snapshot()
        assert isinstance(snap, EngineSnapshot)
        assert snap.total_positions == 1
        e.stop()

    def test_statistics(self):
        e = _started_engine()
        e.create_position(_create_req())
        s = e.statistics()
        assert isinstance(s, EngineStatistics)
        assert s.positions_created == 1
        e.stop()

    def test_history_contains_operation(self):
        e = _started_engine()
        e.create_position(_create_req())
        h = e.history()
        assert len(h) >= 1
        e.stop()

    def test_events_contains_started_and_created(self):
        e = _started_engine()
        e.create_position(_create_req())
        evts = e.events()
        types = {ev.event_type for ev in evts}
        assert EngineEventType.ENGINE_STARTED    in types
        assert EngineEventType.POSITION_CREATED  in types
        e.stop()

    def test_is_empty_true_on_start(self):
        e = _started_engine()
        assert e.is_empty is True
        e.stop()

    def test_is_empty_false_after_create(self):
        e = _started_engine()
        e.create_position(_create_req())
        assert e.is_empty is False
        e.stop()

    def test_engine_stopped_after_stop(self):
        e = _started_engine()
        e.stop()
        assert e.lifecycle_state().value != "running"


# ══════════════════════════════════════════════════════════════════════════════
# Concurrency
# ══════════════════════════════════════════════════════════════════════════════

class TestConcurrency:
    def test_concurrent_creates(self):
        """30 threads each create a position; all should succeed."""
        e      = _started_engine(max_positions=100)
        errors: List[Exception] = []

        def create_one():
            try:
                r = e.create_position(_create_req())
                if r.failed:
                    errors.append(AssertionError(r.error_message))
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=create_one) for _ in range(30)]
        for t in threads: t.start()
        for t in threads: t.join()

        assert errors == [], f"Errors: {errors}"
        assert e.position_count == 30
        e.stop()

    def test_concurrent_history_reads_and_writes(self):
        """50 threads write to history; no data corruption."""
        h      = EngineHistory(max_size=200)
        errors: List[Exception] = []

        def write(i: int):
            try:
                h.append(make_success_result(
                    str(uuid.uuid4()), OperationType.CREATE_POSITION, f"p-{i}", 1.0
                ))
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=write, args=(i,)) for i in range(50)]
        for t in threads: t.start()
        for t in threads: t.join()

        assert errors == []
        assert len(h)  == 50

    def test_concurrent_stats_increments(self):
        """50 threads each increment statistics; total should be 50."""
        s = EngineStatistics()

        def inc():
            s.record_created(1.0)

        threads = [threading.Thread(target=inc) for _ in range(50)]
        for t in threads: t.start()
        for t in threads: t.join()

        # Python GIL means basic int increments are typically safe,
        # but verify the final count is correct
        assert s.positions_created == 50


# ══════════════════════════════════════════════════════════════════════════════
# Regression guards
# ══════════════════════════════════════════════════════════════════════════════

class TestRegression:
    def test_failed_create_does_not_register_position(self):
        e   = _started_engine()
        req = _create_req(quantity=Decimal("-1"))
        e.create_position(req)
        assert e.position_count == 0
        e.stop()

    def test_failed_update_does_not_change_position(self):
        e   = _started_engine()
        pos = _create_and_open_position(e)
        original_state = pos.state
        r = e.update_position(UpdatePositionRequest(
            position_id=pos.position_id, new_state=PositionState.ARCHIVED,
        ))
        assert r.failed
        assert pos.state == original_state
        e.stop()

    def test_statistics_failure_count_incremented_on_bad_create(self):
        e = _started_engine()
        e.create_position(_create_req(quantity=Decimal("0")))
        assert e.statistics().failed_operations == 1
        e.stop()

    def test_close_from_partially_closed_works(self):
        """Position in PARTIALLY_CLOSED must be closeable."""
        e   = _started_engine()
        pos = _create_and_open_position(e)
        pos.transition_to(PositionState.PARTIALLY_CLOSED)
        r = e.close_position(ClosePositionRequest(position_id=pos.position_id))
        assert r.succeeded
        assert pos.state == PositionState.CLOSED
        e.stop()

    def test_full_lifecycle_end_to_end(self):
        """Create → Open → PartiallyClose → Close → Archive."""
        e   = _started_engine()
        cr  = e.create_position(_create_req(quantity=Decimal("100"), auto_open=True))
        pos = cr.position
        pos.transition_to(PositionState.OPEN)

        # Update with partial close
        e.update_position(UpdatePositionRequest(
            position_id=pos.position_id,
            open_quantity=Decimal("60"),
            closed_quantity=Decimal("40"),
            new_state=PositionState.PARTIALLY_CLOSED,
        ))

        # Sync execution data
        e.sync_position(SyncPositionRequest(
            position_id=pos.position_id,
            avg_entry_price=Decimal("22500"),
            avg_exit_price=Decimal("22700"),
        ))

        # Close
        e.close_position(ClosePositionRequest(
            position_id=pos.position_id,
            realized_pnl=Decimal("800"),
        ))
        assert pos.state == PositionState.CLOSED

        # Archive
        e.archive_position(ArchivePositionRequest(position_id=pos.position_id))
        assert pos.state == PositionState.ARCHIVED

        stats = e.statistics()
        assert stats.positions_created      == 1
        assert stats.positions_closed       == 1
        assert stats.positions_archived     == 1
        assert stats.positions_synchronized == 1
        assert stats.positions_updated      >= 1
        e.stop()

    def test_engine_events_contain_all_expected_types_after_full_lifecycle(self):
        e   = _started_engine()
        cr  = e.create_position(_create_req(auto_open=True))
        pos = cr.position
        pos.transition_to(PositionState.OPEN)
        e.sync_position(SyncPositionRequest(position_id=pos.position_id, open_quantity=Decimal("90")))
        e.update_position(UpdatePositionRequest(position_id=pos.position_id))
        e.close_position(ClosePositionRequest(position_id=pos.position_id))
        e.archive_position(ArchivePositionRequest(position_id=pos.position_id))

        types = {ev.event_type for ev in e.events()}
        for et in (
            EngineEventType.ENGINE_STARTED,
            EngineEventType.POSITION_CREATED,
            EngineEventType.POSITION_SYNCHRONIZED,
            EngineEventType.POSITION_UPDATED,
            EngineEventType.POSITION_CLOSED,
            EngineEventType.POSITION_ARCHIVED,
        ):
            assert et in types, f"Missing event: {et}"
        e.stop()

    def test_query_by_instrument(self):
        e = _started_engine()
        e.create_position(_create_req(instrument="NIFTY50"))
        e.create_position(_create_req(instrument="BANKNIFTY"))
        r = e.query_position(QueryPositionRequest(instrument="BANKNIFTY"))
        assert r.result_count == 1
        assert r.data["positions"][0]["instrument"] == "BANKNIFTY"
        e.stop()

    def test_position_count_decreases_after_deregister(self):
        """Deregister directly via registry."""
        e   = _started_engine()
        cr  = e.create_position(_create_req())
        pos = cr.position
        e._manager.registry.deregister(pos.position_id)
        assert e.position_count == 0
        e.stop()
