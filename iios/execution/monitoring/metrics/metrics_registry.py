"""iios/execution/monitoring/metrics/metrics_registry.py
==================================================
MetricsRegistry — LifecycleAwareMixin registry for MetricsSnapshot objects.

C6 Execution Intelligence — Phase 6, Module 3
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import DEFAULT_MAX_SERIES, REGISTRY_SYSTEM_ID
from .exceptions import (
    MetricsEngineNotRunningError,
    MetricsRegistryCapacityError,
    MetricSeriesNotFoundError,
)

_log = get_logger(__name__)


class MetricsRegistry(LifecycleAwareMixin):
    """
    Thread-safe, lifecycle-aware registry for MetricsSnapshot objects.

    Latest snapshot per session_id is always accessible via get_latest().
    Full history is in MetricsHistory (owned by the engine).
    """

    def __init__(self, max_snapshots: int = DEFAULT_MAX_SERIES) -> None:
        super().__init__()
        self._max = max(1, max_snapshots)
        self._snapshots: Dict[str, object] = {}   # session_id → latest snapshot
        self._lock = threading.RLock()

    # ── LifecycleAwareMixin hooks ──────────────────────────────────────────────

    def _on_start(self) -> None:
        _log.info("MetricsRegistry starting.", system_id=REGISTRY_SYSTEM_ID)

    def _on_stop(self) -> None:
        _log.info(
            "MetricsRegistry stopping.",
            system_id=REGISTRY_SYSTEM_ID,
            entries=len(self._snapshots),
        )

    def _assert_running(self) -> None:
        state = self.lifecycle_state()
        if state not in (EngineState.RUNNING, "running"):
            raise MetricsEngineNotRunningError()

    # ── Write ─────────────────────────────────────────────────────────────────

    def store(self, snapshot) -> None:
        """Store the latest snapshot for a session.  Overwrites previous."""
        self._assert_running()
        with self._lock:
            if (snapshot.session_id not in self._snapshots and
                    len(self._snapshots) >= self._max):
                raise MetricsRegistryCapacityError(self._max)
            self._snapshots[snapshot.session_id] = snapshot

    def remove(self, session_id: str) -> None:
        self._assert_running()
        with self._lock:
            self._snapshots.pop(session_id, None)

    def clear(self) -> None:
        self._assert_running()
        with self._lock:
            self._snapshots.clear()

    # ── Read ──────────────────────────────────────────────────────────────────

    def get_latest(self, session_id: str) -> object:
        """Return latest snapshot.  Raises MetricSeriesNotFoundError if absent."""
        self._assert_running()
        with self._lock:
            snap = self._snapshots.get(session_id)
        if snap is None:
            raise MetricSeriesNotFoundError(session_id)
        return snap

    def find_latest(self, session_id: str) -> Optional[object]:
        """Return latest snapshot or None."""
        self._assert_running()
        with self._lock:
            return self._snapshots.get(session_id)

    def all_latest(self) -> List[object]:
        self._assert_running()
        with self._lock:
            return list(self._snapshots.values())

    def by_portfolio(self, portfolio_id: str) -> List[object]:
        self._assert_running()
        with self._lock:
            return [s for s in self._snapshots.values()
                    if s.portfolio_id == portfolio_id]  # type: ignore

    def contains(self, session_id: str) -> bool:
        with self._lock:
            return session_id in self._snapshots

    @property
    def session_count(self) -> int:
        with self._lock:
            return len(self._snapshots)
