"""
secret_manager.py — iios.integration.services
-----------------------------------------------
SecretManager — versioned secret storage and rotation for integration
connectors.

Secrets are stored in-memory only; real deployments back this with
HashiCorp Vault, AWS Secrets Manager, or Azure Key Vault. Secrets are
NEVER logged.

C15 Enterprise Integration & Connectivity — Phase 1, Module 4
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

_log = get_logger(__name__)


@dataclass
class SecretVersion:
    """A single version of a secret."""
    version_id:  str
    value:       str     # NEVER log this
    created_at:  str
    deprecated:  bool = False


@dataclass
class SecretEntry:
    """A named secret with version history."""
    secret_name: str
    versions:    List[SecretVersion] = field(default_factory=list)

    @property
    def current_version(self) -> Optional[SecretVersion]:
        active = [v for v in self.versions if not v.deprecated]
        return active[-1] if active else None

    @property
    def version_count(self) -> int:
        return len(self.versions)


class SecretManager:
    """
    Thread-safe versioned secret manager.

    Supports secret creation, retrieval, rotation (adds a new version),
    and deprecation of old versions.
    """

    def __init__(self, max_versions_per_secret: int = 10) -> None:
        self._lock        = threading.Lock()
        self._secrets:    Dict[str, SecretEntry] = {}
        self._max_ver     = max_versions_per_secret

    # ── Public ───────────────────────────────────────────────────────────

    def set_secret(self, name: str, value: str) -> str:
        """
        Create or update a secret by name. Returns the new version_id.
        """
        version_id = f"sv-{uuid.uuid4().hex[:10]}"
        version    = SecretVersion(
            version_id = version_id,
            value      = value,
            created_at = datetime.now(timezone.utc).isoformat(),
        )
        with self._lock:
            if name not in self._secrets:
                self._secrets[name] = SecretEntry(secret_name=name)
            entry = self._secrets[name]
            entry.versions.append(version)
            # Prune oldest versions beyond max
            if len(entry.versions) > self._max_ver:
                entry.versions = entry.versions[-self._max_ver:]
        return version_id

    def get_secret(self, name: str, version_id: Optional[str] = None) -> Optional[str]:
        """
        Retrieve a secret value. If version_id is None, returns the current.
        Returns None if not found.
        """
        with self._lock:
            entry = self._secrets.get(name)
            if entry is None:
                return None
            if version_id:
                for v in entry.versions:
                    if v.version_id == version_id:
                        return v.value
                return None
            cur = entry.current_version
        return cur.value if cur else None

    def rotate_secret(self, name: str, new_value: str) -> str:
        """
        Rotate a secret by deprecating the current version and adding a new one.
        Returns the new version_id.
        """
        with self._lock:
            entry = self._secrets.get(name)
            if entry and entry.current_version:
                entry.current_version.deprecated = True
        return self.set_secret(name, new_value)

    def delete_secret(self, name: str) -> bool:
        with self._lock:
            if name in self._secrets:
                del self._secrets[name]
                return True
        return False

    def list_names(self) -> List[str]:
        with self._lock:
            return list(self._secrets.keys())

    def version_ids(self, name: str) -> List[str]:
        with self._lock:
            entry = self._secrets.get(name)
            return [v.version_id for v in entry.versions] if entry else []

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._secrets)
