"""
iios/infrastructure/security/identity_provider.py
==================================================
Abstract identity provider interface.
Concrete implementations can integrate with LDAP, OAuth, internal DB, etc.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from .principal import Principal
from .security_constants import PrincipalType
from .security_models import PrincipalRecord

__all__ = ["IdentityProvider", "InMemoryIdentityProvider"]


class IdentityProvider(ABC):
    """Abstract interface for identity lookup and validation."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Unique name identifying this provider."""

    @abstractmethod
    def find(self, principal_id: str) -> Optional[Principal]:
        """Look up a principal by ID. Returns None if not found."""

    @abstractmethod
    def find_by_name(self, name: str, principal_type: Optional[PrincipalType] = None) -> Optional[Principal]:
        """Look up a principal by name (optionally filtered by type)."""

    @abstractmethod
    def exists(self, principal_id: str) -> bool:
        """Return True if the principal is known to this provider."""

    @abstractmethod
    def list_principals(self, principal_type: Optional[PrincipalType] = None) -> list[Principal]:
        """List all known principals, optionally filtered by type."""

    def supports(self, principal_type: PrincipalType) -> bool:
        """Return True if this provider handles the given principal type.
        Default: handle all types."""
        return True


class InMemoryIdentityProvider(IdentityProvider):
    """Simple in-memory identity provider (used internally and for testing).

    Thread safety: callers should synchronise externally if needed,
    or rely on the IdentityManager which holds a lock.
    """

    def __init__(self, name: str = "inmemory") -> None:
        self._name = name
        self._store: dict[str, Principal] = {}   # principal_id → Principal

    @property
    def provider_name(self) -> str:
        return self._name

    def register(self, principal: Principal) -> None:
        self._store[principal.principal_id] = principal

    def unregister(self, principal_id: str) -> bool:
        return self._store.pop(principal_id, None) is not None

    def find(self, principal_id: str) -> Optional[Principal]:
        return self._store.get(principal_id)

    def find_by_name(self, name: str, principal_type: Optional[PrincipalType] = None) -> Optional[Principal]:
        for p in self._store.values():
            if p.name == name:
                if principal_type is None or p.principal_type == principal_type:
                    return p
        return None

    def exists(self, principal_id: str) -> bool:
        return principal_id in self._store

    def list_principals(self, principal_type: Optional[PrincipalType] = None) -> list[Principal]:
        if principal_type is None:
            return list(self._store.values())
        return [p for p in self._store.values() if p.principal_type == principal_type]

    def clear(self) -> None:
        self._store.clear()

    def __len__(self) -> int:
        return len(self._store)
