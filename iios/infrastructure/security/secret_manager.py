"""
iios/infrastructure/security/secret_manager.py
===============================================
High-level secrets management: store, retrieve, rotate, and audit secrets.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Optional

from .secret_store import SecretStore
from .vault_provider import VaultProvider, InMemoryVaultProvider
from .security_constants import SecretType, SecretStatus
from .security_exceptions import (
    SecretNotFoundError,
    SecretAlreadyExistsError,
    SecretRotationError,
)
from .security_models import SecretRecord

__all__ = ["SecretManager", "get_secret_manager", "reset_secret_manager"]

_LOG = logging.getLogger("iios.security.secret")
_mgr_lock = threading.Lock()
_manager: Optional["SecretManager"] = None


class SecretManager:
    """Thread-safe secrets lifecycle manager.

    Provides store/get/rotate/delete operations. Supports an optional external
    VaultProvider for persistent storage (e.g., HashiCorp Vault, env vars).

    Usage::

        sm = get_secret_manager()
        sm.set("iios/broker/dhan/api_key", b"sk-secret", secret_type=SecretType.API_KEY)
        value = sm.get("iios/broker/dhan/api_key")
        sm.rotate("iios/broker/dhan/api_key", new_value=b"sk-new-secret")
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._store = SecretStore()
        self._vault: Optional[VaultProvider] = None

    # ── Vault provider ────────────────────────────────────────────────────────

    def set_vault_provider(self, vault: VaultProvider) -> None:
        with self._lock:
            self._vault = vault
            _LOG.info("Vault provider set: %s", vault.provider_name)

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def set(
        self,
        path: str,
        value: bytes,
        secret_type: SecretType = SecretType.GENERIC,
        description: str = "",
        owner: str = "",
        tags: Optional[list[str]] = None,
        ttl_seconds: Optional[float] = None,
        created_by: str = "",
        allow_override: bool = True,
    ) -> SecretRecord:
        """Store a secret at *path*."""
        with self._lock:
            if not allow_override and self._store.exists(path):
                raise SecretAlreadyExistsError(
                    f"Secret '{path}' already exists",
                    code="SEC-SM-001",
                    context={"path": path},
                )

        record = SecretRecord(
            name=path.split("/")[-1],
            path=path,
            secret_type=secret_type,
            status=SecretStatus.ACTIVE,
            description=description,
            owner=owner,
            tags=list(tags or []),
            expires_at=time.time() + ttl_seconds if ttl_seconds else None,
        )

        self._store.put(path, value, record, created_by=created_by)

        # Also write to vault if available
        if self._vault and self._vault.is_available():
            try:
                self._vault.write(path, value)
            except Exception as exc:
                _LOG.warning("Vault write failed for '%s': %s", path, exc)

        _LOG.info("Secret stored: %s (type=%s)", path, secret_type.value)
        return record

    def get(self, path: str, version: Optional[int] = None) -> bytes:
        """Retrieve a secret's plaintext value.

        Falls through to the vault provider if not in the local store.
        """
        # Try local encrypted store first
        if self._store.exists(path):
            return self._store.get_plaintext(path, version)

        # Try vault provider
        if self._vault and self._vault.is_available():
            val = self._vault.read(path)
            if val is not None:
                _LOG.debug("Secret '%s' loaded from vault", path)
                return val

        raise SecretNotFoundError(
            f"Secret '{path}' not found",
            code="SEC-SM-002",
            context={"path": path},
        )

    def get_str(self, path: str, version: Optional[int] = None) -> str:
        """Like get() but returns a str."""
        return self.get(path, version).decode()

    def get_record(self, path: str) -> SecretRecord:
        return self._store.get_record(path)

    def exists(self, path: str) -> bool:
        if self._store.exists(path):
            return True
        if self._vault and self._vault.is_available():
            return self._vault.exists(path)
        return False

    def delete(self, path: str) -> bool:
        deleted = self._store.delete(path)
        if self._vault and self._vault.is_available():
            try:
                self._vault.delete(path)
            except (NotImplementedError, Exception):
                pass
        if deleted:
            _LOG.info("Deleted secret: %s", path)
        return deleted

    # ── Rotation ──────────────────────────────────────────────────────────────

    def rotate(self, path: str, new_value: bytes, rotated_by: str = "") -> SecretRecord:
        """Replace a secret's value (new version). Returns updated record."""
        try:
            old_record = self._store.get_record(path)
        except SecretNotFoundError:
            raise SecretRotationError(
                f"Cannot rotate non-existent secret '{path}'",
                code="SEC-SM-003",
                context={"path": path},
            )

        # Update status of old record
        old_record.status = SecretStatus.ROTATED

        new_record = SecretRecord(
            secret_id=old_record.secret_id,  # same logical ID
            name=old_record.name,
            path=path,
            secret_type=old_record.secret_type,
            status=SecretStatus.ACTIVE,
            description=old_record.description,
            owner=old_record.owner,
            tags=list(old_record.tags),
            expires_at=old_record.expires_at,
            metadata=dict(old_record.metadata),
            current_version=old_record.current_version + 1,
        )

        self._store.put(path, new_value, new_record, created_by=rotated_by)

        if self._vault and self._vault.is_available():
            try:
                self._vault.write(path, new_value)
            except Exception as exc:
                _LOG.warning("Vault write during rotation failed for '%s': %s", path, exc)

        _LOG.info("Rotated secret: %s (version %d)", path, new_record.current_version)
        return new_record

    # ── List ──────────────────────────────────────────────────────────────────

    def list_paths(self, prefix: str = "") -> list[str]:
        return self._store.list_paths(prefix)

    def list_records(self, prefix: str = "") -> list[SecretRecord]:
        return self._store.list_records(prefix)

    def count(self) -> int:
        return len(self._store.list_paths())

    # ── Convenience helpers ───────────────────────────────────────────────────

    def set_api_key(self, path: str, key: bytes, **kwargs: Any) -> SecretRecord:
        return self.set(path, key, secret_type=SecretType.API_KEY, **kwargs)

    def set_password(self, path: str, password: bytes, **kwargs: Any) -> SecretRecord:
        return self.set(path, password, secret_type=SecretType.PASSWORD, **kwargs)

    def set_database_url(self, path: str, url: bytes, **kwargs: Any) -> SecretRecord:
        return self.set(path, url, secret_type=SecretType.DATABASE_URL, **kwargs)

    def reset(self) -> None:
        with self._lock:
            self._store.clear()
            self._vault = None


# ── Singleton ─────────────────────────────────────────────────────────────────

def get_secret_manager() -> SecretManager:
    global _manager
    with _mgr_lock:
        if _manager is None:
            _manager = SecretManager()
        return _manager


def reset_secret_manager() -> None:
    global _manager
    with _mgr_lock:
        if _manager is not None:
            _manager.reset()
        _manager = None
