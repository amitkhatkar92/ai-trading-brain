"""
integration_registry.py — iios.integration.lifecycle
-----------------------------------------------------
Thread-safe registry of active IntegrationSession objects.

C15 Enterprise Integration & Connectivity — Phase 1, Module 1
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from .constants import DEFAULT_MAX_SESSIONS, IntegrationLifecycleState
from .exceptions import IntegrationCapacityError, IntegrationSessionNotFoundError
from .integration_session import IntegrationSession


class IntegrationRegistry:
    """
    Thread-safe in-memory registry of IntegrationSession objects.

    Keyed by session_id.
    Raises IntegrationCapacityError if max_sessions is exceeded.
    """

    def __init__(self, max_sessions: int = DEFAULT_MAX_SESSIONS) -> None:
        self._max    = max_sessions
        self._store: Dict[str, IntegrationSession] = {}
        self._lock   = threading.Lock()

    # ----------------------------------------------------------------
    # Write
    # ----------------------------------------------------------------

    def register(self, session: IntegrationSession) -> None:
        with self._lock:
            if (
                len(self._store) >= self._max
                and session.session_id not in self._store
            ):
                raise IntegrationCapacityError(limit=self._max)
            self._store[session.session_id] = session

    def deregister(self, session_id: str) -> bool:
        with self._lock:
            if session_id in self._store:
                del self._store[session_id]
                return True
            return False

    # ----------------------------------------------------------------
    # Read
    # ----------------------------------------------------------------

    def get(self, session_id: str) -> Optional[IntegrationSession]:
        with self._lock:
            return self._store.get(session_id)

    def get_or_raise(self, session_id: str) -> IntegrationSession:
        session = self.get(session_id)
        if session is None:
            raise IntegrationSessionNotFoundError(session_id)
        return session

    def all_sessions(self) -> List[IntegrationSession]:
        with self._lock:
            return list(self._store.values())

    def all_session_ids(self) -> List[str]:
        with self._lock:
            return list(self._store.keys())

    def by_state(
        self, state: IntegrationLifecycleState
    ) -> List[IntegrationSession]:
        with self._lock:
            return [s for s in self._store.values() if s.state == state]

    def by_workflow(self, workflow_id: str) -> List[IntegrationSession]:
        with self._lock:
            return [
                s for s in self._store.values()
                if s.workflow_id == workflow_id
            ]

    # ----------------------------------------------------------------
    # Introspection
    # ----------------------------------------------------------------

    def count(self) -> int:
        with self._lock:
            return len(self._store)

    def contains(self, session_id: str) -> bool:
        with self._lock:
            return session_id in self._store

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
