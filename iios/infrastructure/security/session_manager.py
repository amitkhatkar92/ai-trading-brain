"""
iios/infrastructure/security/session_manager.py
================================================
Manages authenticated sessions with TTL, idle timeout, and invalidation.
"""

from __future__ import annotations

import logging
import secrets
import threading
import time
from typing import Any, Optional

from .security_constants import (
    AuthMethod,
    SessionStatus,
    DEFAULT_SESSION_TTL,
    SESSION_ID_LENGTH_BYTES,
)
from .security_exceptions import SessionNotFoundError, SessionExpiredError, SessionInvalidError
from .security_models import SessionRecord

__all__ = ["SessionManager", "get_session_manager", "reset_session_manager"]

_LOG = logging.getLogger("iios.security.session")
_mgr_lock = threading.Lock()
_manager: Optional["SessionManager"] = None


class SessionManager:
    """Thread-safe session lifecycle manager.

    Sessions are stored in-memory with configurable TTL and idle timeout.
    Background cleanup of expired sessions can be triggered manually.

    Usage::

        mgr = get_session_manager()
        session = mgr.create("user:alice", auth_method=AuthMethod.PASSWORD)
        mgr.touch(session.session_id)   # update last_active
        mgr.terminate(session.session_id)
    """

    def __init__(
        self,
        default_ttl: int = DEFAULT_SESSION_TTL,
        idle_timeout: Optional[int] = None,
    ) -> None:
        self._lock = threading.RLock()
        self._sessions: dict[str, SessionRecord] = {}
        self._default_ttl = default_ttl
        self._idle_timeout = idle_timeout  # seconds of inactivity before auto-expire

    # ── Create / Destroy ──────────────────────────────────────────────────────

    def create(
        self,
        principal_id: str,
        auth_method: AuthMethod = AuthMethod.PASSWORD,
        ttl: Optional[int] = None,
        ip_address: str = "",
        user_agent: str = "",
        data: Optional[dict[str, Any]] = None,
    ) -> SessionRecord:
        """Create and store a new session. Returns the SessionRecord."""
        effective_ttl = ttl if ttl is not None else self._default_ttl
        session_id = secrets.token_hex(SESSION_ID_LENGTH_BYTES)
        now = time.time()
        session = SessionRecord(
            session_id=session_id,
            principal_id=principal_id,
            status=SessionStatus.ACTIVE,
            auth_method=auth_method,
            created_at=now,
            last_active=now,
            expires_at=now + effective_ttl,
            ip_address=ip_address,
            user_agent=user_agent,
            data=dict(data or {}),
        )
        with self._lock:
            self._sessions[session_id] = session
        _LOG.debug("Session created: %s for %s", session_id[:8], principal_id)
        return session

    def get(self, session_id: str) -> SessionRecord:
        """Return a valid session. Raises SessionNotFoundError / SessionExpiredError."""
        with self._lock:
            session = self._sessions.get(session_id)
        if session is None:
            raise SessionNotFoundError(
                f"Session '{session_id[:8]}' not found",
                code="SEC-SESS-001",
                context={"session_id": session_id},
            )
        if self._is_expired(session):
            session.status = SessionStatus.EXPIRED
            raise SessionExpiredError(
                "Session has expired",
                code="SEC-SESS-002",
                context={"session_id": session_id},
            )
        return session

    def get_optional(self, session_id: str) -> Optional[SessionRecord]:
        try:
            return self.get(session_id)
        except (SessionNotFoundError, SessionExpiredError):
            return None

    def touch(self, session_id: str) -> None:
        """Update the last-active timestamp on a session (keep-alive)."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session and not self._is_expired(session):
                session.touch()

    def terminate(self, session_id: str) -> bool:
        """Immediately invalidate a session. Returns True if it existed."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False
            session.status = SessionStatus.TERMINATED
            del self._sessions[session_id]
        _LOG.debug("Session terminated: %s", session_id[:8])
        return True

    def terminate_all(self, principal_id: str) -> int:
        """Terminate all sessions for *principal_id*. Returns count terminated."""
        with self._lock:
            to_remove = [
                sid for sid, s in self._sessions.items()
                if s.principal_id == principal_id
            ]
            for sid in to_remove:
                self._sessions.pop(sid, None)
        _LOG.debug("Terminated %d sessions for %s", len(to_remove), principal_id)
        return len(to_remove)

    # ── Lookup ────────────────────────────────────────────────────────────────

    def list_for(self, principal_id: str) -> list[SessionRecord]:
        with self._lock:
            return [
                s for s in self._sessions.values()
                if s.principal_id == principal_id and not self._is_expired(s)
            ]

    def count(self) -> int:
        return sum(1 for s in self._sessions.values() if not self._is_expired(s))

    # ── Data store on session ─────────────────────────────────────────────────

    def set_data(self, session_id: str, key: str, value: Any) -> None:
        session = self.get(session_id)
        session.data[key] = value
        session.touch()

    def get_data(self, session_id: str, key: str, default: Any = None) -> Any:
        session = self.get(session_id)
        return session.data.get(key, default)

    # ── Maintenance ───────────────────────────────────────────────────────────

    def purge_expired(self) -> int:
        """Remove all expired sessions. Returns count removed."""
        with self._lock:
            expired = [
                sid for sid, s in self._sessions.items()
                if self._is_expired(s)
            ]
            for sid in expired:
                del self._sessions[sid]
        return len(expired)

    def _is_expired(self, session: SessionRecord) -> bool:
        if session.status in (SessionStatus.TERMINATED, SessionStatus.EXPIRED):
            return True
        if session.is_expired:
            return True
        if self._idle_timeout is not None:
            if time.time() - session.last_active > self._idle_timeout:
                return True
        return False

    def reset(self) -> None:
        with self._lock:
            self._sessions.clear()


# ── Singleton ─────────────────────────────────────────────────────────────────

def get_session_manager() -> SessionManager:
    global _manager
    with _mgr_lock:
        if _manager is None:
            _manager = SessionManager()
        return _manager


def reset_session_manager() -> None:
    global _manager
    with _mgr_lock:
        if _manager is not None:
            _manager.reset()
        _manager = None
