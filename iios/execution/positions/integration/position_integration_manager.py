"""iios/execution/positions/integration/position_integration_manager.py
==================================================
PositionIntegrationManager — coordinates all five Position Management
components into one coherent subsystem.

This is the workhorse of M6.  It is NOT a public API;
PositionIntegrationEngine delegates to it.

C6 Execution Intelligence — Phase 3, Module 6
"""
from __future__ import annotations

import copy
import threading
import time
from decimal import Decimal
from typing import Any, Dict, List, Optional

from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin
from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger

from iios.execution.positions.lifecycle import PositionState
from iios.execution.positions.engine import PositionEngine
from iios.execution.positions.book import PositionBook
from iios.execution.positions.risk import PositionRiskManager
from iios.execution.positions.snapshot import PositionSnapshot, PositionSnapshotStore

from .constants import (
    ACTOR_MANAGER,
    ACTOR_SYSTEM,
    COMPONENT_BOOK,
    COMPONENT_ENGINE,
    COMPONENT_RISK,
    COMPONENT_SNAPSHOT,
    DEFAULT_MAX_CACHE_ENTRIES,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_POSITIONS,
    MANAGER_SYSTEM_ID,
    VERSION,
)
from .exceptions import (
    ComponentNotFoundError,
    IntegrationOperationError,
    IntegrationSnapshotError,
    PositionIntegrationNotRunningError,
)
from .position_component_factory import ComponentFactory
from .position_component_health import HealthReport
from .position_component_registry import ComponentRegistry
from .position_component_status import ComponentStatus
from .position_integration_events import (
    IntegrationEvent,
    make_component_failed_event,
    make_component_registered_event,
    make_snapshot_published_event,
    make_subsystem_initialized_event,
    make_subsystem_started_event,
    make_subsystem_stopped_event,
    make_validation_completed_event,
)
from .position_integration_history import IntegrationHistory
from .position_integration_request import (
    ArchivePositionIntegrationRequest,
    ClosePositionIntegrationRequest,
    CreatePositionIntegrationRequest,
    QueryPositionIntegrationRequest,
    SyncPositionIntegrationRequest,
    UpdatePositionIntegrationRequest,
)
from .position_integration_response import (
    IntegrationResponse,
    make_failure_response,
    make_success_response,
)
from .position_integration_snapshot import (
    PositionIntegrationSnapshot,
    make_integration_snapshot,
)
from .position_integration_statistics import IntegrationStatistics
from .position_integration_validation import IntegrationValidationResult, IntegrationValidator

_log   = get_logger(__name__, engine_id=MANAGER_SYSTEM_ID)
_audit = get_audit_logger(__name__, engine_id=MANAGER_SYSTEM_ID)


class PositionIntegrationManager(LifecycleAwareMixin):
    """
    Coordinates the four Position Management components to fulfil
    integration requests.

    Responsibilities
    ----------------
    * Start and stop all four components in the correct order.
    * Accept integration requests, delegate to PositionEngine,
      then sync PositionBook, PositionRiskManager, PositionSnapshotStore.
    * Build health reports, statistics, snapshots, and validation results.
    * Maintain bounded event history.

    Non-responsibilities
    --------------------
    * No business logic beyond coordination.
    * No position state-machine (owned by PositionEngine).
    * No risk evaluation logic (owned by PositionRiskManager).
    * No snapshot building logic (owned by PositionSnapshotStore).
    """

    def __init__(
        self,
        *,
        engine:         Optional[PositionEngine]         = None,
        book:           Optional[PositionBook]           = None,
        risk_manager:   Optional[PositionRiskManager]    = None,
        snapshot_store: Optional[PositionSnapshotStore]  = None,
        max_positions:  int = DEFAULT_MAX_POSITIONS,
        max_history:    int = DEFAULT_MAX_HISTORY,
        max_cache:      int = DEFAULT_MAX_CACHE_ENTRIES,
    ) -> None:
        super().__init__()

        _factory = ComponentFactory(
            max_positions=max_positions,
            max_history=max_history,
            max_cache=max_cache,
        )

        self._engine         = engine         or _factory.create_engine()
        self._book           = book           or _factory.create_book()
        self._risk_manager   = risk_manager   or _factory.create_risk_manager()
        self._snapshot_store = snapshot_store or _factory.create_snapshot_store()

        self._comp_registry = ComponentRegistry()
        self._validator     = IntegrationValidator()
        self._statistics    = IntegrationStatistics()
        self._history       = IntegrationHistory(max_events=max_history)
        self._lock          = threading.Lock()

    # ── LifecycleAwareMixin ───────────────────────────────────────────────────

    def _on_start(self) -> None:
        # Start components in dependency order
        self._engine.start()
        self._book.start()
        self._risk_manager.start()
        self._snapshot_store.start()

        # Register components
        self._comp_registry.register_engine(self._engine)
        self._comp_registry.register_book(self._book)
        self._comp_registry.register_risk(self._risk_manager)
        self._comp_registry.register_snapshot(self._snapshot_store)

        _audit.log_lifecycle_event(
            MANAGER_SYSTEM_ID, EngineState.STOPPED, EngineState.RUNNING, VERSION
        )
        _log.info("PositionIntegrationManager started.")

        self._history.append(make_subsystem_started_event(emitted_by=ACTOR_MANAGER))
        for name in [COMPONENT_ENGINE, COMPONENT_BOOK, COMPONENT_RISK, COMPONENT_SNAPSHOT]:
            self._history.append(
                make_component_registered_event(name, emitted_by=ACTOR_MANAGER)
            )

    def _on_stop(self) -> None:
        _audit.log_lifecycle_event(
            MANAGER_SYSTEM_ID, EngineState.RUNNING, EngineState.STOPPED, VERSION
        )
        _log.info(
            "PositionIntegrationManager stopped.",
            positions=self._engine.position_count,
            snapshots_published=self._statistics.snapshots_published,
        )
        self._history.append(make_subsystem_stopped_event(emitted_by=ACTOR_MANAGER))

        # Stop in reverse order
        self._snapshot_store.stop()
        self._risk_manager.stop()
        self._book.stop()
        self._engine.stop()

    def _assert_running(self) -> None:
        if self.lifecycle_state() != EngineState.RUNNING:
            raise PositionIntegrationNotRunningError()

    # ── Create ────────────────────────────────────────────────────────────────

    def create_position(
        self,
        request: CreatePositionIntegrationRequest,
    ) -> IntegrationResponse:
        self._assert_running()
        t0 = time.perf_counter()

        try:
            engine_req = request.to_engine_request()
            result     = self._engine.create_position(engine_req)

            if not result.succeeded:
                return make_failure_response(
                    request.operation_type,
                    result.error_message or "Engine create_position failed",
                    (time.perf_counter() - t0) * 1_000,
                    correlation_id=request.correlation_id,
                    errors=(result.error_message,) if result.error_message else (),
                )

            pos = result.position
            snap_dict: Optional[Dict[str, Any]] = None

            if pos is not None:
                # Sync: Book
                try:
                    self._book.add(pos)
                except Exception as exc:
                    _log.warning("Book.add failed — book may be out of sync.", error=str(exc))

                # Sync: Risk
                try:
                    self._risk_manager.register(pos, limits=request.risk_limits)
                except Exception as exc:
                    _log.warning("Risk.register failed.", error=str(exc))

                # Sync: Snapshot
                try:
                    snap = self._snapshot_store.build_and_store(
                        pos, auto_publish=request.auto_publish_snapshot
                    )
                    snap_dict = snap.to_dict()
                    if request.auto_publish_snapshot:
                        with self._lock:
                            self._statistics.record_snapshot_published()
                        self._history.append(
                            make_snapshot_published_event(
                                pos.position_id,
                                emitted_by=ACTOR_MANAGER,
                                correlation_id=request.correlation_id,
                            )
                        )
                except Exception as exc:
                    _log.warning("Snapshot.build_and_store failed.", error=str(exc))

                with self._lock:
                    self._statistics.record_position_managed()

            elapsed_ms = (time.perf_counter() - t0) * 1_000
            with self._lock:
                self._statistics.record_operation(elapsed_ms)

            return make_success_response(
                request.operation_type,
                result.position_id,
                "Position created",
                elapsed_ms,
                snapshot_dict=snap_dict,
                correlation_id=request.correlation_id,
            )

        except PositionIntegrationNotRunningError:
            raise
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - t0) * 1_000
            with self._lock:
                self._statistics.record_operation(elapsed_ms, failed=True)
            _log.error("create_position failed.", error=str(exc))
            return make_failure_response(
                request.operation_type,
                str(exc),
                elapsed_ms,
                correlation_id=request.correlation_id,
            )

    # ── Update ────────────────────────────────────────────────────────────────

    def update_position(
        self,
        request: UpdatePositionIntegrationRequest,
    ) -> IntegrationResponse:
        self._assert_running()
        t0 = time.perf_counter()

        try:
            result = self._engine.update_position(request.to_engine_request())

            snap_dict: Optional[Dict[str, Any]] = None
            if result.succeeded and result.position is not None:
                pos = result.position
                try:
                    self._book.update(pos.position_id)
                except Exception as exc:
                    _log.warning("Book.update failed.", error=str(exc))

                if request.auto_publish_snapshot:
                    try:
                        snap = self._snapshot_store.build_and_store(
                            pos, auto_publish=True
                        )
                        snap_dict = snap.to_dict()
                        with self._lock:
                            self._statistics.record_snapshot_published()
                        self._history.append(
                            make_snapshot_published_event(
                                pos.position_id, emitted_by=ACTOR_MANAGER
                            )
                        )
                    except Exception as exc:
                        _log.warning("Snapshot update failed.", error=str(exc))

            elapsed_ms = (time.perf_counter() - t0) * 1_000
            with self._lock:
                self._statistics.record_operation(elapsed_ms, failed=not result.succeeded)

            if result.succeeded:
                return make_success_response(
                    request.operation_type,
                    result.position_id,
                    "Position updated",
                    elapsed_ms,
                    snapshot_dict=snap_dict,
                    correlation_id=request.correlation_id,
                )
            return make_failure_response(
                request.operation_type,
                result.error_message or "Engine update failed",
                elapsed_ms,
                position_id=result.position_id,
                correlation_id=request.correlation_id,
            )

        except PositionIntegrationNotRunningError:
            raise
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - t0) * 1_000
            with self._lock:
                self._statistics.record_operation(elapsed_ms, failed=True)
            return make_failure_response(
                request.operation_type, str(exc), elapsed_ms,
                correlation_id=request.correlation_id,
            )

    # ── Close ─────────────────────────────────────────────────────────────────

    def close_position(
        self,
        request: ClosePositionIntegrationRequest,
    ) -> IntegrationResponse:
        self._assert_running()
        t0 = time.perf_counter()

        try:
            # Capture old lifecycle state for book index update
            old_state: Optional[PositionState] = None
            try:
                pos = self._engine.get_position(request.position_id)
                if pos is not None:
                    old_state = pos.state
            except Exception:
                pass

            result = self._engine.close_position(request.to_engine_request())

            snap_dict: Optional[Dict[str, Any]] = None
            if result.succeeded and result.position is not None:
                pos = result.position

                # Book
                try:
                    if old_state is not None:
                        self._book.notify_state_changed(pos.position_id, old_state)
                    else:
                        self._book.update(pos.position_id)
                except Exception as exc:
                    _log.warning("Book.notify_state_changed failed on close.", error=str(exc))

                # Snapshot — always publish on close
                try:
                    snap = self._snapshot_store.build_and_store(pos, auto_publish=True)
                    snap_dict = snap.to_dict()
                    with self._lock:
                        self._statistics.record_snapshot_published()
                        self._statistics.record_position_closed()
                    self._history.append(
                        make_snapshot_published_event(
                            pos.position_id, emitted_by=ACTOR_MANAGER
                        )
                    )
                except Exception as exc:
                    _log.warning("Snapshot on close failed.", error=str(exc))
                    with self._lock:
                        self._statistics.record_position_closed()

            elapsed_ms = (time.perf_counter() - t0) * 1_000
            with self._lock:
                self._statistics.record_operation(elapsed_ms, failed=not result.succeeded)

            if result.succeeded:
                return make_success_response(
                    request.operation_type,
                    result.position_id,
                    "Position closed",
                    elapsed_ms,
                    snapshot_dict=snap_dict,
                    correlation_id=request.correlation_id,
                )
            return make_failure_response(
                request.operation_type,
                result.error_message or "Engine close failed",
                elapsed_ms,
                position_id=result.position_id,
                correlation_id=request.correlation_id,
            )

        except PositionIntegrationNotRunningError:
            raise
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - t0) * 1_000
            with self._lock:
                self._statistics.record_operation(elapsed_ms, failed=True)
            return make_failure_response(
                request.operation_type, str(exc), elapsed_ms,
                correlation_id=request.correlation_id,
            )

    # ── Sync ──────────────────────────────────────────────────────────────────

    def sync_position(
        self,
        request: SyncPositionIntegrationRequest,
    ) -> IntegrationResponse:
        self._assert_running()
        t0 = time.perf_counter()

        try:
            result = self._engine.sync_position(request.to_engine_request())
            snap_dict: Optional[Dict[str, Any]] = None

            if result.succeeded and result.position is not None:
                pos = result.position
                try:
                    self._book.update(pos.position_id)
                except Exception as exc:
                    _log.warning("Book.update failed on sync.", error=str(exc))

                if request.auto_publish_snapshot:
                    try:
                        snap = self._snapshot_store.build_and_store(pos, auto_publish=True)
                        snap_dict = snap.to_dict()
                        with self._lock:
                            self._statistics.record_snapshot_published()
                    except Exception as exc:
                        _log.warning("Snapshot on sync failed.", error=str(exc))

            elapsed_ms = (time.perf_counter() - t0) * 1_000
            with self._lock:
                self._statistics.record_operation(elapsed_ms, failed=not result.succeeded)

            if result.succeeded:
                return make_success_response(
                    request.operation_type,
                    result.position_id,
                    "Position synced",
                    elapsed_ms,
                    snapshot_dict=snap_dict,
                    correlation_id=request.correlation_id,
                )
            return make_failure_response(
                request.operation_type,
                result.error_message or "Engine sync failed",
                elapsed_ms,
                position_id=result.position_id,
                correlation_id=request.correlation_id,
            )

        except PositionIntegrationNotRunningError:
            raise
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - t0) * 1_000
            with self._lock:
                self._statistics.record_operation(elapsed_ms, failed=True)
            return make_failure_response(
                request.operation_type, str(exc), elapsed_ms,
                correlation_id=request.correlation_id,
            )

    # ── Archive ───────────────────────────────────────────────────────────────

    def archive_position(
        self,
        request: ArchivePositionIntegrationRequest,
    ) -> IntegrationResponse:
        self._assert_running()
        t0 = time.perf_counter()

        try:
            old_state: Optional[PositionState] = None
            try:
                pos = self._engine.get_position(request.position_id)
                if pos is not None:
                    old_state = pos.state
            except Exception:
                pass

            result = self._engine.archive_position(request.to_engine_request())
            snap_dict: Optional[Dict[str, Any]] = None

            if result.succeeded and result.position is not None:
                pos = result.position
                try:
                    if old_state is not None:
                        self._book.notify_state_changed(pos.position_id, old_state)
                    else:
                        self._book.update(pos.position_id)
                except Exception as exc:
                    _log.warning("Book.notify_state_changed failed on archive.", error=str(exc))

                if request.auto_publish_snapshot:
                    try:
                        snap = self._snapshot_store.build_and_store(pos, auto_publish=True)
                        snap_dict = snap.to_dict()
                        with self._lock:
                            self._statistics.record_snapshot_published()
                    except Exception as exc:
                        _log.warning("Snapshot on archive failed.", error=str(exc))

                with self._lock:
                    self._statistics.record_position_archived()

            elapsed_ms = (time.perf_counter() - t0) * 1_000
            with self._lock:
                self._statistics.record_operation(elapsed_ms, failed=not result.succeeded)

            if result.succeeded:
                return make_success_response(
                    request.operation_type,
                    result.position_id,
                    "Position archived",
                    elapsed_ms,
                    snapshot_dict=snap_dict,
                    correlation_id=request.correlation_id,
                )
            return make_failure_response(
                request.operation_type,
                result.error_message or "Engine archive failed",
                elapsed_ms,
                position_id=result.position_id,
                correlation_id=request.correlation_id,
            )

        except PositionIntegrationNotRunningError:
            raise
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - t0) * 1_000
            with self._lock:
                self._statistics.record_operation(elapsed_ms, failed=True)
            return make_failure_response(
                request.operation_type, str(exc), elapsed_ms,
                correlation_id=request.correlation_id,
            )

    # ── Query ─────────────────────────────────────────────────────────────────

    def query(
        self,
        request: QueryPositionIntegrationRequest,
    ) -> IntegrationResponse:
        self._assert_running()
        t0 = time.perf_counter()

        try:
            positions = []
            if request.position_id:
                pos = self._engine.get_position(request.position_id)
                if pos is not None:
                    positions = [pos]
            elif request.portfolio_id:
                positions = self._engine.positions_by_portfolio(request.portfolio_id)
            elif request.strategy_id:
                positions = self._engine.positions_by_strategy(request.strategy_id)
            elif request.instrument:
                positions = [
                    p for p in self._engine.all_positions()
                    if p.instrument == request.instrument
                ]
            else:
                # Default: active
                if request.include_active:
                    positions.extend(self._engine.active_positions())
                if request.include_closed:
                    positions.extend(self._engine.closed_positions())
                if request.include_archived:
                    positions.extend(self._engine.archived_positions())

            positions = positions[:request.limit]

            elapsed_ms = (time.perf_counter() - t0) * 1_000
            with self._lock:
                self._statistics.record_operation(elapsed_ms)

            return make_success_response(
                request.operation_type,
                request.position_id,
                f"Query returned {len(positions)} position(s)",
                elapsed_ms,
                data={"position_ids": [p.position_id for p in positions],
                      "count":        len(positions)},
                correlation_id=request.correlation_id,
            )

        except PositionIntegrationNotRunningError:
            raise
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - t0) * 1_000
            with self._lock:
                self._statistics.record_operation(elapsed_ms, failed=True)
            return make_failure_response(
                request.operation_type, str(exc), elapsed_ms,
                correlation_id=request.correlation_id,
            )

    # ── Snapshot publication ──────────────────────────────────────────────────

    def publish_snapshot(self, position_id: str) -> Optional[PositionSnapshot]:
        """
        Explicitly publish the latest snapshot for a position.

        Returns the published ``PositionSnapshot``, or ``None`` if
        the position does not have a stored snapshot yet.
        """
        self._assert_running()
        latest = self._snapshot_store.get_latest(position_id)
        if latest is None:
            return None
        published = self._snapshot_store.publish(latest.snapshot_id)
        with self._lock:
            self._statistics.record_snapshot_published()
        self._history.append(
            make_snapshot_published_event(position_id, emitted_by=ACTOR_MANAGER)
        )
        return published

    # ── Subsystem snapshot ────────────────────────────────────────────────────

    def snapshot(self) -> PositionIntegrationSnapshot:
        """Build and return an immutable subsystem-level snapshot."""
        self._assert_running()
        try:
            engine_snap_dict: Dict[str, Any] = {}
            book_snap_dict:   Dict[str, Any] = {}
            risk_snap_dict:   Dict[str, Any] = {}
            bundle_dict:      Dict[str, Any] = {}

            try:
                engine_snap = self._engine.snapshot()
                engine_snap_dict = engine_snap.to_dict()
            except Exception as exc:
                _log.warning("Engine snapshot failed.", error=str(exc))

            try:
                book_snap = self._book.snapshot()
                book_snap_dict = book_snap.to_dict()
            except Exception as exc:
                _log.warning("Book snapshot failed.", error=str(exc))

            try:
                from iios.execution.positions.risk import make_risk_book_snapshot
                risk_snap = make_risk_book_snapshot(
                    self._risk_manager._registry.all_states()
                )
                risk_snap_dict = risk_snap.to_dict()
            except Exception as exc:
                _log.warning("Risk snapshot failed.", error=str(exc))

            try:
                bundle     = self._snapshot_store.bundle_all()
                bundle_dict = bundle.to_dict()
            except Exception as exc:
                _log.warning("Snapshot bundle failed.", error=str(exc))

            health_report  = self._comp_registry.health_report()
            stats_snapshot = self.statistics()

            # Health summary per component
            health_summary: Dict[str, str] = {}
            for comp_name, comp_data in health_report.components.items():
                health_summary[comp_name] = comp_data.get("status", "UNKNOWN")

            return make_integration_snapshot(
                engine_snapshot=engine_snap_dict,
                book_snapshot=book_snap_dict,
                risk_snapshot=risk_snap_dict,
                position_snapshots=bundle_dict,
                health=health_report.to_dict(),
                statistics=stats_snapshot.to_dict(),
                position_count=self._engine.position_count,
                published_snapshot_count=self._snapshot_store.count(),
                active_position_count=len(self._engine.active_positions()),
                component_health_summary=health_summary,
            )

        except PositionIntegrationNotRunningError:
            raise
        except Exception as exc:
            raise IntegrationSnapshotError(
                f"Failed to build integration snapshot: {exc}"
            ) from exc

    # ── Health ────────────────────────────────────────────────────────────────

    def health(self) -> HealthReport:
        """Return the current health report for all components."""
        report = self._comp_registry.health_report()
        with self._lock:
            self._statistics.record_health_check(report.overall_status)
        return report

    # ── Status ────────────────────────────────────────────────────────────────

    def status(self) -> List[ComponentStatus]:
        """Return per-component status records."""
        return self._comp_registry.all_statuses()

    # ── Validate ─────────────────────────────────────────────────────────────

    def validate(self) -> IntegrationValidationResult:
        """Run all integration validation checks."""
        result = self._validator.validate(
            registry=self._comp_registry,
            engine=self._engine,
            book=self._book,
            risk_manager=self._risk_manager,
            snapshot_store=self._snapshot_store,
            history=self._history,
        )
        with self._lock:
            if result.is_valid:
                self._statistics.record_validation_success()
            else:
                self._statistics.record_validation_failure()
        self._history.append(
            make_validation_completed_event(
                result.is_valid, emitted_by=ACTOR_MANAGER
            )
        )
        return result

    # ── Statistics & history ──────────────────────────────────────────────────

    def statistics(self) -> IntegrationStatistics:
        with self._lock:
            return copy.copy(self._statistics)

    def history(self) -> IntegrationHistory:
        return self._history

    def events(self) -> List[IntegrationEvent]:
        return self._history.all()
