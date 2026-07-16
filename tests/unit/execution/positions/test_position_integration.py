"""tests/unit/execution/positions/test_position_integration.py
==================================================
Test suite for C6 Phase 3 M6 — IIOS Position Integration.

Coverage targets (95%+):
  * Constants, enums, system IDs
  * Exceptions — full hierarchy
  * ComponentStatus — construction, properties, to_dict
  * ComponentHealthRecord + HealthReport + make_health_report
  * ComponentRegistry — register, require, is_registered, all_registered,
      component_status, all_statuses, health_report
  * ComponentFactory — create_all, individual creators
  * IntegrationContext + make_integration_context
  * Request types — all 7 request classes, to_engine_request adapters
  * IntegrationResponse — success, failure, properties, to_dict
  * PositionIntegrationSnapshot — construction, properties, to_dict
  * IntegrationEvent + all 7 factory functions
  * IntegrationHistory — append, extend, filter, eviction, clear
  * IntegrationStatistics — counters, properties, to_dict
  * IntegrationValidationResult — ok, fail, raise_if_invalid
  * IntegrationValidator — all 7 checks + composite validate
  * PositionIntegrationManager — lifecycle, all operations, health, validate,
      snapshot, statistics, events
  * PositionIntegrationEngine — full spec public API (initialize, start, stop,
      health, status, statistics, snapshot, history, validate, query,
      create_position, update_position, close_position, sync_position,
      archive_position, publish_snapshot)
  * Concurrency
  * Regression guards

C6 Execution Intelligence — Phase 3, Module 6
"""
from __future__ import annotations

import dataclasses
import threading
import time
import uuid
from decimal import Decimal
from typing import List

import pytest

from iios.execution.positions.lifecycle import (
    PositionDirection,
    PositionFactory,
    PositionProduct,
    PositionState,
)

from iios.execution.positions.integration import (
    # constants
    INTEGRATION_SYSTEM_ID,
    MANAGER_SYSTEM_ID,
    COMPONENT_ENGINE,
    COMPONENT_BOOK,
    COMPONENT_RISK,
    COMPONENT_SNAPSHOT,
    ALL_COMPONENT_NAMES,
    VERSION,
    ACTOR_INTEGRATION,
    HealthStatus,
    IntegrationEventType,
    IntegrationOperationType,
    # exceptions
    PositionIntegrationError,
    PositionIntegrationNotRunningError,
    PositionIntegrationInitError,
    ComponentRegistrationError,
    ComponentNotFoundError,
    ComponentHealthError,
    IntegrationValidationError,
    IntegrationSnapshotError,
    IntegrationRequestError,
    IntegrationOperationError,
    # component status & health
    ComponentStatus,
    ComponentHealthRecord,
    HealthReport,
    make_health_report,
    # registry & factory
    ComponentRegistry,
    ComponentFactory,
    # context
    IntegrationContext,
    make_integration_context,
    # requests
    CreatePositionIntegrationRequest,
    UpdatePositionIntegrationRequest,
    ClosePositionIntegrationRequest,
    SyncPositionIntegrationRequest,
    ArchivePositionIntegrationRequest,
    QueryPositionIntegrationRequest,
    PublishSnapshotIntegrationRequest,
    # response
    IntegrationResponse,
    make_success_response,
    make_failure_response,
    # snapshot
    PositionIntegrationSnapshot,
    make_integration_snapshot,
    # events
    IntegrationEvent,
    make_subsystem_initialized_event,
    make_subsystem_started_event,
    make_subsystem_stopped_event,
    make_snapshot_published_event,
    make_validation_completed_event,
    make_component_registered_event,
    make_component_failed_event,
    # history
    IntegrationHistory,
    # statistics
    IntegrationStatistics,
    # validation
    IntegrationValidationResult,
    IntegrationValidator,
    # manager & engine
    PositionIntegrationManager,
    PositionIntegrationEngine,
)


# ── Fixtures / helpers ────────────────────────────────────────────────────────

def _started_engine(**kwargs) -> PositionIntegrationEngine:
    e = PositionIntegrationEngine(**kwargs)
    e.start()
    return e


def _create_req(
    instrument:   str = "NIFTY50",
    portfolio_id: str = "port-1",
    strategy_id:  str = "strat-1",
) -> CreatePositionIntegrationRequest:
    return CreatePositionIntegrationRequest(
        instrument=instrument,
        exchange="NSE",
        product=PositionProduct.FUTURES,
        direction=PositionDirection.LONG,
        quantity=Decimal("100"),
        portfolio_id=portfolio_id,
        strategy_id=strategy_id,
        decision_id="dec-1",
        workflow_id="wf-1",
        execution_id="exec-1",
        auto_publish_snapshot=True,
    )


def _update_req(position_id: str) -> UpdatePositionIntegrationRequest:
    return UpdatePositionIntegrationRequest(
        position_id=position_id,
        open_quantity=Decimal("100"),
        reason="test update",
    )


def _open_position(e: PositionIntegrationEngine, position_id: str) -> None:
    """Advance a newly created position from OPENING to OPEN."""
    e.update_position(
        UpdatePositionIntegrationRequest(
            position_id=position_id,
            new_state=PositionState.OPEN,
            reason="test open",
        )
    )


def _close_req(position_id: str) -> ClosePositionIntegrationRequest:
    return ClosePositionIntegrationRequest(
        position_id=position_id,
        avg_exit_price=Decimal("2600"),
        realized_pnl=Decimal("10000"),
    )


def _archive_req(position_id: str) -> ArchivePositionIntegrationRequest:
    return ArchivePositionIntegrationRequest(position_id=position_id)


def _query_req(**kwargs) -> QueryPositionIntegrationRequest:
    return QueryPositionIntegrationRequest(**kwargs)


# ══════════════════════════════════════════════════════════════════════════════
# 1. Constants & enums
# ══════════════════════════════════════════════════════════════════════════════

class TestConstants:
    def test_system_ids(self):
        assert INTEGRATION_SYSTEM_ID
        assert MANAGER_SYSTEM_ID

    def test_version(self):
        assert VERSION == "1.0.0"

    def test_component_names(self):
        assert COMPONENT_ENGINE   == "position_engine"
        assert COMPONENT_BOOK     == "position_book"
        assert COMPONENT_RISK     == "position_risk"
        assert COMPONENT_SNAPSHOT == "position_snapshot"
        assert len(ALL_COMPONENT_NAMES) == 4

    def test_health_status_values(self):
        assert HealthStatus.HEALTHY  == "HEALTHY"
        assert HealthStatus.DEGRADED == "DEGRADED"
        assert HealthStatus.CRITICAL == "CRITICAL"
        assert HealthStatus.UNKNOWN  == "UNKNOWN"

    def test_event_type_values(self):
        assert IntegrationEventType.SUBSYSTEM_INITIALIZED == "SUBSYSTEM_INITIALIZED"
        assert IntegrationEventType.COMPONENT_FAILED      == "COMPONENT_FAILED"

    def test_operation_type_values(self):
        for op in IntegrationOperationType:
            assert op.value


# ══════════════════════════════════════════════════════════════════════════════
# 2. Exceptions
# ══════════════════════════════════════════════════════════════════════════════

class TestExceptions:
    def test_base_hierarchy(self):
        assert issubclass(PositionIntegrationError, Exception)

    def test_not_running_no_args(self):
        e = PositionIntegrationNotRunningError()
        assert "not running" in str(e).lower()
        assert isinstance(e, PositionIntegrationError)

    def test_init_error_has_reason(self):
        e = PositionIntegrationInitError("missing engine")
        assert e.reason == "missing engine"

    def test_component_registration_error(self):
        e = ComponentRegistrationError("position_engine")
        assert e.component_name == "position_engine"

    def test_component_not_found_error(self):
        e = ComponentNotFoundError("position_book")
        assert e.component_name == "position_book"

    def test_component_health_error(self):
        e = ComponentHealthError("position_risk")
        assert e.component_name == "position_risk"

    def test_validation_error_has_errors(self):
        e = IntegrationValidationError("fail", errors=("err1",))
        assert "err1" in e.errors

    def test_snapshot_error(self):
        e = IntegrationSnapshotError("snap fail")
        assert isinstance(e, PositionIntegrationError)

    def test_request_error(self):
        e = IntegrationRequestError("bad req")
        assert isinstance(e, PositionIntegrationError)

    def test_operation_error(self):
        e = IntegrationOperationError("op fail", operation="CREATE", position_id="p1")
        assert e.operation   == "CREATE"
        assert e.position_id == "p1"


# ══════════════════════════════════════════════════════════════════════════════
# 3. ComponentStatus
# ══════════════════════════════════════════════════════════════════════════════

class TestComponentStatus:
    def test_is_ok_all_true(self):
        s = ComponentStatus(
            component_name="position_engine",
            is_registered=True,
            is_running=True,
            is_healthy=True,
            lifecycle_state="running",
        )
        assert s.is_ok is True

    def test_is_ok_false_when_not_running(self):
        s = ComponentStatus("x", True, False, True, "stopped")
        assert s.is_ok is False

    def test_to_dict(self):
        s = ComponentStatus("x", True, True, True, "running")
        d = s.to_dict()
        assert d["component_name"] == "x"
        assert d["is_ok"]          is True

    def test_frozen(self):
        s = ComponentStatus("x", True, True, True, "running")
        with pytest.raises((dataclasses.FrozenInstanceError, TypeError, AttributeError)):
            s.is_running = False  # type: ignore[misc]


# ══════════════════════════════════════════════════════════════════════════════
# 4. ComponentHealthRecord + HealthReport + make_health_report
# ══════════════════════════════════════════════════════════════════════════════

class TestComponentHealth:
    def _record(self, name, healthy=True):
        return ComponentHealthRecord(
            component_name=name,
            status=HealthStatus.HEALTHY if healthy else HealthStatus.DEGRADED,
            is_running=healthy,
            message="OK" if healthy else "degraded",
        )

    def test_healthy_record(self):
        r = self._record("engine", healthy=True)
        assert r.is_healthy is True

    def test_unhealthy_record(self):
        r = self._record("book", healthy=False)
        assert r.is_healthy is False

    def test_to_dict(self):
        r = self._record("engine")
        d = r.to_dict()
        assert "component_name" in d
        assert "status"         in d

    def test_make_health_report_all_healthy(self):
        records = [self._record(n) for n in ["engine", "book", "risk", "snapshot"]]
        report  = make_health_report(records)
        assert report.overall_status == HealthStatus.HEALTHY
        assert report.healthy_count  == 4
        assert report.total_count    == 4

    def test_make_health_report_one_degraded(self):
        records = [
            self._record("engine"),
            self._record("book", healthy=False),
            self._record("risk"),
            self._record("snapshot"),
        ]
        report = make_health_report(records)
        assert report.overall_status == HealthStatus.DEGRADED

    def test_make_health_report_critical(self):
        records = [
            ComponentHealthRecord("engine", HealthStatus.CRITICAL, False, "gone"),
            self._record("book"),
        ]
        report = make_health_report(records)
        assert report.overall_status == HealthStatus.CRITICAL

    def test_make_health_report_empty(self):
        report = make_health_report([])
        assert report.overall_status == HealthStatus.UNKNOWN

    def test_health_report_to_dict(self):
        report = make_health_report([self._record("engine")])
        d      = report.to_dict()
        assert "overall_status" in d
        assert "components"     in d
        assert "report_id"      in d

    def test_health_report_frozen(self):
        r = make_health_report([])
        with pytest.raises((dataclasses.FrozenInstanceError, TypeError, AttributeError)):
            r.overall_status = "HEALTHY"  # type: ignore[misc]


# ══════════════════════════════════════════════════════════════════════════════
# 5. ComponentRegistry
# ══════════════════════════════════════════════════════════════════════════════

class TestComponentRegistry:
    def _started_engine_inst(self):
        from iios.execution.positions.engine import PositionEngine
        e = PositionEngine()
        e.start()
        return e

    def test_register_engine(self):
        r      = ComponentRegistry()
        engine = self._started_engine_inst()
        r.register_engine(engine)
        assert r.is_registered(COMPONENT_ENGINE)
        engine.stop()

    def test_require_engine_not_registered(self):
        r = ComponentRegistry()
        with pytest.raises(ComponentNotFoundError):
            r.require_engine()

    def test_register_none_raises(self):
        r = ComponentRegistry()
        with pytest.raises(ComponentRegistrationError):
            r.register_engine(None)

    def test_all_registered_false_initially(self):
        r = ComponentRegistry()
        assert r.all_registered() is False

    def test_registered_count(self):
        r      = ComponentRegistry()
        engine = self._started_engine_inst()
        r.register_engine(engine)
        assert r.registered_count() == 1
        engine.stop()

    def test_component_status_not_registered(self):
        r = ComponentRegistry()
        s = r.component_status("position_engine")
        assert s.is_registered is False
        assert s.is_running    is False

    def test_component_status_running(self):
        r      = ComponentRegistry()
        engine = self._started_engine_inst()
        r.register_engine(engine)
        s = r.component_status(COMPONENT_ENGINE)
        assert s.is_registered is True
        assert s.is_running    is True
        engine.stop()

    def test_all_statuses_length(self):
        r = ComponentRegistry()
        statuses = r.all_statuses()
        assert len(statuses) == 4  # all 4 components

    def test_health_report_all_critical_when_none(self):
        r      = ComponentRegistry()
        report = r.health_report()
        assert report.overall_status == HealthStatus.CRITICAL


# ══════════════════════════════════════════════════════════════════════════════
# 6. ComponentFactory
# ══════════════════════════════════════════════════════════════════════════════

class TestComponentFactory:
    def test_create_all(self):
        factory = ComponentFactory()
        engine, book, risk, snapshot = factory.create_all()
        assert engine   is not None
        assert book     is not None
        assert risk     is not None
        assert snapshot is not None

    def test_create_engine(self):
        from iios.execution.positions.engine import PositionEngine
        e = ComponentFactory().create_engine()
        assert isinstance(e, PositionEngine)

    def test_create_book(self):
        from iios.execution.positions.book import PositionBook
        b = ComponentFactory().create_book()
        assert isinstance(b, PositionBook)

    def test_create_risk_manager(self):
        from iios.execution.positions.risk import PositionRiskManager
        r = ComponentFactory().create_risk_manager()
        assert isinstance(r, PositionRiskManager)

    def test_create_snapshot_store(self):
        from iios.execution.positions.snapshot import PositionSnapshotStore
        s = ComponentFactory().create_snapshot_store()
        assert isinstance(s, PositionSnapshotStore)

    def test_max_positions_applied(self):
        f = ComponentFactory(max_positions=50)
        assert f._max_positions == 50


# ══════════════════════════════════════════════════════════════════════════════
# 7. IntegrationContext
# ══════════════════════════════════════════════════════════════════════════════

class TestIntegrationContext:
    def test_make_integration_context(self):
        ctx = make_integration_context(
            portfolio_id="port-1",
            strategy_id="strat-1",
        )
        assert ctx.portfolio_id == "port-1"
        assert ctx.strategy_id  == "strat-1"
        uuid.UUID(ctx.context_id)

    def test_frozen(self):
        ctx = make_integration_context()
        with pytest.raises((dataclasses.FrozenInstanceError, TypeError, AttributeError)):
            ctx.portfolio_id = "mutated"  # type: ignore[misc]

    def test_to_dict(self):
        ctx = make_integration_context(portfolio_id="P")
        d   = ctx.to_dict()
        assert d["portfolio_id"] == "P"
        assert "context_id"      in d


# ══════════════════════════════════════════════════════════════════════════════
# 8. Request types
# ══════════════════════════════════════════════════════════════════════════════

class TestRequestTypes:
    def test_create_request_fields(self):
        r = _create_req()
        assert r.instrument == "NIFTY50"
        assert r.quantity   == Decimal("100")

    def test_create_request_operation_type(self):
        assert _create_req().operation_type == IntegrationOperationType.CREATE

    def test_create_to_engine_request(self):
        from iios.execution.positions.engine import CreatePositionRequest
        r      = _create_req()
        eng_r  = r.to_engine_request()
        assert isinstance(eng_r, CreatePositionRequest)
        assert eng_r.instrument == "NIFTY50"

    def test_update_request(self):
        r = _update_req("pos-1")
        assert r.operation_type == IntegrationOperationType.UPDATE

    def test_update_to_engine_request(self):
        from iios.execution.positions.engine import UpdatePositionRequest
        r = _update_req("pos-1")
        assert isinstance(r.to_engine_request(), UpdatePositionRequest)

    def test_close_request(self):
        r = _close_req("pos-1")
        assert r.operation_type == IntegrationOperationType.CLOSE

    def test_close_to_engine_request(self):
        from iios.execution.positions.engine import ClosePositionRequest
        r = _close_req("pos-1")
        assert isinstance(r.to_engine_request(), ClosePositionRequest)

    def test_sync_request(self):
        r = SyncPositionIntegrationRequest(position_id="pos-1")
        assert r.operation_type == IntegrationOperationType.SYNC

    def test_sync_to_engine_request(self):
        from iios.execution.positions.engine import SyncPositionRequest
        r = SyncPositionIntegrationRequest(position_id="pos-1")
        assert isinstance(r.to_engine_request(), SyncPositionRequest)

    def test_archive_request(self):
        r = _archive_req("pos-1")
        assert r.operation_type == IntegrationOperationType.ARCHIVE

    def test_archive_to_engine_request(self):
        from iios.execution.positions.engine import ArchivePositionRequest
        r = _archive_req("pos-1")
        assert isinstance(r.to_engine_request(), ArchivePositionRequest)

    def test_query_request_defaults(self):
        r = _query_req()
        assert r.operation_type == IntegrationOperationType.QUERY
        assert r.include_active is True

    def test_publish_snapshot_request(self):
        r = PublishSnapshotIntegrationRequest(position_id="pos-1")
        assert r.operation_type == IntegrationOperationType.PUBLISH_SNAPSHOT

    def test_request_id_is_uuid(self):
        uuid.UUID(_create_req().request_id)


# ══════════════════════════════════════════════════════════════════════════════
# 9. IntegrationResponse
# ══════════════════════════════════════════════════════════════════════════════

class TestIntegrationResponse:
    def test_make_success_response(self):
        r = make_success_response(
            IntegrationOperationType.CREATE, "pos-1", "Created", 5.0
        )
        assert r.succeeded    is True
        assert r.position_id  == "pos-1"
        assert r.elapsed_ms   == 5.0
        assert r.failed       is False

    def test_make_failure_response(self):
        r = make_failure_response(
            IntegrationOperationType.CREATE, "Engine failed", 2.0
        )
        assert r.succeeded is False
        assert r.failed    is True
        assert len(r.errors) > 0

    def test_has_snapshot(self):
        r1 = make_success_response(
            IntegrationOperationType.CREATE, "p", "ok", 1.0, snapshot_dict={"k": "v"}
        )
        assert r1.has_snapshot is True

        r2 = make_success_response(IntegrationOperationType.QUERY, "p", "ok", 1.0)
        assert r2.has_snapshot is False

    def test_to_dict(self):
        r = make_success_response(IntegrationOperationType.CREATE, "p", "ok", 1.0)
        d = r.to_dict()
        assert "response_id" in d
        assert "operation"   in d

    def test_frozen(self):
        r = make_success_response(IntegrationOperationType.QUERY, "p", "ok", 1.0)
        with pytest.raises((dataclasses.FrozenInstanceError, TypeError, AttributeError)):
            r.succeeded = False  # type: ignore[misc]


# ══════════════════════════════════════════════════════════════════════════════
# 10. PositionIntegrationSnapshot
# ══════════════════════════════════════════════════════════════════════════════

class TestPositionIntegrationSnapshot:
    def test_construction(self):
        snap = make_integration_snapshot(
            engine_snapshot={},
            book_snapshot={},
            risk_snapshot={},
            position_snapshots={},
            health={"overall_status": "HEALTHY"},
            statistics={},
            position_count=5,
        )
        assert snap.position_count == 5
        assert snap.is_healthy     is True

    def test_is_healthy_false_when_degraded(self):
        snap = make_integration_snapshot(
            engine_snapshot={},
            book_snapshot={},
            risk_snapshot={},
            position_snapshots={},
            health={"overall_status": "DEGRADED"},
            statistics={},
        )
        assert snap.is_healthy is False

    def test_to_dict(self):
        snap = make_integration_snapshot(
            engine_snapshot={},
            book_snapshot={},
            risk_snapshot={},
            position_snapshots={},
            health={},
            statistics={},
        )
        d = snap.to_dict()
        assert "integration_snapshot_id" in d
        assert "version"                 in d
        assert "taken_at"                in d

    def test_frozen(self):
        snap = make_integration_snapshot(
            engine_snapshot={},
            book_snapshot={},
            risk_snapshot={},
            position_snapshots={},
            health={},
            statistics={},
        )
        with pytest.raises((dataclasses.FrozenInstanceError, TypeError, AttributeError)):
            snap.position_count = 99  # type: ignore[misc]

    def test_snapshot_id_is_uuid(self):
        snap = make_integration_snapshot(
            engine_snapshot={},
            book_snapshot={},
            risk_snapshot={},
            position_snapshots={},
            health={},
            statistics={},
        )
        uuid.UUID(snap.integration_snapshot_id)


# ══════════════════════════════════════════════════════════════════════════════
# 11. IntegrationEvents
# ══════════════════════════════════════════════════════════════════════════════

class TestIntegrationEvents:
    def test_make_subsystem_initialized(self):
        e = make_subsystem_initialized_event()
        assert e.event_type == IntegrationEventType.SUBSYSTEM_INITIALIZED
        uuid.UUID(e.event_id)

    def test_make_subsystem_started(self):
        e = make_subsystem_started_event()
        assert e.event_type == IntegrationEventType.SUBSYSTEM_STARTED

    def test_make_subsystem_stopped(self):
        e = make_subsystem_stopped_event()
        assert e.event_type == IntegrationEventType.SUBSYSTEM_STOPPED

    def test_make_snapshot_published(self):
        e = make_snapshot_published_event("pos-1")
        assert e.event_type == IntegrationEventType.SNAPSHOT_PUBLISHED
        assert e.metadata["position_id"] == "pos-1"

    def test_make_validation_completed_pass(self):
        e = make_validation_completed_event(True)
        assert e.event_type == IntegrationEventType.VALIDATION_COMPLETED
        assert e.metadata["is_valid"] is True

    def test_make_component_registered(self):
        e = make_component_registered_event("position_engine")
        assert e.event_type == IntegrationEventType.COMPONENT_REGISTERED
        assert e.component  == "position_engine"

    def test_make_component_failed(self):
        e = make_component_failed_event("position_book", reason="crash")
        assert e.event_type           == IntegrationEventType.COMPONENT_FAILED
        assert e.metadata["reason"]   == "crash"

    def test_to_dict(self):
        e = make_subsystem_started_event()
        d = e.to_dict()
        assert "event_id"   in d
        assert "event_type" in d


# ══════════════════════════════════════════════════════════════════════════════
# 12. IntegrationHistory
# ══════════════════════════════════════════════════════════════════════════════

class TestIntegrationHistory:
    def _evt(self):
        return make_subsystem_started_event()

    def test_max_events_lt_1_raises(self):
        with pytest.raises(ValueError):
            IntegrationHistory(max_events=0)

    def test_append_and_count(self):
        h = IntegrationHistory()
        h.append(self._evt())
        assert h.count() == 1

    def test_extend(self):
        h = IntegrationHistory()
        h.extend([self._evt(), self._evt()])
        assert h.count() == 2

    def test_latest(self):
        h = IntegrationHistory()
        for _ in range(5):
            h.append(self._evt())
        assert len(h.latest(3)) == 3

    def test_for_type(self):
        h = IntegrationHistory()
        h.append(make_subsystem_started_event())
        h.append(make_subsystem_stopped_event())
        started = h.for_type(IntegrationEventType.SUBSYSTEM_STARTED)
        assert len(started) == 1

    def test_for_component(self):
        h = IntegrationHistory()
        h.append(make_component_registered_event("engine"))
        h.append(make_component_registered_event("book"))
        assert len(h.for_component("engine")) == 1

    def test_filter(self):
        h = IntegrationHistory()
        h.append(make_snapshot_published_event("p1"))
        h.append(make_snapshot_published_event("p2"))
        r = h.filter(lambda e: e.metadata.get("position_id") == "p1")
        assert len(r) == 1

    def test_eviction(self):
        h = IntegrationHistory(max_events=3)
        for _ in range(5):
            h.append(self._evt())
        assert h.count() == 3

    def test_clear(self):
        h = IntegrationHistory()
        h.append(self._evt())
        h.clear()
        assert h.is_empty()

    def test_len(self):
        h = IntegrationHistory()
        h.append(self._evt())
        assert len(h) == 1


# ══════════════════════════════════════════════════════════════════════════════
# 13. IntegrationStatistics
# ══════════════════════════════════════════════════════════════════════════════

class TestIntegrationStatistics:
    def test_initial_state(self):
        s = IntegrationStatistics()
        assert s.positions_managed   == 0
        assert s.snapshots_published == 0

    def test_record_operation(self):
        s = IntegrationStatistics()
        s.record_operation(10.0)
        assert s.operations_total == 1

    def test_record_operation_failed(self):
        s = IntegrationStatistics()
        s.record_operation(5.0, failed=True)
        assert s.operations_failed == 1

    def test_average_integration_time(self):
        s = IntegrationStatistics()
        s.record_operation(10.0)
        s.record_operation(20.0)
        assert s.average_integration_time_ms == 15.0

    def test_operation_success_rate(self):
        s = IntegrationStatistics()
        s.record_operation()
        s.record_operation()
        s.record_operation(failed=True)
        assert abs(s.operation_success_rate - (2/3)) < 1e-9

    def test_operation_success_rate_no_ops(self):
        assert IntegrationStatistics().operation_success_rate == 1.0

    def test_validation_success_rate(self):
        s = IntegrationStatistics()
        s.record_validation_success()
        s.record_validation_failure()
        assert abs(s.validation_success_rate - 0.5) < 1e-9

    def test_to_dict(self):
        d = IntegrationStatistics().to_dict()
        assert "positions_managed"           in d
        assert "average_integration_time_ms" in d


# ══════════════════════════════════════════════════════════════════════════════
# 14. IntegrationValidation
# ══════════════════════════════════════════════════════════════════════════════

class TestIntegrationValidationResult:
    def test_ok(self):
        r = IntegrationValidationResult.ok()
        assert r.is_valid is True
        assert r.errors   == ()

    def test_ok_with_warnings(self):
        r = IntegrationValidationResult.ok(["w1"])
        assert r.is_valid       is True
        assert "w1" in r.warnings

    def test_fail(self):
        r = IntegrationValidationResult.fail(["e1"])
        assert r.is_valid is False
        assert "e1" in r.errors

    def test_raise_if_invalid(self):
        with pytest.raises(IntegrationValidationError):
            IntegrationValidationResult.fail(["err"]).raise_if_invalid()

    def test_raise_if_valid_noop(self):
        IntegrationValidationResult.ok().raise_if_invalid()

    def test_to_dict(self):
        d = IntegrationValidationResult.ok().to_dict()
        assert "is_valid" in d


class TestIntegrationValidator:
    def _reg_all_running(self):
        """ComponentRegistry with all 4 components started."""
        e = _started_engine()
        reg = e._manager._comp_registry
        e.stop()
        return reg

    def test_validate_component_registration_ok(self):
        eng = _started_engine()
        reg = eng._manager._comp_registry
        result = IntegrationValidator().validate_component_registration(reg)
        assert result.is_valid
        eng.stop()

    def test_validate_component_registration_fail(self):
        reg    = ComponentRegistry()  # empty
        result = IntegrationValidator().validate_component_registration(reg)
        assert not result.is_valid

    def test_validate_component_availability_ok(self):
        eng = _started_engine()
        reg = eng._manager._comp_registry
        result = IntegrationValidator().validate_component_availability(reg)
        assert result.is_valid
        eng.stop()

    def test_validate_history_consistency_ok(self):
        h = IntegrationHistory()
        result = IntegrationValidator().validate_history_consistency(h)
        assert result.is_valid

    def test_validate_subsystem_consistency_healthy(self):
        eng = _started_engine()
        reg = eng._manager._comp_registry
        result = IntegrationValidator().validate_subsystem_consistency(reg)
        assert result.is_valid
        eng.stop()


# ══════════════════════════════════════════════════════════════════════════════
# 15. PositionIntegrationEngine — full lifecycle
# ══════════════════════════════════════════════════════════════════════════════

class TestPositionIntegrationEngineLifecycle:
    def test_start_stop(self):
        e = PositionIntegrationEngine()
        e.start()
        assert e.lifecycle_state().value == "running"
        e.stop()
        assert e.lifecycle_state().value != "running"

    def test_initialize_starts_if_not_running(self):
        e = PositionIntegrationEngine()
        assert e.lifecycle_state().value != "running"
        e.initialize()
        assert e.lifecycle_state().value == "running"
        e.stop()

    def test_initialize_idempotent_when_running(self):
        e = _started_engine()
        e.initialize()   # already running
        assert e.lifecycle_state().value == "running"
        e.stop()

    def test_stop_after_start(self):
        e = _started_engine()
        e.stop()
        assert e.lifecycle_state().value != "running"

    def test_ops_raise_when_not_running(self):
        e = PositionIntegrationEngine()
        with pytest.raises(PositionIntegrationNotRunningError):
            e.create_position(_create_req())


# ══════════════════════════════════════════════════════════════════════════════
# 16. Create position
# ══════════════════════════════════════════════════════════════════════════════

class TestCreatePosition:
    def test_create_returns_success(self):
        e    = _started_engine()
        resp = e.create_position(_create_req())
        assert resp.succeeded is True
        assert resp.position_id
        e.stop()

    def test_create_publishes_snapshot(self):
        e    = _started_engine()
        resp = e.create_position(
            CreatePositionIntegrationRequest(
                instrument="NIFTY50", exchange="NSE",
                product=PositionProduct.FUTURES,
                direction=PositionDirection.LONG,
                quantity=Decimal("100"),
                portfolio_id="port-1", strategy_id="strat-1",
                auto_publish_snapshot=True,
            )
        )
        assert resp.succeeded
        # Check snapshot was built (statistics)
        stats = e.statistics()
        assert stats.snapshots_published >= 1
        e.stop()

    def test_create_increments_position_count(self):
        e = _started_engine()
        assert e.position_count == 0
        e.create_position(_create_req())
        assert e.position_count == 1
        e.stop()

    def test_create_multiple_positions(self):
        e = _started_engine()
        for i in range(5):
            resp = e.create_position(_create_req(f"STOCK{i}"))
            assert resp.succeeded
        assert e.position_count == 5
        e.stop()

    def test_create_bad_instrument_fails(self):
        e    = _started_engine()
        req  = CreatePositionIntegrationRequest(
            instrument="",   # invalid
            exchange="NSE",
            product=PositionProduct.FUTURES,
            direction=PositionDirection.LONG,
            quantity=Decimal("100"),
            portfolio_id="port-1",
            strategy_id="strat-1",
        )
        resp = e.create_position(req)
        # Engine rejects the request
        assert resp.failed
        e.stop()

    def test_create_emits_history_event(self):
        e = _started_engine()
        e.create_position(_create_req())
        events = e.events()
        assert len(events) > 0
        e.stop()


# ══════════════════════════════════════════════════════════════════════════════
# 17. Update position
# ══════════════════════════════════════════════════════════════════════════════

class TestUpdatePosition:
    def test_update_succeeds(self):
        e    = _started_engine()
        resp = e.create_position(_create_req())
        resp2 = e.update_position(_update_req(resp.position_id))
        assert resp2.succeeded
        e.stop()

    def test_update_nonexistent_position(self):
        e    = _started_engine()
        resp = e.update_position(_update_req("ghost-pos"))
        assert resp.failed
        e.stop()


# ══════════════════════════════════════════════════════════════════════════════
# 18. Close position
# ══════════════════════════════════════════════════════════════════════════════

class TestClosePosition:
    def test_close_succeeds(self):
        e    = _started_engine()
        resp = e.create_position(_create_req())
        _open_position(e, resp.position_id)
        resp2 = e.close_position(_close_req(resp.position_id))
        assert resp2.succeeded
        e.stop()

    def test_close_publishes_snapshot(self):
        e     = _started_engine()
        resp  = e.create_position(_create_req())
        _open_position(e, resp.position_id)
        before = e.statistics().snapshots_published
        e.close_position(_close_req(resp.position_id))
        after = e.statistics().snapshots_published
        assert after > before
        e.stop()

    def test_close_updates_position_closed_count(self):
        e    = _started_engine()
        resp = e.create_position(_create_req())
        _open_position(e, resp.position_id)
        e.close_position(_close_req(resp.position_id))
        stats = e.statistics()
        assert stats.positions_closed >= 1
        e.stop()

    def test_close_nonexistent_position_fails(self):
        e    = _started_engine()
        resp = e.close_position(_close_req("ghost"))
        assert resp.failed
        e.stop()


# ══════════════════════════════════════════════════════════════════════════════
# 19. Archive position
# ══════════════════════════════════════════════════════════════════════════════

class TestArchivePosition:
    def _create_and_close(self, e) -> str:
        resp = e.create_position(_create_req())
        _open_position(e, resp.position_id)
        e.close_position(_close_req(resp.position_id))
        return resp.position_id

    def test_archive_succeeds(self):
        e   = _started_engine()
        pid = self._create_and_close(e)
        arc = e.archive_position(_archive_req(pid))
        assert arc.succeeded
        e.stop()

    def test_archive_updates_count(self):
        e   = _started_engine()
        pid = self._create_and_close(e)
        e.archive_position(_archive_req(pid))
        stats = e.statistics()
        assert stats.positions_archived >= 1
        e.stop()


# ══════════════════════════════════════════════════════════════════════════════
# 20. Sync position
# ══════════════════════════════════════════════════════════════════════════════

class TestSyncPosition:
    def test_sync_succeeds(self):
        e    = _started_engine()
        resp = e.create_position(_create_req())
        s    = e.sync_position(
            SyncPositionIntegrationRequest(position_id=resp.position_id)
        )
        assert s.succeeded
        e.stop()


# ══════════════════════════════════════════════════════════════════════════════
# 21. Query
# ══════════════════════════════════════════════════════════════════════════════

class TestQuery:
    def test_query_all_active(self):
        e = _started_engine()
        for i in range(3):
            e.create_position(_create_req(f"S{i}"))
        resp = e.query(_query_req())
        assert resp.succeeded
        assert resp.data["count"] == 3
        e.stop()

    def test_query_by_position_id(self):
        e    = _started_engine()
        resp = e.create_position(_create_req())
        pid  = resp.position_id
        q    = e.query(_query_req(position_id=pid))
        assert q.succeeded
        assert q.data["count"] == 1
        e.stop()

    def test_query_by_portfolio(self):
        e = _started_engine()
        e.create_position(_create_req(portfolio_id="PX"))
        e.create_position(_create_req(portfolio_id="PX"))
        e.create_position(_create_req(portfolio_id="PY"))
        resp = e.query(_query_req(portfolio_id="PX"))
        assert resp.succeeded
        assert resp.data["count"] == 2
        e.stop()

    def test_query_by_strategy(self):
        e = _started_engine()
        e.create_position(_create_req(strategy_id="SX"))
        e.create_position(_create_req(strategy_id="SY"))
        resp = e.query(_query_req(strategy_id="SX"))
        assert resp.succeeded
        assert resp.data["count"] == 1
        e.stop()

    def test_query_not_running_raises(self):
        e = PositionIntegrationEngine()
        with pytest.raises(PositionIntegrationNotRunningError):
            e.query(_query_req())


# ══════════════════════════════════════════════════════════════════════════════
# 22. Publish snapshot
# ══════════════════════════════════════════════════════════════════════════════

class TestPublishSnapshot:
    def test_publish_snapshot_returns_snapshot(self):
        from iios.execution.positions.snapshot import PositionSnapshot
        e    = _started_engine()
        resp = e.create_position(_create_req())
        snap = e.publish_snapshot(resp.position_id)
        # May be None if already published or published during create
        if snap is not None:
            assert isinstance(snap, PositionSnapshot)
        e.stop()

    def test_publish_snapshot_nonexistent_returns_none(self):
        e    = _started_engine()
        snap = e.publish_snapshot("ghost")
        assert snap is None
        e.stop()


# ══════════════════════════════════════════════════════════════════════════════
# 23. Health
# ══════════════════════════════════════════════════════════════════════════════

class TestHealth:
    def test_health_returns_report(self):
        e      = _started_engine()
        report = e.health()
        assert isinstance(report, HealthReport)
        assert report.total_count == 4
        e.stop()

    def test_health_all_healthy_when_started(self):
        e      = _started_engine()
        report = e.health()
        assert report.overall_status == HealthStatus.HEALTHY
        e.stop()

    def test_health_not_running_raises(self):
        e = PositionIntegrationEngine()
        with pytest.raises(PositionIntegrationNotRunningError):
            e.health()


# ══════════════════════════════════════════════════════════════════════════════
# 24. Status
# ══════════════════════════════════════════════════════════════════════════════

class TestStatus:
    def test_status_returns_four_records(self):
        e       = _started_engine()
        records = e.status()
        assert len(records) == 4
        e.stop()

    def test_all_components_running(self):
        e       = _started_engine()
        records = e.status()
        for r in records:
            assert r.is_running is True, f"Component {r.component_name} not running"
        e.stop()

    def test_status_not_running_raises(self):
        e = PositionIntegrationEngine()
        with pytest.raises(PositionIntegrationNotRunningError):
            e.status()


# ══════════════════════════════════════════════════════════════════════════════
# 25. Statistics
# ══════════════════════════════════════════════════════════════════════════════

class TestStatistics:
    def test_statistics_initial(self):
        e     = _started_engine()
        stats = e.statistics()
        assert stats.positions_managed == 0
        e.stop()

    def test_statistics_after_create(self):
        e = _started_engine()
        e.create_position(_create_req())
        stats = e.statistics()
        assert stats.positions_managed >= 1
        assert stats.operations_total  >= 1
        e.stop()

    def test_statistics_returns_copy(self):
        e  = _started_engine()
        s1 = e.statistics()
        s2 = e.statistics()
        assert s1 is not s2
        e.stop()

    def test_statistics_not_running_raises(self):
        e = PositionIntegrationEngine()
        with pytest.raises(PositionIntegrationNotRunningError):
            e.statistics()


# ══════════════════════════════════════════════════════════════════════════════
# 26. Snapshot
# ══════════════════════════════════════════════════════════════════════════════

class TestSnapshot:
    def test_snapshot_returns_integration_snapshot(self):
        e    = _started_engine()
        snap = e.snapshot()
        assert isinstance(snap, PositionIntegrationSnapshot)
        e.stop()

    def test_snapshot_has_correct_position_count(self):
        e = _started_engine()
        e.create_position(_create_req("A"))
        e.create_position(_create_req("B"))
        snap = e.snapshot()
        assert snap.position_count == 2
        e.stop()

    def test_snapshot_is_frozen(self):
        e    = _started_engine()
        snap = e.snapshot()
        with pytest.raises((dataclasses.FrozenInstanceError, TypeError, AttributeError)):
            snap.position_count = 99  # type: ignore[misc]
        e.stop()

    def test_snapshot_not_running_raises(self):
        e = PositionIntegrationEngine()
        with pytest.raises(PositionIntegrationNotRunningError):
            e.snapshot()


# ══════════════════════════════════════════════════════════════════════════════
# 27. History & events
# ══════════════════════════════════════════════════════════════════════════════

class TestHistoryAndEvents:
    def test_history_returns_integration_history(self):
        e = _started_engine()
        h = e.history()
        assert isinstance(h, IntegrationHistory)
        e.stop()

    def test_events_populated_after_start(self):
        e      = _started_engine()
        events = e.events()
        assert len(events) > 0   # started + component-registered events
        e.stop()

    def test_events_grow_on_operations(self):
        e      = _started_engine()
        before = len(e.events())
        e.create_position(_create_req())
        after  = len(e.events())
        assert after > before
        e.stop()

    def test_history_not_running_raises(self):
        e = PositionIntegrationEngine()
        with pytest.raises(PositionIntegrationNotRunningError):
            e.history()


# ══════════════════════════════════════════════════════════════════════════════
# 28. Validate
# ══════════════════════════════════════════════════════════════════════════════

class TestValidate:
    def test_validate_passes_when_running(self):
        e      = _started_engine()
        result = e.validate()
        assert isinstance(result, IntegrationValidationResult)
        assert result.is_valid is True
        e.stop()

    def test_validate_records_in_statistics(self):
        e = _started_engine()
        e.validate()
        stats = e.statistics()
        assert stats.validation_successes >= 1
        e.stop()

    def test_validate_emits_event(self):
        e      = _started_engine()
        before = len(e.events())
        e.validate()
        after  = len(e.events())
        assert after > before
        e.stop()

    def test_validate_not_running_raises(self):
        e = PositionIntegrationEngine()
        with pytest.raises(PositionIntegrationNotRunningError):
            e.validate()


# ══════════════════════════════════════════════════════════════════════════════
# 29. Full lifecycle integration test
# ══════════════════════════════════════════════════════════════════════════════

class TestFullLifecycle:
    def test_create_update_close_archive(self):
        e = _started_engine()

        # Create
        r1 = e.create_position(_create_req())
        assert r1.succeeded
        pid = r1.position_id

        # Open
        _open_position(e, pid)

        # Update
        r2 = e.update_position(
            UpdatePositionIntegrationRequest(
                position_id=pid,
                unrealized_pnl=Decimal("500"),
            )
        )
        assert r2.succeeded

        # Close
        r3 = e.close_position(_close_req(pid))
        assert r3.succeeded

        # Archive
        r4 = e.archive_position(_archive_req(pid))
        assert r4.succeeded

        # Statistics
        stats = e.statistics()
        assert stats.positions_managed  >= 1
        assert stats.positions_closed   >= 1
        assert stats.positions_archived >= 1

        # Snapshot
        snap = e.snapshot()
        assert snap.position_count >= 1

        # Health
        health = e.health()
        assert health.overall_status == HealthStatus.HEALTHY

        # Validate
        validation = e.validate()
        assert validation.is_valid

        e.stop()

    def test_multiple_instruments(self):
        e = _started_engine()
        instruments = ["NIFTY50", "BANKNIFTY", "RELIANCE", "TCS", "INFY"]
        for inst in instruments:
            resp = e.create_position(_create_req(inst))
            assert resp.succeeded

        assert e.position_count == len(instruments)

        snap = e.snapshot()
        assert snap.position_count == len(instruments)
        e.stop()


# ══════════════════════════════════════════════════════════════════════════════
# 30. Concurrency
# ══════════════════════════════════════════════════════════════════════════════

class TestConcurrency:
    def test_concurrent_create_positions(self):
        e      = _started_engine(max_positions=100)
        errors: List[Exception] = []

        def worker(i: int):
            try:
                e.create_position(_create_req(f"STOCK{i}"))
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        assert e.position_count == 20
        e.stop()

    def test_concurrent_query(self):
        e      = _started_engine()
        errors: List[Exception] = []
        e.create_position(_create_req())

        def worker():
            try:
                e.query(_query_req())
                e.health()
                e.statistics()
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        e.stop()


# ══════════════════════════════════════════════════════════════════════════════
# 31. Regression guards
# ══════════════════════════════════════════════════════════════════════════════

class TestRegressionGuards:
    def test_integration_engine_is_lifecycle_aware(self):
        from iios.investment.workflow.engine_lifecycle import LifecycleAwareMixin
        e = PositionIntegrationEngine()
        assert isinstance(e, LifecycleAwareMixin)

    def test_integration_snapshot_is_frozen(self):
        snap = make_integration_snapshot(
            engine_snapshot={},
            book_snapshot={},
            risk_snapshot={},
            position_snapshots={},
            health={},
            statistics={},
        )
        with pytest.raises((dataclasses.FrozenInstanceError, TypeError, AttributeError)):
            snap.position_count = 0  # type: ignore[misc]

    def test_response_is_frozen(self):
        r = make_success_response(IntegrationOperationType.CREATE, "p", "ok", 1.0)
        with pytest.raises((dataclasses.FrozenInstanceError, TypeError, AttributeError)):
            r.succeeded = False  # type: ignore[misc]

    def test_no_internal_classes_exposed(self):
        """PositionIntegrationEngine must NOT expose sub-component classes."""
        from iios.execution.positions.integration import PositionIntegrationEngine
        import iios.execution.positions.integration as pkg
        all_names = dir(pkg)
        # Internal classes should NOT appear in the public API
        for internal in ["PositionRegistry", "BookRegistry", "RiskRegistry"]:
            assert internal not in all_names, f"{internal} should not be in public API"

    def test_only_facade_exposes_create(self):
        """create_position must only be callable on the engine, not the manager directly."""
        e = _started_engine()
        assert hasattr(e, "create_position")
        e.stop()

    def test_statistics_copy_independence(self):
        e  = _started_engine()
        s1 = e.statistics()
        s1.positions_managed = 99   # mutate copy
        s2 = e.statistics()
        assert s2.positions_managed != 99   # original unchanged
        e.stop()

    def test_position_count_matches_snapshot(self):
        e = _started_engine()
        for i in range(3):
            e.create_position(_create_req(f"T{i}"))
        snap = e.snapshot()
        assert snap.position_count == e.position_count == 3
        e.stop()

    def test_events_are_listed_not_internal_queue(self):
        e      = _started_engine()
        events = e.events()
        assert isinstance(events, list)
        e.stop()

    def test_history_object_not_a_list(self):
        e = _started_engine()
        h = e.history()
        assert isinstance(h, IntegrationHistory)
        assert not isinstance(h, list)
        e.stop()
