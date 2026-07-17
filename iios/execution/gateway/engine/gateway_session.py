"""iios/execution/gateway/engine/gateway_session.py
==================================================
GatewaySession and GatewaySessionManager — session management for
the Execution Gateway Engine.

Each session groups one or more gateway requests from the same
execution context (portfolio + strategy + execution ID).

C6 Execution Intelligence — Phase 5, Module 2
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .constants import (
    DEFAULT_MAX_SESSIONS,
    DEFAULT_SESSION_TIMEOUT_SECS,
    SessionStatus,
)
from .exceptions import (
    GatewaySessionExpiredError,
    GatewaySessionNotFoundError,
)


# ── GatewaySession ────────────────────────────────────────────────────────────

class GatewaySession:
    """
    Mutable session record grouping related gateway requests.

    Thread safety is provided by an internal RLock.
    """

    __slots__ = (
        "_session_id",
        "_portfolio_id",
        "_strategy_id",
        "_execution_id",
        "_status",
        "_created_at",
        "_updated_at",
        "_expires_at",
        "_request_ids",
        "_metadata",
        "_lock",
    )

    def __init__(
        self,
        session_id:      str,
        portfolio_id:    str,
        strategy_id:     str,
        execution_id:    str,
        timeout_secs:    float = DEFAULT_SESSION_TIMEOUT_SECS,
        metadata:        Optional[Dict[str, Any]] = None,
    ) -> None:
        now = time.time()
        self._session_id   = session_id
        self._portfolio_id = portfolio_id
        self._strategy_id  = strategy_id
        self._execution_id = execution_id
        self._status       = SessionStatus.ACTIVE
        self._created_at   = now
        self._updated_at   = now
        self._expires_at   = now + max(0.0, timeout_secs)
        self._request_ids: List[str] = []
        self._metadata:    Dict[str, Any] = dict(metadata or {})
        self._lock         = threading.RLock()

    # ── Identity ──────────────────────────────────────────────────────────────

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def portfolio_id(self) -> str:
        return self._portfolio_id

    @property
    def strategy_id(self) -> str:
        return self._strategy_id

    @property
    def execution_id(self) -> str:
        return self._execution_id

    # ── Status ────────────────────────────────────────────────────────────────

    @property
    def status(self) -> SessionStatus:
        with self._lock:
            return self._status

    @property
    def is_active(self) -> bool:
        with self._lock:
            return self._status == SessionStatus.ACTIVE

    @property
    def is_expired(self) -> bool:
        with self._lock:
            return (
                self._status == SessionStatus.EXPIRED
                or (self._status == SessionStatus.ACTIVE and time.time() > self._expires_at)
            )

    @property
    def is_closed(self) -> bool:
        with self._lock:
            return self._status == SessionStatus.CLOSED

    # ── Timing ────────────────────────────────────────────────────────────────

    @property
    def created_at(self) -> float:
        return self._created_at

    @property
    def expires_at(self) -> float:
        with self._lock:
            return self._expires_at

    @property
    def updated_at(self) -> float:
        with self._lock:
            return self._updated_at

    # ── Requests ──────────────────────────────────────────────────────────────

    def add_request(self, request_id: str) -> None:
        with self._lock:
            if request_id not in self._request_ids:
                self._request_ids.append(request_id)
                self._updated_at = time.time()

    @property
    def request_ids(self) -> List[str]:
        with self._lock:
            return list(self._request_ids)

    @property
    def request_count(self) -> int:
        with self._lock:
            return len(self._request_ids)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def expire(self) -> None:
        with self._lock:
            if self._status == SessionStatus.ACTIVE:
                self._status     = SessionStatus.EXPIRED
                self._updated_at = time.time()

    def close(self) -> None:
        with self._lock:
            if self._status not in (SessionStatus.CLOSED,):
                self._status     = SessionStatus.CLOSED
                self._updated_at = time.time()

    def extend(self, extra_secs: float) -> None:
        """Extend session expiry."""
        with self._lock:
            self._expires_at += max(0.0, extra_secs)
            self._updated_at  = time.time()

    def touch(self) -> None:
        """Update the last-updated timestamp."""
        with self._lock:
            self._updated_at = time.time()

    # ── Metadata ──────────────────────────────────────────────────────────────

    @property
    def metadata(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._metadata)

    def set_metadata(self, key: str, value: Any) -> None:
        with self._lock:
            self._metadata[key] = value
            self._updated_at    = time.time()

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "session_id":    self._session_id,
                "portfolio_id":  self._portfolio_id,
                "strategy_id":   self._strategy_id,
                "execution_id":  self._execution_id,
                "status":        self._status.value,
                "created_at":    self._created_at,
                "updated_at":    self._updated_at,
                "expires_at":    self._expires_at,
                "request_count": len(self._request_ids),
                "request_ids":   list(self._request_ids),
                "metadata":      dict(self._metadata),
            }

    def __repr__(self) -> str:
        return (
            f"GatewaySession("
            f"session_id={self._session_id!r}, "
            f"status={self._status.value!r}, "
            f"requests={len(self._request_ids)})"
        )


# ── GatewaySessionManager ─────────────────────────────────────────────────────

class GatewaySessionManager:
    """
    Thread-safe manager for GatewaySession objects.

    Responsibilities
    ----------------
    * Create sessions.
    * Look up sessions by ID.
    * Expire stale sessions.
    * Add request IDs to sessions.
    * Close sessions on demand.
    """

    def __init__(
        self,
        max_sessions:    int   = DEFAULT_MAX_SESSIONS,
        timeout_secs:    float = DEFAULT_SESSION_TIMEOUT_SECS,
    ) -> None:
        self._max_sessions = max(1, max_sessions)
        self._timeout_secs = max(0.0, timeout_secs)
        self._sessions:    Dict[str, GatewaySession] = {}
        self._lock         = threading.RLock()

    # ── Create ────────────────────────────────────────────────────────────────

    def create_session(
        self,
        portfolio_id: str,
        strategy_id:  str,
        execution_id: str,
        *,
        session_id: Optional[str] = None,
        metadata:   Optional[Dict[str, Any]] = None,
    ) -> GatewaySession:
        """Create and register a new session."""
        sid = session_id or str(uuid.uuid4())
        session = GatewaySession(
            session_id=sid,
            portfolio_id=portfolio_id,
            strategy_id=strategy_id,
            execution_id=execution_id,
            timeout_secs=self._timeout_secs,
            metadata=metadata,
        )
        with self._lock:
            self._sessions[sid] = session
        return session

    # ── Lookup ────────────────────────────────────────────────────────────────

    def get_session(self, session_id: str) -> GatewaySession:
        with self._lock:
            session = self._sessions.get(session_id)
        if session is None:
            raise GatewaySessionNotFoundError(session_id)
        return session

    def get_session_optional(self, session_id: str) -> Optional[GatewaySession]:
        with self._lock:
            return self._sessions.get(session_id)

    def exists(self, session_id: str) -> bool:
        with self._lock:
            return session_id in self._sessions

    # ── Mutations ─────────────────────────────────────────────────────────────

    def add_request_to_session(self, session_id: str, request_id: str) -> None:
        session = self.get_session(session_id)
        if session.is_expired:
            raise GatewaySessionExpiredError(session_id)
        session.add_request(request_id)

    def close_session(self, session_id: str) -> None:
        session = self.get_session(session_id)
        session.close()

    def expire_stale_sessions(self) -> int:
        """Expire all sessions past their deadline.  Returns the count expired."""
        expired = 0
        with self._lock:
            sessions = list(self._sessions.values())
        for session in sessions:
            if (
                session.status == SessionStatus.ACTIVE
                and time.time() > session.expires_at
            ):
                session.expire()
                expired += 1
        return expired

    # ── Query ─────────────────────────────────────────────────────────────────

    def all_sessions(self) -> List[GatewaySession]:
        with self._lock:
            return list(self._sessions.values())

    def active_sessions(self) -> List[GatewaySession]:
        with self._lock:
            return [s for s in self._sessions.values() if s.is_active]

    def expired_sessions(self) -> List[GatewaySession]:
        with self._lock:
            return [s for s in self._sessions.values() if s.is_expired]

    # ── Counts ────────────────────────────────────────────────────────────────

    @property
    def session_count(self) -> int:
        with self._lock:
            return len(self._sessions)

    @property
    def active_count(self) -> int:
        with self._lock:
            return sum(1 for s in self._sessions.values() if s.is_active)

    @property
    def capacity(self) -> int:
        return self._max_sessions

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "session_count":  len(self._sessions),
                "active_count":   sum(1 for s in self._sessions.values() if s.is_active),
                "capacity":       self._max_sessions,
                "timeout_secs":   self._timeout_secs,
            }
