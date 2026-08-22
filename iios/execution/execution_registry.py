"""iios/execution/execution_registry.py"""
from __future__ import annotations

import threading
from typing import Any

from iios.execution.core.execution_session    import ExecutionSession
from iios.execution.core.execution_result     import ExecutionResult
from iios.execution.execution_constants       import DEFAULT_MAX_SESSIONS, ExecutionStatus
from iios.execution.execution_exceptions      import (
    RegistryItemAlreadyExistsError,
    RegistryItemNotFoundError,
    RegistryOverflowError,
)


class ExecutionRegistry:
    """
    Thread-safe registry of active and recently completed executions.

    Provides O(1) lookup by execution_id.  Only the most recent N sessions
    are kept to bound memory.
    """

    def __init__(self, max_size: int = DEFAULT_MAX_SESSIONS) -> None:
        self._lock:     threading.RLock = threading.RLock()
        self._sessions: dict[str, ExecutionSession] = {}
        self._results:  dict[str, ExecutionResult]  = {}
        self._max_size = max_size

    # ── Session registry ──────────────────────────────────────────────────────

    def register(self, session: ExecutionSession) -> None:
        with self._lock:
            if session.execution_id in self._sessions:
                raise RegistryItemAlreadyExistsError(
                    f"Execution already registered: {session.execution_id}",
                    item_id=session.execution_id,
                )
            if len(self._sessions) >= self._max_size:
                raise RegistryOverflowError(
                    f"Registry full (max={self._max_size})",
                    capacity=self._max_size,
                    current=len(self._sessions),
                )
            self._sessions[session.execution_id] = session

    def update(self, session: ExecutionSession) -> None:
        with self._lock:
            if session.execution_id not in self._sessions:
                raise RegistryItemNotFoundError(
                    f"Execution not in registry: {session.execution_id}",
                    item_id=session.execution_id,
                )
            self._sessions[session.execution_id] = session

    def get_session(self, execution_id: str) -> ExecutionSession:
        with self._lock:
            session = self._sessions.get(execution_id)
            if session is None:
                raise RegistryItemNotFoundError(
                    f"Execution not found: {execution_id}",
                    item_id=execution_id,
                )
            return session

    def session_exists(self, execution_id: str) -> bool:
        with self._lock:
            return execution_id in self._sessions

    # ── Result registry ───────────────────────────────────────────────────────

    def store_result(self, result: ExecutionResult) -> None:
        with self._lock:
            self._results[result.execution_id] = result

    def get_result(self, execution_id: str) -> ExecutionResult | None:
        with self._lock:
            return self._results.get(execution_id)

    # ── Query ─────────────────────────────────────────────────────────────────

    def list_active(self) -> list[ExecutionSession]:
        with self._lock:
            return [s for s in self._sessions.values() if s.is_active]

    def list_all(self) -> list[ExecutionSession]:
        with self._lock:
            return list(self._sessions.values())

    def count(self) -> int:
        with self._lock:
            return len(self._sessions)

    def active_count(self) -> int:
        with self._lock:
            return sum(1 for s in self._sessions.values() if s.is_active)

    # ── Maintenance ───────────────────────────────────────────────────────────

    def deregister(self, execution_id: str) -> None:
        with self._lock:
            self._sessions.pop(execution_id, None)

    def clear(self) -> None:
        with self._lock:
            self._sessions.clear()
            self._results.clear()

    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            return {
                "count":       len(self._sessions),
                "active":      sum(1 for s in self._sessions.values() if s.is_active),
                "max_size":    self._max_size,
                "result_count": len(self._results),
            }


# ── Module-level singleton ────────────────────────────────────────────────────

_registry:     ExecutionRegistry | None = None
_registry_lock: threading.Lock         = threading.Lock()


def get_execution_registry() -> ExecutionRegistry:
    global _registry
    with _registry_lock:
        if _registry is None:
            _registry = ExecutionRegistry()
        return _registry


def reset_execution_registry() -> None:
    global _registry
    with _registry_lock:
        _registry = None
