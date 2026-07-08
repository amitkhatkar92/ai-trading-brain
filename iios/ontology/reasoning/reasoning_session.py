"""
iios/ontology/reasoning/reasoning_session.py
=============================================
Session lifecycle management for the reasoning engine.

Sessions are lightweight containers that hold the request, result,
and trace for one reasoning operation.  They expire after SESSION_TTL_SECONDS.

Singleton: get_session_manager() / reset_session_manager()
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

from .reasoning_constants import (
    InferenceStatus,
    SESSION_TTL_SECONDS,
    MAX_SESSIONS,
)
from .reasoning_exceptions import SessionNotFoundError, SessionExpiredError
from .reasoning_factory    import ReasoningRequest
from .reasoning_result     import ReasoningResult
from .reasoning_trace      import ReasoningTrace

__all__ = [
    "ReasoningSession",
    "SessionManager",
    "get_session_manager",
    "reset_session_manager",
]


@dataclass
class ReasoningSession:
    """Tracks a single reasoning operation from creation to completion."""
    session_id:  str
    request:     ReasoningRequest
    status:      InferenceStatus              = InferenceStatus.PENDING
    result:      Optional[ReasoningResult]    = None
    trace:       Optional[ReasoningTrace]     = None
    created_at:  float                        = field(default_factory=time.time)
    finished_at: Optional[float]              = None
    ttl:         float                        = float(SESSION_TTL_SECONDS)

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > self.ttl

    @property
    def is_active(self) -> bool:
        return self.status in (InferenceStatus.PENDING, InferenceStatus.RUNNING)

    @property
    def duration_ms(self) -> float:
        end = self.finished_at or time.time()
        return (end - self.created_at) * 1_000.0

    def complete(self, result: ReasoningResult, trace: ReasoningTrace) -> None:
        self.result      = result
        self.trace       = trace
        self.status      = result.status
        self.finished_at = time.time()

    def fail(self, error: str) -> None:
        self.status      = InferenceStatus.FAILED
        self.finished_at = time.time()

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "status":     self.status.value,
            "reasoning_type": self.request.reasoning_type.value,
            "target_uri": self.request.target_uri,
            "created_at": self.created_at,
            "duration_ms": round(self.duration_ms, 3),
            "is_expired": self.is_expired,
        }


class SessionManager:
    """Thread-safe registry for active and completed reasoning sessions."""

    def __init__(self) -> None:
        self._sessions: dict[str, ReasoningSession] = {}
        self._lock      = threading.RLock()

    def create(self, request: ReasoningRequest) -> ReasoningSession:
        with self._lock:
            if len(self._sessions) >= MAX_SESSIONS:
                self._evict_expired()
            session = ReasoningSession(
                session_id = str(uuid.uuid4()),
                request    = request,
                status     = InferenceStatus.RUNNING,
            )
            self._sessions[session.session_id] = session
            return session

    def get(self, session_id: str) -> ReasoningSession:
        with self._lock:
            s = self._sessions.get(session_id)
            if s is None:
                raise SessionNotFoundError(session_id)
            if s.is_expired:
                raise SessionExpiredError(session_id)
            return s

    def get_or_none(self, session_id: str) -> Optional[ReasoningSession]:
        with self._lock:
            return self._sessions.get(session_id)

    def close(self, session_id: str) -> bool:
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                return True
            return False

    def active_sessions(self) -> list[ReasoningSession]:
        with self._lock:
            return [s for s in self._sessions.values() if s.is_active]

    def all_sessions(self) -> list[ReasoningSession]:
        with self._lock:
            return list(self._sessions.values())

    def _evict_expired(self) -> int:
        expired = [sid for sid, s in self._sessions.items() if s.is_expired]
        for sid in expired:
            del self._sessions[sid]
        return len(expired)

    def evict_expired(self) -> int:
        with self._lock:
            return self._evict_expired()

    def stats(self) -> dict:
        with self._lock:
            total    = len(self._sessions)
            active   = sum(1 for s in self._sessions.values() if s.is_active)
            expired  = sum(1 for s in self._sessions.values() if s.is_expired)
            return {
                "total":   total,
                "active":  active,
                "expired": expired,
            }

    def clear(self) -> None:
        with self._lock:
            self._sessions.clear()


_sm_lock = threading.Lock()
_sm_inst: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    global _sm_inst
    if _sm_inst is None:
        with _sm_lock:
            if _sm_inst is None:
                _sm_inst = SessionManager()
    return _sm_inst


def reset_session_manager() -> None:
    global _sm_inst
    with _sm_lock:
        _sm_inst = None
