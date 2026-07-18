"""
iios/execution/recovery/integration/recovery_integration_registry.py
====================================================================
IntegrationRegistry — lifecycle-aware registry that tracks active
and processed integration request IDs.

Provides idempotency: the same request_id cannot be submitted twice.

C7 Execution Recovery & Resilience — Phase 1, Module 6
"""
from __future__ import annotations

import threading
from typing import List, Set

from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import REGISTRY_ID, VERSION
from .exceptions import IntegrationDuplicateError, IntegrationNotRunningError

_log = get_logger(__name__)

_RUNNING = frozenset({EngineState.RUNNING, "running"})


class IntegrationRegistry(LifecycleAwareMixin):
    """
    Lifecycle-aware registry for integration request IDs.

    Tracks which request_ids are currently active (in-flight) and which
    have been processed (completed/failed).  Raises IntegrationDuplicateError
    if the same request_id is submitted twice.
    """

    VERSION   = VERSION
    SYSTEM_ID = REGISTRY_ID

    def __init__(self, max_active: int = 200) -> None:
        super().__init__()
        self._max_active = max_active
        self._lock: threading.Lock = threading.Lock()
        self._active:    Set[str] = set()
        self._processed: Set[str] = set()

    def _on_start(self) -> None:
        _log.info("IntegrationRegistry started", system_id=REGISTRY_ID)

    def _on_stop(self) -> None:
        _log.info("IntegrationRegistry stopped", system_id=REGISTRY_ID)

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in _RUNNING:
            raise IntegrationNotRunningError()

    # ── Registration ──────────────────────────────────────────────────────────

    def register_active(self, request_id: str) -> None:
        """Register a new request as active.
        Raises IntegrationDuplicateError if already processed."""
        self._assert_running()
        with self._lock:
            if request_id in self._processed:
                raise IntegrationDuplicateError(request_id)
            self._active.add(request_id)

    def complete(self, request_id: str) -> None:
        """Mark a request as completed (move from active → processed)."""
        self._assert_running()
        with self._lock:
            self._active.discard(request_id)
            self._processed.add(request_id)

    # ── Queries ───────────────────────────────────────────────────────────────

    def is_active(self, request_id: str) -> bool:
        with self._lock:
            return request_id in self._active

    def is_processed(self, request_id: str) -> bool:
        with self._lock:
            return request_id in self._processed

    def active_request_ids(self) -> List[str]:
        with self._lock:
            return list(self._active)

    # ── Counts ────────────────────────────────────────────────────────────────

    @property
    def active_count(self) -> int:
        with self._lock:
            return len(self._active)

    @property
    def processed_count(self) -> int:
        with self._lock:
            return len(self._processed)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def clear(self) -> None:
        with self._lock:
            self._active.clear()
            self._processed.clear()
