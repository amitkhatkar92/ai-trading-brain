"""iios/execution/sessions/session_manager.py"""
from __future__ import annotations

import threading
from typing import Any

from iios.execution.core.execution_request import ExecutionRequest
from iios.execution.core.execution_session import ExecutionSession
from iios.execution.core.execution_state import ExecutionState
from iios.execution.execution_constants import ExecutionStatus
from iios.execution.execution_exceptions import SessionNotFoundError
from iios.execution.sessions.session_store import SessionStore


class SessionManager:
    """
    Creates, tracks, and closes ExecutionSession objects.

    Owns the SessionStore and ensures thread-safe access.
    """

    def __init__(self, store: SessionStore | None = None) -> None:
        self._store: SessionStore = store or SessionStore()
        self._lock:  threading.RLock = threading.RLock()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def create_session(self, request: ExecutionRequest) -> ExecutionSession:
        with self._lock:
            state = ExecutionState()  # initialises to CREATED
            session = ExecutionSession(
                request=request,
                state=state,
            )
            session.state.execution_id = session.execution_id
            self._store.save(session)
            return session

    def get_session(self, execution_id: str) -> ExecutionSession:
        return self._store.load(execution_id)

    def update_session(self, session: ExecutionSession) -> None:
        self._store.save(session)

    def archive_session(self, execution_id: str) -> None:
        with self._lock:
            session = self._store.load(execution_id)
            if session.can_transition(ExecutionStatus.ARCHIVED):
                session.transition(ExecutionStatus.ARCHIVED, reason="archived by manager")
                self._store.save(session)

    def delete_session(self, execution_id: str) -> None:
        self._store.delete(execution_id)

    # ── Query ─────────────────────────────────────────────────────────────────

    def list_active(self) -> list[ExecutionSession]:
        with self._lock:
            return [
                self._store.load(eid)
                for eid in self._store.list_all()
                if self._store.load(eid).is_active
            ]

    def list_all(self) -> list[ExecutionSession]:
        with self._lock:
            return [self._store.load(eid) for eid in self._store.list_all()]

    def session_exists(self, execution_id: str) -> bool:
        return self._store.exists(execution_id)

    def session_count(self) -> int:
        return self._store.count()

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_count": self._store.count(),
            "store":         self._store.to_dict(),
        }
