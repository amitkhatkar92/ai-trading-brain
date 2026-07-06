"""
iios/configuration/configuration_encryption.py
================================================
Encryption/decryption support for sensitive configuration values.

Values prefixed with ``ENC:`` are treated as encrypted. The ``ENC:``
scheme uses Fernet symmetric encryption if the ``cryptography`` package
is available. Without it, a base64 obfuscation fallback is used (NOT
true encryption — intended for non-production use only).

Usage:
    enc = ConfigurationEncryption(key="my-secret-key")
    ciphertext = enc.encrypt("my-token")       # returns "ENC:<base64>"
    plaintext  = enc.decrypt(ciphertext)        # returns "my-token"
    data       = enc.scan_and_decrypt(config_dict, key="my-secret-key")

Architecture Reference: IIOS-CIS-001 INFRA-CFG-001
"""

from __future__ import annotations

import base64
import copy
import hashlib
import logging
import os
from typing import Any, Optional

from .configuration_constants import ENCRYPTED_MARKER
from .configuration_exception import ConfigurationEncryptionError

logger = logging.getLogger(__name__)

__all__ = [
    "ConfigurationEncryption",
]

# Check availability of Fernet
try:
    from cryptography.fernet import Fernet, InvalidToken
    _HAS_CRYPTOGRAPHY = True
except ImportError:
    _HAS_CRYPTOGRAPHY = False


class ConfigurationEncryption:
    """Encrypt and decrypt configuration values.

    When the ``cryptography`` package is installed, uses Fernet symmetric
    encryption. Without it, uses reversible base64 encoding (obfuscation
    only — not suitable for production secrets).

    Args:
        key: Master key (arbitrary string). Will be hashed to a 32-byte
             Fernet-compatible key internally.
    """

    def __init__(self, key: Optional[str] = None) -> None:
        self._key = key or os.environ.get("IIOS_ENCRYPTION_KEY", "")
        self._fernet = None

        if _HAS_CRYPTOGRAPHY and self._key:
            self._fernet = self._make_fernet(self._key)
        elif not _HAS_CRYPTOGRAPHY:
            logger.debug(
                "cryptography package not installed — "
                "using base64 obfuscation (not true encryption)"
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def encrypt(self, plaintext: str) -> str:
        """Encrypt *plaintext* and return ``"ENC:<ciphertext>"``.

        Raises ``ConfigurationEncryptionError`` if no key is configured.
        """
        if not self._key:
            raise ConfigurationEncryptionError("No encryption key configured")
        if self._fernet is not None:
            try:
                token = self._fernet.encrypt(plaintext.encode()).decode()
                return f"{ENCRYPTED_MARKER}{token}"
            except Exception as exc:
                raise ConfigurationEncryptionError(
                    f"Fernet encryption failed: {exc}"
                ) from exc
        # Fallback: base64 obfuscation
        encoded = base64.b64encode(plaintext.encode()).decode()
        return f"{ENCRYPTED_MARKER}b64:{encoded}"

    def decrypt(self, value: str) -> str:
        """Decrypt a value that starts with ``ENC:``.

        If the value does not start with ``ENC:``, it is returned unchanged
        (allows calling unconditionally on any config value).

        Raises ``ConfigurationEncryptionError`` on decryption failure.
        """
        if not value.startswith(ENCRYPTED_MARKER):
            return value  # Not encrypted — pass through

        ciphertext = value[len(ENCRYPTED_MARKER):]

        if ciphertext.startswith("b64:"):
            # Obfuscation fallback
            try:
                return base64.b64decode(ciphertext[4:]).decode()
            except Exception as exc:
                raise ConfigurationEncryptionError(
                    f"Base64 decode failed: {exc}", key="<unknown>"
                ) from exc

        if not self._key:
            raise ConfigurationEncryptionError("No encryption key configured — cannot decrypt")
        if self._fernet is None:
            raise ConfigurationEncryptionError(
                "cryptography package required for Fernet decryption"
            )
        try:
            return self._fernet.decrypt(ciphertext.encode()).decode()
        except Exception as exc:
            raise ConfigurationEncryptionError(
                f"Fernet decryption failed (wrong key or corrupt data): {exc}"
            ) from exc

    def is_encrypted(self, value: Any) -> bool:
        """Return ``True`` if *value* is a string starting with ``ENC:``."""
        return isinstance(value, str) and value.startswith(ENCRYPTED_MARKER)

    def scan_and_decrypt(self, data: dict[str, Any]) -> dict[str, Any]:
        """Recursively decrypt all ``ENC:``-prefixed values in *data*.

        Returns a deep copy — the input is not mutated.
        Logs a warning for values that fail to decrypt but does not raise,
        so a single bad value doesn't abort startup.
        """
        return self._walk(copy.deepcopy(data))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _walk(self, node: Any) -> Any:
        if isinstance(node, dict):
            return {k: self._walk(v) for k, v in node.items()}
        if isinstance(node, list):
            return [self._walk(item) for item in node]
        if isinstance(node, str) and self.is_encrypted(node):
            try:
                return self.decrypt(node)
            except ConfigurationEncryptionError:
                logger.warning("Failed to decrypt encrypted config value — leaving raw")
                return node
        return node

    @staticmethod
    def _make_fernet(raw_key: str):  # type: ignore[return]
        """Derive a Fernet key from an arbitrary-length string key."""
        digest = hashlib.sha256(raw_key.encode()).digest()
        url_safe_key = base64.urlsafe_b64encode(digest)
        return Fernet(url_safe_key)

    @staticmethod
    def generate_key() -> str:
        """Generate a new random Fernet key (requires ``cryptography``)."""
        if not _HAS_CRYPTOGRAPHY:
            raise ConfigurationEncryptionError(
                "cryptography package required to generate keys"
            )
        from cryptography.fernet import Fernet  # noqa: F811
        return Fernet.generate_key().decode()
