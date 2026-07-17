"""iios/execution/monitoring/lifecycle/monitoring_registry.py
==================================================
MonitoringRegistry — LifecycleAwareMixin store for MonitoringSession objects.

C6 Execution Intelligence — Phase 6, Module 1
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
    ACTIVE_STATES,
    MonitoringState,
)
from .exceptions import (
    MonitoringLifecycleNotRunningError,
    MonitoringRegistryCapacityError,
    MonitoringSessionAlreadyExistsError,
    MonitoringSessionNotFoundError,
)
from .monitoring_session import MonitoringSession

_log = get_logger(__name__)


class MonitoringRegistry(LifecycleAwareMixin):
    """
    Thread-safe, lifecycle-aware store for MonitoringSession objects.

    Lifecycle-protected: most operations reject calls when the registry
    is not in RUNNING state.
    """

    def __init__(
        self,
        max_sessions: int = DEFAULT_MAX_SESSIONS,
    ) -> None:
        super().__init__()
        self._max_sessions = max(1, max_sessions)
        self._sessions: Dict[str, MonitoringSession] = {}
        self._archived: Dict[str, MonitoringSession] = {}
        self._lock = threading.RLock()

    # ── LifecycleAwareMixin hooks ──────────────────────────────────────────────

    def _on_start(self) -> None:
        _log.info("MonitoringRegistry starting.", system_id=REGISTRY_SYSTEM_ID)

    def _on_stop(self) -> None:
        _log.info(
            "MonitoringRegistry stopping.",
            system_id=REGISTRY_SYSTEM_ID,
            active=len(self._sessions),
            archived=len(self._archived),
        )

    # ── Internal guard ────────────────────────────────────────────────────────

    def _assert_running(self) -> None:
        state = self.lifecycle_state()
        if state not in (EngineState.RUNNING, "running"):
            raise MonitoringLifecycleNotRunningError()

    # ── Write operations ──────────────────────────────────────────────────────

    def store(self, session: MonitoringSession) -> None:
        """Register a new session.  Raises if already exists or at capacity."""
        self._assert_running()
        with self._lock:
            if session.session_id in self._sessions:
                raise MonitoringSessionAlreadyExistsError(session.session_id)
            if len(self._sessions) >= self._max_sessions:
                raise MonitoringRegistryCapacityError(self._max_sessions)
            self._sessions[session.session_id] = session
        _log.info(
            "MonitoringSession stored.",
            session_id=session.session_id,
            portfolio_id=session.portfolio_id,
        )

    def update(self, session: MonitoringSession) -> None:
        """Update an existing session.  Raises if not found."""
        self._assert_running()
        with self._lock:
            if session.session_id not in self._sessions:
                raise MonitoringSessionNotFoundError(session.session_id)
            self._sessions[session.session_id] = session

    def archive(self, session_id: str) -> MonitoringSession:
        """Move a session from active store to archive store."""
        self._assert_running()
        with self._lock:
            if session_id not in self._sessions:
                raise MonitoringSessionNotFoundError(session_id)
            session = self._sessions.pop(session_id)
            self._archived[session_id] = session
        _log.info("MonitoringSession archived.", session_id=session_id)
        return session

    def remove(self, session_id: str) -> Optional[MonitoringSession]:
        """Remove a session from active store (no archive)."""
        self._assert_running()
        with self._lock:
            return self._sessions.pop(session_id, None)

    # ── Read operations ───────────────────────────────────────────────────────

    def get(self, session_id: str) -> MonitoringSession:
        """Return active session.  Raises MonitoringSessionNotFoundError."""
        self._assert_running()
        with self._lock:
            if session_id not in self._sessions:
                raise MonitoringSessionNotFoundError(session_id)
            return self._sessions[session_id]

    def get_archived(self, session_id: str) -> MonitoringSession:
        """Return archived session.  Raises MonitoringSessionNotFoundError."""
        self._assert_running()
        with self._lock:
            if session_id not in self._archived:
                raise MonitoringSessionNotFoundError(session_id)
            return self._archived[session_id]

    def find(self, session_id: str) -> Optional[MonitoringSession]:
        """Return active session or None if not found."""
        self._assert_running()
        with self._lock:
            return self._sessions.get(session_id)

    def all(self) -> List[MonitoringSession]:
        self._assert_running()
        with self._lock:
            return list(self._sessions.values())

    def all_archived(self) -> List[MonitoringSession]:
        self._assert_running()
        with self._lock:
            return list(self._archived.values())

    def active(self) -> List[MonitoringSession]:
        self._assert_running()
        with self._lock:
            return [s for s in self._sessions.values()
                    if s.state == MonitoringState.ACTIVE]

    def failed(self) -> List[MonitoringSession]:
        self._assert_running()
        with self._lock:
            return [s for s in self._sessions.values()
                    if s.state == MonitoringState.FAILED]

    def by_execution_session_id(
        self, execution_session_id: str
    ) -> List[MonitoringSession]:
        self._assert_running()
        with self._lock:
            return [s for s in self._sessions.values()
                    if s.execution_session_id == execution_session_id]

    def by_portfolio_id(self, portfolio_id: str) -> List[MonitoringSession]:
        self._assert_running()
        with self._lock:
            return [s for s in self._sessions.values()
                    if s.portfolio_id == portfolio_id]

    def contains(self, session_id: str) -> bool:
        with self._lock:
            return session_id in self._sessions

    # ── State ─────────────────────────────────────────────────────────────────

    @property
    def active_count(self) -> int:
        with self._lock:
            return len(self._sessions)

    @property
    def archived_count(self) -> int:
        with self._lock:
            return len(self._archived)
