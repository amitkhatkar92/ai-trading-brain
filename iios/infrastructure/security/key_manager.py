"""
iios/infrastructure/security/key_manager.py
============================================
Manages encryption key lifecycle: generation, rotation, revocation, and storage.
Key material is held only in-memory (encrypted at rest in production via vault).
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from typing import Optional

from .crypto_provider import get_crypto_provider
from .security_constants import (
    EncryptionAlgorithm,
    KeyStatus,
    KeyType,
    DEFAULT_KEY_ROTATION_DAYS,
)
from .security_exceptions import KeyNotFoundError, KeyRotationError, KeyRevocationError
from .security_models import KeyRecord

__all__ = ["KeyManager", "get_key_manager", "reset_key_manager"]

_LOG = logging.getLogger("iios.security.key")
_mgr_lock = threading.Lock()
_manager: Optional["KeyManager"] = None


class KeyManager:
    """Thread-safe encryption key lifecycle manager.

    Keys are stored in memory as bytes. The metadata (KeyRecord) tracks
    rotation schedules and status. For production, connect a VaultProvider
    as the persistent backend.

    Usage::

        km = get_key_manager()
        key_id, key_bytes = km.generate("data_encryption", rotation_days=90)
        ciphertext = get_crypto_provider().encrypt(data, key_bytes)
        active_key = km.get_active("data_encryption")
    """

    def __init__(self, rotation_days: int = DEFAULT_KEY_ROTATION_DAYS) -> None:
        self._lock = threading.RLock()
        self._default_rotation_days = rotation_days
        # key_id → (KeyRecord, raw_bytes)
        self._keys: dict[str, tuple[KeyRecord, bytes]] = {}
        # name → current active key_id
        self._active: dict[str, str] = {}

    # ── Generation ────────────────────────────────────────────────────────────

    def generate(
        self,
        name: str,
        algorithm: EncryptionAlgorithm = EncryptionAlgorithm.FERNET,
        rotation_days: Optional[int] = None,
        key_type: KeyType = KeyType.SYMMETRIC,
    ) -> tuple[str, bytes]:
        """Generate a new key and register it as the active key for *name*.

        Returns (key_id, raw_key_bytes).
        """
        days = rotation_days if rotation_days is not None else self._default_rotation_days
        crypto = get_crypto_provider()

        raw: bytes
        if algorithm == EncryptionAlgorithm.FERNET:
            raw = crypto.generate_key(32)
        else:
            raw = crypto.generate_key(32)

        record = KeyRecord(
            name=name,
            key_type=key_type,
            algorithm=algorithm,
            status=KeyStatus.ACTIVE,
            rotates_at=time.time() + days * 86400 if days > 0 else None,
        )

        with self._lock:
            # Mark any existing active key as INACTIVE
            old_id = self._active.get(name)
            if old_id and old_id in self._keys:
                old_record, old_raw = self._keys[old_id]
                if old_record.status == KeyStatus.ACTIVE:
                    old_record.status = KeyStatus.INACTIVE

            self._keys[record.key_id] = (record, raw)
            self._active[name] = record.key_id

        _LOG.info("Generated key '%s' (id=%s, algo=%s)", name, record.key_id[:8], algorithm.value)
        return record.key_id, raw

    # ── Retrieval ─────────────────────────────────────────────────────────────

    def get_raw(self, key_id: str) -> bytes:
        """Return the raw key bytes for *key_id*."""
        with self._lock:
            entry = self._keys.get(key_id)
        if entry is None:
            raise KeyNotFoundError(
                f"Key '{key_id}' not found",
                code="SEC-KEY-001",
                context={"key_id": key_id},
            )
        return entry[1]

    def get_record(self, key_id: str) -> KeyRecord:
        with self._lock:
            entry = self._keys.get(key_id)
        if entry is None:
            raise KeyNotFoundError(
                f"Key '{key_id}' not found",
                code="SEC-KEY-002",
                context={"key_id": key_id},
            )
        return entry[0]

    def get_active(self, name: str) -> tuple[str, bytes]:
        """Return (key_id, raw_bytes) for the active key named *name*."""
        with self._lock:
            key_id = self._active.get(name)
        if key_id is None:
            raise KeyNotFoundError(
                f"No active key for name '{name}'",
                code="SEC-KEY-003",
                context={"name": name},
            )
        return key_id, self.get_raw(key_id)

    # ── Rotation ──────────────────────────────────────────────────────────────

    def rotate(self, name: str) -> tuple[str, bytes]:
        """Rotate the active key for *name*. Old key is marked ROTATED.

        Returns (new_key_id, new_raw_bytes).
        """
        with self._lock:
            old_id = self._active.get(name)
            if old_id and old_id in self._keys:
                old_record, _ = self._keys[old_id]
                old_record.status = KeyStatus.ROTATED
                _LOG.info("Rotated key '%s' (old id=%s)", name, old_id[:8])

        new_id, new_raw = self.generate(name)
        if old_id:
            new_record = self.get_record(new_id)
            new_record.rotated_from = old_id

        _LOG.info("Key '%s' rotated → new id=%s", name, new_id[:8])
        return new_id, new_raw

    def needs_rotation(self, name: str) -> bool:
        """Return True if the active key for *name* is due for rotation."""
        try:
            key_id, _ = self.get_active(name)
            record = self.get_record(key_id)
            return record.needs_rotation
        except KeyNotFoundError:
            return False

    # ── Revocation ────────────────────────────────────────────────────────────

    def revoke(self, key_id: str) -> None:
        with self._lock:
            entry = self._keys.get(key_id)
            if entry is None:
                raise KeyRevocationError(
                    f"Key '{key_id}' not found for revocation",
                    code="SEC-KEY-004",
                    context={"key_id": key_id},
                )
            entry[0].status = KeyStatus.REVOKED
            # Remove from active map if it was active
            for name, active_id in list(self._active.items()):
                if active_id == key_id:
                    del self._active[name]
        _LOG.warning("Revoked key id=%s", key_id[:8])

    # ── Inventory ─────────────────────────────────────────────────────────────

    def list_records(self) -> list[KeyRecord]:
        with self._lock:
            return [r for r, _ in self._keys.values()]

    def active_names(self) -> list[str]:
        with self._lock:
            return list(self._active.keys())

    def reset(self) -> None:
        with self._lock:
            self._keys.clear()
            self._active.clear()


# ── Singleton ─────────────────────────────────────────────────────────────────

def get_key_manager() -> KeyManager:
    global _manager
    with _mgr_lock:
        if _manager is None:
            _manager = KeyManager()
        return _manager


def reset_key_manager() -> None:
    global _manager
    with _mgr_lock:
        if _manager is not None:
            _manager.reset()
        _manager = None
