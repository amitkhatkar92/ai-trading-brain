"""iios/execution/positions/engine/position_registry.py
==================================================
EngineRegistry — LifecycleAwareMixin wrapper around the M1
PositionRegistry, exposing engine-level read and notify APIs.

C6 Execution Intelligence — Phase 3, Module 2
"""
from __future__ import annotations

import threading
from typing import List, Optional

from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin
from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger

from iios.execution.positions.lifecycle import (
    Position,
    PositionRegistry as LifecycleRegistry,
    PositionState,
    PositionStatistics as LifecycleStatistics,
)

from .constants import DEFAULT_MAX_POSITIONS, REGISTRY_SYSTEM_ID, VERSION
from .exceptions import PositionEngineNotRunningError

_log   = get_logger(__name__, engine_id=REGISTRY_SYSTEM_ID)
_audit = get_audit_logger(__name__, engine_id=REGISTRY_SYSTEM_ID)


class EngineRegistry(LifecycleAwareMixin):
    """
    Engine-layer wrapper around ``iios.execution.positions.lifecycle.PositionRegistry``.

    Owns and manages the lifecycle of the underlying M1 registry.
    Delegates all storage operations to it while providing engine-level
    lifecycle control and logging.
    """

    def __init__(self, max_positions: int = DEFAULT_MAX_POSITIONS) -> None:
        super().__init__()
        self._inner = LifecycleRegistry(max_positions=max_positions)

    # ── LifecycleAwareMixin ───────────────────────────────────────────────────

    def _on_start(self) -> None:
        self._inner.start()
        _audit.log_lifecycle_event(REGISTRY_SYSTEM_ID, EngineState.STOPPED, EngineState.RUNNING, VERSION)
        _log.info("EngineRegistry started.", max_positions=self._inner._max)

    def _on_stop(self) -> None:
        self._inner.stop()
        _audit.log_lifecycle_event(REGISTRY_SYSTEM_ID, EngineState.RUNNING, EngineState.STOPPED, VERSION)
        _log.info("EngineRegistry stopped.", position_count=self._inner.count)

    # ── Write ─────────────────────────────────────────────────────────────────

    def register(self, position: Position) -> None:
        """Register *position*; delegates to the M1 registry."""
        self._assert_running()
        self._inner.register(position)

    def deregister(self, position_id: str) -> None:
        self._assert_running()
        self._inner.deregister(position_id)

    # ── Read ──────────────────────────────────────────────────────────────────

    def get(self, position_id: str) -> Optional[Position]:
        return self._inner.get(position_id)

    def require(self, position_id: str) -> Position:
        return self._inner.require(position_id)

    def contains(self, position_id: str) -> bool:
        return self._inner.contains(position_id)

    # ── Filters ───────────────────────────────────────────────────────────────

    def all(self) -> List[Position]:
        return self._inner.all()

    def by_state(self, state: PositionState) -> List[Position]:
        return self._inner.by_state(state)

    def by_portfolio(self, portfolio_id: str) -> List[Position]:
        return self._inner.by_portfolio(portfolio_id)

    def by_strategy(self, strategy_id: str) -> List[Position]:
        return self._inner.by_strategy(strategy_id)

    def by_instrument(self, instrument: str) -> List[Position]:
        return self._inner.by_instrument(instrument)

    def active(self) -> List[Position]:
        return self._inner.active()

    def closed(self) -> List[Position]:
        return self._inner.closed()

    def archived(self) -> List[Position]:
        return self._inner.archived()

    def suspended(self) -> List[Position]:
        return self._inner.suspended()

    # ── Counters ──────────────────────────────────────────────────────────────

    @property
    def count(self) -> int:
        return self._inner.count

    @property
    def is_empty(self) -> bool:
        return self._inner.is_empty

    # ── Statistics ────────────────────────────────────────────────────────────

    def notify_transition(
        self,
        to_state: PositionState,
        *,
        holding_time_ms: float = 0.0,
        is_recovery: bool = False,
    ) -> None:
        """Forward a lifecycle transition notification to the M1 registry."""
        self._inner.notify_transition(
            to_state, holding_time_ms=holding_time_ms, is_recovery=is_recovery
        )

    def lifecycle_statistics(self) -> LifecycleStatistics:
        """Return M1-level position statistics (opened/closed/etc.)."""
        return self._inner.statistics()

    # ── Internal ─────────────────────────────────────────────────────────────

    def _assert_running(self) -> None:
        if self.lifecycle_state() != EngineState.RUNNING:
            raise PositionEngineNotRunningError()
