"""
iios/infrastructure/security/token_manager.py (NEW — replaces the stub)
=========================================================================
Full-featured HMAC-signed token manager with issuance, validation, revocation,
and refresh support.  Extends (and is compatible with) the existing TokenManager.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import secrets
import threading
import time
import uuid
from collections import deque
from typing import Any, Optional

from .security_constants import (
    DEFAULT_TOKEN_TTL,
    TokenType,
    TokenStatus,
)
from .security_exceptions import TokenError
from .security_models import TokenRecord

__all__ = [
    "SecurityTokenManager",
    "get_token_manager",
    "reset_token_manager",
]

_LOG = logging.getLogger("iios.security.token")
_mgr_lock = threading.Lock()
_manager: Optional["SecurityTokenManager"] = None

_MAX_REVOKED_CACHE = 50_000


class SecurityTokenManager:
    """HMAC-SHA256 signed token manager.

    Tokens are self-contained signed strings (header.payload.signature).
    Revocation is tracked via an in-memory jti set — tokens whose jti
    appears in the revoked set are rejected even if otherwise valid.

    Usage::

        mgr = get_token_manager()
        token_str = mgr.issue(principal_id="user:alice", scopes=["trade"])
        claims = mgr.validate_raw(token_str)
        mgr.revoke(claims["jti"])
    """

    def __init__(
        self,
        secret: Optional[str] = None,
        default_ttl: int = DEFAULT_TOKEN_TTL,
    ) -> None:
        if secret is None:
            secret = secrets.token_urlsafe(64)
        if not secret:
            raise TokenError("Token secret must not be empty", code="SEC-TOK-001")
        self._secret = secret.encode()
        self._default_ttl = default_ttl
        self._lock = threading.RLock()
        # jti → TokenRecord (for revocation/status checks)
        self._records: dict[str, TokenRecord] = {}
        # Fast revocation set (bounded deque for memory control)
        self._revoked_jtis: set[str] = set()
        self._revoked_order: deque[str] = deque(maxlen=_MAX_REVOKED_CACHE)

    # ── Issue ─────────────────────────────────────────────────────────────────

    def issue(
        self,
        principal_id: str,
        token_type: TokenType = TokenType.ACCESS,
        scopes: Optional[list[str]] = None,
        ttl: Optional[int] = None,
        extra_claims: Optional[dict[str, Any]] = None,
    ) -> str:
        """Issue a signed token for *principal_id*. Returns token string."""
        effective_ttl = ttl if ttl is not None else self._default_ttl
        now = int(time.time())
        jti = str(uuid.uuid4())

        payload: dict[str, Any] = {
            "sub": principal_id,
            "typ": token_type.value,
            "iat": now,
            "exp": now + effective_ttl,
            "jti": jti,
            "scopes": scopes or [],
        }
        if extra_claims:
            payload.update(extra_claims)

        token_str = self._encode(payload)

        record = TokenRecord(
            token_id=jti,
            principal_id=principal_id,
            token_type=token_type,
            status=TokenStatus.ACTIVE,
            issued_at=float(now),
            expires_at=float(now + effective_ttl),
            scopes=scopes or [],
        )
        with self._lock:
            self._records[jti] = record

        _LOG.debug("Issued %s token for %s (jti=%s)", token_type.value, principal_id, jti[:8])
        return token_str

    # ── Validate ──────────────────────────────────────────────────────────────

    def validate_raw(self, token_str: str) -> dict[str, Any]:
        """Validate token string. Returns claims dict. Raises TokenError on failure."""
        parts = token_str.split(".")
        if len(parts) != 3:
            raise TokenError("Malformed token — expected 3 parts", code="SEC-TOK-002")

        header_b64, payload_b64, sig_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}"
        expected_sig = hmac.new(self._secret, signing_input.encode(), "sha256").digest()
        try:
            actual_sig = base64.urlsafe_b64decode(self._pad(sig_b64))
        except Exception as exc:
            raise TokenError("Malformed token signature", code="SEC-TOK-003") from exc

        if not hmac.compare_digest(expected_sig, actual_sig):
            raise TokenError("Invalid token signature", code="SEC-TOK-004")

        try:
            claims = json.loads(base64.urlsafe_b64decode(self._pad(payload_b64)).decode())
        except Exception as exc:
            raise TokenError("Malformed token payload", code="SEC-TOK-005") from exc

        # Expiry check
        if time.time() > claims.get("exp", 0):
            raise TokenError("Token has expired", code="SEC-TOK-006")

        # Revocation check
        jti = claims.get("jti", "")
        with self._lock:
            if jti in self._revoked_jtis:
                raise TokenError("Token has been revoked", code="SEC-TOK-007")

        return claims

    def validate(self, token_str: str) -> Optional[TokenRecord]:
        """Validate and return the TokenRecord, or None on failure."""
        try:
            claims = self.validate_raw(token_str)
        except TokenError:
            return None
        jti = claims.get("jti", "")
        with self._lock:
            return self._records.get(jti)

    # ── Revoke ────────────────────────────────────────────────────────────────

    def revoke(self, jti: str) -> bool:
        """Revoke a token by its jti (JWT ID). Returns True if it existed."""
        with self._lock:
            record = self._records.get(jti)
            if record:
                record.status = TokenStatus.REVOKED
            self._revoked_jtis.add(jti)
            self._revoked_order.append(jti)
            # Trim the revoked set to match the deque maxlen
            if len(self._revoked_jtis) > _MAX_REVOKED_CACHE:
                oldest = self._revoked_order.popleft()
                self._revoked_jtis.discard(oldest)
        _LOG.debug("Revoked token jti=%s", jti[:8])
        return record is not None

    def revoke_all(self, principal_id: str) -> int:
        """Revoke all tokens for *principal_id*. Returns count revoked."""
        with self._lock:
            count = 0
            for jti, record in self._records.items():
                if record.principal_id == principal_id and record.status == TokenStatus.ACTIVE:
                    record.status = TokenStatus.REVOKED
                    self._revoked_jtis.add(jti)
                    count += 1
        return count

    def is_revoked(self, jti: str) -> bool:
        with self._lock:
            return jti in self._revoked_jtis

    # ── Status ────────────────────────────────────────────────────────────────

    def get_record(self, jti: str) -> Optional[TokenRecord]:
        with self._lock:
            return self._records.get(jti)

    def purge_expired(self) -> int:
        """Remove records for expired tokens. Returns count removed."""
        with self._lock:
            expired = [
                jti for jti, r in self._records.items()
                if r.is_expired or r.status == TokenStatus.REVOKED
            ]
            for jti in expired:
                del self._records[jti]
        return len(expired)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _encode(self, payload: dict[str, Any]) -> str:
        header = {"alg": "HS256", "typ": "JWT"}
        header_b64 = base64.urlsafe_b64encode(
            json.dumps(header, separators=(",", ":")).encode()
        ).rstrip(b"=").decode()
        payload_b64 = base64.urlsafe_b64encode(
            json.dumps(payload, separators=(",", ":")).encode()
        ).rstrip(b"=").decode()
        signing_input = f"{header_b64}.{payload_b64}"
        sig = hmac.new(self._secret, signing_input.encode(), "sha256").digest()
        sig_b64 = base64.urlsafe_b64encode(sig).rstrip(b"=").decode()
        return f"{signing_input}.{sig_b64}"

    @staticmethod
    def _pad(b64: str) -> str:
        """Add back stripped base64 padding."""
        return b64 + "=" * (-len(b64) % 4)

    def reset(self) -> None:
        with self._lock:
            self._records.clear()
            self._revoked_jtis.clear()
            self._revoked_order.clear()


# ── Singleton ─────────────────────────────────────────────────────────────────

def get_token_manager() -> SecurityTokenManager:
    global _manager
    with _mgr_lock:
        if _manager is None:
            _manager = SecurityTokenManager()
        return _manager


def reset_token_manager() -> None:
    global _manager
    with _mgr_lock:
        if _manager is not None:
            _manager.reset()
        _manager = None
