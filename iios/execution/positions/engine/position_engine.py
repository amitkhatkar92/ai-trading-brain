"""iios/execution/positions/engine/position_engine.py
==================================================
PositionEngine — the primary public entry point to the IIOS
Position Engine.

Coordinates all position operations (create / update / close /
sync / archive / query), delegates to PositionManager, and
exposes a clean facade to higher layers.

C6 Execution Intelligence — Phase 3, Module 2
"""
from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional

from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin
from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger

from iios.execution.positions.lifecycle import Position, PositionState

from .constants import (
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_POSITIONS,
    ENGINE_SYSTEM_ID,
    VERSION,
)
from .exceptions import PositionEngineNotRunningError
from .position_events import EngineEvent
from .position_history import EngineHistory
from .position_manager import PositionManager
from .position_request import (
    ArchivePositionRequest,
    ClosePositionRequest,
    CreatePositionRequest,
    QueryPositionRequest,
    SyncPositionRequest,
    UpdatePositionRequest,
)
from .position_result import PositionResult
from .position_snapshot import EngineSnapshot
from .position_statistics import EngineStatistics

_log   = get_logger(__name__, engine_id=ENGINE_SYSTEM_ID)
_audit = get_audit_logger(__name__, engine_id=ENGINE_SYSTEM_ID)


class PositionEngine(LifecycleAwareMixin):
    """
    Primary public entry point for Position Engine operations.

    Usage
    -----
    engine = PositionEngine()
    engine.start()

    request = CreatePositionRequest(
        instrument="NIFTY50", exchange="NSE",
        product=PositionProduct.FUTURES,
        direction=PositionDirection.LONG,
        quantity=Decimal("100"),
        portfolio_id="port-001",
        strategy_id="momentum-v2",
    )
    result = engine.create_position(request)
    assert result.succeeded

    engine.stop()

    Responsibilities
    ----------------
    * Lifecycle management (start / stop).
    * Single facade over PositionManager.
    * No business logic beyond delegation and guard checks.
    """

    def __init__(
        self,
        *,
        manager:       Optional[PositionManager] = None,
        max_positions: int = DEFAULT_MAX_POSITIONS,
        max_history:   int = DEFAULT_MAX_HISTORY,
    ) -> None:
        super().__init__()
        self._manager = manager or PositionManager(
            max_positions=max_positions,
            max_history=max_history,
        )

    # ── LifecycleAwareMixin ───────────────────────────────────────────────────

    def _on_start(self) -> None:
        self._manager.start()
        _audit.log_lifecycle_event(ENGINE_SYSTEM_ID, EngineState.STOPPED, EngineState.RUNNING, VERSION)
        _log.info("PositionEngine started.", version=VERSION)

    def _on_stop(self) -> None:
        _audit.log_lifecycle_event(ENGINE_SYSTEM_ID, EngineState.RUNNING, EngineState.STOPPED, VERSION)
        _log.info(
            "PositionEngine stopped.",
            positions=self._manager.registry.count,
        )
        self._manager.stop()

    # ── Primary operations ────────────────────────────────────────────────────

    def create_position(self, request: CreatePositionRequest) -> PositionResult:
        """Create a new position and register it in the engine."""
        self._assert_running()
        return self._manager.create_position(request)

    def update_position(self, request: UpdatePositionRequest) -> PositionResult:
        """Update fields and/or lifecycle state of an existing position."""
        self._assert_running()
        return self._manager.update_position(request)

    def close_position(self, request: ClosePositionRequest) -> PositionResult:
        """Close a position (drives to CLOSED lifecycle state)."""
        self._assert_running()
        return self._manager.close_position(request)

    def sync_position(self, request: SyncPositionRequest) -> PositionResult:
        """Synchronize execution data into an existing position."""
        self._assert_running()
        return self._manager.sync_position(request)

    def archive_position(self, request: ArchivePositionRequest) -> PositionResult:
        """Archive a CLOSED position (transitions to ARCHIVED)."""
        self._assert_running()
        return self._manager.archive_position(request)

    def query_position(self, request: QueryPositionRequest) -> PositionResult:
        """Query one or more positions."""
        self._assert_running()
        return self._manager.query_position(request)

    # ── Inspection ────────────────────────────────────────────────────────────

    def snapshot(self) -> EngineSnapshot:
        """Return a full point-in-time snapshot of the engine."""
        self._assert_running()
        return self._manager.snapshot()

    def statistics(self) -> EngineStatistics:
        """Return a copy of current engine statistics."""
        return self._manager.statistics()

    def history(self) -> EngineHistory:
        """Return the engine operation history."""
        return self._manager.history()

    def events(self) -> List[EngineEvent]:
        """Return all engine events emitted since start."""
        return self._manager.events()

    # ── Position access ───────────────────────────────────────────────────────

    def get_position(self, position_id: str) -> Optional[Position]:
        """Return a position by ID, or None if not found."""
        return self._manager.registry.get(position_id)

    def require_position(self, position_id: str) -> Position:
        """Return a position by ID; raises PositionNotFoundError if absent."""
        return self._manager.registry.require(position_id)

    def active_positions(self) -> List[Position]:
        """All positions in an active lifecycle state."""
        return self._manager.registry.active()

    def closed_positions(self) -> List[Position]:
        """All positions in CLOSED or ARCHIVED state."""
        return self._manager.registry.closed()

    def archived_positions(self) -> List[Position]:
        """All positions in the terminal ARCHIVED state."""
        return self._manager.registry.archived()

    def all_positions(self) -> List[Position]:
        """All registered positions."""
        return self._manager.registry.all()

    def positions_by_portfolio(self, portfolio_id: str) -> List[Position]:
        return self._manager.registry.by_portfolio(portfolio_id)

    def positions_by_strategy(self, strategy_id: str) -> List[Position]:
        return self._manager.registry.by_strategy(strategy_id)

    # ── Counters ──────────────────────────────────────────────────────────────

    @property
    def position_count(self) -> int:
        return self._manager.registry.count

    @property
    def is_empty(self) -> bool:
        return self._manager.registry.is_empty

    # ── Internal ─────────────────────────────────────────────────────────────

    def _assert_running(self) -> None:
        if self.lifecycle_state() != EngineState.RUNNING:
            raise PositionEngineNotRunningError()
