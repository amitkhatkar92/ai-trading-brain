"""
iios/execution/recovery/engine/recovery_registry.py
===================================================
RecoveryRegistry — LifecycleAwareMixin store for active recovery requests.

Maintains a mapping of request_id → RecoveryRequest with bounded eviction.
Completed requests are moved to an archive store.

C7 Execution Recovery & Resilience — Phase 1, Module 2
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import (
    DEFAULT_MAX_REQUESTS,
    REGISTRY_ID,
    VERSION,
)
from .exceptions import (
    RecoveryEngineNotRunningError,
    RecoveryRequestNotFoundError,
)
from .recovery_request import RecoveryRequest

_log = get_logger(__name__)


class RecoveryRegistry(LifecycleAwareMixin):
    """
    Thread-safe, lifecycle-aware in-memory store for RecoveryRequest objects.

    Active requests remain until explicitly archived.
    Archived requests are moved to a separate store.
    When the active store exceeds max_requests the oldest entry is evicted.
    """

    def __init__(self, max_requests: int = DEFAULT_MAX_REQUESTS) -> None:
        super().__init__()
        self._max_requests = max(1, max_requests)
        self._active:  Dict[str, RecoveryRequest] = {}
        self._archive: Dict[str, RecoveryRequest] = {}
        self._lock = threading.RLock()

    # ── LifecycleAwareMixin hooks ─────────────────────────────────────────────

    def _on_start(self) -> None:
        _log.info("RecoveryRegistry started.", system_id=REGISTRY_ID, version=VERSION)

    def _on_stop(self) -> None:
        with self._lock:
            active = len(self._active)
        _log.info("RecoveryRegistry stopped.", system_id=REGISTRY_ID, active=active)

    # ── Guard ─────────────────────────────────────────────────────────────────

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in (EngineState.RUNNING, "running"):
            raise RecoveryEngineNotRunningError()

    # ── CRUD ─────────────────────────────────────────────────────────────────

    def store(self, request: RecoveryRequest) -> None:
        """Store an active request.  Evicts oldest if capacity exceeded."""
        self._assert_running()
        with self._lock:
            if len(self._active) >= self._max_requests:
                oldest_id = next(iter(self._active))
                evicted = self._active.pop(oldest_id)
                self._archive[oldest_id] = evicted
                _log.warning(
                    "RecoveryRegistry capacity exceeded — evicting oldest request.",
                    evicted_id=oldest_id,
                )
            self._active[request.request_id] = request

    def get(self, request_id: str) -> RecoveryRequest:
        """Return an active request or raise RecoveryRequestNotFoundError."""
        self._assert_running()
        with self._lock:
            request = self._active.get(request_id)
        if request is None:
            raise RecoveryRequestNotFoundError(request_id)
        return request

    def find(self, request_id: str) -> Optional[RecoveryRequest]:
        """Return an active request or None."""
        with self._lock:
            return self._active.get(request_id)

    def archive(self, request_id: str) -> None:
        """Move an active request to the archive store."""
        self._assert_running()
        with self._lock:
            request = self._active.pop(request_id, None)
        if request is None:
            raise RecoveryRequestNotFoundError(request_id)
        with self._lock:
            self._archive[request_id] = request

    def find_archived(self, request_id: str) -> Optional[RecoveryRequest]:
        with self._lock:
            return self._archive.get(request_id)

    def all_archived(self) -> List[RecoveryRequest]:
        with self._lock:
            return list(self._archive.values())

    # ── Queries ───────────────────────────────────────────────────────────────

    def all(self) -> List[RecoveryRequest]:
        with self._lock:
            return list(self._active.values())

    def for_subsystem(self, subsystem_id: str) -> List[RecoveryRequest]:
        with self._lock:
            return [r for r in self._active.values() if r.subsystem_id == subsystem_id]

    def for_execution_session(self, execution_session_id: str) -> List[RecoveryRequest]:
        with self._lock:
            return [
                r for r in self._active.values()
                if r.execution_session_id == execution_session_id
            ]

    def contains(self, request_id: str) -> bool:
        with self._lock:
            return request_id in self._active

    # ── Counts ────────────────────────────────────────────────────────────────

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._active)

    @property
    def archive_count(self) -> int:
        with self._lock:
            return len(self._archive)

    def clear(self) -> None:
        with self._lock:
            self._active.clear()
