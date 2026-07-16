"""iios/execution/oms/integration/oms_integration_manager.py
==================================================
OMSIntegrationManager — internal coordinator for all OMS components.

Delegates to the five OMS subsystems, aggregates statistics, runs
validation cycles, and emits domain events.  Not public — callers
must go through OMSIntegrationEngine.

C6 Execution Intelligence — Phase 2, Module 6
"""
from __future__ import annotations

import dataclasses
import threading
import time
from typing import Any

from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin
from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger

from iios.execution.oms.integration.constants import (
    DEFAULT_MAX_EVENTS,
    MANAGER_SYSTEM_ID,
    VERSION,
    ComponentType,
    IntegrationEventType,
    IntegrationQueryType,
    OMSState,
    REQUIRED_COMPONENTS,
)
from iios.execution.oms.integration.exceptions import (
    OMSNotInitializedError,
    OMSQueryError,
    OMSSnapshotError,
)
from iios.execution.oms.integration.oms_component_factory import OMSComponentFactory
from iios.execution.oms.integration.oms_component_registry import OMSComponentRegistry
from iios.execution.oms.integration.oms_integration_events import (
    OMSEvent,
    make_component_failed,
    make_component_registered,
    make_oms_initialized,
    make_oms_started,
    make_oms_stopped,
    make_oms_validated,
    make_snapshot_published,
)
from iios.execution.oms.integration.oms_integration_history import (
    HistoryEntry,
    IntegrationHistory,
)
from iios.execution.oms.integration.oms_integration_request import IntegrationRequest
from iios.execution.oms.integration.oms_integration_response import IntegrationResponse
from iios.execution.oms.integration.oms_integration_snapshot import OMSSnapshot
from iios.execution.oms.integration.oms_integration_statistics import IntegrationStatistics
from iios.execution.oms.integration.oms_integration_validation import (
    OMSValidator,
    ValidationReport,
)


class OMSIntegrationManager(LifecycleAwareMixin):
    """
    Internal OMS coordinator.

    Responsibilities:
    - Start / stop all registered components
    - Aggregate health, status, statistics
    - Generate OMSSnapshot
    - Route query requests to the correct component
    - Run validation cycles
    - Emit and store domain events
    """

    def __init__(
        self,
        registry:  OMSComponentRegistry | None  = None,
        factory:   OMSComponentFactory  | None  = None,
        validator: OMSValidator          | None = None,
        max_events: int = DEFAULT_MAX_EVENTS,
    ) -> None:
        super().__init__()
        self._registry   = registry  or OMSComponentRegistry()
        self._factory    = factory   or OMSComponentFactory()
        self._validator  = validator or OMSValidator()
        self._max_events = max_events
        self._history    = IntegrationHistory()
        self._events:    list[OMSEvent] = []
        self._oms_state  = OMSState.UNINITIALIZED
        self._lock       = threading.RLock()
        self._log        = get_logger(__name__, engine_id=MANAGER_SYSTEM_ID)
        self._audit      = get_audit_logger(__name__, engine_id=MANAGER_SYSTEM_ID)

        # Aggregate counters
        self._snapshot_count     = 0
        self._validation_success = 0
        self._validation_failure = 0
        self._query_count        = 0
        self._latencies:         list[float] = []

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def _on_start(self) -> None:
        if self._registry.lifecycle_state() != EngineState.RUNNING:
            self._registry.start()
        self._set_state(OMSState.RUNNING)
        self._audit.log_lifecycle_event(
            MANAGER_SYSTEM_ID, EngineState.STOPPED, EngineState.RUNNING, VERSION
        )
        self._log.info("OMSIntegrationManager started.")
        self._emit(make_oms_started())

    def _on_stop(self) -> None:
        self._emit(make_oms_stopped())
        self._set_state(OMSState.STOPPED)
        self._registry.stop_all()
        if self._registry.lifecycle_state() == EngineState.RUNNING:
            self._registry.stop()
        self._audit.log_lifecycle_event(
            MANAGER_SYSTEM_ID, EngineState.RUNNING, EngineState.STOPPED, VERSION
        )
        self._log.info(
            "OMSIntegrationManager stopped.",
            snapshots=self._snapshot_count,
            validations=self._validation_success + self._validation_failure,
        )

    def _assert_running(self) -> None:
        if self.lifecycle_state() != EngineState.RUNNING:
            raise OMSNotInitializedError(
                "OMSIntegrationManager is not running",
                code="OI-001",
            )

    # ------------------------------------------------------------------
    # Component registration
    # ------------------------------------------------------------------

    def register_component(self, component_type: ComponentType, component: Any) -> None:
        self._assert_running()
        self._registry.register(component_type, component)
        self._emit(make_component_registered(component_type))
        self._record_history(
            IntegrationEventType.COMPONENT_REGISTERED,
            detail=f"Registered {component_type.value}",
        )

    def initialize_defaults(self) -> None:
        """
        Register all components that are not yet registered, using factory defaults.
        After registration, start all components.
        """
        components = self._factory.create_all()
        for ct, component in components.items():
            if self._registry.get(ct) is None:
                self._registry.register(ct, component)
                self._emit(make_component_registered(ct))
        self._registry.start_all()
        # Ensure persistence has a default repository
        persistence = self._registry.get(ComponentType.PERSISTENCE)
        if persistence is not None:
            self._factory.ensure_default_repository(persistence)
        self._set_state(OMSState.RUNNING)
        self._emit(make_oms_initialized(VERSION))
        self._record_history(
            IntegrationEventType.OMS_INITIALIZED,
            detail="OMS initialized with default components",
        )
        self._log.info("OMS initialized with all default components.")

    # ------------------------------------------------------------------
    # Health / status
    # ------------------------------------------------------------------

    def health_all(self):
        return self._registry.health_all()

    def status_all(self):
        return self._registry.status_all()

    @property
    def oms_state(self) -> OMSState:
        with self._lock:
            return self._oms_state

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self) -> ValidationReport:
        report = self._validator.validate(self._registry)
        with self._lock:
            if report.is_valid:
                self._validation_success += 1
            else:
                self._validation_failure += 1
        self._emit(make_oms_validated(report.is_valid))
        self._record_history(
            IntegrationEventType.OMS_VALIDATED,
            succeeded=report.is_valid,
            detail=f"errors={report.error_count} warnings={report.warning_count}",
        )
        return report

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def snapshot(self) -> OMSSnapshot:
        t0 = time.time()
        try:
            health   = self._registry.health_all()
            statuses = self._registry.status_all()
            stats    = self._build_statistics()

            degraded = [h.component_type.value for h in health if h.is_degraded]
            is_deg   = len(degraded) > 0

            # Gather component snapshots — each component's snapshot() method
            mgr  = self._registry.get(ComponentType.ORDER_MANAGER)
            bk   = self._registry.get(ComponentType.ORDER_BOOK)
            rtr  = self._registry.get(ComponentType.ORDER_ROUTER)
            qu   = self._registry.get(ComponentType.ORDER_QUEUE)
            per  = self._registry.get(ComponentType.PERSISTENCE)

            mgr_snap  = mgr.snapshot()  if mgr  and _is_running(mgr)  else None
            bk_snap   = bk.snapshot()   if bk   and _is_running(bk)   else None
            rtr_snap  = rtr.snapshot()  if rtr  and _is_running(rtr)  else None
            qu_snap   = qu.snapshot()   if qu   and _is_running(qu)   else None
            per_snap  = per._registry.default().snapshot() if (
                per and _is_running(per) and per._registry.count > 0
            ) else None

            snap = OMSSnapshot(
                oms_state            = self._oms_state,
                manager_snapshot     = mgr_snap,
                book_snapshot        = bk_snap,
                router_snapshot      = rtr_snap,
                queue_snapshot       = qu_snap,
                persistence_snapshot = per_snap,
                component_health     = tuple(health),
                component_status     = tuple(statuses),
                statistics           = stats,
                is_degraded          = is_deg,
                degraded_components  = tuple(degraded),
            )

            with self._lock:
                self._snapshot_count += 1
                lat = (time.time() - t0) * 1000.0
                self._latencies.append(lat)

            self._emit(make_snapshot_published(snap.snapshot_id))
            return snap

        except Exception as exc:
            raise OMSSnapshotError(
                f"Failed to generate OMS snapshot: {exc}",
                code="OI-005",
            ) from exc

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def statistics(self) -> IntegrationStatistics:
        return self._build_statistics()

    def _build_statistics(self) -> IntegrationStatistics:
        mgr = self._registry.get(ComponentType.ORDER_MANAGER)
        bk  = self._registry.get(ComponentType.ORDER_BOOK)
        rtr = self._registry.get(ComponentType.ORDER_ROUTER)
        qu  = self._registry.get(ComponentType.ORDER_QUEUE)
        per = self._registry.get(ComponentType.PERSISTENCE)

        # Order Manager stats
        orders_managed   = 0
        orders_active    = 0
        orders_completed = 0
        orders_cancelled = 0
        if mgr and _is_running(mgr):
            try:
                s = mgr.statistics()
                orders_managed   = s.orders_created
                orders_active    = s.orders_active
                orders_completed = s.orders_completed
                orders_cancelled = s.orders_cancelled
            except Exception:  # noqa: BLE001
                pass

        # Queue stats
        orders_queued       = 0
        orders_dispatched   = 0
        orders_failed_queue = 0
        if qu and _is_running(qu):
            try:
                s = qu.statistics()
                orders_queued       = s._total_enqueued
                orders_dispatched   = s._total_dispatched
                orders_failed_queue = s._total_failed
            except Exception:  # noqa: BLE001
                pass

        # Router stats
        orders_routed   = 0
        routing_rejected = 0
        routing_failed   = 0
        if rtr and _is_running(rtr):
            try:
                s = rtr.statistics()
                d = s.to_dict()
                orders_routed    = d.get("successful", 0)
                routing_rejected = d.get("rejected", 0)
                routing_failed   = d.get("failed", 0)
            except Exception:  # noqa: BLE001
                pass

        # Persistence stats
        orders_persisted = 0
        orders_arch      = 0
        if per and _is_running(per):
            try:
                # Aggregate across all registered repositories
                for repo_id in per._registry.repository_ids():
                    s = per.statistics(repo_id)
                    if s:
                        orders_persisted += s.records_stored
                        orders_arch      += s.records_archived
            except Exception:  # noqa: BLE001
                pass

        # Book stats
        book_entries        = 0
        book_active_entries = 0
        if bk and _is_running(bk):
            try:
                book_entries        = bk.count()
                book_active_entries = len(bk.find_active())
            except Exception:  # noqa: BLE001
                pass

        with self._lock:
            avg_lat = (
                sum(self._latencies) / len(self._latencies)
                if self._latencies else 0.0
            )

        return IntegrationStatistics(
            orders_managed       = orders_managed,
            orders_active        = orders_active,
            orders_completed     = orders_completed,
            orders_cancelled     = orders_cancelled,
            orders_queued        = orders_queued,
            orders_dispatched    = orders_dispatched,
            orders_failed_queue  = orders_failed_queue,
            orders_routed        = orders_routed,
            routing_rejected     = routing_rejected,
            routing_failed       = routing_failed,
            orders_persisted     = orders_persisted,
            orders_archived      = orders_arch,
            book_entries         = book_entries,
            book_active_entries  = book_active_entries,
            snapshots_published  = self._snapshot_count,
            validations_run      = self._validation_success + self._validation_failure,
            validation_success   = self._validation_success,
            validation_failure   = self._validation_failure,
            queries_served       = self._query_count,
            component_count      = self._registry.count,
            avg_latency_ms       = avg_lat,
        )

    # ------------------------------------------------------------------
    # Query routing
    # ------------------------------------------------------------------

    def query(self, request: IntegrationRequest) -> IntegrationResponse:
        t0 = time.time()
        try:
            data  = self._route_query(request)
            elapsed = (time.time() - t0) * 1000.0
            with self._lock:
                self._query_count += 1
            return IntegrationResponse(
                request_id     = request.request_id,
                query_type     = request.query_type,
                component_type = request.component_type,
                succeeded      = True,
                data           = data,
                elapsed_ms     = elapsed,
                result_count   = data.get("count", len(data.get("items", []))) if data else 0,
            )
        except Exception as exc:
            elapsed = (time.time() - t0) * 1000.0
            return IntegrationResponse(
                request_id    = request.request_id,
                query_type    = request.query_type,
                component_type = request.component_type,
                succeeded     = False,
                elapsed_ms    = elapsed,
                error_code    = "OI-006",
                error_message = str(exc),
            )

    def _route_query(self, request: IntegrationRequest) -> dict:
        qt = request.query_type

        if qt == IntegrationQueryType.FIND_ORDER:
            mgr = self._registry.require(ComponentType.ORDER_MANAGER)
            order_id = request.payload.get("order_id", "")
            result   = mgr.lookup(order_id)
            return {"order": result.to_dict() if result else None}

        elif qt == IntegrationQueryType.LIST_ACTIVE:
            mgr = self._registry.require(ComponentType.ORDER_MANAGER)
            active = mgr.get_active()
            return {"items": [o.to_dict() for o in active], "count": len(active)}

        elif qt == IntegrationQueryType.COUNT_ACTIVE:
            mgr = self._registry.require(ComponentType.ORDER_MANAGER)
            return {"count": mgr.count()}

        elif qt == IntegrationQueryType.BOOK_CONTAINS:
            bk = self._registry.require(ComponentType.ORDER_BOOK)
            oid = request.payload.get("order_id", "")
            return {"contains": bk.contains(oid), "order_id": oid}

        elif qt == IntegrationQueryType.BOOK_QUERY:
            bk = self._registry.require(ComponentType.ORDER_BOOK)
            result = bk.query()
            return {"entries": [e.to_dict() for e in result.entries], "count": len(result.entries)}

        elif qt == IntegrationQueryType.QUEUE_PEEK:
            qu = self._registry.require(ComponentType.ORDER_QUEUE)
            entry = qu.peek()
            return {"entry": entry.to_dict() if entry else None}

        elif qt == IntegrationQueryType.QUEUE_SIZE:
            qu = self._registry.require(ComponentType.ORDER_QUEUE)
            info = qu.info()
            return info

        elif qt == IntegrationQueryType.ROUTER_HISTORY:
            rtr = self._registry.require(ComponentType.ORDER_ROUTER)
            h   = rtr.history()
            all_decisions = list(h)
            return {"decisions": [d.to_dict() for d in all_decisions], "count": len(all_decisions)}

        elif qt == IntegrationQueryType.PERSIST_FIND:
            per = self._registry.require(ComponentType.PERSISTENCE)
            from iios.execution.oms.persistence import RepositoryFactory
            factory = RepositoryFactory()
            rec_id  = request.payload.get("record_id", "")
            repo_id = request.payload.get("repository_id", "")
            ctx     = None  # persistence manager needs context
            from iios.execution.oms.persistence import RepositoryContext, OperationType
            ctx  = RepositoryContext(operation=OperationType.FIND)
            req_ = factory.make_find_request(rec_id, repository_id=repo_id)
            resp = per.find(ctx, req_)
            return {
                "found":    resp.succeeded,
                "record":   resp.record.to_dict() if resp.record else None,
                "version":  resp.record_version,
            }

        elif qt == IntegrationQueryType.FULL_HEALTH:
            health = self._registry.health_all()
            return {
                "component_health": [h.to_dict() for h in health],
                "all_healthy": all(h.is_healthy for h in health),
                "count": len(health),
            }

        else:
            raise OMSQueryError(qt.value, reason="unknown query type")

    # ------------------------------------------------------------------
    # Events / history
    # ------------------------------------------------------------------

    def events(self) -> list[OMSEvent]:
        with self._lock:
            return list(self._events)

    def history(self) -> IntegrationHistory:
        return self._history

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _set_state(self, state: OMSState) -> None:
        with self._lock:
            self._oms_state = state

    def _emit(self, event: OMSEvent) -> None:
        with self._lock:
            if len(self._events) >= self._max_events:
                self._events.pop(0)
            self._events.append(event)

    def _record_history(
        self,
        event_type: IntegrationEventType,
        *,
        succeeded: bool = True,
        detail:    str  = "",
    ) -> None:
        entry = HistoryEntry(
            event_type  = event_type,
            oms_state   = self._oms_state,
            succeeded   = succeeded,
            detail      = detail,
        )
        self._history.append(entry)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_running(component: Any) -> bool:
    try:
        from iios.investment.workflow.engine_lifecycle import EngineState
        return component.lifecycle_state() == EngineState.RUNNING
    except Exception:  # noqa: BLE001
        return False
