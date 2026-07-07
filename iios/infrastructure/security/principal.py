"""
iios/infrastructure/security/principal.py
==========================================
Abstract base for all principals in the IIOS Security Framework.
A principal is any entity that can be authenticated and authorised.
"""

from __future__ import annotations

import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

from .security_constants import (
    IdentityStatus,
    PrincipalType,
    ANONYMOUS_PRINCIPAL_ID,
    SYSTEM_PRINCIPAL_ID,
)
from .security_models import PrincipalRecord

__all__ = [
    "Principal",
    "AnonymousPrincipal",
    "ANONYMOUS",
    "SYSTEM",
]


class Principal(ABC):
    """Abstract base for all principals (users, services, systems, machines)."""

    @property
    @abstractmethod
    def principal_id(self) -> str:
        """Unique identifier for this principal."""

    @property
    @abstractmethod
    def principal_type(self) -> PrincipalType:
        """Type classification of this principal."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name."""

    @property
    @abstractmethod
    def status(self) -> IdentityStatus:
        """Current status of this identity."""

    @property
    def is_active(self) -> bool:
        return self.status == IdentityStatus.ACTIVE

    @property
    def is_anonymous(self) -> bool:
        return self.principal_id == ANONYMOUS_PRINCIPAL_ID

    @property
    def is_system(self) -> bool:
        return self.principal_id == SYSTEM_PRINCIPAL_ID

    @abstractmethod
    def to_record(self) -> PrincipalRecord:
        """Serialise this principal to a PrincipalRecord."""

    @abstractmethod
    def has_role(self, role_name: str) -> bool:
        """Return True if this principal holds the given role."""

    @abstractmethod
    def get_attribute(self, key: str, default: Any = None) -> Any:
        """Return a principal-specific attribute."""

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.principal_id!r}, name={self.name!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Principal):
            return NotImplemented
        return self.principal_id == other.principal_id

    def __hash__(self) -> int:
        return hash(self.principal_id)


# ── Anonymous & System singletons ─────────────────────────────────────────────

class AnonymousPrincipal(Principal):
    """Represents an unauthenticated caller."""

    @property
    def principal_id(self) -> str:
        return ANONYMOUS_PRINCIPAL_ID

    @property
    def principal_type(self) -> PrincipalType:
        return PrincipalType.ANONYMOUS

    @property
    def name(self) -> str:
        return "anonymous"

    @property
    def status(self) -> IdentityStatus:
        return IdentityStatus.ACTIVE

    def to_record(self) -> PrincipalRecord:
        return PrincipalRecord(
            principal_id=ANONYMOUS_PRINCIPAL_ID,
            principal_type=PrincipalType.ANONYMOUS,
            name="anonymous",
        )

    def has_role(self, role_name: str) -> bool:
        return False

    def get_attribute(self, key: str, default: Any = None) -> Any:
        return default


# Pre-built singletons
ANONYMOUS: AnonymousPrincipal = AnonymousPrincipal()
SYSTEM: "SystemIdentity | None" = None  # populated after SystemIdentity is defined
