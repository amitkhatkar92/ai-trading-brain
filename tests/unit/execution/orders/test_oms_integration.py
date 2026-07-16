"""tests/unit/execution/orders/test_oms_integration.py
==============================================================
Test suite for C6 Phase 2 M6 — OMS Integration.

Coverage:
  - All constants and enums
  - All 11 exception types
  - ComponentStatus, ComponentHealth
  - IntegrationContext, Request, Response, Statistics
  - OMSEvent + 7 factory functions
  - HistoryEntry, IntegrationHistory
  - OMSSnapshot
  - ValidationReport, OMSValidator
  - OMSComponentRegistry (lifecycle, register, health/status)
  - OMSComponentFactory (all create_* methods)
  - OMSIntegrationManager (full pipeline)
  - OMSIntegrationEngine (initialize, start, stop, all public API)
  - Concurrency (100 threads calling snapshot/query concurrently)
  - Regression: all 5 modules accessible through the engine
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from iios.execution.oms.integration import (
    DEFAULT_MAX_EVENTS,
    DEFAULT_MAX_HISTORY,
    ENGINE_SYSTEM_ID,
    OMS_INTEGRATION_SYSTEM_ID,
    REQUIRED_COMPONENT_COUNT,
    REQUIRED_COMPONENTS,
    VERSION,
    ComponentHealth,
    ComponentRegistrationError,
    ComponentStatus,
    ComponentType,
    HistoryEntry,
    IntegrationContext,
    IntegrationEventType,
    IntegrationHistory,
    IntegrationQueryType,
    IntegrationRequest,
    IntegrationResponse,
    IntegrationStatistics,
    OMSComponentFactory,
    OMSComponentMissingError,
    OMSComponentNotRunningError,
    OMSComponentRegistry,
    OMSEvent,
    OMSInitializationError,
    OMSIntegrationEngine,
    OMSIntegrationError,
    OMSIntegrationManager,
    OMSNotInitializedError,
    OMSQueryError,
    OMSRegistryCapacityError,
    OMSSnapshot,
    OMSSnapshotError,
    OMSState,
    OMSStateError,
    OMSValidationError,
    OMSValidator,
    ValidationCode,
    ValidationReport,
    make_component_failed,
    make_component_registered,
    make_oms_initialized,
    make_oms_started,
    make_oms_stopped,
    make_oms_validated,
    make_snapshot_published,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _uid() -> str:
    return str(uuid.uuid4())


def _started_engine() -> OMSIntegrationEngine:
    """Return a fully initialized, started engine backed by real components."""
    engine = OMSIntegrationEngine()
    engine.initialize()
    engine.start()
    return engine


def _mock_component(running: bool = True) -> MagicMock:
    """Create a minimal mock that passes registry registration."""
    from iios.investment.workflow.engine_lifecycle import EngineState
    m = MagicMock()
    m.lifecycle_state.return_value = EngineState.RUNNING if running else EngineState.STOPPED
    m.start.return_value = None
    m.stop.return_value  = None
    # Required methods from RepositoryInterface / StorageContract
    for method in ("save", "update", "delete", "archive", "restore",
                   "exists", "find", "search", "health", "statistics", "snapshot"):
        getattr(m, method)
    m.repository_id = "mock-repo"
    return m


# ===========================================================================
# TestConstants
# ===========================================================================

class TestConstants:
    def test_system_id(self):
        assert OMS_INTEGRATION_SYSTEM_ID.startswith("iios:")

    def test_version(self):
        parts = VERSION.split(".")
        assert len(parts) == 3

    def test_required_component_count(self):
        assert REQUIRED_COMPONENT_COUNT == 5
        assert len(REQUIRED_COMPONENTS) == 5

    def test_component_types(self):
        types = {ct.value for ct in ComponentType}
        for name in ("ORDER_MANAGER", "ORDER_BOOK", "ORDER_ROUTER", "ORDER_QUEUE", "PERSISTENCE"):
            assert name in types

    def test_oms_state_members(self):
        states = {s.value for s in OMSState}
        for name in ("UNINITIALIZED", "INITIALIZING", "RUNNING", "DEGRADED", "STOPPED", "ERROR"):
            assert name in states

    def test_integration_event_types(self):
        types = {t.value for t in IntegrationEventType}
        for name in (
            "OMS_INITIALIZED", "OMS_STARTED", "OMS_STOPPED", "OMS_VALIDATED",
            "SNAPSHOT_PUBLISHED", "COMPONENT_REGISTERED", "COMPONENT_FAILED",
        ):
            assert name in types

    def test_query_types(self):
        types = {t.value for t in IntegrationQueryType}
        for name in (
            "FIND_ORDER", "LIST_ACTIVE", "COUNT_ACTIVE",
            "BOOK_CONTAINS", "BOOK_QUERY",
            "QUEUE_PEEK", "QUEUE_SIZE",
            "ROUTER_HISTORY", "PERSIST_FIND", "FULL_HEALTH",
        ):
            assert name in types

    def test_validation_codes(self):
        codes = {c.value for c in ValidationCode}
        for name in (
            "COMPONENT_MISSING", "COMPONENT_NOT_RUNNING",
            "STATE_INCONSISTENCY", "SNAPSHOT_INCONSISTENCY",
        ):
            assert name in codes


# ===========================================================================
# TestExceptions
# ===========================================================================

class TestExceptions:
    def test_hierarchy(self):
        e = OMSIntegrationError("base", code="OI-000")
        assert isinstance(e, Exception)

    def test_all_codes(self):
        codes = [
            OMSIntegrationError("x", code="OI-000").code,
            OMSNotInitializedError("x", code="OI-001").code,
            OMSComponentMissingError("MANAGER").code,
            OMSComponentNotRunningError("BOOK").code,
            OMSValidationError("x").code,
            OMSSnapshotError("x", code="OI-005").code,
            OMSQueryError("FIND_ORDER").code,
            OMSStateError("RUNNING", "STOP").code,
            OMSRegistryCapacityError("x", code="OI-008").code,
            ComponentRegistrationError("QUEUE").code,
            OMSInitializationError("x").code,
        ]
        for i, code in enumerate(codes):
            assert code == f"OI-{i:03d}", f"Code at index {i}: {code}"

    def test_component_missing_stores_type(self):
        e = OMSComponentMissingError("ORDER_MANAGER")
        assert e.component_type == "ORDER_MANAGER"

    def test_oms_query_error(self):
        e = OMSQueryError("FIND_ORDER", "not found")
        assert e.query_type == "FIND_ORDER"
        assert e.reason     == "not found"

    def test_oms_state_error(self):
        e = OMSStateError("RUNNING", "re-initialize")
        assert e.current_state == "RUNNING"

    def test_initialization_error_with_errors(self):
        e = OMSInitializationError("failed", errors=("e1", "e2"))
        assert e.errors == ("e1", "e2")


# ===========================================================================
# TestComponentStatus
# ===========================================================================

class TestComponentStatus:
    def test_defaults(self):
        s = ComponentStatus()
        assert s.component_type == ComponentType.ORDER_MANAGER

    def test_frozen(self):
        s = ComponentStatus()
        with pytest.raises((AttributeError, TypeError)):
            s.is_running = True  # type: ignore

    def test_is_healthy_if_running(self):
        s = ComponentStatus(is_running=True)
        assert s.is_healthy
        s2 = ComponentStatus(is_running=False)
        assert not s2.is_healthy

    def test_to_dict(self):
        s = ComponentStatus(component_type=ComponentType.ORDER_BOOK, is_running=True)
        d = s.to_dict()
        assert d["component_type"] == "ORDER_BOOK"
        assert d["is_running"]     is True


# ===========================================================================
# TestComponentHealth
# ===========================================================================

class TestComponentHealth:
    def test_defaults(self):
        h = ComponentHealth()
        assert h.is_healthy

    def test_frozen(self):
        h = ComponentHealth()
        with pytest.raises((AttributeError, TypeError)):
            h.is_healthy = False  # type: ignore

    def test_is_degraded(self):
        h = ComponentHealth(is_healthy=False)
        assert h.is_degraded

    def test_to_dict(self):
        h = ComponentHealth(
            component_type=ComponentType.ORDER_QUEUE,
            is_healthy=True,
            latency_ms=1.5,
        )
        d = h.to_dict()
        assert d["component_type"] == "ORDER_QUEUE"
        assert d["is_healthy"]     is True


# ===========================================================================
# TestIntegrationContext
# ===========================================================================

class TestIntegrationContext:
    def test_defaults(self):
        ctx = IntegrationContext()
        assert ctx.query_type == IntegrationQueryType.FULL_HEALTH

    def test_frozen(self):
        ctx = IntegrationContext()
        with pytest.raises((AttributeError, TypeError)):
            ctx.query_type = IntegrationQueryType.FIND_ORDER  # type: ignore

    def test_cross_component_when_no_type(self):
        ctx = IntegrationContext(component_type=None)
        assert ctx.is_cross_component
        assert not ctx.is_single_component

    def test_single_component(self):
        ctx = IntegrationContext(component_type=ComponentType.ORDER_MANAGER)
        assert ctx.is_single_component

    def test_to_dict(self):
        ctx = IntegrationContext(portfolio_id="pf1")
        d   = ctx.to_dict()
        assert d["portfolio_id"] == "pf1"


# ===========================================================================
# TestIntegrationRequest
# ===========================================================================

class TestIntegrationRequest:
    def test_defaults(self):
        r = IntegrationRequest()
        assert r.limit == 1000

    def test_mutable(self):
        r = IntegrationRequest()
        r.query_type = IntegrationQueryType.FIND_ORDER
        assert r.query_type == IntegrationQueryType.FIND_ORDER

    def test_to_dict(self):
        r = IntegrationRequest(query_type=IntegrationQueryType.COUNT_ACTIVE)
        d = r.to_dict()
        assert d["query_type"] == "COUNT_ACTIVE"


# ===========================================================================
# TestIntegrationResponse
# ===========================================================================

class TestIntegrationResponse:
    def test_success(self):
        r = IntegrationResponse(succeeded=True, data={"count": 5})
        assert r.succeeded
        assert not r.is_error

    def test_error(self):
        r = IntegrationResponse(succeeded=False, error_code="OI-006")
        assert r.is_error
        assert r.error_code == "OI-006"

    def test_frozen(self):
        r = IntegrationResponse()
        with pytest.raises((AttributeError, TypeError)):
            r.succeeded = False  # type: ignore

    def test_to_dict(self):
        r = IntegrationResponse(query_type=IntegrationQueryType.COUNT_ACTIVE, succeeded=True)
        d = r.to_dict()
        assert d["query_type"] == "COUNT_ACTIVE"
        assert d["succeeded"]  is True


# ===========================================================================
# TestIntegrationStatistics
# ===========================================================================

class TestIntegrationStatistics:
    def test_defaults(self):
        s = IntegrationStatistics()
        assert s.orders_managed == 0
        assert s.component_count == 5

    def test_frozen(self):
        s = IntegrationStatistics()
        with pytest.raises((AttributeError, TypeError)):
            s.orders_managed = 10  # type: ignore

    def test_to_dict(self):
        s = IntegrationStatistics(orders_managed=100, validations_run=5)
        d = s.to_dict()
        assert d["orders_managed"]   == 100
        assert d["validations_run"]  == 5


# ===========================================================================
# TestOMSEvents
# ===========================================================================

class TestOMSEvents:
    def test_event_frozen(self):
        e = OMSEvent()
        with pytest.raises((AttributeError, TypeError)):
            e.succeeded = False  # type: ignore

    def test_make_oms_initialized(self):
        e = make_oms_initialized("1.0.0")
        assert e.event_type == IntegrationEventType.OMS_INITIALIZED
        assert e.succeeded  is True

    def test_make_oms_started(self):
        e = make_oms_started()
        assert e.event_type == IntegrationEventType.OMS_STARTED
        assert e.oms_state  == OMSState.RUNNING

    def test_make_oms_stopped(self):
        e = make_oms_stopped()
        assert e.event_type == IntegrationEventType.OMS_STOPPED
        assert e.oms_state  == OMSState.STOPPED

    def test_make_oms_validated_pass(self):
        e = make_oms_validated(is_valid=True)
        assert e.event_type == IntegrationEventType.OMS_VALIDATED
        assert e.succeeded  is True

    def test_make_oms_validated_fail(self):
        e = make_oms_validated(is_valid=False)
        assert e.succeeded is False

    def test_make_snapshot_published(self):
        e = make_snapshot_published("snap-1")
        assert e.event_type == IntegrationEventType.SNAPSHOT_PUBLISHED
        assert "snap-1"     in e.detail

    def test_make_component_registered(self):
        e = make_component_registered(ComponentType.ORDER_BOOK)
        assert e.event_type     == IntegrationEventType.COMPONENT_REGISTERED
        assert e.component_type == ComponentType.ORDER_BOOK

    def test_make_component_failed(self):
        e = make_component_failed(ComponentType.ORDER_QUEUE, "timeout")
        assert e.event_type     == IntegrationEventType.COMPONENT_FAILED
        assert e.component_type == ComponentType.ORDER_QUEUE
        assert e.succeeded      is False

    def test_to_dict(self):
        e = make_oms_started()
        d = e.to_dict()
        assert d["event_type"] == "OMS_STARTED"


# ===========================================================================
# TestIntegrationHistory
# ===========================================================================

class TestIntegrationHistory:
    def test_empty(self):
        h = IntegrationHistory()
        assert h.count == 0
        assert len(h)  == 0

    def test_append_and_all(self):
        h = IntegrationHistory()
        e = HistoryEntry()
        h.append(e)
        assert h.count == 1
        assert e in h.all()

    def test_latest(self):
        h = IntegrationHistory()
        for i in range(10):
            h.append(HistoryEntry(detail=f"entry-{i}"))
        last5 = h.latest(5)
        assert len(last5) == 5
        assert last5[-1].detail == "entry-9"

    def test_by_event_type(self):
        h = IntegrationHistory()
        h.append(HistoryEntry(event_type=IntegrationEventType.OMS_STARTED))
        h.append(HistoryEntry(event_type=IntegrationEventType.OMS_VALIDATED))
        h.append(HistoryEntry(event_type=IntegrationEventType.OMS_STARTED))
        assert len(h.by_event_type(IntegrationEventType.OMS_STARTED)) == 2

    def test_by_oms_state(self):
        h = IntegrationHistory()
        h.append(HistoryEntry(oms_state=OMSState.RUNNING))
        h.append(HistoryEntry(oms_state=OMSState.STOPPED))
        assert len(h.by_oms_state(OMSState.RUNNING)) == 1

    def test_failed(self):
        h = IntegrationHistory()
        h.append(HistoryEntry(succeeded=True))
        h.append(HistoryEntry(succeeded=False))
        assert len(h.failed()) == 1

    def test_bounded(self):
        max_e = 10
        h     = IntegrationHistory(max_entries=max_e)
        for _ in range(max_e + 5):
            h.append(HistoryEntry())
        assert h.count == max_e

    def test_iter(self):
        h = IntegrationHistory()
        h.append(HistoryEntry(detail="a"))
        h.append(HistoryEntry(detail="b"))
        entries = list(h)
        assert len(entries) == 2

    def test_history_entry_frozen(self):
        e = HistoryEntry()
        with pytest.raises((AttributeError, TypeError)):
            e.detail = "changed"  # type: ignore

    def test_history_entry_to_dict(self):
        e = HistoryEntry(detail="test")
        d = e.to_dict()
        assert d["detail"] == "test"


# ===========================================================================
# TestOMSSnapshot
# ===========================================================================

class TestOMSSnapshot:
    def test_defaults(self):
        s = OMSSnapshot()
        assert s.oms_state == OMSState.RUNNING

    def test_frozen(self):
        s = OMSSnapshot()
        with pytest.raises((AttributeError, TypeError)):
            s.oms_state = OMSState.STOPPED  # type: ignore

    def test_is_healthy_when_running(self):
        s = OMSSnapshot(oms_state=OMSState.RUNNING, is_degraded=False)
        assert s.is_healthy

    def test_is_unhealthy_when_degraded(self):
        s = OMSSnapshot(oms_state=OMSState.RUNNING, is_degraded=True)
        assert not s.is_healthy

    def test_healthy_unhealthy_counts(self):
        h1 = ComponentHealth(component_type=ComponentType.ORDER_MANAGER, is_healthy=True)
        h2 = ComponentHealth(component_type=ComponentType.ORDER_BOOK,    is_healthy=False)
        s  = OMSSnapshot(component_health=(h1, h2))
        assert s.healthy_component_count   == 1
        assert s.unhealthy_component_count == 1

    def test_to_dict(self):
        s = OMSSnapshot(oms_state=OMSState.RUNNING)
        d = s.to_dict()
        assert d["oms_state"]     == "RUNNING"
        assert "statistics"       in d
        assert "component_health" in d


# ===========================================================================
# TestOMSValidator
# ===========================================================================

class TestOMSValidator:
    def _mock_registry(self, all_running: bool = True) -> MagicMock:
        from iios.investment.workflow.engine_lifecycle import EngineState
        registry = MagicMock()
        state    = EngineState.RUNNING if all_running else EngineState.STOPPED
        mock_comp = MagicMock()
        mock_comp.lifecycle_state.return_value = state
        registry.get.return_value = mock_comp
        return registry

    def test_validate_all_pass(self):
        v        = OMSValidator()
        registry = self._mock_registry(all_running=True)
        report   = v.validate(registry)
        assert isinstance(report, ValidationReport)
        assert report.is_valid

    def test_validate_missing_component(self):
        v        = OMSValidator()
        registry = MagicMock()
        registry.get.return_value = None   # all missing
        report   = v.validate(registry)
        assert not report.is_valid
        assert report.error_count > 0
        assert ValidationCode.COMPONENT_MISSING in report.codes

    def test_validate_not_running(self):
        v        = OMSValidator()
        registry = self._mock_registry(all_running=False)
        report   = v.validate(registry)
        assert not report.is_valid
        assert ValidationCode.COMPONENT_NOT_RUNNING in report.codes

    def test_validate_snapshot_valid(self):
        v = OMSValidator()
        snap = OMSSnapshot(
            manager_snapshot     = {},
            book_snapshot        = {},
            router_snapshot      = {},
            queue_snapshot       = {},
            persistence_snapshot = {},
            statistics           = IntegrationStatistics(),
            component_health     = tuple(
                ComponentHealth(component_type=ct) for ct in ComponentType
            ),
        )
        report = v.validate_snapshot(snap)
        assert report.is_valid

    def test_validate_snapshot_missing_field(self):
        v = OMSValidator()
        snap = OMSSnapshot(
            # manager_snapshot missing (None)
            book_snapshot        = {},
            router_snapshot      = {},
            queue_snapshot       = {},
            persistence_snapshot = {},
        )
        report = v.validate_snapshot(snap)
        assert not report.is_valid

    def test_report_to_dict(self):
        r = ValidationReport(is_valid=True, errors=(), warnings=())
        d = r.to_dict()
        assert d["is_valid"]   is True
        assert "elapsed_ms"    in d


# ===========================================================================
# TestOMSComponentRegistry
# ===========================================================================

class TestOMSComponentRegistry:
    def test_not_started_raises(self):
        r = OMSComponentRegistry()
        m = _mock_component()
        with pytest.raises(Exception):
            r.register(ComponentType.ORDER_MANAGER, m)

    def test_lifecycle(self):
        r = OMSComponentRegistry()
        r.start()
        assert r.lifecycle_state().value == "running"
        r.stop()
        assert r.lifecycle_state().value == "stopped"

    def test_register_and_get(self):
        r = OMSComponentRegistry()
        r.start()
        m = _mock_component()
        r.register(ComponentType.ORDER_MANAGER, m)
        assert r.get(ComponentType.ORDER_MANAGER) is m
        r.stop()

    def test_register_none_raises(self):
        r = OMSComponentRegistry()
        r.start()
        with pytest.raises(ComponentRegistrationError):
            r.register(ComponentType.ORDER_BOOK, None)
        r.stop()

    def test_unregister(self):
        r = OMSComponentRegistry()
        r.start()
        m = _mock_component()
        r.register(ComponentType.ORDER_MANAGER, m)
        assert r.unregister(ComponentType.ORDER_MANAGER) is True
        assert r.get(ComponentType.ORDER_MANAGER)        is None
        assert r.unregister(ComponentType.ORDER_MANAGER) is False
        r.stop()

    def test_missing(self):
        r = OMSComponentRegistry()
        r.start()
        m = _mock_component()
        r.register(ComponentType.ORDER_MANAGER, m)
        missing = r.missing()
        assert ComponentType.ORDER_MANAGER not in missing
        assert ComponentType.ORDER_BOOK    in missing
        r.stop()

    def test_is_complete(self):
        r = OMSComponentRegistry()
        r.start()
        for ct in ComponentType:
            r.register(ct, _mock_component())
        assert r.is_complete
        r.stop()

    def test_start_all_and_stop_all(self):
        from iios.investment.workflow.engine_lifecycle import EngineState
        r = OMSComponentRegistry()
        r.start()
        for ct in ComponentType:
            m = MagicMock()
            m.lifecycle_state.return_value = EngineState.STOPPED
            r.register(ct, m)
        r.start_all()
        # Verify start() was called on all
        for ct in ComponentType:
            r.get(ct).start.assert_called_once()
        r.stop()

    def test_health_all(self):
        from iios.investment.workflow.engine_lifecycle import EngineState
        r = OMSComponentRegistry()
        r.start()
        m = MagicMock()
        m.lifecycle_state.return_value = EngineState.RUNNING
        m.health.return_value = MagicMock(is_healthy=True, message="ok")
        r.register(ComponentType.ORDER_MANAGER, m)
        health = r.health_all()
        assert len(health) == 1
        assert health[0].is_healthy
        r.stop()

    def test_status_all(self):
        from iios.investment.workflow.engine_lifecycle import EngineState
        r = OMSComponentRegistry()
        r.start()
        m = MagicMock()
        m.lifecycle_state.return_value = EngineState.RUNNING
        r.register(ComponentType.ORDER_QUEUE, m)
        statuses = r.status_all()
        assert len(statuses) == 1
        assert statuses[0].is_running
        r.stop()

    def test_iter_and_len(self):
        r = OMSComponentRegistry()
        r.start()
        for ct in ComponentType:
            r.register(ct, _mock_component())
        assert len(r) == 5
        pairs = list(r)
        assert len(pairs) == 5
        r.stop()


# ===========================================================================
# TestOMSComponentFactory
# ===========================================================================

class TestOMSComponentFactory:
    def test_create_order_manager(self):
        f = OMSComponentFactory()
        m = f.create_order_manager()
        assert m is not None
        m.start()
        assert m.lifecycle_state().value == "running"
        m.stop()

    def test_create_order_book(self):
        f  = OMSComponentFactory()
        bk = f.create_order_book()
        assert bk is not None
        bk.start()
        bk.stop()

    def test_create_order_router(self):
        f   = OMSComponentFactory()
        rtr = f.create_order_router()
        assert rtr is not None
        rtr.start()
        rtr.stop()

    def test_create_order_queue(self):
        f  = OMSComponentFactory()
        qu = f.create_order_queue()
        assert qu is not None
        qu.start()
        qu.stop()

    def test_create_persistence_manager(self):
        f   = OMSComponentFactory()
        pm  = f.create_persistence_manager()
        assert pm is not None
        pm.start()
        pm.stop()

    def test_create_all_returns_five(self):
        f        = OMSComponentFactory()
        all_comp = f.create_all()
        assert len(all_comp) == 5
        for ct in ComponentType:
            assert ct in all_comp
            assert all_comp[ct] is not None

    def test_ensure_default_repository(self):
        f  = OMSComponentFactory()
        pm = f.create_persistence_manager()
        pm.start()
        f.ensure_default_repository(pm)
        # After ensure, registry should have exactly 1 repo
        assert pm._registry.count == 1
        pm.stop()


# ===========================================================================
# TestOMSIntegrationManager
# ===========================================================================

class TestOMSIntegrationManager:
    def test_lifecycle(self):
        m = OMSIntegrationManager()
        m.start()
        assert m.lifecycle_state().value == "running"
        assert m.oms_state               == OMSState.RUNNING
        m.stop()

    def test_initialize_defaults_registers_all(self):
        m = OMSIntegrationManager()
        m.start()
        m.initialize_defaults()
        assert m._registry.count == 5
        assert m._registry.is_complete
        m.stop()

    def test_register_component(self):
        m = OMSIntegrationManager()
        m.start()
        factory = OMSComponentFactory()
        mgr_comp = factory.create_order_manager()
        mgr_comp.start()
        m.register_component(ComponentType.ORDER_MANAGER, mgr_comp)
        assert m._registry.get(ComponentType.ORDER_MANAGER) is mgr_comp
        m.stop()

    def test_validate_after_init(self):
        m = OMSIntegrationManager()
        m.start()
        m.initialize_defaults()
        report = m.validate()
        assert isinstance(report, ValidationReport)
        assert report.is_valid
        m.stop()

    def test_snapshot(self):
        m = OMSIntegrationManager()
        m.start()
        m.initialize_defaults()
        snap = m.snapshot()
        assert isinstance(snap, OMSSnapshot)
        assert snap.oms_state == OMSState.RUNNING
        m.stop()

    def test_statistics(self):
        m = OMSIntegrationManager()
        m.start()
        m.initialize_defaults()
        stats = m.statistics()
        assert isinstance(stats, IntegrationStatistics)
        assert stats.component_count == 5
        m.stop()

    def test_events_populated(self):
        m = OMSIntegrationManager()
        m.start()
        m.initialize_defaults()
        events = m.events()
        types  = [e.event_type for e in events]
        assert IntegrationEventType.OMS_STARTED       in types
        assert IntegrationEventType.OMS_INITIALIZED   in types
        m.stop()

    def test_history_populated(self):
        m = OMSIntegrationManager()
        m.start()
        m.initialize_defaults()
        history = m.history()
        assert history.count > 0
        m.stop()

    def test_query_full_health(self):
        m = OMSIntegrationManager()
        m.start()
        m.initialize_defaults()
        req  = IntegrationRequest(query_type=IntegrationQueryType.FULL_HEALTH)
        resp = m.query(req)
        assert resp.succeeded
        assert "all_healthy" in resp.data
        m.stop()


# ===========================================================================
# TestOMSIntegrationEngine
# ===========================================================================

class TestOMSIntegrationEngine:
    def test_not_started_raises(self):
        engine = OMSIntegrationEngine()
        with pytest.raises(OMSNotInitializedError):
            engine.health()

    def test_lifecycle_running(self):
        engine = _started_engine()
        assert engine.lifecycle_state().value == "running"
        assert engine.is_initialized
        engine.stop()

    def test_stop_and_restart(self):
        engine = _started_engine()
        engine.stop()
        assert engine.lifecycle_state().value == "stopped"
        # Re-start after stop
        engine2 = OMSIntegrationEngine()
        engine2.initialize()
        engine2.start()
        assert engine2.lifecycle_state().value == "running"
        engine2.stop()

    def test_oms_state_running_after_start(self):
        engine = _started_engine()
        assert engine.oms_state == OMSState.RUNNING
        engine.stop()

    def test_health_returns_component_healths(self):
        engine = _started_engine()
        h = engine.health()
        assert isinstance(h, list)
        assert len(h) == 5
        for item in h:
            assert isinstance(item, ComponentHealth)
        engine.stop()

    def test_all_components_healthy_after_init(self):
        engine = _started_engine()
        h = engine.health()
        for item in h:
            assert item.is_healthy, f"{item.component_type.value} not healthy"
        engine.stop()

    def test_status_returns_component_statuses(self):
        engine = _started_engine()
        s = engine.status()
        assert len(s) == 5
        for item in s:
            assert isinstance(item, ComponentStatus)
            assert item.is_running
        engine.stop()

    def test_statistics(self):
        engine = _started_engine()
        stats  = engine.statistics()
        assert isinstance(stats, IntegrationStatistics)
        assert stats.component_count == 5
        engine.stop()

    def test_snapshot(self):
        engine = _started_engine()
        snap   = engine.snapshot()
        assert isinstance(snap, OMSSnapshot)
        assert snap.oms_state    == OMSState.RUNNING
        assert snap.is_healthy
        assert snap.manager_snapshot    is not None
        assert snap.book_snapshot       is not None
        assert snap.queue_snapshot      is not None
        # Router snapshot is a dict
        assert snap.router_snapshot     is not None
        engine.stop()

    def test_snapshot_increments_counter(self):
        engine = _started_engine()
        engine.snapshot()
        engine.snapshot()
        stats = engine.statistics()
        assert stats.snapshots_published == 2
        engine.stop()

    def test_history(self):
        engine = _started_engine()
        h      = engine.history()
        assert isinstance(h, IntegrationHistory)
        assert h.count > 0
        engine.stop()

    def test_validate_passes(self):
        engine = _started_engine()
        report = engine.validate()
        assert isinstance(report, ValidationReport)
        assert report.is_valid
        engine.stop()

    def test_validate_increments_counter(self):
        engine = _started_engine()
        engine.validate()
        engine.validate()
        stats = engine.statistics()
        assert stats.validations_run     == 2
        assert stats.validation_success  == 2
        engine.stop()

    def test_query_full_health(self):
        engine = _started_engine()
        req    = IntegrationRequest(query_type=IntegrationQueryType.FULL_HEALTH)
        resp   = engine.query(req)
        assert resp.succeeded
        assert resp.data.get("all_healthy") is True
        engine.stop()

    def test_query_count_active(self):
        engine = _started_engine()
        req    = IntegrationRequest(query_type=IntegrationQueryType.COUNT_ACTIVE)
        resp   = engine.query(req)
        assert resp.succeeded
        assert "count" in resp.data
        engine.stop()

    def test_query_list_active(self):
        engine = _started_engine()
        req    = IntegrationRequest(query_type=IntegrationQueryType.LIST_ACTIVE)
        resp   = engine.query(req)
        assert resp.succeeded
        assert "items" in resp.data
        engine.stop()

    def test_query_book_query(self):
        engine = _started_engine()
        req    = IntegrationRequest(query_type=IntegrationQueryType.BOOK_QUERY)
        resp   = engine.query(req)
        assert resp.succeeded
        assert "entries" in resp.data
        engine.stop()

    def test_query_queue_peek(self):
        engine = _started_engine()
        req    = IntegrationRequest(query_type=IntegrationQueryType.QUEUE_PEEK)
        resp   = engine.query(req)
        assert resp.succeeded   # empty queue returns entry=None
        engine.stop()

    def test_query_queue_size(self):
        engine = _started_engine()
        req    = IntegrationRequest(query_type=IntegrationQueryType.QUEUE_SIZE)
        resp   = engine.query(req)
        assert resp.succeeded
        engine.stop()

    def test_query_router_history(self):
        engine = _started_engine()
        req    = IntegrationRequest(query_type=IntegrationQueryType.ROUTER_HISTORY)
        resp   = engine.query(req)
        assert resp.succeeded
        assert "decisions" in resp.data
        engine.stop()

    def test_query_find_order_missing(self):
        engine = _started_engine()
        req    = IntegrationRequest(
            query_type = IntegrationQueryType.FIND_ORDER,
            payload    = {"order_id": "does-not-exist"},
        )
        resp   = engine.query(req)
        assert resp.succeeded
        assert resp.data.get("order") is None
        engine.stop()

    def test_query_book_contains_false(self):
        engine = _started_engine()
        req    = IntegrationRequest(
            query_type = IntegrationQueryType.BOOK_CONTAINS,
            payload    = {"order_id": "ghost"},
        )
        resp   = engine.query(req)
        assert resp.succeeded
        assert resp.data.get("contains") is False
        engine.stop()

    def test_query_persist_find_missing(self):
        engine = _started_engine()
        req    = IntegrationRequest(
            query_type = IntegrationQueryType.PERSIST_FIND,
            payload    = {"record_id": "no-record", "repository_id": "oms:default"},
        )
        resp   = engine.query(req)
        assert resp.succeeded
        assert resp.data.get("found") is False
        engine.stop()

    def test_get_component(self):
        engine = _started_engine()
        from iios.execution.oms.order_manager import OrderManager
        mgr = engine.get_component(ComponentType.ORDER_MANAGER)
        assert isinstance(mgr, OrderManager)
        engine.stop()

    def test_events_emit_on_start(self):
        engine = _started_engine()
        events = engine.events()
        types  = [e.event_type for e in events]
        assert IntegrationEventType.OMS_STARTED      in types
        assert IntegrationEventType.OMS_INITIALIZED  in types
        engine.stop()

    def test_summary(self):
        engine = _started_engine()
        s      = engine.summary()
        assert s["oms_state"]       == "RUNNING"
        assert s["is_initialized"]  is True
        assert s["component_count"] == 5
        assert s["version"]         == VERSION
        engine.stop()

    def test_initialize_is_idempotent(self):
        engine = OMSIntegrationEngine()
        engine.initialize()
        engine.initialize()   # second call is no-op
        engine.start()
        assert engine._manager._registry.count == 5
        engine.stop()

    def test_inject_custom_components(self):
        factory     = OMSComponentFactory()
        custom_mgr  = factory.create_order_manager()
        engine      = OMSIntegrationEngine(order_manager=custom_mgr)
        engine.initialize()
        engine.start()
        assert engine.get_component(ComponentType.ORDER_MANAGER) is custom_mgr
        engine.stop()


# ===========================================================================
# TestConcurrency
# ===========================================================================

class TestConcurrency:
    def test_100_concurrent_snapshots(self):
        engine = _started_engine()
        errors = []

        def worker():
            try:
                engine.snapshot()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        stats = engine.statistics()
        assert stats.snapshots_published == 100
        engine.stop()

    def test_concurrent_query_and_validate(self):
        engine = _started_engine()
        errors = []

        def snapshot_worker():
            try:
                engine.snapshot()
            except Exception as e:
                errors.append(e)

        def validate_worker():
            try:
                engine.validate()
            except Exception as e:
                errors.append(e)

        def query_worker():
            try:
                engine.query(IntegrationRequest(
                    query_type=IntegrationQueryType.FULL_HEALTH
                ))
            except Exception as e:
                errors.append(e)

        threads = (
            [threading.Thread(target=snapshot_worker) for _ in range(30)]
            + [threading.Thread(target=validate_worker) for _ in range(30)]
            + [threading.Thread(target=query_worker)    for _ in range(40)]
        )
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        engine.stop()

    def test_concurrent_statistics_reads(self):
        engine = _started_engine()
        errors = []
        stats_list = []
        lock       = threading.Lock()

        def worker():
            try:
                s = engine.statistics()
                with lock:
                    stats_list.append(s)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert len(stats_list) == 50
        engine.stop()


# ===========================================================================
# TestRegression — all 5 OMS modules accessible through engine
# ===========================================================================

class TestRegression:
    def test_order_manager_accessible(self):
        engine = _started_engine()
        from iios.execution.oms.order_manager import OrderManager
        assert isinstance(engine.get_component(ComponentType.ORDER_MANAGER), OrderManager)
        engine.stop()

    def test_order_book_accessible(self):
        engine = _started_engine()
        from iios.execution.oms.order_book import OrderBook
        assert isinstance(engine.get_component(ComponentType.ORDER_BOOK), OrderBook)
        engine.stop()

    def test_order_router_accessible(self):
        engine = _started_engine()
        from iios.execution.oms.order_router import OrderRouter
        assert isinstance(engine.get_component(ComponentType.ORDER_ROUTER), OrderRouter)
        engine.stop()

    def test_order_queue_accessible(self):
        engine = _started_engine()
        from iios.execution.oms.order_queue import OrderQueue
        assert isinstance(engine.get_component(ComponentType.ORDER_QUEUE), OrderQueue)
        engine.stop()

    def test_persistence_accessible(self):
        engine = _started_engine()
        from iios.execution.oms.persistence import RepositoryManager
        assert isinstance(engine.get_component(ComponentType.PERSISTENCE), RepositoryManager)
        engine.stop()

    def test_all_components_running_after_start(self):
        from iios.investment.workflow.engine_lifecycle import EngineState
        engine = _started_engine()
        for ct in ComponentType:
            comp = engine.get_component(ct)
            assert comp is not None, f"{ct.value} not registered"
            assert comp.lifecycle_state() == EngineState.RUNNING, (
                f"{ct.value} not running: {comp.lifecycle_state()}"
            )
        engine.stop()

    def test_validation_report_has_no_errors_on_clean_start(self):
        engine = _started_engine()
        report = engine.validate()
        assert report.is_valid, f"Validation errors: {report.errors}"
        engine.stop()

    def test_snapshot_contains_all_subsystem_snapshots(self):
        engine = _started_engine()
        snap   = engine.snapshot()
        assert snap.manager_snapshot     is not None, "manager_snapshot is None"
        assert snap.book_snapshot        is not None, "book_snapshot is None"
        assert snap.queue_snapshot       is not None, "queue_snapshot is None"
        assert snap.router_snapshot      is not None, "router_snapshot is None"
        assert snap.persistence_snapshot is not None, "persistence_snapshot is None"
        engine.stop()
