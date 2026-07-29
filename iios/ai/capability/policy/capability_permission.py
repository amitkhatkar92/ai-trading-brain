"""
capability_permission.py -- iios.ai.capability.policy
=======================================================
:class:`CapabilityPermission`    — per-principal, per-capability grant.
:class:`CapabilityAuthorization` — thread-safe RBAC + direct-grant manager.

A9 Enterprise Capability Platform — Phase 3, Module 9
"""
from __future__ import annotations

import fnmatch
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Dict, FrozenSet, List, Optional, Set

from ..exceptions.capability_exceptions import (
    AICapabilityPermissionDeniedError,
)


# ── CapabilityPermission ─────────────────────────────────────────────────────

@dataclass(frozen=True)
class CapabilityPermission:
    """Immutable grant record for (principal_id, capability_id)."""

    permission_id: str
    principal_id:  str
    capability_id: str   # exact capability_id or wildcard pattern
    granted_at:    float
    granted_by:    str
    expires_at:    Optional[float]

    @classmethod
    def create(
        cls,
        principal_id:  str,
        capability_id: str,
        granted_by:    str  = "system",
        expires_at:    Optional[float] = None,
    ) -> "CapabilityPermission":
        return cls(
            permission_id = str(uuid.uuid4()),
            principal_id  = principal_id,
            capability_id = capability_id,
            granted_at    = time.time(),
            granted_by    = granted_by,
            expires_at    = expires_at,
        )

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    def is_active(self) -> bool:
        return not self.is_expired()


# ── Role ─────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class CapabilityRole:
    """Named set of capability patterns."""

    role_id:      str
    name:         str
    capabilities: FrozenSet[str]  # exact IDs or fnmatch patterns

    @classmethod
    def create(cls, name: str, capabilities: FrozenSet[str]) -> "CapabilityRole":
        return cls(
            role_id      = str(uuid.uuid4()),
            name         = name,
            capabilities = capabilities,
        )

    def grants(self, capability_id: str) -> bool:
        for pattern in self.capabilities:
            if pattern == "*" or fnmatch.fnmatch(capability_id, pattern):
                return True
        return False


# ── CapabilityAuthorization ──────────────────────────────────────────────────

class CapabilityAuthorization:
    """
    Thread-safe RBAC + direct-grant authorization manager.

    Roles are named capability sets.  A principal may have multiple roles
    and also direct per-capability grants.
    """

    def __init__(self) -> None:
        self._lock:           threading.Lock                    = threading.Lock()
        self._roles:          Dict[str, CapabilityRole]          = {}  # name -> role
        self._principal_roles: Dict[str, Set[str]]               = {}  # principal -> role names
        self._permissions:    List[CapabilityPermission]          = []

    # ── roles ─────────────────────────────────────────────────────────────────

    def create_role(self, role: CapabilityRole) -> None:
        with self._lock:
            self._roles[role.name] = role

    def get_role(self, name: str) -> Optional[CapabilityRole]:
        with self._lock:
            return self._roles.get(name)

    def list_roles(self) -> List[CapabilityRole]:
        with self._lock:
            return list(self._roles.values())

    def assign_role(self, principal_id: str, role_name: str) -> None:
        with self._lock:
            self._principal_roles.setdefault(principal_id, set()).add(role_name)

    def revoke_role(self, principal_id: str, role_name: str) -> None:
        with self._lock:
            roles = self._principal_roles.get(principal_id, set())
            roles.discard(role_name)

    # ── direct grants ─────────────────────────────────────────────────────────

    def grant(self, permission: CapabilityPermission) -> None:
        with self._lock:
            self._permissions.append(permission)

    def revoke(self, principal_id: str, capability_id: str) -> None:
        with self._lock:
            self._permissions = [
                p for p in self._permissions
                if not (p.principal_id == principal_id and p.capability_id == capability_id)
            ]

    def list_permissions(self, principal_id: str) -> List[CapabilityPermission]:
        with self._lock:
            return [p for p in self._permissions if p.principal_id == principal_id]

    # ── authorization check ──────────────────────────────────────────────────

    def is_authorized(self, principal_id: str, capability_id: str) -> bool:
        """Return True if the principal has active access to the capability."""
        with self._lock:
            # 1. Check direct grants
            for perm in self._permissions:
                if (perm.principal_id == principal_id
                        and perm.is_active()
                        and fnmatch.fnmatch(capability_id, perm.capability_id)):
                    return True

            # 2. Check roles
            role_names = self._principal_roles.get(principal_id, set())
            for role_name in role_names:
                role = self._roles.get(role_name)
                if role and role.grants(capability_id):
                    return True

        return False

    def authorize(self, principal_id: str, capability_id: str) -> None:
        """Raise :class:`AICapabilityPermissionDeniedError` if not authorized."""
        if not self.is_authorized(principal_id, capability_id):
            raise AICapabilityPermissionDeniedError(
                f"Principal '{principal_id}' is not authorized to use "
                f"capability '{capability_id}'"
            )

    def permission_count(self) -> int:
        with self._lock:
            return len(self._permissions)
