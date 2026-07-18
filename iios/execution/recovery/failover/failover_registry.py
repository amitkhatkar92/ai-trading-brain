"""
iios/execution/recovery/failover/failover_registry.py
=====================================================
FailoverRegistry — lifecycle-aware tracker for active failover sessions.

Provides idempotency: a source decision that has already been processed
will not trigger a second failover execution.

C7 Execution Recovery & Resilience — Phase 1, Module 4
"""
from __future__ import annotations

import threading
from typing import List, Optional, Set

from iios.common.logging.logging_manager import get_logger
from iios.common.logging.audit_logger import get_audit_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import DEFAULT_MAX_SESSIONS, REGISTRY_ID, VERSION
from .exceptions import FailoverNotRunningError, FailoverRegistryError

_log   = get_logger(__name__)
_audit = get_audit_logger(__name__)


class FailoverRegistry(LifecycleAwareMixin):
    """
    Lifecycle-aware tracker for active and completed failover sessions.

    Active sessions: currently executing (in-flight).
    Completed decisions: source M3 decision IDs already processed.
    """

    def __init__(self, max_sessions: int = DEFAULT_MAX_SESSIONS) -> None:
        super().__init__()
        self._max = max_sessions
        self._lock: threading.Lock = threading.Lock()
        self._active: Set[str]    = set()   # active failover_session_ids
        self._processed: Set[str] = set()   # completed source_decision_ids

    def _on_start(self) -> None:
        _audit.log_lifecycle_event(REGISTRY_ID, EngineState.STOPPED, EngineState.RUNNING, VERSION)
        _log.info("FailoverRegistry started")

    def _on_stop(self) -> None:
        _audit.log_lifecycle_event(REGISTRY_ID, EngineState.RUNNING, EngineState.STOPPED, VERSION)
        with self._lock:
            self._active.clear()
            self._processed.clear()
        _log.info("FailoverRegistry stopped")

    # ── Guard ─────────────────────────────────────────────────────────────────

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in (EngineState.RUNNING, "running"):
            raise FailoverNotRunningError()

    # ── Session tracking ──────────────────────────────────────────────────────

    def register_active(self, failover_session_id: str) -> None:
        """Mark a session as active (in-flight)."""
        self._assert_running()
        with self._lock:
            if len(self._active) >= self._max:
                raise FailoverRegistryError(
                    f"Active session capacity reached ({self._max})"
                )
            self._active.add(failover_session_id)

    def complete(self, failover_session_id: str, source_decision_id: str) -> None:
        """Mark session as completed and record the source decision as processed."""
        with self._lock:
            self._active.discard(failover_session_id)
            self._processed.add(source_decision_id)

    def is_active(self, failover_session_id: str) -> bool:
        with self._lock:
            return failover_session_id in self._active

    def is_decision_processed(self, source_decision_id: str) -> bool:
        """True if the M3 decision has already triggered a failover."""
        with self._lock:
            return source_decision_id in self._processed

    def active_sessions(self) -> List[str]:
        with self._lock:
            return list(self._active)

    @property
    def active_count(self) -> int:
        with self._lock:
            return len(self._active)

    @property
    def processed_decision_count(self) -> int:
        with self._lock:
            return len(self._processed)

    def clear(self) -> None:
        with self._lock:
            self._active.clear()
            self._processed.clear()
