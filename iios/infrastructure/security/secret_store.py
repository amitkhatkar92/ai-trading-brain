"""
iios/infrastructure/security/secret_store.py
=============================================
Encrypted in-memory secret store.
All values are encrypted at rest using the EncryptionManager.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Optional

from .encryption_manager import get_encryption_manager
from .security_constants import SecretStatus
from .security_exceptions import (
    SecretNotFoundError,
    SecretAlreadyExistsError,
)
from .security_models import SecretRecord, SecretVersion

__all__ = ["SecretStore"]

_LOG = logging.getLogger("iios.security.secret_store")


class SecretStore:
    """Thread-safe encrypted in-memory store for secrets.

    Values are encrypted at rest using the process EncryptionManager.
    The plaintext value is NEVER stored in memory longer than needed.

    Usage::

        store = SecretStore()
        store.put("dhan/api_key", b"sk-abc123", record)
        value = store.get_plaintext("dhan/api_key")
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._records: dict[str, SecretRecord] = {}        # path → record
        # path → list[SecretVersion] (each version has encrypted_value)
        self._versions: dict[str, list[SecretVersion]] = {}

    # ── Write ─────────────────────────────────────────────────────────────────

    def put(
        self,
        path: str,
        plaintext_value: bytes,
        record: SecretRecord,
        created_by: str = "",
    ) -> SecretRecord:
        """Store a secret (encrypted). Creates or updates existing path."""
        em = get_encryption_manager()
        encrypted = em.encrypt(plaintext_value)

        with self._lock:
            existing_versions = self._versions.get(path, [])
            new_version_num = (max(v.version for v in existing_versions) + 1) if existing_versions else 1

            # Mark old current version as not current
            for v in existing_versions:
                v.is_current = False

            sv = SecretVersion(
                version=new_version_num,
                encrypted_value=encrypted,
                created_at=time.time(),
                created_by=created_by,
                is_current=True,
            )
            existing_versions.append(sv)
            self._versions[path] = existing_versions

            record.path = path
            record.current_version = new_version_num
            record.updated_at = time.time()
            self._records[path] = record

        _LOG.debug("Stored secret: %s (version %d)", path, new_version_num)
        return record

    # ── Read ──────────────────────────────────────────────────────────────────

    def get_plaintext(self, path: str, version: Optional[int] = None) -> bytes:
        """Retrieve and decrypt a secret's value."""
        with self._lock:
            record = self._records.get(path)
            if record is None:
                raise SecretNotFoundError(
                    f"Secret '{path}' not found",
                    code="SEC-SEC-001",
                    context={"path": path},
                )
            if record.is_expired:
                raise SecretNotFoundError(
                    f"Secret '{path}' has expired",
                    code="SEC-SEC-002",
                    context={"path": path},
                )
            versions = self._versions.get(path, [])
            sv = self._get_version(versions, version)

        em = get_encryption_manager()
        return em.decrypt(sv.encrypted_value)

    def get_record(self, path: str) -> SecretRecord:
        with self._lock:
            r = self._records.get(path)
        if r is None:
            raise SecretNotFoundError(
                f"Secret '{path}' not found",
                code="SEC-SEC-003",
                context={"path": path},
            )
        return r

    def get_record_optional(self, path: str) -> Optional[SecretRecord]:
        with self._lock:
            return self._records.get(path)

    def exists(self, path: str) -> bool:
        with self._lock:
            r = self._records.get(path)
            return r is not None and not r.is_expired

    # ── Delete ────────────────────────────────────────────────────────────────

    def delete(self, path: str) -> bool:
        with self._lock:
            if path not in self._records:
                return False
            self._records[path].status = SecretStatus.DELETED
            self._records.pop(path)
            self._versions.pop(path, None)
        _LOG.info("Deleted secret: %s", path)
        return True

    # ── List ──────────────────────────────────────────────────────────────────

    def list_paths(self, prefix: str = "") -> list[str]:
        with self._lock:
            paths = list(self._records.keys())
        return [p for p in paths if p.startswith(prefix)]

    def list_records(self, prefix: str = "") -> list[SecretRecord]:
        with self._lock:
            return [r for p, r in self._records.items() if p.startswith(prefix)]

    def version_count(self, path: str) -> int:
        with self._lock:
            return len(self._versions.get(path, []))

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _get_version(versions: list[SecretVersion], version: Optional[int]) -> SecretVersion:
        if not versions:
            raise SecretNotFoundError("No versions found", code="SEC-SEC-004")
        if version is None:
            # Return current
            for v in versions:
                if v.is_current:
                    return v
            return versions[-1]
        for v in versions:
            if v.version == version:
                return v
        raise SecretNotFoundError(f"Version {version} not found", code="SEC-SEC-005")

    def clear(self) -> None:
        with self._lock:
            self._records.clear()
            self._versions.clear()
