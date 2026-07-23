"""
market_registry.py — iios.market.lifecycle
============================================
Thread-safe registry of active and archived market sessions.

C12 Market Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from .constants import (
    DEFAULT_MAX_ARCHIVED,
    DEFAULT_MAX_SESSIONS,
    ACTIVE_STATES,
    TERMINAL_STATES,
    MarketState,
)
from .market_session import MarketSession
from .exceptions import (
    MarketCapacityExceededError,
    MarketRegistryError,
    MarketSessionNotFoundError,
)


class MarketRegistry:
    """
    Thread-safe registry of market sessions.

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
        self._active:   Dict[str, MarketSession] = {}
        self._archived: Dict[str, MarketSession] = {}
        self._archived_order: List[str]          = []
        self._max_active   = max_active_sessions
        self._max_archived = max_archived_sessions

    # ------------------------------------------------------------------
    # Add
    # ------------------------------------------------------------------

    def add(self, session: MarketSession) -> None:
        """
        Register a new session.

        Raises
        ------
        MarketCapacityExceededError
            When the active-session limit is reached.
        MarketRegistryError
            When a session with the same ID already exists.
        """
        with self._lock:
            if session.session_id in self._active:
                raise MarketRegistryError(
                    f"Duplicate session_id: {session.session_id!r}"
                )
            if len(self._active) >= self._max_active:
                raise MarketCapacityExceededError(self._max_active)
            self._active[session.session_id] = session

    # ------------------------------------------------------------------
    # Retrieve
    # ------------------------------------------------------------------

    def get(self, session_id: str) -> MarketSession:
        """
        Return an active or archived session by ID.

        Raises
        ------
        MarketSessionNotFoundError
        """
        with self._lock:
            s = self._active.get(session_id) or self._archived.get(session_id)
        if s is None:
            raise MarketSessionNotFoundError(session_id)
        return s

    def find(self, session_id: str) -> Optional[MarketSession]:
        """Return session by ID or None if not found."""
        with self._lock:
            return self._active.get(session_id) or self._archived.get(session_id)

    def get_active(self, session_id: str) -> MarketSession:
        """Return an active (non-archived) session by ID."""
        with self._lock:
            s = self._active.get(session_id)
        if s is None:
            raise MarketSessionNotFoundError(session_id)
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
                raise MarketSessionNotFoundError(session_id)
            # Evict oldest entry if at capacity
            while len(self._archived) >= self._max_archived and self._archived_order:
                oldest = self._archived_order.pop(0)
                self._archived.pop(oldest, None)
            self._archived[session_id] = session
            self._archived_order.append(session_id)

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def active_count(self) -> int:
        with self._lock:
            return len(self._active)

    def archived_count(self) -> int:
        with self._lock:
            return len(self._archived)

    def active_sessions(self) -> List[MarketSession]:
        """Return all active sessions (snapshot)."""
        with self._lock:
            return list(self._active.values())

    def sessions_by_state(self, state: MarketState) -> List[MarketSession]:
        """Return all active sessions in the given state."""
        with self._lock:
            return [s for s in self._active.values() if s.state == state]

    def sessions_by_exchange(self, exchange: str) -> List[MarketSession]:
        """Return all active sessions for the given exchange."""
        with self._lock:
            return [s for s in self._active.values() if s.exchange == exchange]

    def contains(self, session_id: str) -> bool:
        """Return True if session_id is active or archived."""
        with self._lock:
            return (
                session_id in self._active
                or session_id in self._archived
            )

    def clear(self) -> None:
        """Remove all sessions (active and archived)."""
        with self._lock:
            self._active.clear()
            self._archived.clear()
            self._archived_order.clear()
