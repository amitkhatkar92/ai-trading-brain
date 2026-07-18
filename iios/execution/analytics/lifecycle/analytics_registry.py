"""
iios/execution/analytics/lifecycle/analytics_registry.py
========================================================
AnalyticsRegistry — LifecycleAwareMixin session store for the analytics
lifecycle subsystem.

C8 Execution Analytics & Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import (
    DEFAULT_MAX_SESSIONS,
    REGISTRY_SYSTEM_ID,
    VERSION,
    AnalyticsState,
)
from .exceptions import (
    AnalyticsNotRunningError,
    AnalyticsSessionAlreadyExistsError,
    AnalyticsSessionNotFoundError,
)
from .analytics_session import AnalyticsSession

_log = get_logger(__name__)

_RUNNING = frozenset({EngineState.RUNNING, "running"})


class AnalyticsRegistry(LifecycleAwareMixin):
    """
    Thread-safe, lifecycle-aware in-memory store for AnalyticsSession objects.

    Active sessions remain until archived or cleared.
    Archived sessions are moved to a separate archive store.
    """

    def __init__(self, max_sessions: int = DEFAULT_MAX_SESSIONS) -> None:
        super().__init__()
        self._max_sessions = max(1, max_sessions)
        self._sessions: Dict[str, AnalyticsSession] = {}
        self._archive:  Dict[str, AnalyticsSession] = {}
        self._lock = threading.RLock()

    # ── LifecycleAwareMixin hooks ──────────────────────────────────────────────

    def _on_start(self) -> None:
        _log.info(
            "AnalyticsRegistry started.",
            system_id = REGISTRY_SYSTEM_ID,
            version   = VERSION,
        )

    def _on_stop(self) -> None:
        with self._lock:
            active = len(self._sessions)
        _log.info(
            "AnalyticsRegistry stopped.",
            system_id      = REGISTRY_SYSTEM_ID,
            active_sessions= active,
        )

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in _RUNNING:
            raise AnalyticsNotRunningError()

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def store(self, session: AnalyticsSession) -> None:
        """Store a new session.  Raises AnalyticsSessionAlreadyExistsError if duplicate."""
        self._assert_running()
        with self._lock:
            if session.session_id in self._sessions:
                raise AnalyticsSessionAlreadyExistsError(session.session_id)
            if len(self._sessions) >= self._max_sessions:
                oldest = next(iter(self._sessions))
                _log.warning(
                    "AnalyticsRegistry at capacity; evicting oldest session.",
                    evicted=oldest,
                )
                del self._sessions[oldest]
            self._sessions[session.session_id] = session

    def get(self, session_id: str) -> AnalyticsSession:
        """Return session or raise AnalyticsSessionNotFoundError."""
        self._assert_running()
        with self._lock:
            s = self._sessions.get(session_id)
        if s is None:
            raise AnalyticsSessionNotFoundError(session_id)
        return s

    def find(self, session_id: str) -> Optional[AnalyticsSession]:
        """Return session or None (no exception)."""
        with self._lock:
            return self._sessions.get(session_id)

    def archive(self, session_id: str) -> None:
        """Move a terminal session from active store to archive."""
        self._assert_running()
        with self._lock:
            s = self._sessions.get(session_id)
            if s is None:
                raise AnalyticsSessionNotFoundError(session_id)
            self._archive[session_id] = s
            del self._sessions[session_id]

    def find_archived(self, session_id: str) -> Optional[AnalyticsSession]:
        with self._lock:
            return self._archive.get(session_id)

    # ── Queries ───────────────────────────────────────────────────────────────

    def all(self) -> List[AnalyticsSession]:
        with self._lock:
            return list(self._sessions.values())

    def all_archived(self) -> List[AnalyticsSession]:
        with self._lock:
            return list(self._archive.values())

    def by_state(self, state: AnalyticsState) -> List[AnalyticsSession]:
        with self._lock:
            return [s for s in self._sessions.values() if s.state == state]

    def by_execution_session(
        self, execution_session_id: str
    ) -> List[AnalyticsSession]:
        with self._lock:
            return [
                s for s in self._sessions.values()
                if s.execution_session_id == execution_session_id
            ]

    # ── Counts ────────────────────────────────────────────────────────────────

    @property
    def active_count(self) -> int:
        with self._lock:
            return len(self._sessions)

    @property
    def archived_count(self) -> int:
        with self._lock:
            return len(self._archive)

    # ── Lifecycle helpers ─────────────────────────────────────────────────────

    def clear(self) -> None:
        """Remove all active sessions (does not affect archive)."""
        with self._lock:
            self._sessions.clear()
