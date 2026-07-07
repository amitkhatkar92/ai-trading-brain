"""
iios/infrastructure/security/credential_manager.py
===================================================
Stores and verifies credentials (hashed passwords, hashed API keys, TOTP seeds).
All values are hashed at rest — no plaintext is ever persisted.
"""

from __future__ import annotations

import logging
import os
import secrets
import threading
import time
from typing import Optional

from .crypto_provider import get_crypto_provider
from .security_constants import (
    CredentialType,
    API_KEY_LENGTH_BYTES,
    MIN_PASSWORD_LENGTH,
)
from .security_exceptions import (
    InvalidCredentialError,
    CredentialExpiredError,
    IdentityNotFoundError,
)
from .security_models import CredentialRecord

__all__ = ["CredentialManager", "get_credential_manager", "reset_credential_manager"]

_LOG = logging.getLogger("iios.security.credential")
_mgr_lock = threading.Lock()
_manager: Optional["CredentialManager"] = None


class CredentialManager:
    """Thread-safe manager for hashed credentials.

    Supports:
    - Password hashing / verification (PBKDF2 or SHA256 fallback)
    - API key generation / hashing / verification
    - Credential expiry

    Usage::

        mgr = get_credential_manager()
        mgr.set_password("user:alice", "SuperSecret123!")
        ok = mgr.verify_password("user:alice", "SuperSecret123!")
        api_key = mgr.generate_api_key("service:bot", prefix="sk_")
        ok = mgr.verify_api_key("service:bot", api_key)
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        # principal_id → CredentialRecord
        self._credentials: dict[str, list[CredentialRecord]] = {}
        # api_key_prefix → CredentialRecord (for fast prefix lookup)
        self._api_key_index: dict[str, CredentialRecord] = {}
        self._crypto = get_crypto_provider()

    # ── Password ──────────────────────────────────────────────────────────────

    def set_password(
        self,
        principal_id: str,
        password: str,
        ttl_seconds: Optional[float] = None,
    ) -> CredentialRecord:
        """Hash and store a password for *principal_id*."""
        if len(password) < MIN_PASSWORD_LENGTH:
            raise InvalidCredentialError(
                f"Password must be at least {MIN_PASSWORD_LENGTH} characters",
                code="SEC-CRED-001",
            )
        hashed = self._crypto.hash_password(password)
        expires = time.time() + ttl_seconds if ttl_seconds else None
        record = CredentialRecord(
            principal_id=principal_id,
            credential_type=CredentialType.PASSWORD,
            hashed_value=hashed,
            expires_at=expires,
            is_primary=True,
        )
        with self._lock:
            existing = self._credentials.setdefault(principal_id, [])
            # Deactivate any existing primary password
            for c in existing:
                if c.credential_type == CredentialType.PASSWORD and c.is_primary:
                    c.is_primary = False
            existing.append(record)
        _LOG.debug("Password set for principal %s", principal_id)
        return record

    def verify_password(self, principal_id: str, password: str) -> bool:
        """Verify a password. Raises CredentialExpiredError if expired."""
        with self._lock:
            creds = self._credentials.get(principal_id, [])
        for c in creds:
            if c.credential_type == CredentialType.PASSWORD and c.is_primary:
                if c.is_expired:
                    raise CredentialExpiredError(
                        "Password has expired",
                        code="SEC-CRED-002",
                        context={"principal_id": principal_id},
                    )
                return self._crypto.verify_password(password, c.hashed_value)
        return False

    # ── API Keys ──────────────────────────────────────────────────────────────

    def generate_api_key(
        self,
        principal_id: str,
        prefix: str = "",
        ttl_seconds: Optional[float] = None,
    ) -> str:
        """Generate, hash, and store an API key. Returns the plaintext key (show-once)."""
        raw_key = self._crypto.generate_api_key(prefix=prefix, byte_length=API_KEY_LENGTH_BYTES)
        hashed = self._hash_api_key(raw_key)
        # Store a prefix for fast lookup (first 8 chars of the key after prefix)
        key_prefix = raw_key[len(prefix): len(prefix) + 8]
        expires = time.time() + ttl_seconds if ttl_seconds else None
        record = CredentialRecord(
            principal_id=principal_id,
            credential_type=CredentialType.API_KEY,
            hashed_value=hashed,
            expires_at=expires,
            is_primary=True,
            metadata={"prefix": prefix, "key_prefix": key_prefix},
        )
        with self._lock:
            self._credentials.setdefault(principal_id, []).append(record)
            self._api_key_index[key_prefix] = record
        _LOG.info("API key generated for principal %s", principal_id)
        return raw_key

    def verify_api_key(self, raw_key: str) -> Optional[str]:
        """Verify an API key and return the owning principal_id, or None."""
        # Try each credential — in production this would use a prefix index
        import hmac as _hmac
        key_hash = self._hash_api_key(raw_key)
        with self._lock:
            for pid, creds in self._credentials.items():
                for c in creds:
                    if c.credential_type != CredentialType.API_KEY:
                        continue
                    if c.is_expired:
                        continue
                    if _hmac.compare_digest(c.hashed_value, key_hash):
                        return pid
        return None

    def _hash_api_key(self, raw_key: str) -> str:
        """SHA-256 of the raw key (no salt needed — keys are already high-entropy)."""
        import hashlib
        return hashlib.sha256(raw_key.encode()).hexdigest()

    # ── General ───────────────────────────────────────────────────────────────

    def get_credentials(self, principal_id: str) -> list[CredentialRecord]:
        with self._lock:
            return list(self._credentials.get(principal_id, []))

    def revoke_credentials(self, principal_id: str) -> int:
        """Remove all credentials for a principal. Returns count removed."""
        with self._lock:
            creds = self._credentials.pop(principal_id, [])
            for c in creds:
                kp = c.metadata.get("key_prefix", "")
                if kp:
                    self._api_key_index.pop(kp, None)
            return len(creds)

    def has_password(self, principal_id: str) -> bool:
        with self._lock:
            creds = self._credentials.get(principal_id, [])
        return any(c.credential_type == CredentialType.PASSWORD and c.is_primary for c in creds)

    def reset(self) -> None:
        with self._lock:
            self._credentials.clear()
            self._api_key_index.clear()


# ── Singleton ─────────────────────────────────────────────────────────────────

def get_credential_manager() -> CredentialManager:
    global _manager
    with _mgr_lock:
        if _manager is None:
            _manager = CredentialManager()
        return _manager


def reset_credential_manager() -> None:
    global _manager
    with _mgr_lock:
        if _manager is not None:
            _manager.reset()
        _manager = None
