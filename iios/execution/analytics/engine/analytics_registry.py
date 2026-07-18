"""
iios/execution/analytics/engine/analytics_registry.py
=====================================================
EngineAnalyticsRegistry — lifecycle-aware in-memory store for
AnalyticsRequest objects processed by the Execution Analytics Engine.

Tracks active requests (in-flight) and completed requests separately.

C8 Execution Analytics & Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Dict, List, Optional

from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import DEFAULT_MAX_REQUESTS, REGISTRY_SYSTEM_ID, VERSION
from .exceptions import (
    AnalyticsEngineNotRunningError,
    AnalyticsRequestNotFoundError,
)
from .analytics_request import AnalyticsRequest

_log = get_logger(__name__)

_RUNNING = frozenset({EngineState.RUNNING, "running"})


class EngineAnalyticsRegistry(LifecycleAwareMixin):
    """
    Thread-safe, lifecycle-aware store for AnalyticsRequest objects.

    Active requests remain until explicitly completed or failed.
    Completed requests are moved to a bounded completed store.

    Thread-safe.  Must be started before use.
    """

    def __init__(self, max_requests: int = DEFAULT_MAX_REQUESTS) -> None:
        super().__init__()
        self._max_requests = max(1, max_requests)
        self._active:    Dict[str, AnalyticsRequest] = {}
        self._completed: deque[AnalyticsRequest]      = deque(maxlen=max_requests)
        self._failed:    deque[AnalyticsRequest]      = deque(maxlen=max_requests)
        self._lock       = threading.RLock()

    # ── LifecycleAwareMixin hooks ──────────────────────────────────────────────

    def _on_start(self) -> None:
        _log.info(
            "EngineAnalyticsRegistry started.",
            system_id = REGISTRY_SYSTEM_ID,
            version   = VERSION,
        )

    def _on_stop(self) -> None:
        with self._lock:
            active = len(self._active)
        _log.info(
            "EngineAnalyticsRegistry stopped.",
            system_id      = REGISTRY_SYSTEM_ID,
            active_requests= active,
        )

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in _RUNNING:
            raise AnalyticsEngineNotRunningError()

    # ── Active request store ──────────────────────────────────────────────────

    def store(self, request: AnalyticsRequest) -> None:
        """Store a new active request.  Evicts oldest if at capacity."""
        self._assert_running()
        with self._lock:
            if len(self._active) >= self._max_requests:
                oldest_key = next(iter(self._active))
                evicted = self._active.pop(oldest_key)
                _log.warning(
                    "Active request registry at capacity; evicted oldest request.",
                    evicted_id = evicted.request_id,
                )
            self._active[request.request_id] = request

    def get(self, request_id: str) -> AnalyticsRequest:
        """Retrieve an active request.  Raises if not found."""
        self._assert_running()
        with self._lock:
            req = self._active.get(request_id)
        if req is None:
            raise AnalyticsRequestNotFoundError(request_id)
        return req

    def find(self, request_id: str) -> Optional[AnalyticsRequest]:
        """Return an active request or None if not found."""
        with self._lock:
            return self._active.get(request_id)

    def complete(self, request_id: str) -> None:
        """Move a request from active to completed."""
        self._assert_running()
        with self._lock:
            req = self._active.pop(request_id, None)
            if req is None:
                raise AnalyticsRequestNotFoundError(request_id)
            self._completed.append(req)

    def fail(self, request_id: str) -> None:
        """Move a request from active to failed."""
        self._assert_running()
        with self._lock:
            req = self._active.pop(request_id, None)
            if req is None:
                raise AnalyticsRequestNotFoundError(request_id)
            self._failed.append(req)

    # ── Read API ──────────────────────────────────────────────────────────────

    def all_active(self) -> List[AnalyticsRequest]:
        with self._lock:
            return list(self._active.values())

    def all_completed(self) -> List[AnalyticsRequest]:
        with self._lock:
            return list(self._completed)

    def all_failed(self) -> List[AnalyticsRequest]:
        with self._lock:
            return list(self._failed)

    def clear(self) -> None:
        """Clear all stores."""
        with self._lock:
            self._active.clear()
            self._completed.clear()
            self._failed.clear()

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def active_count(self) -> int:
        with self._lock:
            return len(self._active)

    @property
    def completed_count(self) -> int:
        with self._lock:
            return len(self._completed)

    @property
    def failed_count(self) -> int:
        with self._lock:
            return len(self._failed)
