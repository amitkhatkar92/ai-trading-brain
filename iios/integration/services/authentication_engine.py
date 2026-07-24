"""
authentication_engine.py — iios.integration.services
------------------------------------------------------
AuthenticationEngine — validates authentication credentials and issues
session tokens for integration connectors.

Supports 9 auth methods. Credentials are never logged.

C15 Enterprise Integration & Connectivity — Phase 1, Module 4
"""
from __future__ import annotations

import hashlib
import hmac
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import AuthScheme

_log = get_logger(__name__)


@dataclass(frozen=True)
class AuthToken:
    """An issued authentication token."""
    token_id:    str
    scheme:      AuthScheme
    principal:   str      # identity (username, client-id, etc.)
    token:       str      # opaque token value
    valid:       bool
    expires_at:  Optional[str]
    issued_at:   str

    @classmethod
    def create(
        cls,
        scheme:    AuthScheme,
        principal: str,
        valid:     bool = True,
    ) -> "AuthToken":
        return cls(
            token_id   = f"atk-{uuid.uuid4().hex[:12]}",
            scheme     = scheme,
            principal  = principal,
            token      = uuid.uuid4().hex,
            valid      = valid,
            expires_at = None,
            issued_at  = datetime.now(timezone.utc).isoformat(),
        )


@dataclass
class AuthenticationResult:
    """Result of an authentication attempt."""
    success:   bool
    token:     Optional[AuthToken]
    scheme:    AuthScheme
    error:     str = ""
    latency_ms: float = 0.0


class AuthenticationEngine:
    """
    Authenticates connector requests using configured auth schemes.

    Credential validation is simulated — real credential storage is
    delegated to CredentialProvider / SecretManager.
    """

    def __init__(self) -> None:
        self._lock       = threading.Lock()
        self._tokens:    Dict[str, AuthToken] = {}
        self._success    = 0
        self._failure    = 0

    # ── Public ────────────────────────────────────────────────────────────

    def authenticate(
        self,
        scheme:      AuthScheme,
        credentials: Dict[str, Any],
    ) -> AuthenticationResult:
        """Validate credentials and return an AuthenticationResult."""
        start = time.perf_counter_ns()
        try:
            principal = self._resolve_principal(scheme, credentials)
            valid     = self._validate(scheme, credentials)
            token     = AuthToken.create(scheme=scheme, principal=principal, valid=valid)
            if valid:
                with self._lock:
                    self._tokens[token.token_id] = token
                    self._success += 1
            else:
                with self._lock:
                    self._failure += 1
            latency_ms = (time.perf_counter_ns() - start) / 1_000_000
            return AuthenticationResult(
                success    = valid,
                token      = token if valid else None,
                scheme     = scheme,
                latency_ms = latency_ms,
                error      = "" if valid else "Authentication failed",
            )
        except Exception as exc:
            with self._lock:
                self._failure += 1
            latency_ms = (time.perf_counter_ns() - start) / 1_000_000
            return AuthenticationResult(
                success=False, token=None, scheme=scheme,
                error=str(exc), latency_ms=latency_ms,
            )

    def validate_token(self, token_id: str) -> bool:
        """Return True if the token exists and is valid."""
        with self._lock:
            tok = self._tokens.get(token_id)
        return tok is not None and tok.valid

    def revoke_token(self, token_id: str) -> bool:
        """Revoke a token. Returns True if found."""
        with self._lock:
            if token_id in self._tokens:
                del self._tokens[token_id]
                return True
        return False

    @property
    def stats(self) -> Dict[str, int]:
        with self._lock:
            return {
                "active_tokens": len(self._tokens),
                "success":       self._success,
                "failure":       self._failure,
            }

    # ── Internals ─────────────────────────────────────────────────────────

    def _resolve_principal(
        self, scheme: AuthScheme, creds: Dict[str, Any]
    ) -> str:
        if scheme == AuthScheme.BASIC:
            return creds.get("username", "anonymous")
        if scheme in (AuthScheme.API_KEY, AuthScheme.BEARER_TOKEN):
            return creds.get("client_id", "api-client")
        if scheme == AuthScheme.OAUTH2:
            return creds.get("client_id", "oauth-client")
        if scheme == AuthScheme.MTLS:
            return creds.get("common_name", "cert-client")
        return creds.get("principal", "system")

    def _validate(self, scheme: AuthScheme, creds: Dict[str, Any]) -> bool:
        """
        Simulated credential validation.
        In production this delegates to a real IdP / secret store.
        """
        if scheme == AuthScheme.NONE:
            return True
        # For simulation: any non-empty credential passes
        required_keys: Dict[AuthScheme, str] = {
            AuthScheme.API_KEY:      "api_key",
            AuthScheme.BEARER_TOKEN: "token",
            AuthScheme.BASIC:        "username",
            AuthScheme.OAUTH2:       "client_id",
            AuthScheme.MTLS:         "certificate",
            AuthScheme.SAML:         "assertion",
            AuthScheme.CUSTOM:       "credential",
        }
        key = required_keys.get(scheme, "credential")
        return bool(creds.get(key))
