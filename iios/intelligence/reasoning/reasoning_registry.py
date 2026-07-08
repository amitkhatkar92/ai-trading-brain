"""
iios/intelligence/reasoning/reasoning_registry.py
=================================================
Thread-safe registry for ReasoningSession objects.
"""
from __future__ import annotations

import threading
from typing import Any

from .reasoning_constants import ReasoningStatus, MAX_REASONING_SESSIONS
from .reasoning_exceptions import (
    SessionAlreadyExistsError,
    SessionNotFoundError,
)
from .reasoning_session import ReasoningSession


class ReasoningSessionRegistry:
    """Thread-safe, in-memory store for ReasoningSession objects."""

    def __init__(self) -> None:
        self._sessions: dict[str, ReasoningSession] = {}
        self._lock:     threading.RLock              = threading.RLock()

    # -- Write ─────────────────────────────────────────────────────────────────

    def register(
        self,
        session:   ReasoningSession,
        overwrite: bool = False,
    ) -> None:
        with self._lock:
            if not overwrite and session.session_id in self._sessions:
                raise SessionAlreadyExistsError(session.session_id)
            if len(self._sessions) >= MAX_REASONING_SESSIONS and session.session_id not in self._sessions:
                raise OverflowError(
                    f"ReasoningSessionRegistry is full "
                    f"(max {MAX_REASONING_SESSIONS} sessions)"
                )
            self._sessions[session.session_id] = session

    def unregister(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)

    # -- Read ──────────────────────────────────────────────────────────────────

    def get(self, session_id: str) -> ReasoningSession:
        with self._lock:
            s = self._sessions.get(session_id)
        if s is None:
            raise SessionNotFoundError(session_id)
        return s

    def has(self, session_id: str) -> bool:
        with self._lock:
            return session_id in self._sessions

    def list_by_status(
        self, status: ReasoningStatus
    ) -> list[ReasoningSession]:
        with self._lock:
            return [s for s in self._sessions.values() if s.status == status]

    def list_active(self) -> list[ReasoningSession]:
        with self._lock:
            return [
                s for s in self._sessions.values()
                if s.status in (ReasoningStatus.RUNNING, ReasoningStatus.PAUSED)
            ]

    def all(self) -> list[ReasoningSession]:
        with self._lock:
            return list(self._sessions.values())

    # -- Stats ─────────────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        with self._lock:
            by_status: dict[str, int] = {}
            for s in self._sessions.values():
                k = s.status.value
                by_status[k] = by_status.get(k, 0) + 1
            return {
                "total":    len(self._sessions),
                "active":   len([s for s in self._sessions.values()
                                 if s.status == ReasoningStatus.RUNNING]),
                "by_status": by_status,
                "capacity":  MAX_REASONING_SESSIONS,
            }


# ── Singleton ──────────────────────────────────────────────────────────────────

_LOCK:     threading.Lock                 = threading.Lock()
_REGISTRY: ReasoningSessionRegistry | None = None


def get_session_registry() -> ReasoningSessionRegistry:
    global _REGISTRY
    if _REGISTRY is None:
        with _LOCK:
            if _REGISTRY is None:
                _REGISTRY = ReasoningSessionRegistry()
    return _REGISTRY


def reset_session_registry() -> None:
    global _REGISTRY
    with _LOCK:
        _REGISTRY = None
