"""iios/execution/brokers/authentication/session_manager.py"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any

from iios.execution.brokers.broker_constants import AuthMethod, DEFAULT_SESSION_TTL_SEC
from iios.execution.brokers.broker_exceptions import (
    AuthenticationExpiredError,
    AuthenticationFailedError,
)
from iios.execution.brokers.core.broker_session import BrokerSession

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages authenticated BrokerSession objects across all registered brokers.
    Thread-safe.
    """

    def __init__(self, session_ttl_sec: float = DEFAULT_SESSION_TTL_SEC) -> None:
        self._sessions:  dict[str, BrokerSession] = {}
        self._session_ttl_sec = session_ttl_sec
        self._lock = threading.RLock()

    # ── Session lifecycle ─────────────────────────────────────────────────────

    def create(
        self,
        broker_id:     str,
        user_id:       str       = "",
        auth_method:   AuthMethod = AuthMethod.API_KEY,
        access_token:  str       = "",
        refresh_token: str       = "",
        expires_at:    float | None = None,
        scope:         list[str] = [],
        metadata:      dict[str, Any] = {},
    ) -> BrokerSession:
        with self._lock:
            if broker_id in self._sessions:
                old = self._sessions[broker_id]
                if old.is_valid():
                    logger.debug(
                        "Replacing existing valid session for broker %s", broker_id
                    )
            session = BrokerSession(
                broker_id=broker_id,
                user_id=user_id,
                auth_method=auth_method,
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=expires_at
                if expires_at is not None
                else time.time() + self._session_ttl_sec,
                scope=list(scope),
                metadata=dict(metadata),
            )
            self._sessions[broker_id] = session
            logger.info("Created session %s for broker %s", session.session_id, broker_id)
            return session

    def get(self, broker_id: str) -> BrokerSession:
        with self._lock:
            session = self._sessions.get(broker_id)
            if session is None:
                raise AuthenticationFailedError(
                    f"No session found for broker '{broker_id}'",
                    "BAF-031",
                )
            if session.is_expired():
                raise AuthenticationExpiredError(
                    f"Session for broker '{broker_id}' has expired",
                    "BAF-032",
                )
            session.touch()
            return session

    def has(self, broker_id: str) -> bool:
        with self._lock:
            session = self._sessions.get(broker_id)
            return session is not None and session.is_valid()

    def invalidate(self, broker_id: str) -> None:
        with self._lock:
            session = self._sessions.get(broker_id)
            if session:
                session.invalidate()
            self._sessions.pop(broker_id, None)
            logger.info("Invalidated session for broker %s", broker_id)

    def renew(
        self,
        broker_id:       str,
        new_access_token: str,
        new_expires_at:   float | None = None,
    ) -> BrokerSession:
        with self._lock:
            session = self._sessions.get(broker_id)
            if session is None:
                raise AuthenticationFailedError(
                    f"No session to renew for broker '{broker_id}'",
                    "BAF-031",
                )
            session.refresh(new_access_token, new_expires_at)
            logger.info("Renewed session for broker %s", broker_id)
            return session

    def all_sessions(self) -> list[BrokerSession]:
        with self._lock:
            return list(self._sessions.values())

    def active_broker_ids(self) -> list[str]:
        with self._lock:
            return [
                bid for bid, sess in self._sessions.items() if sess.is_valid()
            ]

    def purge_expired(self) -> int:
        with self._lock:
            expired = [
                bid for bid, sess in self._sessions.items() if not sess.is_valid()
            ]
            for bid in expired:
                del self._sessions[bid]
            if expired:
                logger.info("Purged %d expired sessions", len(expired))
            return len(expired)
