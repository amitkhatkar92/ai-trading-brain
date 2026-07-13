"""iios/investment/strategy/lifecycle/runtime_manager.py
Runtime lifecycle controller for the strategy execution engine.

Manages the start / stop / pause / resume / restart lifecycle of the engine
and coordinates all subsystems through RuntimeState transitions.
"""
from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from typing import Callable, List, Optional

from iios.investment.strategy.lifecycle.runtime_context import RuntimeContext
from iios.investment.strategy.lifecycle.runtime_state import (
    RuntimeState,
    RuntimeStateSnapshot,
    validate_runtime_transition,
)
from iios.investment.strategy.lifecycle.runtime_statistics import RuntimeStatistics

logger = logging.getLogger(__name__)


class RuntimeManagerError(Exception):
    """Raised for invalid runtime operations."""


class RuntimeManager:
    """
    Controls the engine runtime state machine.

    Responsibilities:
    - Validate and apply state transitions (IDLE → INITIALIZING → RUNNING → …)
    - Broadcast state-change callbacks to registered listeners
    - Expose uptime, cycle statistics, and context factories
    - Support graceful shutdown with in-flight drain
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._state = RuntimeState.IDLE
        self._started_at: Optional[datetime] = None
        self._paused_at: Optional[datetime] = None
        self._statistics = RuntimeStatistics()
        self._listeners: List[Callable[[RuntimeState, RuntimeState], None]] = []

    # ── Listener API ──────────────────────────────────────────────────────────

    def add_state_listener(
        self,
        listener: Callable[[RuntimeState, RuntimeState], None],
    ) -> None:
        """Register a callback invoked on every state transition.

        The callback receives (from_state, to_state).
        Exceptions in listeners are caught and logged; they do not abort
        the transition.
        """
        with self._lock:
            self._listeners.append(listener)

    # ── Control API ───────────────────────────────────────────────────────────

    def start(self) -> None:
        """Transition IDLE → INITIALIZING → RUNNING."""
        with self._lock:
            self._transition(RuntimeState.INITIALIZING)
            self._started_at = datetime.now(timezone.utc)
            self._transition(RuntimeState.RUNNING)
        logger.info("RuntimeManager started")

    def pause(self) -> None:
        """Transition RUNNING → PAUSED. Preserves in-flight work and queue."""
        with self._lock:
            self._transition(RuntimeState.PAUSED)
            self._paused_at = datetime.now(timezone.utc)
        logger.info("RuntimeManager paused")

    def resume(self) -> None:
        """Transition PAUSED → RUNNING."""
        with self._lock:
            self._transition(RuntimeState.RUNNING)
            self._paused_at = None
        logger.info("RuntimeManager resumed")

    def stop(self, drain: bool = True) -> None:
        """
        Transition to DRAINING (if drain=True) then SHUTDOWN.

        Args:
            drain: When True, transition through DRAINING to allow callers
                   to finish in-flight work before SHUTDOWN is declared.
        """
        with self._lock:
            if drain and self._state.can_stop():
                try:
                    self._transition(RuntimeState.DRAINING)
                except RuntimeManagerError:
                    pass
            self._transition(RuntimeState.SHUTDOWN)
        logger.info("RuntimeManager stopped")

    def restart(self) -> None:
        """Stop and restart the runtime manager (resets statistics)."""
        self.stop(drain=False)
        with self._lock:
            self._state = RuntimeState.IDLE
            self._statistics = RuntimeStatistics()
            self._started_at = None
            self._paused_at = None
        self.start()
        logger.info("RuntimeManager restarted")

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def state(self) -> RuntimeState:
        with self._lock:
            return self._state

    @property
    def is_running(self) -> bool:
        return self.state == RuntimeState.RUNNING

    @property
    def is_paused(self) -> bool:
        return self.state == RuntimeState.PAUSED

    @property
    def is_shutdown(self) -> bool:
        return self.state == RuntimeState.SHUTDOWN

    @property
    def statistics(self) -> RuntimeStatistics:
        return self._statistics

    # ── Snapshot / context ────────────────────────────────────────────────────

    def snapshot(self) -> RuntimeStateSnapshot:
        """Return a point-in-time view of engine state and counters."""
        with self._lock:
            uptime = (
                (datetime.now(timezone.utc) - self._started_at).total_seconds()
                if self._started_at
                else 0.0
            )
            return RuntimeStateSnapshot(
                state=self._state,
                total_cycles=self._statistics.total_cycles,
                failed_cycles=self._statistics.total_failures,
                uptime_seconds=uptime,
                paused_at=self._paused_at,
                started_at=self._started_at,
            )

    def make_context(
        self,
        *,
        is_live: bool = False,
        is_paper: bool = True,
        is_backtest: bool = False,
        market_intelligence: object | None = None,
        company_intelligence: object | None = None,
    ) -> RuntimeContext:
        """Create a fresh RuntimeContext for a new cycle."""
        return RuntimeContext(
            is_live=is_live,
            is_paper=is_paper,
            is_backtest=is_backtest,
            market_intelligence=market_intelligence,
            company_intelligence=company_intelligence,
        )

    # ── Internal ──────────────────────────────────────────────────────────────

    def _transition(self, to_state: RuntimeState) -> None:
        """Apply a state transition; raises RuntimeManagerError if invalid."""
        from_state = self._state
        if from_state == to_state:
            return
        if not validate_runtime_transition(from_state, to_state):
            raise RuntimeManagerError(
                f"Invalid runtime transition: {from_state.value} → {to_state.value}"
            )
        self._state = to_state
        logger.debug("Runtime: %s → %s", from_state.value, to_state.value)
        for listener in self._listeners:
            try:
                listener(from_state, to_state)
            except Exception:  # noqa: BLE001
                logger.exception("State listener raised an exception")
