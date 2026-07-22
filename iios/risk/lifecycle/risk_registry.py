"""
risk_registry.py — iios.risk.lifecycle
=========================================
Thread-safe registry of active and archived risk sessions.

C11 Risk Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from .constants import (
    DEFAULT_MAX_ARCHIVED,
    DEFAULT_MAX_SESSIONS,
    ACTIVE_STATES,
    TERMINAL_STATES,
    RiskState,
)
from .risk_session import RiskSession
from .exceptions import (
    RiskCapacityExceededError,
    RiskRegistryError,
    RiskSessionNotFoundError,
)


class RiskRegistry:
    """
    Thread-safe registry of risk sessions.

    Maintains two collections:
    * **active** — sessions currently being managed.
    * **archived** — terminated sessions retained for auditing.

    Usage
    -----
    ::

        registry = RiskRegistry()
        registry.add(session)
        s = registry.get(session_id)
        registry.archive(session_id)

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
        self._lock     = threading.RLock()
        self._active:   Dict[str, RiskSession] = {}
        self._archived: Dict[str, RiskSession] = {}
        self._archived_order: List[str]        = []
        self._max_active   = max_active_sessions
        self._max_archived = max_archived_sessions

    # ------------------------------------------------------------------
    # Add
    # ------------------------------------------------------------------

    def add(self, session: RiskSession) -> None:
        """
        Register a new session.

        Raises
        ------
        RiskCapacityExceededError
            When the active-session limit is reached.
        RiskRegistryError
            When a session with the same ID already exists.
        """
        with self._lock:
            if session.session_id in self._active:
                raise RiskRegistryError(
                    f"Duplicate session_id: {session.session_id!r}"
                )
            if len(self._active) >= self._max_active:
                raise RiskCapacityExceededError(self._max_active)
            self._active[session.session_id] = session

    # ------------------------------------------------------------------
    # Retrieve
    # ------------------------------------------------------------------

    def get(self, session_id: str) -> RiskSession:
        """
        Return an active or archived session by ID.

        Raises
        ------
        RiskSessionNotFoundError
        """
        with self._lock:
            s = self._active.get(session_id) or self._archived.get(session_id)
        if s is None:
            raise RiskSessionNotFoundError(session_id)
        return s

    def find(self, session_id: str) -> Optional[RiskSession]:
        """Return session by ID or None if not found."""
        with self._lock:
            return self._active.get(session_id) or self._archived.get(session_id)

    def get_active(self, session_id: str) -> RiskSession:
        """Return an active (non-archived) session by ID."""
        with self._lock:
            s = self._active.get(session_id)
        if s is None:
            raise RiskSessionNotFoundError(session_id)
        return s

    # ------------------------------------------------------------------
    # Archive
    # ------------------------------------------------------------------

    def archive(self, session_id: str) -> None:
        """
        Move a session from active to archived.

        Evicts the oldest archived record when the archive is full.
        """
        with self._lock:
            session = self._active.pop(session_id, None)
            if session is None:
                raise RiskSessionNotFoundError(session_id)

            while len(self._archived_order) >= self._max_archived:
                oldest = self._archived_order.pop(0)
                self._archived.pop(oldest, None)

            self._archived[session_id] = session
            self._archived_order.append(session_id)

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def active_sessions(self) -> List[RiskSession]:
        """Return all currently active sessions."""
        with self._lock:
            return list(self._active.values())

    def archived_sessions(self) -> List[RiskSession]:
        """Return all archived sessions (oldest first)."""
        with self._lock:
            return [self._archived[sid] for sid in self._archived_order
                    if sid in self._archived]

    def sessions_for_portfolio(self, portfolio_id: str) -> List[RiskSession]:
        """Return all sessions (active + archived) for a given portfolio_id."""
        with self._lock:
            all_sessions = (
                list(self._active.values()) + list(self._archived.values())
            )
        return [s for s in all_sessions if s.portfolio_id == portfolio_id]

    def sessions_for_risk(self, risk_id: str) -> List[RiskSession]:
        """Return all sessions (active + archived) for a given risk_id."""
        with self._lock:
            all_sessions = (
                list(self._active.values()) + list(self._archived.values())
            )
        return [s for s in all_sessions if s.risk_id == risk_id]

    def sessions_by_state(self, state: RiskState) -> List[RiskSession]:
        """Return all active sessions in a given state."""
        with self._lock:
            return [s for s in self._active.values() if s.state == state]

    def active_count(self) -> int:
        with self._lock:
            return len(self._active)

    def archived_count(self) -> int:
        with self._lock:
            return len(self._archived)

    def contains_active(self, session_id: str) -> bool:
        with self._lock:
            return session_id in self._active

    def contains(self, session_id: str) -> bool:
        with self._lock:
            return (
                session_id in self._active
                or session_id in self._archived
            )

    def clear(self) -> None:
        with self._lock:
            self._active.clear()
            self._archived.clear()
            self._archived_order.clear()
