"""iios/execution/brokers/authentication/authentication_manager.py"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any

from iios.execution.brokers.broker_constants import AuthMethod
from iios.execution.brokers.authentication.credential_provider import (
    CredentialProvider,
    Credentials,
    InMemoryCredentialProvider,
)
from iios.execution.brokers.authentication.session_manager import SessionManager
from iios.execution.brokers.authentication.token_manager import TokenInfo, TokenManager
from iios.execution.brokers.core.broker_session import BrokerSession

logger = logging.getLogger(__name__)


class AuthenticationManager:
    """
    Orchestrates credentials, tokens, and sessions for all broker adapters.

    Design:
    - CredentialProvider   → where credentials come from (env, vault, etc.)
    - TokenManager         → manages access/refresh tokens
    - SessionManager       → manages authenticated sessions
    - AuthenticationManager orchestrates the above three components
    """

    def __init__(
        self,
        credential_provider: CredentialProvider | None = None,
        session_ttl_sec: float = 86_400.0,
        token_refresh_buffer_sec: float = 300.0,
    ) -> None:
        self._credential_provider: CredentialProvider = (
            credential_provider or InMemoryCredentialProvider()
        )
        self._session_manager = SessionManager(session_ttl_sec=session_ttl_sec)
        self._token_manager   = TokenManager(refresh_buffer_sec=token_refresh_buffer_sec)
        self._lock = threading.RLock()

    # ── Public API ────────────────────────────────────────────────────────────

    @property
    def session_manager(self) -> SessionManager:
        return self._session_manager

    @property
    def token_manager(self) -> TokenManager:
        return self._token_manager

    @property
    def credential_provider(self) -> CredentialProvider:
        return self._credential_provider

    def authenticate(
        self,
        broker_id:    str,
        auth_method:  AuthMethod,
        raw_response: dict[str, Any],
        user_id:      str = "",
        scope:        list[str] = [],
    ) -> BrokerSession:
        """
        Persist authentication state after a successful broker authenticate() call.

        *raw_response* is the parsed body returned by the broker API.  Field
        names are normalised here so adapters don't need to agree on naming.
        """
        access_token  = raw_response.get("access_token",  "")
        refresh_token = raw_response.get("refresh_token", "")
        expires_in    = raw_response.get("expires_in",    None)
        expires_at    = (
            time.time() + float(expires_in)
            if expires_in is not None
            else None
        )

        # Store token
        token_info = TokenInfo(
            broker_id=broker_id,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at or (time.time() + 3_600.0),
            scope=list(scope),
        )
        self._token_manager.store(token_info)

        # Create session
        session = self._session_manager.create(
            broker_id=broker_id,
            user_id=user_id,
            auth_method=auth_method,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            scope=scope,
        )
        return session

    def get_session(self, broker_id: str) -> BrokerSession:
        return self._session_manager.get(broker_id)

    def has_session(self, broker_id: str) -> bool:
        return self._session_manager.has(broker_id)

    def get_credentials(self, broker_id: str) -> Credentials:
        return self._credential_provider.get_credentials(broker_id)

    def has_credentials(self, broker_id: str) -> bool:
        return self._credential_provider.has_credentials(broker_id)

    def invalidate(self, broker_id: str) -> None:
        self._session_manager.invalidate(broker_id)
        self._token_manager.invalidate(broker_id)
        logger.info("Invalidated auth for broker %s", broker_id)

    def rotate_credentials(self, broker_id: str, new_credentials: Credentials) -> None:
        self._credential_provider.rotate_credentials(broker_id, new_credentials)

    def renew_session(
        self,
        broker_id:        str,
        new_access_token: str,
        new_expires_at:   float | None = None,
    ) -> BrokerSession:
        return self._session_manager.renew(broker_id, new_access_token, new_expires_at)

    def active_broker_ids(self) -> list[str]:
        return self._session_manager.active_broker_ids()

    def purge_expired(self) -> int:
        return self._session_manager.purge_expired()

    def statistics(self) -> dict[str, Any]:
        return {
            "active_sessions":  len(self._session_manager.active_broker_ids()),
            "stored_tokens":    len(self._token_manager.list_broker_ids()),
        }
