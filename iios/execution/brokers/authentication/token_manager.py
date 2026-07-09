"""iios/execution/brokers/authentication/token_manager.py"""
from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

from iios.execution.brokers.broker_constants import DEFAULT_TOKEN_TTL_SEC
from iios.execution.brokers.broker_exceptions import AuthenticationExpiredError

logger = logging.getLogger(__name__)


@dataclass
class TokenInfo:
    """Holds a single broker access token with its lifecycle data."""

    broker_id:     str   = ""
    access_token:  str   = ""
    refresh_token: str   = ""
    token_type:    str   = "Bearer"
    expires_at:    float = field(default_factory=lambda: time.time() + DEFAULT_TOKEN_TTL_SEC)
    scope:         list[str] = field(default_factory=list)
    metadata:      dict[str, Any] = field(default_factory=dict)
    token_id:      str   = field(default_factory=lambda: str(uuid.uuid4()))
    created_at:    float = field(default_factory=time.time)

    def is_expired(self) -> bool:
        return time.time() >= self.expires_at

    def seconds_until_expiry(self) -> float:
        return max(0.0, self.expires_at - time.time())

    def is_expiring_soon(self, threshold_sec: float = 300.0) -> bool:
        return self.seconds_until_expiry() < threshold_sec

    def to_dict(self) -> dict[str, Any]:
        return {
            "token_id":    self.token_id,
            "broker_id":   self.broker_id,
            "token_type":  self.token_type,
            "expires_at":  self.expires_at,
            "created_at":  self.created_at,
            "is_expired":  self.is_expired(),
            "scope":       self.scope,
            "metadata":    self.metadata,
        }


class TokenManager:
    """
    Manages access tokens for all registered brokers.

    Supports proactive refresh via an optional refresh callback.
    Thread-safe.
    """

    def __init__(
        self,
        refresh_buffer_sec: float = 300.0,   # refresh when <5 min remain
    ) -> None:
        self._tokens: dict[str, TokenInfo] = {}
        self._refresh_callbacks: dict[str, Callable[[str], TokenInfo]] = {}
        self._refresh_buffer_sec = refresh_buffer_sec
        self._lock = threading.RLock()

    # ── Registration ──────────────────────────────────────────────────────────

    def store(self, token_info: TokenInfo) -> None:
        with self._lock:
            self._tokens[token_info.broker_id] = token_info
            logger.debug("Stored token for broker %s", token_info.broker_id)

    def register_refresh_callback(
        self, broker_id: str, callback: Callable[[str], TokenInfo]
    ) -> None:
        with self._lock:
            self._refresh_callbacks[broker_id] = callback

    # ── Retrieval ─────────────────────────────────────────────────────────────

    def get(self, broker_id: str, auto_refresh: bool = True) -> TokenInfo:
        with self._lock:
            token = self._tokens.get(broker_id)
            if token is None:
                raise AuthenticationExpiredError(
                    f"No token stored for broker '{broker_id}'",
                    "BAF-032",
                )
            if token.is_expiring_soon(self._refresh_buffer_sec) and auto_refresh:
                token = self._try_refresh(broker_id, token)
            if token.is_expired():
                raise AuthenticationExpiredError(
                    f"Token for broker '{broker_id}' has expired",
                    "BAF-032",
                )
            return token

    def has(self, broker_id: str) -> bool:
        with self._lock:
            return broker_id in self._tokens

    def invalidate(self, broker_id: str) -> None:
        with self._lock:
            self._tokens.pop(broker_id, None)
            logger.info("Invalidated token for broker %s", broker_id)

    def list_broker_ids(self) -> list[str]:
        with self._lock:
            return list(self._tokens.keys())

    # ── Internal refresh ──────────────────────────────────────────────────────

    def _try_refresh(self, broker_id: str, current: TokenInfo) -> TokenInfo:
        callback = self._refresh_callbacks.get(broker_id)
        if callback is None:
            logger.debug("No refresh callback for broker %s", broker_id)
            return current
        try:
            new_token = callback(broker_id)
            self._tokens[broker_id] = new_token
            logger.info("Refreshed token for broker %s", broker_id)
            return new_token
        except Exception as exc:
            logger.warning("Token refresh failed for broker %s: %s", broker_id, exc)
            return current
