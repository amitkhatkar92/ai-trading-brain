"""iios/execution/positions/risk/position_risk_registry.py
==================================================
RiskRegistry — LifecycleAwareMixin storage layer for the Position Risk module.

Stores per-position risk state, limits, and thresholds.
All write operations require the registry to be in the RUNNING state.
Read operations are always permitted.

C6 Execution Intelligence — Phase 3, Module 4
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional, Tuple

from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin
from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger

from .constants import REGISTRY_SYSTEM_ID, VERSION
from .exceptions import (
    DuplicateRiskStateError,
    PositionRiskCapacityError,
    PositionRiskNotRunningError,
    RiskStateNotFoundError,
)
from .position_risk_limits import RiskLimits
from .position_risk_state import PositionRiskState
from .position_risk_threshold import RiskThreshold

_log   = get_logger(__name__, engine_id=REGISTRY_SYSTEM_ID)
_audit = get_audit_logger(__name__, engine_id=REGISTRY_SYSTEM_ID)

_DEFAULT_MAX_POSITIONS = 10_000

# Registry entry: (state, limits, thresholds)
_Entry = Tuple[PositionRiskState, RiskLimits, RiskThreshold]


class RiskRegistry(LifecycleAwareMixin):
    """
    Thread-safe registry for position risk state, limits, and thresholds.

    Write operations (register, unregister) require RUNNING state.
    Read operations are always permitted.
    """

    def __init__(self, max_positions: int = _DEFAULT_MAX_POSITIONS) -> None:
        super().__init__()
        self._max: int = max(1, max_positions)
        self._entries: Dict[str, _Entry] = {}
        self._lock = threading.Lock()

    # ── LifecycleAwareMixin ───────────────────────────────────────────────────

    def _on_start(self) -> None:
        _audit.log_lifecycle_event(REGISTRY_SYSTEM_ID, EngineState.STOPPED, EngineState.RUNNING, VERSION)
        _log.info("RiskRegistry started.", max_positions=self._max)

    def _on_stop(self) -> None:
        _audit.log_lifecycle_event(REGISTRY_SYSTEM_ID, EngineState.RUNNING, EngineState.STOPPED, VERSION)
        _log.info("RiskRegistry stopped.", tracked_positions=len(self._entries))

    def _assert_running(self) -> None:
        if self.lifecycle_state() != EngineState.RUNNING:
            raise PositionRiskNotRunningError()

    # ── Write ─────────────────────────────────────────────────────────────────

    def register(
        self,
        state:      PositionRiskState,
        limits:     RiskLimits,
        thresholds: RiskThreshold,
    ) -> None:
        """
        Register a position risk state.

        Raises
        ------
        PositionRiskNotRunningError   — registry not started
        PositionRiskCapacityError     — at maximum capacity
        DuplicateRiskStateError       — position already tracked
        """
        self._assert_running()
        pid = state.position_id
        with self._lock:
            if len(self._entries) >= self._max:
                raise PositionRiskCapacityError(self._max)
            if pid in self._entries:
                raise DuplicateRiskStateError(pid)
            self._entries[pid] = (state, limits, thresholds)
        _log.debug("RiskRegistry: registered.", position_id=pid)

    def unregister(self, position_id: str) -> PositionRiskState:
        """
        Remove a position from the registry and return its state.

        Raises
        ------
        PositionRiskNotRunningError   — registry not started
        RiskStateNotFoundError        — position not tracked
        """
        self._assert_running()
        with self._lock:
            if position_id not in self._entries:
                raise RiskStateNotFoundError(position_id)
            state, _, _ = self._entries.pop(position_id)
        _log.debug("RiskRegistry: unregistered.", position_id=position_id)
        return state

    # ── Read ──────────────────────────────────────────────────────────────────

    def get_state(self, position_id: str) -> Optional[PositionRiskState]:
        with self._lock:
            entry = self._entries.get(position_id)
        return entry[0] if entry else None

    def require_state(self, position_id: str) -> PositionRiskState:
        state = self.get_state(position_id)
        if state is None:
            raise RiskStateNotFoundError(position_id)
        return state

    def get_limits(self, position_id: str) -> Optional[RiskLimits]:
        with self._lock:
            entry = self._entries.get(position_id)
        return entry[1] if entry else None

    def require_limits(self, position_id: str) -> RiskLimits:
        limits = self.get_limits(position_id)
        if limits is None:
            raise RiskStateNotFoundError(position_id)
        return limits

    def get_thresholds(self, position_id: str) -> Optional[RiskThreshold]:
        with self._lock:
            entry = self._entries.get(position_id)
        return entry[2] if entry else None

    def require_thresholds(self, position_id: str) -> RiskThreshold:
        thresholds = self.get_thresholds(position_id)
        if thresholds is None:
            raise RiskStateNotFoundError(position_id)
        return thresholds

    def all_states(self) -> List[PositionRiskState]:
        with self._lock:
            return [e[0] for e in self._entries.values()]

    def all_entries(self) -> List[_Entry]:
        with self._lock:
            return list(self._entries.values())

    def contains(self, position_id: str) -> bool:
        with self._lock:
            return position_id in self._entries

    def count(self) -> int:
        with self._lock:
            return len(self._entries)

    def is_empty(self) -> bool:
        with self._lock:
            return len(self._entries) == 0
