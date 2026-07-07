"""
iios/infrastructure/security/system_identity.py
================================================
SystemIdentity — represents the IIOS platform itself.
Also provides a singleton SYSTEM principal.
"""

from __future__ import annotations

import time
from typing import Any, Optional

from .principal import Principal
from .security_constants import (
    IdentityStatus,
    PrincipalType,
    SYSTEM_PRINCIPAL_ID,
    SUPER_ADMIN_ROLE,
)
from .security_models import PrincipalRecord

__all__ = ["SystemIdentity", "get_system_identity"]

_system: Optional["SystemIdentity"] = None


class SystemIdentity(Principal):
    """The IIOS platform system identity.

    The system identity has full access to all resources and bypasses
    standard authorisation checks. Use only for internal framework operations.
    """

    def __init__(
        self,
        extra_roles: Optional[list[str]] = None,
        attributes: Optional[dict[str, Any]] = None,
    ) -> None:
        self._roles: list[str] = [SUPER_ADMIN_ROLE] + list(extra_roles or [])
        self._attributes: dict[str, Any] = dict(attributes or {})
        self.created_at = time.time()

    @property
    def principal_id(self) -> str:
        return SYSTEM_PRINCIPAL_ID

    @property
    def principal_type(self) -> PrincipalType:
        return PrincipalType.SYSTEM

    @property
    def name(self) -> str:
        return "iios-system"

    @property
    def status(self) -> IdentityStatus:
        return IdentityStatus.ACTIVE

    def has_role(self, role_name: str) -> bool:
        # System always has every role
        return True

    def get_attribute(self, key: str, default: Any = None) -> Any:
        return self._attributes.get(key, default)

    def to_record(self) -> PrincipalRecord:
        return PrincipalRecord(
            principal_id=SYSTEM_PRINCIPAL_ID,
            principal_type=PrincipalType.SYSTEM,
            name="iios-system",
            status=IdentityStatus.ACTIVE,
            roles=list(self._roles),
            attributes=dict(self._attributes),
            created_at=self.created_at,
            metadata={"is_system": True},
        )


def get_system_identity() -> SystemIdentity:
    """Return the process-wide SystemIdentity singleton."""
    global _system
    if _system is None:
        _system = SystemIdentity()
    return _system
