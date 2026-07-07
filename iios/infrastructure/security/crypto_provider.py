"""
iios/infrastructure/security/crypto_provider.py
================================================
Cryptographic provider — wraps the ``cryptography`` package for AES-256/Fernet,
HMAC-SHA256/SHA-512, secure random generation, and RSA.
Falls back gracefully to stdlib-only operations where possible.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os
import secrets
from abc import ABC, abstractmethod
from typing import Optional, Tuple

from .security_exceptions import EncryptionError, SignatureInvalidError

__all__ = [
    "CryptoProvider",
    "StdlibCryptoProvider",
    "FernetCryptoProvider",
    "get_crypto_provider",
    "reset_crypto_provider",
]

_LOG = logging.getLogger("iios.security.crypto")

_FERNET_OK = False
try:
    from cryptography.fernet import Fernet, InvalidToken
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa, padding
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.backends import default_backend
    _FERNET_OK = True
except ImportError:
    pass


class CryptoProvider(ABC):
    """Abstract cryptographic operations interface."""

    @abstractmethod
    def generate_key(self, key_bytes: int = 32) -> bytes:
        """Generate *key_bytes* cryptographically random bytes."""

    @abstractmethod
    def encrypt(self, data: bytes, key: bytes) -> bytes:
        """Encrypt *data* using *key*. Returns ciphertext."""

    @abstractmethod
    def decrypt(self, ciphertext: bytes, key: bytes) -> bytes:
        """Decrypt *ciphertext* using *key*. Returns plaintext."""

    @abstractmethod
    def hmac_sign(self, data: bytes, key: bytes, algorithm: str = "sha256") -> bytes:
        """Compute HMAC signature of *data*."""

    @abstractmethod
    def hmac_verify(self, data: bytes, signature: bytes, key: bytes, algorithm: str = "sha256") -> bool:
        """Verify HMAC signature. Returns True on success."""

    @abstractmethod
    def hash(self, data: bytes, algorithm: str = "sha256") -> str:
        """Return hex digest of *data* using the given algorithm."""

    @abstractmethod
    def derive_key(self, password: bytes, salt: bytes, length: int = 32, iterations: int = 260_000) -> bytes:
        """Derive a key from a password using PBKDF2-HMAC-SHA256."""

    def generate_secure_token(self, byte_length: int = 32) -> str:
        """Generate a URL-safe base64 token of *byte_length* bytes."""
        return secrets.token_urlsafe(byte_length)

    def generate_api_key(self, prefix: str = "", byte_length: int = 32) -> str:
        """Generate a random API key with optional prefix."""
        raw = secrets.token_urlsafe(byte_length)
        return f"{prefix}{raw}" if prefix else raw

    def constant_time_compare(self, a: str, b: str) -> bool:
        """Timing-safe string comparison."""
        return hmac.compare_digest(a.encode(), b.encode())


class StdlibCryptoProvider(CryptoProvider):
    """Pure stdlib crypto provider (no external dependencies).

    Encryption: XOR-stream with PBKDF2-derived key + HMAC-SHA256 authentication.
    This is adequate for development/testing. For production use FernetCryptoProvider.
    """

    def generate_key(self, key_bytes: int = 32) -> bytes:
        return os.urandom(key_bytes)

    def _derive_stream_key(self, key: bytes, nonce: bytes, length: int) -> bytes:
        """Deterministic PBKDF2 key-stream from key + nonce."""
        derived = hashlib.pbkdf2_hmac("sha256", key, nonce, 1, dklen=length)
        return derived

    def encrypt(self, data: bytes, key: bytes) -> bytes:
        """Encrypt using XOR key-stream + HMAC-SHA256 authentication tag.

        Format: nonce(16) || hmac(32) || ciphertext
        """
        nonce = os.urandom(16)
        stream = self._derive_stream_key(key, nonce, len(data))
        ciphertext = bytes(d ^ s for d, s in zip(data, stream))
        # Auth tag covers nonce + ciphertext
        mac = hmac.new(key, nonce + ciphertext, "sha256").digest()
        return nonce + mac + ciphertext

    def decrypt(self, ciphertext_with_header: bytes, key: bytes) -> bytes:
        """Decrypt XOR-stream + verify HMAC."""
        if len(ciphertext_with_header) < 48:
            raise EncryptionError("Ciphertext too short", code="SEC-CRYPTO-001")
        nonce = ciphertext_with_header[:16]
        mac = ciphertext_with_header[16:48]
        ciphertext = ciphertext_with_header[48:]
        expected_mac = hmac.new(key, nonce + ciphertext, "sha256").digest()
        if not hmac.compare_digest(mac, expected_mac):
            raise EncryptionError("Authentication tag mismatch", code="SEC-CRYPTO-002")
        stream = self._derive_stream_key(key, nonce, len(ciphertext))
        return bytes(c ^ s for c, s in zip(ciphertext, stream))

    def hmac_sign(self, data: bytes, key: bytes, algorithm: str = "sha256") -> bytes:
        return hmac.new(key, data, algorithm).digest()

    def hmac_verify(self, data: bytes, signature: bytes, key: bytes, algorithm: str = "sha256") -> bool:
        expected = hmac.new(key, data, algorithm).digest()
        return hmac.compare_digest(expected, signature)

    def hash(self, data: bytes, algorithm: str = "sha256") -> str:
        algo_map = {
            "sha256": hashlib.sha256,
            "sha512": hashlib.sha512,
            "sha3_256": hashlib.sha3_256,
            "blake2b": lambda d: hashlib.blake2b(d, digest_size=32),
        }
        h = algo_map.get(algorithm, hashlib.sha256)
        return h(data).hexdigest()

    def derive_key(self, password: bytes, salt: bytes, length: int = 32, iterations: int = 260_000) -> bytes:
        return hashlib.pbkdf2_hmac("sha256", password, salt, iterations, dklen=length)

    def hash_password(self, password: str, salt: Optional[bytes] = None) -> str:
        """Hash a password. Returns ``sha256:<hex_salt>:<hex_hash>``."""
        if salt is None:
            salt = os.urandom(32)
        key = self.derive_key(password.encode(), salt)
        return f"sha256:{salt.hex()}:{key.hex()}"

    def verify_password(self, password: str, stored_hash: str) -> bool:
        """Verify a password against a stored hash."""
        parts = stored_hash.split(":")
        if len(parts) != 3:
            return False
        algorithm, salt_hex, expected_hex = parts
        try:
            salt = bytes.fromhex(salt_hex)
            expected = bytes.fromhex(expected_hex)
        except ValueError:
            return False
        if algorithm == "sha256":
            derived = self.derive_key(password.encode(), salt)
            return hmac.compare_digest(derived, expected)
        return False


class FernetCryptoProvider(StdlibCryptoProvider):
    """Fernet-backed crypto provider (requires ``cryptography`` package).

    Uses AES-128-CBC + HMAC-SHA256 for symmetric encryption.
    Falls back to StdlibCryptoProvider if cryptography is not installed.
    """

    def __init__(self) -> None:
        if not _FERNET_OK:
            _LOG.warning("cryptography package not available; using stdlib crypto")

    def generate_key(self, key_bytes: int = 32) -> bytes:
        if _FERNET_OK:
            return Fernet.generate_key()    # 32-byte Fernet key, base64-encoded
        return os.urandom(key_bytes)

    def encrypt(self, data: bytes, key: bytes) -> bytes:
        if _FERNET_OK:
            try:
                f = Fernet(key)
                return f.encrypt(data)
            except Exception as exc:
                raise EncryptionError("Fernet encryption failed", code="SEC-CRYPTO-003") from exc
        return super().encrypt(data, key)

    def decrypt(self, ciphertext: bytes, key: bytes) -> bytes:
        if _FERNET_OK:
            try:
                f = Fernet(key)
                return f.decrypt(ciphertext)
            except InvalidToken as exc:
                raise EncryptionError("Fernet decryption failed — invalid token", code="SEC-CRYPTO-004") from exc
            except Exception as exc:
                raise EncryptionError("Fernet decryption failed", code="SEC-CRYPTO-005") from exc
        return super().decrypt(ciphertext, key)

    def rsa_generate_keypair(self, key_size: int = 2048) -> Tuple[bytes, bytes]:
        """Generate RSA key pair. Returns (private_pem, public_pem)."""
        if not _FERNET_OK:
            raise EncryptionError("RSA requires cryptography package", code="SEC-CRYPTO-006")
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size,
            backend=default_backend(),
        )
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        public_pem = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        return private_pem, public_pem

    def rsa_encrypt(self, data: bytes, public_pem: bytes) -> bytes:
        """Encrypt data with RSA public key (OAEP padding)."""
        if not _FERNET_OK:
            raise EncryptionError("RSA requires cryptography package", code="SEC-CRYPTO-007")
        public_key = serialization.load_pem_public_key(public_pem, backend=default_backend())
        return public_key.encrypt(
            data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )

    def rsa_decrypt(self, ciphertext: bytes, private_pem: bytes) -> bytes:
        """Decrypt data with RSA private key (OAEP padding)."""
        if not _FERNET_OK:
            raise EncryptionError("RSA requires cryptography package", code="SEC-CRYPTO-008")
        private_key = serialization.load_pem_private_key(private_pem, password=None, backend=default_backend())
        return private_key.decrypt(
            ciphertext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )

    def hash_password(self, password: str, salt: Optional[bytes] = None) -> str:
        """PBKDF2-SHA256 password hash.  Returns ``pbkdf2:<hex_salt>:<hex_hash>``."""
        if not _FERNET_OK:
            return super().hash_password(password, salt)
        if salt is None:
            salt = os.urandom(32)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=260_000,
            backend=default_backend(),
        )
        key = kdf.derive(password.encode())
        return f"pbkdf2:{salt.hex()}:{key.hex()}"

    def verify_password(self, password: str, stored_hash: str) -> bool:
        """Verify a password against a stored PBKDF2 or SHA256 hash."""
        parts = stored_hash.split(":")
        if len(parts) != 3:
            return False
        algorithm, salt_hex, expected_hex = parts
        try:
            salt = bytes.fromhex(salt_hex)
            expected = bytes.fromhex(expected_hex)
        except ValueError:
            return False
        if algorithm == "pbkdf2" and _FERNET_OK:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=260_000,
                backend=default_backend(),
            )
            try:
                kdf.verify(password.encode(), expected)
                return True
            except Exception:
                return False
        if algorithm == "sha256":
            derived = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 260_000, dklen=32)
            return hmac.compare_digest(derived, expected)
        return False


# ── Singleton ─────────────────────────────────────────────────────────────────

import threading as _threading

_provider_lock = _threading.Lock()
_provider: Optional[CryptoProvider] = None


def get_crypto_provider() -> CryptoProvider:
    global _provider
    with _provider_lock:
        if _provider is None:
            _provider = FernetCryptoProvider()
        return _provider


def reset_crypto_provider() -> None:
    global _provider
    with _provider_lock:
        _provider = None
