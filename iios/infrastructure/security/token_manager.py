"""
iios/infrastructure/security/token_manager.py
=============================================
HMAC-based token generation and validation.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid
from typing import Any, Optional

from ..infrastructure_exceptions import SecurityError

__all__ = ["TokenManager"]

_DEFAULT_TTL = 3600  # 1 hour


class TokenManager:
    """Generates and validates HMAC-SHA256 signed tokens.

    Usage::

        tm = TokenManager(secret="my-secret")
        token = tm.generate({"user": "bot", "role": "trader"})
        claims = tm.validate(token)   # raises SecurityError if invalid/expired
    """

    def __init__(self, secret: str, algorithm: str = "sha256", ttl: int = _DEFAULT_TTL) -> None:
        if not secret:
            raise SecurityError("Token secret must not be empty", code="INF-SEC-001")
        self._secret = secret.encode("utf-8")
        self._algorithm = algorithm
        self._default_ttl = ttl

    def generate(self, payload: dict[str, Any], ttl: Optional[int] = None) -> str:
        """Generate a signed token embedding *payload*.

        Returns:
            A ``<header>.<payload>.<signature>`` string (all base64url).
        """
        import base64

        effective_ttl = ttl if ttl is not None else self._default_ttl
        claims = dict(payload)
        claims["iat"] = int(time.time())
        claims["exp"] = claims["iat"] + effective_ttl
        claims["jti"] = str(uuid.uuid4())

        header = {"alg": f"HS{self._algorithm.replace('sha', '')}", "typ": "JWT-like"}
        header_b64 = base64.urlsafe_b64encode(
            json.dumps(header, separators=(",", ":")).encode()
        ).rstrip(b"=").decode()
        payload_b64 = base64.urlsafe_b64encode(
            json.dumps(claims, separators=(",", ":")).encode()
        ).rstrip(b"=").decode()

        signing_input = f"{header_b64}.{payload_b64}"
        sig = hmac.new(self._secret, signing_input.encode(), self._algorithm)
        sig_b64 = base64.urlsafe_b64encode(sig.digest()).rstrip(b"=").decode()
        return f"{signing_input}.{sig_b64}"

    def validate(self, token: str) -> dict[str, Any]:
        """Validate *token* and return the claims dict.

        Raises:
            SecurityError: If token is malformed, signature is invalid, or expired.
        """
        import base64

        parts = token.split(".")
        if len(parts) != 3:
            raise SecurityError("Malformed token", code="INF-SEC-002")

        header_b64, payload_b64, sig_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}"

        # Verify signature
        expected = hmac.new(self._secret, signing_input.encode(), self._algorithm)
        # Pad base64
        padded = sig_b64 + "=" * (-len(sig_b64) % 4)
        try:
            provided_sig = base64.urlsafe_b64decode(padded)
        except Exception as exc:
            raise SecurityError("Token signature decode error", code="INF-SEC-002") from exc

        if not hmac.compare_digest(expected.digest(), provided_sig):
            raise SecurityError("Token signature invalid", code="INF-SEC-003")

        # Decode payload
        padded_payload = payload_b64 + "=" * (-len(payload_b64) % 4)
        try:
            claims: dict[str, Any] = json.loads(base64.urlsafe_b64decode(padded_payload))
        except Exception as exc:
            raise SecurityError("Token payload decode error", code="INF-SEC-002") from exc

        # Check expiry
        exp = claims.get("exp", 0)
        if int(time.time()) > exp:
            raise SecurityError("Token has expired", code="INF-SEC-004")

        return claims

    def is_valid(self, token: str) -> bool:
        try:
            self.validate(token)
            return True
        except SecurityError:
            return False
