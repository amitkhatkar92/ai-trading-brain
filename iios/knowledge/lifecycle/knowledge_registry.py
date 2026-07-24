"""
knowledge_registry.py — iios.knowledge.lifecycle
--------------------------------------------------
Thread-safe registry of active and archived knowledge sessions.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from .constants import (
    DEFAULT_MAX_ARCHIVED,
    DEFAULT_MAX_SESSIONS,
    ACTIVE_STATES,
    TERMINAL_STATES,
    KnowledgeLifecycleState,
    KnowledgeScope,
    KnowledgeType,
)
from .exceptions import (
    KnowledgeCapacityError,
    KnowledgeRegistryError,
    KnowledgeSessionNotFoundError,
)
from .knowledge_session import KnowledgeSession


class KnowledgeRegistry:
    """
    Thread-safe registry of :class:`KnowledgeSession` objects.

    Active and terminal sessions are stored in separate buckets.
    Archived sessions are additionally subject to a separate cap so they
    do not grow unboundedly in long-running deployments.
    """

    def __init__(
        self,
        max_sessions: int = DEFAULT_MAX_SESSIONS,
        max_archived: int = DEFAULT_MAX_ARCHIVED,
    ) -> None:
        self._max_sessions = max(1, max_sessions)
        self._max_archived = max(1, max_archived)
        self._active: Dict[str, KnowledgeSession]   = {}
        self._archive: Dict[str, KnowledgeSession]  = {}
        self._lock    = threading.Lock()

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def register(self, session: KnowledgeSession) -> None:
        """Register a new session.

        Raises
        ------
        KnowledgeRegistryError
            If a session with the same ID already exists.
        KnowledgeCapacityError
            If the active session cap is reached.
        """
        with self._lock:
            if session.session_id in self._active or session.session_id in self._archive:
                raise KnowledgeRegistryError(
                    f"Session already registered: {session.session_id!r}"
                )
            if len(self._active) >= self._max_sessions:
                raise KnowledgeCapacityError(
                    f"Active session limit reached: {self._max_sessions}",
                    limit=self._max_sessions,
                )
            self._active[session.session_id] = session

    def update(self, session: KnowledgeSession) -> None:
        """Move a session to the archive bucket if it has been archived."""
        with self._lock:
            if session.state == KnowledgeLifecycleState.ARCHIVED:
                self._active.pop(session.session_id, None)
                if len(self._archive) < self._max_archived:
                    self._archive[session.session_id] = session
            # Otherwise just keep it in active (state already mutated in-place)

    def remove(self, session_id: str) -> Optional[KnowledgeSession]:
        """Remove a session from either bucket and return it, or ``None``."""
        with self._lock:
            session = self._active.pop(session_id, None)
            if session is None:
                session = self._archive.pop(session_id, None)
            return session

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get(self, session_id: str) -> KnowledgeSession:
        """Return a session by ID.

        Raises
        ------
        KnowledgeSessionNotFoundError
            If no session with that ID exists.
        """
        with self._lock:
            session = self._active.get(session_id) or self._archive.get(session_id)
        if session is None:
            raise KnowledgeSessionNotFoundError(session_id=session_id)
        return session

    def get_or_none(self, session_id: str) -> Optional[KnowledgeSession]:
        with self._lock:
            return self._active.get(session_id) or self._archive.get(session_id)

    def all_active(self) -> List[KnowledgeSession]:
        """All sessions in non-terminal states."""
        with self._lock:
            return list(self._active.values())

    def all_archived(self) -> List[KnowledgeSession]:
        """All sessions in the ARCHIVED bucket."""
        with self._lock:
            return list(self._archive.values())

    def all(self) -> List[KnowledgeSession]:
        """All sessions (active + archived)."""
        with self._lock:
            result = list(self._active.values())
            result.extend(self._archive.values())
            return result

    def by_state(self, state: KnowledgeLifecycleState) -> List[KnowledgeSession]:
        with self._lock:
            bucket = self._archive if state == KnowledgeLifecycleState.ARCHIVED else self._active
            return [s for s in bucket.values() if s.state == state]

    def by_type(self, knowledge_type: KnowledgeType) -> List[KnowledgeSession]:
        with self._lock:
            all_sessions = list(self._active.values()) + list(self._archive.values())
        return [s for s in all_sessions if s.knowledge_type == knowledge_type]

    def by_scope(self, scope: KnowledgeScope) -> List[KnowledgeSession]:
        with self._lock:
            all_sessions = list(self._active.values()) + list(self._archive.values())
        return [s for s in all_sessions if s.knowledge_scope == scope]

    def contains(self, session_id: str) -> bool:
        with self._lock:
            return session_id in self._active or session_id in self._archive

    # ------------------------------------------------------------------
    # Counts
    # ------------------------------------------------------------------

    def active_count(self) -> int:
        with self._lock:
            return len(self._active)

    def archived_count(self) -> int:
        with self._lock:
            return len(self._archive)

    def total_count(self) -> int:
        with self._lock:
            return len(self._active) + len(self._archive)

    def clear(self) -> None:
        with self._lock:
            self._active.clear()
            self._archive.clear()
