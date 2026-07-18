"""
iios/execution/analytics/performance/performance_registry.py
============================================================
PerformanceAnalyticsRegistry — stores active and completed analytics
requests.

Limits active request store to DEFAULT_MAX_REQUESTS.
Completed requests stored with bounded deque (DEFAULT_MAX_HISTORY).

C8 Execution Analytics & Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import collections
import threading
from typing import Dict, List, Optional

from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import DEFAULT_MAX_HISTORY, DEFAULT_MAX_REQUESTS, REGISTRY_SYSTEM_ID
from .exceptions import PerformanceEngineNotRunningError, PerformanceRequestNotFoundError
from .performance_request import PerformanceRequest

_log = get_logger(__name__)

_RUNNING = frozenset({EngineState.RUNNING, "running"})


class PerformanceAnalyticsRegistry(LifecycleAwareMixin):
    """
    Thread-safe registry for PerformanceRequest objects.

    Active requests are stored in a dict for O(1) lookup.
    Completed requests are pushed to a bounded deque.
    """

    def __init__(
        self,
        max_active:    int = DEFAULT_MAX_REQUESTS,
        max_completed: int = DEFAULT_MAX_HISTORY,
    ) -> None:
        super().__init__()
        self._max_active     = max_active
        self._active:    Dict[str, PerformanceRequest] = {}
        self._completed: collections.deque[PerformanceRequest] = (
            collections.deque(maxlen=max_completed)
        )
        self._lock = threading.Lock()

    def _on_start(self) -> None:
        _log.info("PerformanceAnalyticsRegistry started.", system_id=REGISTRY_SYSTEM_ID)

    def _on_stop(self) -> None:
        _log.info("PerformanceAnalyticsRegistry stopped.", system_id=REGISTRY_SYSTEM_ID)

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in _RUNNING:
            raise PerformanceEngineNotRunningError()

    # ── Public API ────────────────────────────────────────────────────────────

    def register(self, request: PerformanceRequest) -> None:
        """Store request as active.  LRU-evicts oldest if at capacity."""
        self._assert_running()
        with self._lock:
            if len(self._active) >= self._max_active and request.request_id not in self._active:
                # Evict the oldest entry
                oldest_key = next(iter(self._active))
                del self._active[oldest_key]
            self._active[request.request_id] = request

    def complete(self, request_id: str) -> None:
        """Move a request from active to completed."""
        self._assert_running()
        with self._lock:
            req = self._active.pop(request_id, None)
            if req is not None:
                self._completed.append(req)

    def get_active(self, request_id: str) -> PerformanceRequest:
        """Return the active request or raise PerformanceRequestNotFoundError."""
        with self._lock:
            req = self._active.get(request_id)
        if req is None:
            raise PerformanceRequestNotFoundError(request_id)
        return req

    def is_active(self, request_id: str) -> bool:
        with self._lock:
            return request_id in self._active

    def active_requests(self) -> List[PerformanceRequest]:
        with self._lock:
            return list(self._active.values())

    def completed_requests(self) -> List[PerformanceRequest]:
        with self._lock:
            return list(self._completed)

    @property
    def active_count(self) -> int:
        with self._lock:
            return len(self._active)

    @property
    def completed_count(self) -> int:
        with self._lock:
            return len(self._completed)

    def clear(self) -> None:
        with self._lock:
            self._active.clear()
            self._completed.clear()
