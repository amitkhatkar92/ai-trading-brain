"""
iios/infrastructure/security/encryption_manager.py
===================================================
High-level encryption façade: encrypt/decrypt data, compute digests,
sign/verify payloads, and manage key references.
"""

from __future__ import annotations

import base64
import logging
import threading
from typing import Optional

from .crypto_provider import get_crypto_provider
from .key_manager import get_key_manager
from .security_constants import EncryptionAlgorithm, HashAlgorithm
from .security_exceptions import EncryptionError
from .security_models import SignedPayload

__all__ = ["EncryptionManager", "get_encryption_manager", "reset_encryption_manager"]

_LOG = logging.getLogger("iios.security.encryption")
_mgr_lock = threading.Lock()
_manager: Optional["EncryptionManager"] = None

_DEFAULT_KEY_NAME = "iios_default"


class EncryptionManager:
    """High-level encryption façade.

    Provides simple encrypt/decrypt/sign/verify/hash operations.
    Uses the KeyManager for key material and CryptoProvider for operations.

    Usage::

        em = get_encryption_manager()
        ciphertext = em.encrypt(b"secret data")
        plaintext = em.decrypt(ciphertext)
        sig = em.sign(b"payload")
        em.verify(b"payload", sig)
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._default_key_id: Optional[str] = None

    def _get_default_key(self) -> tuple[str, bytes]:
        """Return (key_id, raw_bytes) — auto-generate if not yet created."""
        km = get_key_manager()
        try:
            return km.get_active(_DEFAULT_KEY_NAME)
        except Exception:
            key_id, raw = km.generate(_DEFAULT_KEY_NAME, algorithm=EncryptionAlgorithm.FERNET)
            return key_id, raw

    # ── Symmetric encryption ──────────────────────────────────────────────────

    def encrypt(self, data: bytes, key_name: Optional[str] = None) -> bytes:
        """Encrypt *data* and return ciphertext.

        The ciphertext is prefixed with ``key_id:`` so the correct key can be
        looked up for decryption even after rotation.
        """
        try:
            name = key_name or _DEFAULT_KEY_NAME
            km = get_key_manager()
            try:
                key_id, raw = km.get_active(name)
            except Exception:
                key_id, raw = km.generate(name)
            ciphertext = get_crypto_provider().encrypt(data, raw)
            # Prepend key_id length-prefixed header: [1 byte len][key_id bytes][ciphertext]
            kid_bytes = key_id.encode()
            return bytes([len(kid_bytes)]) + kid_bytes + ciphertext
        except EncryptionError:
            raise
        except Exception as exc:
            raise EncryptionError("Encryption failed", code="SEC-ENC-001") from exc

    def decrypt(self, ciphertext_with_header: bytes, key_name: Optional[str] = None) -> bytes:
        """Decrypt data produced by :meth:`encrypt`."""
        try:
            if len(ciphertext_with_header) < 2:
                raise EncryptionError("Invalid ciphertext", code="SEC-ENC-002")

            kid_len = ciphertext_with_header[0]
            if len(ciphertext_with_header) < 1 + kid_len:
                raise EncryptionError("Invalid ciphertext header", code="SEC-ENC-003")

            key_id = ciphertext_with_header[1: 1 + kid_len].decode()
            ciphertext = ciphertext_with_header[1 + kid_len:]

            raw = get_key_manager().get_raw(key_id)
            return get_crypto_provider().decrypt(ciphertext, raw)
        except EncryptionError:
            raise
        except Exception as exc:
            raise EncryptionError("Decryption failed", code="SEC-ENC-004") from exc

    def encrypt_text(self, text: str, key_name: Optional[str] = None) -> str:
        """Encrypt a UTF-8 string and return a base64url-encoded result."""
        ciphertext = self.encrypt(text.encode(), key_name)
        return base64.urlsafe_b64encode(ciphertext).decode()

    def decrypt_text(self, encoded: str, key_name: Optional[str] = None) -> str:
        """Decrypt a string produced by :meth:`encrypt_text`."""
        ciphertext = base64.urlsafe_b64decode(encoded + "==")
        return self.decrypt(ciphertext, key_name).decode()

    # ── Hashing ───────────────────────────────────────────────────────────────

    def hash(self, data: bytes, algorithm: HashAlgorithm = HashAlgorithm.SHA256) -> str:
        """Return the hex digest of *data* using *algorithm*."""
        return get_crypto_provider().hash(data, algorithm.value)

    def hash_text(self, text: str, algorithm: HashAlgorithm = HashAlgorithm.SHA256) -> str:
        return self.hash(text.encode(), algorithm)

    # ── Signing ───────────────────────────────────────────────────────────────

    def sign(self, data: bytes, key_name: Optional[str] = None) -> bytes:
        """Compute an HMAC-SHA256 signature of *data*."""
        _, raw = self._get_default_key() if key_name is None else get_key_manager().get_active(key_name)
        return get_crypto_provider().hmac_sign(data, raw)

    def verify(self, data: bytes, signature: bytes, key_name: Optional[str] = None) -> bool:
        """Verify an HMAC-SHA256 signature. Returns True on success."""
        _, raw = self._get_default_key() if key_name is None else get_key_manager().get_active(key_name)
        return get_crypto_provider().hmac_verify(data, signature, raw)

    def create_signed_payload(self, data: bytes, key_name: Optional[str] = None) -> SignedPayload:
        """Create a SignedPayload bundling data and its HMAC signature."""
        try:
            key_id, raw = self._get_default_key() if key_name is None else get_key_manager().get_active(key_name)
            signature = get_crypto_provider().hmac_sign(data, raw)
            return SignedPayload(
                payload=data,
                signature=signature,
                algorithm="hmac-sha256",
                key_id=key_id,
            )
        except Exception as exc:
            raise EncryptionError("Signing failed", code="SEC-ENC-005") from exc

    def verify_signed_payload(self, sp: SignedPayload) -> bool:
        """Verify the signature of a SignedPayload."""
        try:
            raw = get_key_manager().get_raw(sp.key_id)
            return get_crypto_provider().hmac_verify(sp.payload, sp.signature, raw)
        except Exception:
            return False

    # ── Password operations ────────────────────────────────────────────────────

    def hash_password(self, password: str) -> str:
        """Hash a password (PBKDF2 or SHA-256 fallback)."""
        return get_crypto_provider().hash_password(password)

    def verify_password(self, password: str, stored_hash: str) -> bool:
        """Verify a password against a stored hash."""
        return get_crypto_provider().verify_password(password, stored_hash)

    # ── Random generation ─────────────────────────────────────────────────────

    def generate_token(self, byte_length: int = 32) -> str:
        """Generate a cryptographically random URL-safe token."""
        return get_crypto_provider().generate_secure_token(byte_length)

    def generate_api_key(self, prefix: str = "") -> str:
        """Generate a random API key."""
        return get_crypto_provider().generate_api_key(prefix=prefix)

    def reset(self) -> None:
        with self._lock:
            self._default_key_id = None


# ── Singleton ─────────────────────────────────────────────────────────────────

def get_encryption_manager() -> EncryptionManager:
    global _manager
    with _mgr_lock:
        if _manager is None:
            _manager = EncryptionManager()
        return _manager


def reset_encryption_manager() -> None:
    global _manager
    with _mgr_lock:
        if _manager is not None:
            _manager.reset()
        _manager = None
