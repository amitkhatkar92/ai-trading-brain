"""iios/execution/positions/integration/position_integration_engine.py
==================================================
PositionIntegrationEngine — the ONLY public interface to the
IIOS Position Management subsystem.

This is the primary facade.  All external callers (Execution Risk,
Recovery, Monitoring, Analytics, Compliance, Reporting) MUST
interact with Position Management exclusively through this class.

C6 Execution Intelligence — Phase 3, Module 6
"""
from __future__ import annotations

import threading
from decimal import Decimal
from typing import Any, Dict, List, Optional

from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin
from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger

from iios.execution.positions.engine import PositionEngine
from iios.execution.positions.book import PositionBook
from iios.execution.positions.risk import PositionRiskManager
from iios.execution.positions.snapshot import PositionSnapshot, PositionSnapshotStore

from .constants import (
    DEFAULT_MAX_CACHE_ENTRIES,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_POSITIONS,
    INTEGRATION_SYSTEM_ID,
    VERSION,
)
from .exceptions import PositionIntegrationNotRunningError
from .position_component_health import HealthReport
from .position_component_status import ComponentStatus
from .position_integration_events import IntegrationEvent
from .position_integration_history import IntegrationHistory
from .position_integration_manager import PositionIntegrationManager
from .position_integration_request import (
    ArchivePositionIntegrationRequest,
    ClosePositionIntegrationRequest,
    CreatePositionIntegrationRequest,
    QueryPositionIntegrationRequest,
    SyncPositionIntegrationRequest,
    UpdatePositionIntegrationRequest,
)
from .position_integration_response import IntegrationResponse
from .position_integration_snapshot import PositionIntegrationSnapshot
from .position_integration_statistics import IntegrationStatistics
from .position_integration_validation import IntegrationValidationResult

_log   = get_logger(__name__, engine_id=INTEGRATION_SYSTEM_ID)
_audit = get_audit_logger(__name__, engine_id=INTEGRATION_SYSTEM_ID)


class PositionIntegrationEngine(LifecycleAwareMixin):
    """
    Primary public entry point for the IIOS Position Management subsystem.

    ┌─────────────────────────────────────────────────┐
    │           PositionIntegrationEngine             │
    │  (the ONLY public interface to positions)       │
    ├─────────┬────────────┬────────────┬─────────────┤
    │ Engine  │    Book    │    Risk    │  Snapshot   │
    │  (M2)   │    (M3)    │    (M4)   │    (M5)     │
    └─────────┴────────────┴────────────┴─────────────┘

    Responsibilities
    ----------------
    * Provide the single integration facade over all 4 components.
    * Expose create / update / close / sync / archive / query operations.
    * Provide health, status, statistics, snapshot, history, validate.

    Non-responsibilities
    --------------------
    * No position logic (owned by PositionEngine).
    * No portfolio logic.
    * No trading decisions.
    * No broker connectivity.

    Usage
    -----
    engine = PositionIntegrationEngine()
    engine.start()

    resp = engine.create_position(
        CreatePositionIntegrationRequest(
            instrument="NIFTY50", exchange="NSE",
            product=PositionProduct.FUTURES,
            direction=PositionDirection.LONG,
            quantity=Decimal("100"),
            portfolio_id="port-001",
            strategy_id="momentum-v2",
        )
    )
    assert resp.succeeded

    snap = engine.snapshot()
    health = engine.health()

    engine.stop()
    """

    def __init__(
        self,
        *,
        manager:       Optional[PositionIntegrationManager] = None,
        engine:        Optional[PositionEngine]             = None,
        book:          Optional[PositionBook]               = None,
        risk_manager:  Optional[PositionRiskManager]        = None,
        snapshot_store: Optional[PositionSnapshotStore]     = None,
        max_positions: int = DEFAULT_MAX_POSITIONS,
        max_history:   int = DEFAULT_MAX_HISTORY,
        max_cache:     int = DEFAULT_MAX_CACHE_ENTRIES,
    ) -> None:
        super().__init__()
        self._manager = manager or PositionIntegrationManager(
            engine=engine,
            book=book,
            risk_manager=risk_manager,
            snapshot_store=snapshot_store,
            max_positions=max_positions,
            max_history=max_history,
            max_cache=max_cache,
        )

    # ── LifecycleAwareMixin ───────────────────────────────────────────────────

    def _on_start(self) -> None:
        self._manager.start()
        _audit.log_lifecycle_event(
            INTEGRATION_SYSTEM_ID, EngineState.STOPPED, EngineState.RUNNING, VERSION
        )
        _log.info("PositionIntegrationEngine started.", version=VERSION)

    def _on_stop(self) -> None:
        _audit.log_lifecycle_event(
            INTEGRATION_SYSTEM_ID, EngineState.RUNNING, EngineState.STOPPED, VERSION
        )
        _log.info("PositionIntegrationEngine stopped.")
        self._manager.stop()

    def _assert_running(self) -> None:
        if self.lifecycle_state() != EngineState.RUNNING:
            raise PositionIntegrationNotRunningError()

    # ── Spec public API: initialize / start / stop ────────────────────────────

    def initialize(self) -> None:
        """
        Initialize the integration engine.

        May be called before :meth:`start` to eagerly validate that
        all dependencies are importable.  Is idempotent if already started.
        """
        if self.lifecycle_state() != EngineState.RUNNING:
            self.start()

    # ── Position operations ───────────────────────────────────────────────────

    def create_position(
        self,
        request: CreatePositionIntegrationRequest,
    ) -> IntegrationResponse:
        """
        Create a new managed position.

        Coordinates: PositionEngine → PositionBook → PositionRiskManager
        → PositionSnapshotStore.

        Raises
        ------
        PositionIntegrationNotRunningError
        """
        self._assert_running()
        return self._manager.create_position(request)

    def update_position(
        self,
        request: UpdatePositionIntegrationRequest,
    ) -> IntegrationResponse:
        """Update a position's fields and/or lifecycle state."""
        self._assert_running()
        return self._manager.update_position(request)

    def close_position(
        self,
        request: ClosePositionIntegrationRequest,
    ) -> IntegrationResponse:
        """Close a position and publish a final snapshot."""
        self._assert_running()
        return self._manager.close_position(request)

    def sync_position(
        self,
        request: SyncPositionIntegrationRequest,
    ) -> IntegrationResponse:
        """Synchronize execution data into a position."""
        self._assert_running()
        return self._manager.sync_position(request)

    def archive_position(
        self,
        request: ArchivePositionIntegrationRequest,
    ) -> IntegrationResponse:
        """Archive a CLOSED position."""
        self._assert_running()
        return self._manager.archive_position(request)

    # ── Spec public API: query ────────────────────────────────────────────────

    def query(
        self,
        request: QueryPositionIntegrationRequest,
    ) -> IntegrationResponse:
        """
        Query positions.

        Supports lookup by position_id, portfolio, strategy, or instrument.
        Defaults to returning all active positions if no filter is set.

        Raises
        ------
        PositionIntegrationNotRunningError
        """
        self._assert_running()
        return self._manager.query(request)

    # ── Snapshot publication ──────────────────────────────────────────────────

    def publish_snapshot(self, position_id: str) -> Optional[PositionSnapshot]:
        """
        Explicitly publish the latest snapshot for *position_id*.

        Returns the published :class:`PositionSnapshot`, or ``None``
        if no snapshot exists yet.

        Raises
        ------
        PositionIntegrationNotRunningError
        """
        self._assert_running()
        return self._manager.publish_snapshot(position_id)

    # ── Spec public API: health ───────────────────────────────────────────────

    def health(self) -> HealthReport:
        """
        Return a :class:`HealthReport` covering all four components.

        Raises
        ------
        PositionIntegrationNotRunningError
        """
        self._assert_running()
        return self._manager.health()

    # ── Spec public API: status ───────────────────────────────────────────────

    def status(self) -> List[ComponentStatus]:
        """
        Return per-component :class:`ComponentStatus` records.

        Raises
        ------
        PositionIntegrationNotRunningError
        """
        self._assert_running()
        return self._manager.status()

    # ── Spec public API: statistics ───────────────────────────────────────────

    def statistics(self) -> IntegrationStatistics:
        """
        Return a copy of current :class:`IntegrationStatistics`.

        Raises
        ------
        PositionIntegrationNotRunningError
        """
        self._assert_running()
        return self._manager.statistics()

    # ── Spec public API: snapshot ─────────────────────────────────────────────

    def snapshot(self) -> PositionIntegrationSnapshot:
        """
        Build and return an immutable :class:`PositionIntegrationSnapshot`
        of the entire Position Management subsystem.

        Raises
        ------
        PositionIntegrationNotRunningError
        IntegrationSnapshotError
        """
        self._assert_running()
        return self._manager.snapshot()

    # ── Spec public API: history ──────────────────────────────────────────────

    def history(self) -> IntegrationHistory:
        """
        Return the subsystem event history.

        Raises
        ------
        PositionIntegrationNotRunningError
        """
        self._assert_running()
        return self._manager.history()

    def events(self) -> List[IntegrationEvent]:
        """Return all emitted integration events as a list."""
        self._assert_running()
        return self._manager.events()

    # ── Spec public API: validate ─────────────────────────────────────────────

    def validate(self) -> IntegrationValidationResult:
        """
        Run all integration validation checks and return the result.

        Raises
        ------
        PositionIntegrationNotRunningError
        """
        self._assert_running()
        return self._manager.validate()

    # ── Convenience accessors ─────────────────────────────────────────────────

    @property
    def position_count(self) -> int:
        """Total number of managed positions."""
        return self._manager._engine.position_count

    @property
    def is_empty(self) -> bool:
        return self._manager._engine.is_empty
