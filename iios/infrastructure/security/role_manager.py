"""
iios/infrastructure/security/role_manager.py
=============================================
Registry for RBAC roles with permission assignment and hierarchical inheritance.
"""

from __future__ import annotations

import logging
import threading
from typing import Optional

from .security_constants import SUPER_ADMIN_ROLE
from .security_exceptions import (
    RoleNotFoundError,
    RoleAlreadyExistsError,
    AuthorizationError,
)
from .security_models import RoleRecord

__all__ = ["RoleManager", "get_role_manager", "reset_role_manager"]

_LOG = logging.getLogger("iios.security.role")
_mgr_lock = threading.Lock()
_manager: Optional["RoleManager"] = None

# Built-in role hierarchy
_BUILTIN_ROLES: list[dict] = [
    {
        "name": "super_admin",
        "description": "Full system access",
        "permissions": ["*"],
        "parent_roles": [],
        "is_system": True,
    },
    {
        "name": "admin",
        "description": "Administrative access (no system operations)",
        "permissions": ["iios:admin", "audit:read", "secrets:read"],
        "parent_roles": ["viewer", "trader"],
        "is_system": True,
    },
    {
        "name": "trader",
        "description": "Can execute trades and manage orders",
        "permissions": ["trade:execute", "trade:read", "orders:read", "orders:write", "orders:cancel", "portfolio:read"],
        "parent_roles": ["viewer"],
        "is_system": True,
    },
    {
        "name": "viewer",
        "description": "Read-only access",
        "permissions": ["trade:read", "orders:read", "portfolio:read", "iios:read"],
        "parent_roles": [],
        "is_system": True,
    },
    {
        "name": "risk_manager",
        "description": "Risk oversight and override",
        "permissions": ["risk:read", "risk:override", "portfolio:read", "orders:read"],
        "parent_roles": ["viewer"],
        "is_system": True,
    },
    {
        "name": "service",
        "description": "Internal service-to-service access",
        "permissions": ["iios:read", "iios:write"],
        "parent_roles": [],
        "is_system": True,
    },
]


class RoleManager:
    """Thread-safe RBAC role registry with inheritance resolution.

    Usage::

        rm = get_role_manager()
        rm.create("data_analyst", permissions=["portfolio:read", "orders:read"])
        perms = rm.resolve_permissions("trader")   # includes parent permissions
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._roles: dict[str, RoleRecord] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        for r in _BUILTIN_ROLES:
            self._roles[r["name"]] = RoleRecord(
                name=r["name"],
                description=r["description"],
                permissions=list(r["permissions"]),
                parent_roles=list(r["parent_roles"]),
                is_system=r["is_system"],
            )

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def create(
        self,
        name: str,
        description: str = "",
        permissions: Optional[list[str]] = None,
        parent_roles: Optional[list[str]] = None,
        is_system: bool = False,
    ) -> RoleRecord:
        with self._lock:
            if name in self._roles:
                raise RoleAlreadyExistsError(
                    f"Role '{name}' already exists",
                    code="SEC-ROLE-001",
                    context={"name": name},
                )
            role = RoleRecord(
                name=name,
                description=description,
                permissions=list(permissions or []),
                parent_roles=list(parent_roles or []),
                is_system=is_system,
            )
            self._roles[name] = role
        _LOG.debug("Created role: %s", name)
        return role

    def get(self, name: str) -> RoleRecord:
        r = self.get_optional(name)
        if r is None:
            raise RoleNotFoundError(
                f"Role '{name}' not found",
                code="SEC-ROLE-002",
                context={"name": name},
            )
        return r

    def get_optional(self, name: str) -> Optional[RoleRecord]:
        with self._lock:
            return self._roles.get(name)

    def has(self, name: str) -> bool:
        with self._lock:
            return name in self._roles

    def delete(self, name: str) -> bool:
        with self._lock:
            role = self._roles.get(name)
            if role is None:
                return False
            if role.is_system:
                raise AuthorizationError(
                    f"Cannot delete system role '{name}'",
                    code="SEC-ROLE-003",
                    context={"name": name},
                )
            del self._roles[name]
        _LOG.info("Deleted role: %s", name)
        return True

    def add_permission(self, role_name: str, permission: str) -> None:
        role = self.get(role_name)
        if permission not in role.permissions:
            role.permissions.append(permission)

    def remove_permission(self, role_name: str, permission: str) -> None:
        role = self.get(role_name)
        if permission in role.permissions:
            role.permissions.remove(permission)

    def list_all(self) -> list[RoleRecord]:
        with self._lock:
            return list(self._roles.values())

    def list_names(self) -> list[str]:
        with self._lock:
            return list(self._roles.keys())

    # ── Permission resolution (with inheritance) ──────────────────────────────

    def resolve_permissions(self, role_name: str, _visited: Optional[set[str]] = None) -> set[str]:
        """Return the complete set of permissions for *role_name*, including inherited ones."""
        if _visited is None:
            _visited = set()
        if role_name in _visited:
            return set()  # cycle protection
        _visited.add(role_name)

        role = self.get_optional(role_name)
        if role is None:
            return set()

        perms = set(role.permissions)
        for parent in role.parent_roles:
            perms |= self.resolve_permissions(parent, _visited)
        return perms

    def has_permission(self, role_name: str, permission: str) -> bool:
        """Return True if *role_name* has *permission* (direct or inherited)."""
        from .permission_manager import get_permission_manager
        resolved = self.resolve_permissions(role_name)
        if "*" in resolved:
            return True
        pm = get_permission_manager()
        for p in resolved:
            if pm.matches(permission, p):
                return True
        return False

    def reset(self) -> None:
        with self._lock:
            self._roles.clear()
            self._register_defaults()


# ── Singleton ─────────────────────────────────────────────────────────────────

def get_role_manager() -> RoleManager:
    global _manager
    with _mgr_lock:
        if _manager is None:
            _manager = RoleManager()
        return _manager


def reset_role_manager() -> None:
    global _manager
    with _mgr_lock:
        if _manager is not None:
            _manager.reset()
        _manager = None
