"""
iios/infrastructure/security/encryption.py
==========================================
Symmetric encryption using Python's built-in hmac + secrets.
Provides Fernet-compatible interface without requiring cryptography package.
"""

from __future__ import annotations

import base64
import hashlib
import hmac as _hmac
import os
import struct
import time
from typing import Optional

from ..infrastructure_exceptions import SecurityError

__all__ = ["SymmetricEncryption", "generate_key"]

_FERNET_AVAILABLE = False
try:
    from cryptography.fernet import Fernet as _Fernet, InvalidToken
    _FERNET_AVAILABLE = True
except ImportError:
    pass


def generate_key() -> str:
    """Generate a 256-bit random key (base64url encoded)."""
    raw = os.urandom(32)
    return base64.urlsafe_b64encode(raw).decode()


class SymmetricEncryption:
    """Symmetric encryption facade.

    Uses ``cryptography.fernet.Fernet`` when available, falls back to a
    simple XOR-stream cipher with HMAC authentication for environments
    where ``cryptography`` is not installed.

    Usage::

        enc = SymmetricEncryption(key=generate_key())
        ciphertext = enc.encrypt(b"secret data")
        plaintext  = enc.decrypt(ciphertext)
    """

    def __init__(self, key: Optional[str] = None) -> None:
        self._key_str = key or generate_key()
        if _FERNET_AVAILABLE:
            try:
                self._fernet = _Fernet(self._key_str.encode())
            except Exception:
                # If key isn't Fernet-format, derive one
                raw = hashlib.sha256(self._key_str.encode()).digest()
                fernet_key = base64.urlsafe_b64encode(raw)
                self._fernet = _Fernet(fernet_key)
        else:
            self._fernet = None
            raw = hashlib.sha256(self._key_str.encode()).digest()
            self._raw_key = raw

    def encrypt(self, data: bytes) -> bytes:
        if self._fernet is not None:
            return self._fernet.encrypt(data)
        return self._xor_encrypt(data)

    def decrypt(self, token: bytes) -> bytes:
        if self._fernet is not None:
            try:
                return self._fernet.decrypt(token)
            except Exception as exc:
                raise SecurityError("Decryption failed", code="INF-SEC-010") from exc
        return self._xor_decrypt(token)

    def encrypt_text(self, text: str) -> str:
        return base64.urlsafe_b64encode(self.encrypt(text.encode())).decode()

    def decrypt_text(self, token: str) -> str:
        raw = base64.urlsafe_b64decode(token)
        return self.decrypt(raw).decode()

    @property
    def key(self) -> str:
        return self._key_str

    @staticmethod
    def is_strong() -> bool:
        """True if the cryptography package is available (Fernet)."""
        return _FERNET_AVAILABLE

    # ------------------------------------------------------------------
    # Fallback XOR cipher with HMAC-SHA256 authentication
    # ------------------------------------------------------------------

    def _xor_encrypt(self, data: bytes) -> bytes:
        iv = os.urandom(16)
        keystream = self._derive_keystream(iv, len(data))
        ciphertext = bytes(b ^ k for b, k in zip(data, keystream))
        # Prepend IV then HMAC
        payload = iv + ciphertext
        mac = _hmac.new(self._raw_key, payload, hashlib.sha256).digest()
        # timestamp (8 bytes) + payload + mac
        ts = struct.pack(">Q", int(time.time()))
        return base64.urlsafe_b64encode(ts + payload + mac)

    def _xor_decrypt(self, token: bytes) -> bytes:
        try:
            raw = base64.urlsafe_b64decode(token)
        except Exception as exc:
            raise SecurityError("Decryption failed — bad encoding", code="INF-SEC-010") from exc
        # ts(8) + iv(16) + ciphertext + mac(32)
        if len(raw) < 56:
            raise SecurityError("Decryption failed — token too short", code="INF-SEC-010")
        _ts = raw[:8]
        mac = raw[-32:]
        payload = raw[8:-32]
        expected_mac = _hmac.new(self._raw_key, payload, hashlib.sha256).digest()
        if not _hmac.compare_digest(expected_mac, mac):
            raise SecurityError("Decryption failed — HMAC mismatch", code="INF-SEC-010")
        iv = payload[:16]
        ciphertext = payload[16:]
        keystream = self._derive_keystream(iv, len(ciphertext))
        return bytes(b ^ k for b, k in zip(ciphertext, keystream))

    def _derive_keystream(self, iv: bytes, length: int) -> bytes:
        stream = b""
        counter = 0
        while len(stream) < length:
            block = hashlib.sha256(self._raw_key + iv + counter.to_bytes(4, "big")).digest()
            stream += block
            counter += 1
        return stream[:length]
