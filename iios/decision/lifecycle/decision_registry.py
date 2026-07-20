"""
decision_registry.py — iios.decision.lifecycle
================================================
Thread-safe registry for active and archived decision sessions.

C9 Decision Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Dict, List, Optional

from .constants import (
    DEFAULT_MAX_SESSIONS,
    DEFAULT_MAX_ARCHIVED,
    ACTIVE_STATES,
    DecisionState,
)
from .decision_session import DecisionSession
from .exceptions import (
    DecisionSessionAlreadyExistsError,
    DecisionSessionNotFoundError,
)


class DecisionRegistry:
    """
    Thread-safe registry that manages active and archived decision sessions.

    Active sessions are stored in an unbounded dict (up to
    ``max_active_sessions``).  Archived / terminal sessions are moved to a
    bounded ``deque`` to limit memory.

    Parameters
    ----------
    max_active_sessions :   Hard cap on the number of simultaneous active
                            sessions (default 5 000).
    max_archived_sessions : Maximum archived sessions retained in memory
                            (default 10 000).  Oldest entries are evicted.
    """

    def __init__(
        self,
        max_active_sessions:   int = DEFAULT_MAX_SESSIONS,
        max_archived_sessions: int = DEFAULT_MAX_ARCHIVED,
    ) -> None:
        self._lock   = threading.RLock()
        self._max_active = max_active_sessions

        # session_id → DecisionSession (in-flight only)
        self._active:   Dict[str, DecisionSession] = {}

        # Bounded archive (terminal sessions)
        self._archived: deque[DecisionSession] = deque(maxlen=max_archived_sessions)

        # decision_id → [session_id, ...] (all sessions for a decision)
        self._by_decision: Dict[str, List[str]] = {}

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------
    def add(self, session: DecisionSession) -> None:
        """
        Register a new decision session.

        Raises
        ------
        DecisionSessionAlreadyExistsError
            If *session.session_id* is already registered and active.
        RuntimeError
            If the active-session cap has been reached.
        """
        with self._lock:
            if session.session_id in self._active:
                raise DecisionSessionAlreadyExistsError(session.session_id)
            if len(self._active) >= self._max_active:
                raise RuntimeError(
                    f"DecisionRegistry: active session cap "
                    f"({self._max_active}) reached"
                )
            self._active[session.session_id] = session

            # Index by decision_id
            self._by_decision.setdefault(session.decision_id, [])
            if session.session_id not in self._by_decision[session.decision_id]:
                self._by_decision[session.decision_id].append(session.session_id)

    def move_to_archive(self, session_id: str) -> None:
        """
        Move a session from the active dict to the archived deque.

        Safe to call even if the session is not in the active dict
        (no-op in that case).
        """
        with self._lock:
            session = self._active.pop(session_id, None)
            if session is not None:
                self._archived.append(session)

    def remove(self, session_id: str) -> None:
        """
        Remove a session from both active and archived stores.

        Used for housekeeping; normally sessions are moved to archive,
        not deleted.
        """
        with self._lock:
            self._active.pop(session_id, None)
            # Remove from decision index
            for sessions_list in self._by_decision.values():
                if session_id in sessions_list:
                    sessions_list.remove(session_id)

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------
    def get(self, session_id: str) -> DecisionSession:
        """
        Return the active session for *session_id*.

        Raises
        ------
        DecisionSessionNotFoundError
            When *session_id* is not in the active registry.
        """
        with self._lock:
            session = self._active.get(session_id)
            if session is None:
                raise DecisionSessionNotFoundError(session_id)
            return session

    def find(self, session_id: str) -> Optional[DecisionSession]:
        """Return the active session for *session_id*, or ``None``."""
        with self._lock:
            return self._active.get(session_id)

    def find_archived(self, session_id: str) -> Optional[DecisionSession]:
        """Search the archived deque for *session_id*."""
        with self._lock:
            for session in self._archived:
                if session.session_id == session_id:
                    return session
            return None

    def find_any(self, session_id: str) -> Optional[DecisionSession]:
        """Search active then archived; return ``None`` if not found."""
        with self._lock:
            s = self._active.get(session_id)
            if s is not None:
                return s
            for session in self._archived:
                if session.session_id == session_id:
                    return session
            return None

    def all_active(self) -> List[DecisionSession]:
        """Return all active sessions (state order undefined)."""
        with self._lock:
            return list(self._active.values())

    def by_state(self, state: DecisionState) -> List[DecisionSession]:
        """Return all active sessions in *state*."""
        with self._lock:
            return [s for s in self._active.values() if s.state == state]

    def by_decision(self, decision_id: str) -> List[DecisionSession]:
        """Return all active sessions for *decision_id*."""
        with self._lock:
            ids = self._by_decision.get(decision_id, [])
            return [self._active[sid] for sid in ids if sid in self._active]

    def all_archived(self) -> List[DecisionSession]:
        """Return all archived sessions (oldest first)."""
        with self._lock:
            return list(self._archived)

    # ------------------------------------------------------------------
    # Counts
    # ------------------------------------------------------------------
    def active_count(self) -> int:
        """Number of sessions currently active."""
        with self._lock:
            return len(self._active)

    def archived_count(self) -> int:
        """Number of archived sessions retained."""
        with self._lock:
            return len(self._archived)

    def total_count(self) -> int:
        """Active + archived count."""
        with self._lock:
            return len(self._active) + len(self._archived)

    def is_active(self, session_id: str) -> bool:
        """``True`` when *session_id* is in the active registry."""
        with self._lock:
            return session_id in self._active

    # ------------------------------------------------------------------
    # Housekeeping
    # ------------------------------------------------------------------
    def clear(self) -> None:
        """Remove all sessions from both stores (used on lifecycle reset)."""
        with self._lock:
            self._active.clear()
            self._archived.clear()
            self._by_decision.clear()

    def __repr__(self) -> str:
        with self._lock:
            return (
                f"DecisionRegistry("
                f"active={len(self._active)}, "
                f"archived={len(self._archived)})"
            )
