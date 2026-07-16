"""iios/execution/positions/lifecycle/position_registry.py
==================================================
PositionRegistry — LifecycleAwareMixin registry of Position objects.

Thread-safe storage and retrieval with filtering helpers.
Aggregates statistics across all registered positions.

C6 Execution Intelligence — Phase 3, Module 1
"""
from __future__ import annotations

import threading
from typing import Iterator, List, Optional

from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin
from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger

from .constants import (
    ACTIVE_STATES,
    CLOSED_STATES,
    DEFAULT_MAX_POSITIONS,
    REGISTRY_SYSTEM_ID,
    TERMINAL_STATES,
    VERSION,
    PositionState,
)
from .exceptions import (
    DuplicatePositionError,
    PositionNotFoundError,
    PositionNotRunningError,
    PositionRegistryCapacityError,
)
from .position import Position
from .position_statistics import PositionStatistics

_log   = get_logger(__name__, engine_id=REGISTRY_SYSTEM_ID)
_audit = get_audit_logger(__name__, engine_id=REGISTRY_SYSTEM_ID)


class PositionRegistry(LifecycleAwareMixin):
    """
    Thread-safe registry for ``Position`` objects.

    The registry must be started before any write operations.
    Read operations (``get``, ``all``, filters) are permitted
    regardless of lifecycle state to allow inspection after shutdown.

    Positions are keyed by ``position_id``.
    """

    def __init__(self, max_positions: int = DEFAULT_MAX_POSITIONS) -> None:
        super().__init__()
        self._max        = max(1, max_positions)
        self._store:     dict[str, Position]  = {}
        self._stats                           = PositionStatistics()
        self._lock                            = threading.Lock()

    # ── LifecycleAwareMixin ───────────────────────────────────────────────────

    def _on_start(self) -> None:
        _audit.log_lifecycle_event(REGISTRY_SYSTEM_ID, EngineState.STOPPED, EngineState.RUNNING, VERSION)
        _log.info("PositionRegistry started.", max_positions=self._max)

    def _on_stop(self) -> None:
        _audit.log_lifecycle_event(REGISTRY_SYSTEM_ID, EngineState.RUNNING, EngineState.STOPPED, VERSION)
        _log.info(
            "PositionRegistry stopped.",
            position_count=len(self._store),
        )

    # ── Write ─────────────────────────────────────────────────────────────────

    def register(self, position: Position) -> None:
        """
        Register *position* in the registry.

        Raises
        ------
        PositionNotRunningError
            If the registry has not been started.
        PositionRegistryCapacityError
            If the registry is at maximum capacity.
        DuplicatePositionError
            If a position with the same ``position_id`` already exists.
        """
        self._assert_running()
        with self._lock:
            if len(self._store) >= self._max:
                raise PositionRegistryCapacityError(self._max)
            pid = position.position_id
            if pid in self._store:
                raise DuplicatePositionError(pid)
            self._store[pid] = position
            self._stats.record_created(position.quantity)

        _log.info(
            "Position registered.",
            position_id=position.position_id,
            instrument=position.instrument,
            direction=position.direction.value,
            state=position.state.value,
        )

    def deregister(self, position_id: str) -> None:
        """
        Remove a position from the registry.

        Raises ``PositionNotFoundError`` if not present.
        """
        self._assert_running()
        with self._lock:
            if position_id not in self._store:
                raise PositionNotFoundError(position_id)
            del self._store[position_id]

        _log.info("Position deregistered.", position_id=position_id)

    # ── Read ──────────────────────────────────────────────────────────────────

    def get(self, position_id: str) -> Optional[Position]:
        """Return the position or ``None`` if not found."""
        with self._lock:
            return self._store.get(position_id)

    def require(self, position_id: str) -> Position:
        """Return the position or raise ``PositionNotFoundError``."""
        with self._lock:
            pos = self._store.get(position_id)
        if pos is None:
            raise PositionNotFoundError(position_id)
        return pos

    def contains(self, position_id: str) -> bool:
        with self._lock:
            return position_id in self._store

    # ── Filtering ─────────────────────────────────────────────────────────────

    def all(self) -> List[Position]:
        """All registered positions."""
        with self._lock:
            return list(self._store.values())

    def by_state(self, state: PositionState) -> List[Position]:
        """Positions in the given *state*."""
        with self._lock:
            return [p for p in self._store.values() if p.state == state]

    def by_portfolio(self, portfolio_id: str) -> List[Position]:
        """Positions belonging to *portfolio_id*."""
        with self._lock:
            return [p for p in self._store.values() if p.portfolio_id == portfolio_id]

    def by_strategy(self, strategy_id: str) -> List[Position]:
        """Positions belonging to *strategy_id*."""
        with self._lock:
            return [p for p in self._store.values() if p.strategy_id == strategy_id]

    def by_instrument(self, instrument: str) -> List[Position]:
        """Positions on the given *instrument*."""
        with self._lock:
            return [p for p in self._store.values() if p.instrument == instrument]

    def active(self) -> List[Position]:
        """Positions in any active state (OPENING / OPEN / PARTIALLY_CLOSED / CLOSING)."""
        with self._lock:
            return [p for p in self._store.values() if p.state in ACTIVE_STATES]

    def closed(self) -> List[Position]:
        """Positions in CLOSED or ARCHIVED state."""
        with self._lock:
            return [p for p in self._store.values() if p.state in CLOSED_STATES]

    def archived(self) -> List[Position]:
        """Positions in the terminal ARCHIVED state."""
        with self._lock:
            return [p for p in self._store.values() if p.state in TERMINAL_STATES]

    def suspended(self) -> List[Position]:
        """Positions in SUSPENDED / RECOVERING / RECOVERED state."""
        with self._lock:
            from .constants import SUSPENDED_STATES
            return [p for p in self._store.values() if p.state in SUSPENDED_STATES]

    # ── Counters ──────────────────────────────────────────────────────────────

    @property
    def count(self) -> int:
        """Total number of registered positions."""
        with self._lock:
            return len(self._store)

    @property
    def is_empty(self) -> bool:
        with self._lock:
            return len(self._store) == 0

    # ── Statistics ────────────────────────────────────────────────────────────

    def notify_transition(
        self,
        to_state: PositionState,
        *,
        holding_time_ms: float = 0.0,
        is_recovery: bool = False,
    ) -> None:
        """
        Called by external code (e.g. an engine) after a successful
        ``Position.transition_to()`` to keep statistics current.
        """
        with self._lock:
            self._stats.record_transition(is_recovery=is_recovery)
            if to_state == PositionState.OPEN:
                self._stats.record_opened()
            elif to_state == PositionState.PARTIALLY_CLOSED:
                self._stats.record_partially_closed()
            elif to_state == PositionState.CLOSED:
                self._stats.record_closed(holding_time_ms=holding_time_ms)
            elif to_state == PositionState.ARCHIVED:
                self._stats.record_archived()
            elif to_state == PositionState.SUSPENDED:
                self._stats.record_suspended()
            elif to_state == PositionState.RECOVERED:
                self._stats.record_recovered()

    def statistics(self) -> PositionStatistics:
        """Return a shallow copy of the current statistics."""
        with self._lock:
            import copy
            return copy.copy(self._stats)

    # ── Iteration ─────────────────────────────────────────────────────────────

    def __iter__(self) -> Iterator[Position]:
        with self._lock:
            return iter(list(self._store.values()))

    def __len__(self) -> int:
        return self.count

    # ── Internal ─────────────────────────────────────────────────────────────

    def _assert_running(self) -> None:
        if self.lifecycle_state() != EngineState.RUNNING:
            raise PositionNotRunningError()
