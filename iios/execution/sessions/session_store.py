"""iios/execution/sessions/session_store.py"""
from __future__ import annotations

import threading
from typing import Any

from iios.execution.core.execution_session import ExecutionSession
from iios.execution.execution_exceptions import (
    SessionAlreadyExistsError,
    SessionNotFoundError,
)


class SessionStore:
    """
    Thread-safe in-memory key/value store for ExecutionSession objects.

    Each session is keyed by its ``execution_id``.  This is intentionally
    simple — a future phase may replace it with Redis or a database backend.
    """

    def __init__(self, max_size: int = 10_000) -> None:
        self._lock: threading.RLock = threading.RLock()
        self._data: dict[str, ExecutionSession] = {}
        self._max_size = max_size

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def save(self, session: ExecutionSession) -> None:
        with self._lock:
            if session.execution_id in self._data:
                # Update in-place.
                self._data[session.execution_id] = session
            else:
                if len(self._data) >= self._max_size:
                    from iios.execution.execution_exceptions import RegistryOverflowError
                    raise RegistryOverflowError(
                        f"SessionStore full (max={self._max_size})",
                        capacity=self._max_size,
                        current=len(self._data),
                    )
                self._data[session.execution_id] = session

    def load(self, execution_id: str) -> ExecutionSession:
        with self._lock:
            session = self._data.get(execution_id)
            if session is None:
                raise SessionNotFoundError(
                    f"Session not found: {execution_id}",
                    session_id=execution_id,
                )
            return session

    def exists(self, execution_id: str) -> bool:
        with self._lock:
            return execution_id in self._data

    def delete(self, execution_id: str) -> None:
        with self._lock:
            if execution_id not in self._data:
                raise SessionNotFoundError(
                    f"Session not found: {execution_id}",
                    session_id=execution_id,
                )
            del self._data[execution_id]

    def list_all(self) -> list[str]:
        with self._lock:
            return list(self._data.keys())

    def count(self) -> int:
        with self._lock:
            return len(self._data)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            return {
                "count":    len(self._data),
                "max_size": self._max_size,
            }
