"""iios/execution/gateway/brokers/broker_session.py
==================================================
BrokerSession and BrokerSessionManager — authentication session
management for the Broker Abstraction Layer.

Sessions track authentication state and token expiry metadata.
Credentials and tokens are NEVER stored here.

C6 Execution Intelligence — Phase 5, Module 3
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Dict, List, Optional

from .constants import DEFAULT_SESSION_TIMEOUT_SECS
from .exceptions import BrokerNotRegisteredError, BrokerSessionExpiredError


# ── BrokerSession ─────────────────────────────────────────────────────────────

class BrokerSession:
    """
    Mutable authentication session record for a single broker.

    Tracks whether the broker is authenticated, when the session
    expires, and how many times it has been refreshed.

    Security note
    -------------
    No credentials, tokens, or API keys are stored here.
    The session only records the presence and expiry of authentication.
    """

    __slots__ = (
        "_broker_id",
        "_session_id",
        "_is_authenticated",
        "_created_at",
        "_expires_at",
        "_last_refreshed_at",
        "_refresh_count",
        "_lock",
    )

    def __init__(self, broker_id: str) -> None:
        self._broker_id          = broker_id
        self._session_id:         Optional[str]   = None
        self._is_authenticated    = False
        self._created_at          = time.time()
        self._expires_at:         Optional[float] = None
        self._last_refreshed_at:  Optional[float] = None
        self._refresh_count       = 0
        self._lock                = threading.RLock()

    # ── Identity ──────────────────────────────────────────────────────────────

    @property
    def broker_id(self) -> str:
        return self._broker_id

    @property
    def session_id(self) -> Optional[str]:
        with self._lock:
            return self._session_id

    # ── State transitions ─────────────────────────────────────────────────────

    def mark_authenticated(
        self,
        timeout_secs: float = DEFAULT_SESSION_TIMEOUT_SECS,
        *,
        session_id: Optional[str] = None,
    ) -> None:
        """
        Record a successful authentication.

        Parameters
        ----------
        timeout_secs:
            Seconds until this session expires.
        session_id:
            Optional external session identifier (e.g., broker-assigned token ID).
        """
        with self._lock:
            self._session_id       = session_id or str(uuid.uuid4())
            self._is_authenticated = True
            self._expires_at       = time.time() + max(0.0, timeout_secs)
            self._last_refreshed_at = time.time()

    def refresh(self, timeout_secs: float = DEFAULT_SESSION_TIMEOUT_SECS) -> None:
        """Extend the session expiry and increment the refresh counter."""
        with self._lock:
            self._expires_at        = time.time() + max(0.0, timeout_secs)
            self._last_refreshed_at = time.time()
            self._refresh_count    += 1

    def mark_expired(self) -> None:
        """Explicitly mark the session as expired."""
        with self._lock:
            self._is_authenticated = False
            self._expires_at       = time.time()

    def mark_disconnected(self) -> None:
        """Clear authentication state on disconnect."""
        with self._lock:
            self._is_authenticated = False
            self._session_id       = None
            self._expires_at       = None

    # ── Queries ───────────────────────────────────────────────────────────────

    @property
    def is_authenticated(self) -> bool:
        """True when authenticated AND session has not expired."""
        with self._lock:
            if not self._is_authenticated:
                return False
            if self._expires_at is None:
                return False
            return time.time() < self._expires_at

    @property
    def is_expired(self) -> bool:
        """True when session exists but expiry time has passed."""
        with self._lock:
            if not self._is_authenticated or self._expires_at is None:
                return False
            return time.time() >= self._expires_at

    @property
    def expires_at(self) -> Optional[float]:
        with self._lock:
            return self._expires_at

    @property
    def last_refreshed_at(self) -> Optional[float]:
        with self._lock:
            return self._last_refreshed_at

    @property
    def refresh_count(self) -> int:
        with self._lock:
            return self._refresh_count

    @property
    def seconds_until_expiry(self) -> float:
        """Seconds remaining before expiry; 0.0 if already expired or no session."""
        with self._lock:
            if self._expires_at is None:
                return 0.0
            return max(0.0, self._expires_at - time.time())

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "broker_id":         self._broker_id,
                "session_id":        self._session_id,
                "is_authenticated":  self._is_authenticated,
                "created_at":        self._created_at,
                "expires_at":        self._expires_at,
                "last_refreshed_at": self._last_refreshed_at,
                "refresh_count":     self._refresh_count,
                "seconds_remaining": max(0.0, (self._expires_at or 0) - time.time()),
            }

    def __repr__(self) -> str:
        return (
            f"BrokerSession("
            f"broker_id={self._broker_id!r}, "
            f"authenticated={self.is_authenticated}"
            f")"
        )


# ── BrokerSessionManager ──────────────────────────────────────────────────────

class BrokerSessionManager:
    """
    Thread-safe manager for BrokerSession objects, one per registered broker.
    """

    def __init__(self) -> None:
        self._sessions: Dict[str, BrokerSession] = {}
        self._lock      = threading.Lock()

    # ── Session creation / removal ────────────────────────────────────────────

    def create_session(self, broker_id: str) -> BrokerSession:
        """Create and register a session for a broker."""
        session = BrokerSession(broker_id)
        with self._lock:
            self._sessions[broker_id] = session
        return session

    def remove_session(self, broker_id: str) -> None:
        """Remove the session for a broker (called on de-registration)."""
        with self._lock:
            self._sessions.pop(broker_id, None)

    def clear(self) -> None:
        """Remove all sessions."""
        with self._lock:
            self._sessions.clear()

    # ── Queries ───────────────────────────────────────────────────────────────

    def get_session(self, broker_id: str) -> BrokerSession:
        """Return the session for a broker.  Raises BrokerNotRegisteredError if absent."""
        with self._lock:
            session = self._sessions.get(broker_id)
        if session is None:
            raise BrokerNotRegisteredError(broker_id)
        return session

    def get_session_optional(self, broker_id: str) -> Optional[BrokerSession]:
        with self._lock:
            return self._sessions.get(broker_id)

    def is_authenticated(self, broker_id: str) -> bool:
        """Return True if the broker has a valid, non-expired session."""
        with self._lock:
            session = self._sessions.get(broker_id)
        return session is not None and session.is_authenticated

    def expire_stale_sessions(self) -> int:
        """
        Mark all expired sessions as explicitly expired.

        Returns the number of sessions that were expired.
        """
        count = 0
        with self._lock:
            snapshot = list(self._sessions.values())
        for session in snapshot:
            if session.is_expired:
                session.mark_expired()
                count += 1
        return count

    def all_sessions(self) -> List[BrokerSession]:
        with self._lock:
            return list(self._sessions.values())

    def authenticated_sessions(self) -> List[BrokerSession]:
        with self._lock:
            return [s for s in self._sessions.values() if s.is_authenticated]

    def count(self) -> int:
        with self._lock:
            return len(self._sessions)

    def authenticated_count(self) -> int:
        with self._lock:
            return sum(1 for s in self._sessions.values() if s.is_authenticated)
