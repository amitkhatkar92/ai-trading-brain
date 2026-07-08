"""
iios/intelligence/sessions/session_manager.py
=============================================
SessionManager — full lifecycle management for IntelligenceSessions.

Supports:
  - Session creation (flat and nested)
  - Session persistence (in-memory, serializable to dict)
  - Session replay (re-execute from stored session data)
  - Session recovery (resume from checkpoint)
  - Session timeout (TTL-based expiry)
  - Nested sessions (parent → child)
  - Concurrent sessions (thread-safe)

Singleton: get_session_manager() / reset_session_manager()
"""

from __future__ import annotations

import threading
import time
from typing import Any, Optional

from ..intelligence_constants import (
    SessionStatus,
    Priority,
    MAX_CONCURRENT_SESSIONS,
    SESSION_TTL_SECONDS,
    SYSTEM_ACTOR,
)
from ..intelligence_exceptions import (
    SessionNotFoundError,
    SessionExpiredError,
    SessionAlreadyActiveError,
    SessionCapacityError,
    SessionRecoveryError,
)
from .intelligence_session import IntelligenceSession
from .session_result        import SessionResult

__all__ = [
    "SessionManager",
    "get_session_manager",
    "reset_session_manager",
]


class SessionManager:
    """
    Thread-safe lifecycle manager for IntelligenceSessions.

    Sessions are stored in memory. Expired sessions are evicted lazily
    (on every create() call that would exceed capacity) and eagerly via
    evict_expired().
    """

    def __init__(self) -> None:
        self._sessions:  dict[str, IntelligenceSession] = {}
        self._children:  dict[str, list[str]]           = {}  # parent_id -> [child_id]
        self._lock       = threading.RLock()

    # ── Create ────────────────────────────────────────────────────────────────

    def create(
        self,
        actor:      str           = SYSTEM_ACTOR,
        priority:   Priority      = Priority.NORMAL,
        parent_id:  Optional[str] = None,
        tags:       list[str] | None = None,
        metadata:   dict | None   = None,
        ttl:        float         = float(SESSION_TTL_SECONDS),
    ) -> IntelligenceSession:
        with self._lock:
            if len(self._sessions) >= MAX_CONCURRENT_SESSIONS:
                evicted = self._evict_expired()
                if len(self._sessions) >= MAX_CONCURRENT_SESSIONS:
                    raise SessionCapacityError(MAX_CONCURRENT_SESSIONS)

            session = IntelligenceSession(
                actor     = actor,
                priority  = priority,
                parent_id = parent_id,
                tags      = tags or [],
                metadata  = metadata or {},
                ttl       = ttl,
            )
            self._sessions[session.session_id] = session
            if parent_id:
                self._children.setdefault(parent_id, []).append(session.session_id)
            return session

    def create_nested(
        self,
        parent_id: str,
        actor:     str      = SYSTEM_ACTOR,
        priority:  Priority = Priority.NORMAL,
    ) -> IntelligenceSession:
        """Create a child session under *parent_id*."""
        self.get(parent_id)   # Raises if parent not found / expired
        return self.create(actor=actor, priority=priority, parent_id=parent_id)

    # ── Retrieve ──────────────────────────────────────────────────────────────

    def get(self, session_id: str) -> IntelligenceSession:
        with self._lock:
            s = self._sessions.get(session_id)
            if s is None:
                raise SessionNotFoundError(session_id)
            if s.is_expired and not s.is_terminal:
                s.expire()
                raise SessionExpiredError(session_id)
            return s

    def get_or_none(self, session_id: str) -> Optional[IntelligenceSession]:
        with self._lock:
            return self._sessions.get(session_id)

    def children_of(self, parent_id: str) -> list[IntelligenceSession]:
        with self._lock:
            ids = self._children.get(parent_id, [])
            return [self._sessions[i] for i in ids if i in self._sessions]

    # ── Lifecycle transitions ─────────────────────────────────────────────────

    def start(self, session_id: str) -> IntelligenceSession:
        s = self.get(session_id)
        with self._lock:
            if s.is_active:
                raise SessionAlreadyActiveError(session_id)
            s.start()
            return s

    def complete(
        self,
        session_id: str,
        result:     Optional[SessionResult] = None,
    ) -> IntelligenceSession:
        s = self.get(session_id)
        with self._lock:
            s.complete(result)
            return s

    def fail(self, session_id: str, reason: str = "") -> IntelligenceSession:
        s = self.get(session_id)
        with self._lock:
            s.fail(reason)
            return s

    def pause(self, session_id: str) -> IntelligenceSession:
        s = self.get(session_id)
        with self._lock:
            s.pause()
            return s

    def resume(self, session_id: str) -> IntelligenceSession:
        s = self.get(session_id)
        with self._lock:
            s.resume()
            return s

    def cancel(self, session_id: str) -> IntelligenceSession:
        with self._lock:
            s = self._sessions.get(session_id)
            if s is None:
                raise SessionNotFoundError(session_id)
            s.cancel()
            return s

    # ── Recovery ──────────────────────────────────────────────────────────────

    def recover(
        self,
        session_id:    str,
        checkpoint_id: Optional[str] = None,
    ) -> IntelligenceSession:
        """
        Mark a session for recovery.

        The caller is responsible for re-executing the session from
        the checkpoint.  This method simply transitions the status to
        RECOVERING and records the checkpoint ID.
        """
        with self._lock:
            s = self._sessions.get(session_id)
            if s is None:
                raise SessionRecoveryError(session_id, "session not found")
            if s.is_terminal and s.status != SessionStatus.FAILED:
                raise SessionRecoveryError(
                    session_id,
                    f"cannot recover a {s.status.value} session",
                )
            s.mark_recovering(checkpoint_id)
            return s

    # ── Persistence ───────────────────────────────────────────────────────────

    def snapshot(self, session_id: str) -> dict:
        """Serialise session to dict (for persistence / replay)."""
        return self.get(session_id).to_dict()

    def all_snapshots(self) -> list[dict]:
        with self._lock:
            return [s.to_dict() for s in self._sessions.values()]

    # ── Eviction ──────────────────────────────────────────────────────────────

    def evict_expired(self) -> int:
        with self._lock:
            return self._evict_expired()

    def _evict_expired(self) -> int:
        now = time.time()
        expired = [
            sid for sid, s in self._sessions.items()
            if (now - s.created_at) > s.ttl and not s.is_terminal
        ]
        for sid in expired:
            s = self._sessions[sid]
            s.expire()
        # Remove terminal sessions beyond capacity
        terminal = [
            sid for sid, s in self._sessions.items()
            if s.is_terminal
        ]
        for sid in terminal:
            del self._sessions[sid]
            self._children.pop(sid, None)
        return len(expired)

    def close(self, session_id: str) -> bool:
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                self._children.pop(session_id, None)
                return True
            return False

    def clear(self) -> None:
        with self._lock:
            self._sessions.clear()
            self._children.clear()

    # ── Query ─────────────────────────────────────────────────────────────────

    def active_sessions(self) -> list[IntelligenceSession]:
        with self._lock:
            return [s for s in self._sessions.values() if s.is_active]

    def all_sessions(self) -> list[IntelligenceSession]:
        with self._lock:
            return list(self._sessions.values())

    def stats(self) -> dict:
        with self._lock:
            total    = len(self._sessions)
            active   = sum(1 for s in self._sessions.values() if s.is_active)
            terminal = sum(1 for s in self._sessions.values() if s.is_terminal)
            nested   = sum(1 for s in self._sessions.values() if s.is_nested)
            return {
                "total":    total,
                "active":   active,
                "terminal": terminal,
                "nested":   nested,
                "capacity": MAX_CONCURRENT_SESSIONS,
            }


# ── Singleton ─────────────────────────────────────────────────────────────────

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
