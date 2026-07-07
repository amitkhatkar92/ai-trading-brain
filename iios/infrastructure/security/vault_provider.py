"""
iios/infrastructure/security/vault_provider.py
===============================================
Vault provider interface + InMemoryVault implementation.
Future: connect to HashiCorp Vault, AWS Secrets Manager, Azure Key Vault.
"""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from typing import Optional

__all__ = [
    "VaultProvider",
    "InMemoryVaultProvider",
    "EnvironmentVaultProvider",
]

_LOG = logging.getLogger("iios.security.vault")


class VaultProvider(ABC):
    """Abstract interface for an external secrets vault."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Unique identifier for this vault provider."""

    @abstractmethod
    def read(self, path: str) -> Optional[bytes]:
        """Read raw bytes for *path*. Returns None if not found."""

    @abstractmethod
    def write(self, path: str, value: bytes) -> None:
        """Write raw bytes to *path*."""

    @abstractmethod
    def delete(self, path: str) -> bool:
        """Delete *path*. Returns True if it existed."""

    @abstractmethod
    def exists(self, path: str) -> bool:
        """Return True if *path* exists in the vault."""

    @abstractmethod
    def list_paths(self, prefix: str = "") -> list[str]:
        """List all paths, optionally filtered by *prefix*."""

    def is_available(self) -> bool:
        """Return True if the vault backend is reachable."""
        return True


class InMemoryVaultProvider(VaultProvider):
    """Simple in-memory vault (not persistent). Suitable for testing and development."""

    def __init__(self, name: str = "inmemory") -> None:
        self._name = name
        self._store: dict[str, bytes] = {}

    @property
    def provider_name(self) -> str:
        return self._name

    def read(self, path: str) -> Optional[bytes]:
        return self._store.get(path)

    def write(self, path: str, value: bytes) -> None:
        self._store[path] = value
        _LOG.debug("Vault write: %s", path)

    def delete(self, path: str) -> bool:
        return self._store.pop(path, None) is not None

    def exists(self, path: str) -> bool:
        return path in self._store

    def list_paths(self, prefix: str = "") -> list[str]:
        return [p for p in self._store if p.startswith(prefix)]

    def clear(self) -> None:
        self._store.clear()

    def __len__(self) -> int:
        return len(self._store)


class EnvironmentVaultProvider(VaultProvider):
    """Read-only vault backed by environment variables.

    Maps path separators (``/``) to underscores and upper-cases the key.
    E.g., ``iios/broker/dhan/api_key`` → env var ``IIOS_BROKER_DHAN_API_KEY``.
    """

    def __init__(self, prefix: str = "") -> None:
        self._prefix = prefix.upper()

    @property
    def provider_name(self) -> str:
        return "environment"

    def _to_env_key(self, path: str) -> str:
        key = path.upper().replace("/", "_").replace("-", "_")
        if self._prefix:
            key = f"{self._prefix}_{key}"
        return key

    def read(self, path: str) -> Optional[bytes]:
        env_key = self._to_env_key(path)
        val = os.environ.get(env_key)
        return val.encode() if val is not None else None

    def write(self, path: str, value: bytes) -> None:
        # Environment variables are read-only at runtime
        raise NotImplementedError("EnvironmentVaultProvider is read-only")

    def delete(self, path: str) -> bool:
        raise NotImplementedError("EnvironmentVaultProvider is read-only")

    def exists(self, path: str) -> bool:
        return self._to_env_key(path) in os.environ

    def list_paths(self, prefix: str = "") -> list[str]:
        env_prefix = self._to_env_key(prefix) if prefix else self._prefix
        result = []
        for key in os.environ:
            if key.startswith(env_prefix):
                # Convert back to path format (rough approximation)
                path = key[len(self._prefix):].lstrip("_").lower().replace("_", "/")
                result.append(path)
        return result
