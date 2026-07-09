"""iios/execution/brokers/core/broker_session.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.execution.brokers.broker_constants import AuthMethod


@dataclass
class BrokerSession:
    """Represents an authenticated session with a single broker."""

    broker_id:     str        = ""
    user_id:       str        = ""
    auth_method:   AuthMethod = AuthMethod.API_KEY
    access_token:  str        = ""
    refresh_token: str        = ""
    expires_at:    float | None = None     # Unix epoch; None = non-expiring
    session_id:    str        = field(default_factory=lambda: str(uuid.uuid4()))
    created_at:    float      = field(default_factory=time.time)
    last_used_at:  float      = field(default_factory=time.time)
    is_active:     bool       = True
    scope:         list[str]  = field(default_factory=list)
    metadata:      dict[str, Any] = field(default_factory=dict)

    # ── Queries ───────────────────────────────────────────────────────────────

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() >= self.expires_at

    def is_valid(self) -> bool:
        return self.is_active and not self.is_expired()

    def seconds_until_expiry(self) -> float | None:
        if self.expires_at is None:
            return None
        remaining = self.expires_at - time.time()
        return max(0.0, remaining)

    # ── Mutation ──────────────────────────────────────────────────────────────

    def touch(self) -> None:
        self.last_used_at = time.time()

    def refresh(self, new_access_token: str, new_expires_at: float | None = None) -> None:
        self.access_token = new_access_token
        if new_expires_at is not None:
            self.expires_at = new_expires_at
        self.last_used_at = time.time()

    def invalidate(self) -> None:
        self.is_active = False
        self.access_token  = ""
        self.refresh_token = ""

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id":    self.session_id,
            "broker_id":     self.broker_id,
            "user_id":       self.user_id,
            "auth_method":   self.auth_method.value,
            "expires_at":    self.expires_at,
            "created_at":    self.created_at,
            "last_used_at":  self.last_used_at,
            "is_active":     self.is_active,
            "is_expired":    self.is_expired(),
            "scope":         self.scope,
            "metadata":      self.metadata,
        }
