"""
supervisor_registry.py — iios.supervisor.lifecycle
---------------------------------------------------
Thread-safe registry of active and archived supervisor sessions.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 1
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from .constants import (
    DEFAULT_MAX_ARCHIVED,
    DEFAULT_MAX_SESSIONS,
    ACTIVE_STATES,
    TERMINAL_STATES,
    SupervisorState,
)
from .supervisor_session import SupervisorSession
from .exceptions import (
    SupervisorCapacityExceededError,
    SupervisorRegistryError,
    SupervisorSessionNotFoundError,
)


class SupervisorRegistry:
    """
    Thread-safe registry of supervisor sessions.

    Maintains two collections:
    * **active**   — sessions currently being managed.
    * **archived** — terminated sessions retained for auditing.

    Parameters
    ----------
    max_active_sessions :   Maximum simultaneous in-flight sessions.
    max_archived_sessions : Maximum archived sessions retained in memory.
    """

    def __init__(
        self,
        max_active_sessions:   int = DEFAULT_MAX_SESSIONS,
        max_archived_sessions: int = DEFAULT_MAX_ARCHIVED,
    ) -> None:
        self._lock             = threading.RLock()
        self._active:   Dict[str, SupervisorSession] = {}
        self._archived: Dict[str, SupervisorSession] = {}
        self._archived_order: List[str]              = []
        self._max_active   = max_active_sessions
        self._max_archived = max_archived_sessions

    # ------------------------------------------------------------------
    # Add
    # ------------------------------------------------------------------

    def add(self, session: SupervisorSession) -> None:
        """
        Register a new session.

        Raises
        ------
        SupervisorCapacityExceededError
            When the active-session limit is reached.
        SupervisorRegistryError
            When a session with the same ID already exists.
        """
        with self._lock:
            if session.session_id in self._active:
                raise SupervisorRegistryError(
                    f"Duplicate session_id: {session.session_id!r}"
                )
            if len(self._active) >= self._max_active:
                raise SupervisorCapacityExceededError(self._max_active)
            self._active[session.session_id] = session

    # ------------------------------------------------------------------
    # Retrieve
    # ------------------------------------------------------------------

    def get(self, session_id: str) -> SupervisorSession:
        """
        Return an active or archived session by ID.

        Raises
        ------
        SupervisorSessionNotFoundError
        """
        with self._lock:
            s = self._active.get(session_id) or self._archived.get(session_id)
        if s is None:
            raise SupervisorSessionNotFoundError(session_id)
        return s

    def find(self, session_id: str) -> Optional[SupervisorSession]:
        """Return session by ID or None if not found."""
        with self._lock:
            return self._active.get(session_id) or self._archived.get(session_id)

    def get_active(self, session_id: str) -> SupervisorSession:
        """
        Return an active session by ID.

        Raises
        ------
        SupervisorSessionNotFoundError
            When the session is not in the active pool.
        """
        with self._lock:
            s = self._active.get(session_id)
        if s is None:
            raise SupervisorSessionNotFoundError(session_id)
        return s

    # ------------------------------------------------------------------
    # Archive
    # ------------------------------------------------------------------

    def archive(self, session_id: str) -> None:
        """
        Move an active session to the archived pool.

        Raises
        ------
        SupervisorSessionNotFoundError
        SupervisorCapacityExceededError
        """
        with self._lock:
            session = self._active.pop(session_id, None)
            if session is None:
                raise SupervisorSessionNotFoundError(session_id)
            if len(self._archived) >= self._max_archived:
                # evict the oldest archived entry (FIFO)
                if self._archived_order:
                    oldest = self._archived_order.pop(0)
                    self._archived.pop(oldest, None)
            self._archived[session_id] = session
            self._archived_order.append(session_id)

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def active_sessions(self) -> List[SupervisorSession]:
        """Return all active sessions (copy)."""
        with self._lock:
            return list(self._active.values())

    def sessions_by_state(self, state: SupervisorState) -> List[SupervisorSession]:
        """Return active sessions in the given state."""
        with self._lock:
            return [s for s in self._active.values() if s.state == state]

    def sessions_by_type(self, supervisor_type: object) -> List[SupervisorSession]:
        """Return active sessions of the given supervisor type."""
        with self._lock:
            return [s for s in self._active.values()
                    if s.supervisor_type == supervisor_type]

    def sessions_by_scope(self, supervisor_scope: object) -> List[SupervisorSession]:
        """Return active sessions with the given supervisor scope."""
        with self._lock:
            return [s for s in self._active.values()
                    if s.supervisor_scope == supervisor_scope]

    def sessions_by_workflow(self, workflow_id: str) -> List[SupervisorSession]:
        """Return active sessions for the given workflow_id."""
        with self._lock:
            return [s for s in self._active.values()
                    if s.workflow_id == workflow_id]

    # ------------------------------------------------------------------
    # Counts
    # ------------------------------------------------------------------

    @property
    def active_count(self) -> int:
        with self._lock:
            return len(self._active)

    @property
    def archived_count(self) -> int:
        with self._lock:
            return len(self._archived)

    def clear(self) -> None:
        """Remove all sessions from both pools (for testing)."""
        with self._lock:
            self._active.clear()
            self._archived.clear()
            self._archived_order.clear()
