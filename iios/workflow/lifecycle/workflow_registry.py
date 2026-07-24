"""
workflow_registry.py — iios.workflow.lifecycle
-----------------------------------------------
Thread-safe registry of active WorkflowSession objects.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 1
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from .constants import DEFAULT_MAX_SESSIONS, WorkflowLifecycleState
from .exceptions import WorkflowCapacityError, WorkflowSessionNotFoundError
from .workflow_session import WorkflowSession


class WorkflowRegistry:
    """
    Thread-safe in-memory registry of WorkflowSession objects.

    Keyed by session_id.
    Raises WorkflowCapacityError if max_sessions is exceeded.
    """

    def __init__(self, max_sessions: int = DEFAULT_MAX_SESSIONS) -> None:
        self._max    = max_sessions
        self._store: Dict[str, WorkflowSession] = {}
        self._lock   = threading.Lock()

    # ----------------------------------------------------------------
    # Write
    # ----------------------------------------------------------------

    def register(self, session: WorkflowSession) -> None:
        with self._lock:
            if (
                len(self._store) >= self._max
                and session.session_id not in self._store
            ):
                raise WorkflowCapacityError(limit=self._max)
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

    def get(self, session_id: str) -> Optional[WorkflowSession]:
        with self._lock:
            return self._store.get(session_id)

    def get_or_raise(self, session_id: str) -> WorkflowSession:
        session = self.get(session_id)
        if session is None:
            raise WorkflowSessionNotFoundError(session_id)
        return session

    def all_sessions(self) -> List[WorkflowSession]:
        with self._lock:
            return list(self._store.values())

    def all_session_ids(self) -> List[str]:
        with self._lock:
            return list(self._store.keys())

    def by_state(
        self, state: WorkflowLifecycleState
    ) -> List[WorkflowSession]:
        with self._lock:
            return [s for s in self._store.values() if s.state == state]

    def by_workflow(self, workflow_id: str) -> List[WorkflowSession]:
        with self._lock:
            return [
                s for s in self._store.values()
                if s.workflow_id == workflow_id
            ]

    def by_enterprise(self, enterprise_id: str) -> List[WorkflowSession]:
        with self._lock:
            return [
                s for s in self._store.values()
                if s.enterprise_id == enterprise_id
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

    @property
    def max_sessions(self) -> int:
        return self._max
