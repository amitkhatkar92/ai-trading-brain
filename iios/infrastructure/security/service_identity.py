"""
iios/infrastructure/security/service_identity.py
=================================================
ServiceIdentity — represents a software service (microservice, agent, etc.).
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Optional

from .principal import Principal
from .security_constants import IdentityStatus, PrincipalType
from .security_models import PrincipalRecord

__all__ = ["ServiceIdentity"]


class ServiceIdentity(Principal):
    """A service principal (represents an IIOS layer, agent, or external service).

    Usage::

        svc = ServiceIdentity(
            name="execution_engine",
            roles=["order:write", "risk:read"],
        )
    """

    def __init__(
        self,
        principal_id: Optional[str] = None,
        name: str = "unknown_service",
        service_name: str = "",
        version: str = "1.0",
        roles: Optional[list[str]] = None,
        attributes: Optional[dict[str, Any]] = None,
        status: IdentityStatus = IdentityStatus.ACTIVE,
    ) -> None:
        self._principal_id = principal_id or f"service:{uuid.uuid4()}"
        self._name = name
        self.service_name = service_name or name
        self.version = version
        self._status = status
        self._roles: list[str] = list(roles or [])
        self._attributes: dict[str, Any] = dict(attributes or {})
        self.created_at = time.time()
        self.updated_at = time.time()

    @property
    def principal_id(self) -> str:
        return self._principal_id

    @property
    def principal_type(self) -> PrincipalType:
        return PrincipalType.SERVICE

    @property
    def name(self) -> str:
        return self._name

    @property
    def status(self) -> IdentityStatus:
        return self._status

    @status.setter
    def status(self, value: IdentityStatus) -> None:
        self._status = value
        self.updated_at = time.time()

    def add_role(self, role_name: str) -> None:
        if role_name not in self._roles:
            self._roles.append(role_name)
            self.updated_at = time.time()

    def has_role(self, role_name: str) -> bool:
        return role_name in self._roles

    def get_attribute(self, key: str, default: Any = None) -> Any:
        return self._attributes.get(key, default)

    def set_attribute(self, key: str, value: Any) -> None:
        self._attributes[key] = value
        self.updated_at = time.time()

    def to_record(self) -> PrincipalRecord:
        return PrincipalRecord(
            principal_id=self._principal_id,
            principal_type=PrincipalType.SERVICE,
            name=self._name,
            status=self._status,
            roles=list(self._roles),
            attributes=dict(self._attributes),
            created_at=self.created_at,
            updated_at=self.updated_at,
            metadata={"service_name": self.service_name, "version": self.version},
        )
