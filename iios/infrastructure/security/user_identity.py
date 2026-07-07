"""
iios/infrastructure/security/user_identity.py
==============================================
UserIdentity — represents a human user principal.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from .principal import Principal
from .security_constants import IdentityStatus, PrincipalType
from .security_models import PrincipalRecord

__all__ = ["UserIdentity"]


@dataclass
class UserIdentity(Principal):
    """A human user identity.

    Usage::

        user = UserIdentity(
            principal_id="user:alice",
            name="Alice",
            email="alice@example.com",
            roles=["trader", "viewer"],
        )
    """
    _principal_id: str = field(default_factory=lambda: f"user:{uuid.uuid4()}")
    _name: str = "unknown"
    email: str = ""
    display_name: str = ""
    _status: IdentityStatus = IdentityStatus.ACTIVE
    _roles: list[str] = field(default_factory=list)
    _attributes: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    last_login: Optional[float] = None
    login_failures: int = 0
    locked_until: Optional[float] = None

    def __init__(
        self,
        principal_id: Optional[str] = None,
        name: str = "unknown",
        email: str = "",
        display_name: str = "",
        status: IdentityStatus = IdentityStatus.ACTIVE,
        roles: Optional[list[str]] = None,
        attributes: Optional[dict[str, Any]] = None,
    ) -> None:
        self._principal_id = principal_id or f"user:{uuid.uuid4()}"
        self._name = name
        self.email = email
        self.display_name = display_name or name
        self._status = status
        self._roles = list(roles or [])
        self._attributes = dict(attributes or {})
        self.created_at = time.time()
        self.updated_at = time.time()
        self.last_login = None
        self.login_failures = 0
        self.locked_until = None

    @property
    def principal_id(self) -> str:
        return self._principal_id

    @property
    def principal_type(self) -> PrincipalType:
        return PrincipalType.USER

    @property
    def name(self) -> str:
        return self._name

    @property
    def status(self) -> IdentityStatus:
        if self._status == IdentityStatus.LOCKED:
            if self.locked_until is not None and time.time() >= self.locked_until:
                return IdentityStatus.ACTIVE  # auto-unlock
        return self._status

    @status.setter
    def status(self, value: IdentityStatus) -> None:
        self._status = value
        self.updated_at = time.time()

    def add_role(self, role_name: str) -> None:
        if role_name not in self._roles:
            self._roles.append(role_name)
            self.updated_at = time.time()

    def remove_role(self, role_name: str) -> None:
        if role_name in self._roles:
            self._roles.remove(role_name)
            self.updated_at = time.time()

    def has_role(self, role_name: str) -> bool:
        return role_name in self._roles

    def set_attribute(self, key: str, value: Any) -> None:
        self._attributes[key] = value
        self.updated_at = time.time()

    def get_attribute(self, key: str, default: Any = None) -> Any:
        return self._attributes.get(key, default)

    def record_login(self) -> None:
        self.last_login = time.time()
        self.login_failures = 0
        self.updated_at = time.time()

    def record_failure(self, max_failures: int = 5, lockout_seconds: float = 900) -> bool:
        """Increment failure count. Returns True if the account is now locked."""
        self.login_failures += 1
        self.updated_at = time.time()
        if self.login_failures >= max_failures:
            self._status = IdentityStatus.LOCKED
            self.locked_until = time.time() + lockout_seconds
            return True
        return False

    def unlock(self) -> None:
        self._status = IdentityStatus.ACTIVE
        self.login_failures = 0
        self.locked_until = None
        self.updated_at = time.time()

    def to_record(self) -> PrincipalRecord:
        return PrincipalRecord(
            principal_id=self._principal_id,
            principal_type=PrincipalType.USER,
            name=self._name,
            status=self.status,
            roles=list(self._roles),
            attributes=dict(self._attributes),
            created_at=self.created_at,
            updated_at=self.updated_at,
            last_login=self.last_login,
            login_failures=self.login_failures,
            locked_until=self.locked_until,
            metadata={"email": self.email, "display_name": self.display_name},
        )
