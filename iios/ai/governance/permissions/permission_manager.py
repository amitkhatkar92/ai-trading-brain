"""
permission_manager.py -- iios.ai.governance.permissions
=========================================================
:class:`PermissionManager` — high-level authorization façade.

A8 AI Governance Platform — Phase 3, Module 8
"""
from __future__ import annotations

from typing import List, Optional

from ..exceptions.governance_exceptions import (
    AIPermissionDeniedError,
    AIRoleAlreadyExistsError,
    AIRoleNotFoundError,
)
from .access_control import AccessControl, CapabilityRestriction, RolePolicy


class PermissionManager:
    """
    High-level authorization façade over :class:`AccessControl`.

    Provides role management, capability checking, and restriction application.
    """

    # Built-in system roles
    ROLE_ADMIN    = "admin"
    ROLE_OBSERVER = "observer"
    ROLE_AGENT    = "agent"
    ROLE_MODEL    = "model"
    ROLE_READONLY = "readonly"

    def __init__(self, access_control: Optional[AccessControl] = None) -> None:
        self._ac = access_control or AccessControl()
        self._bootstrap_system_roles()

    def _bootstrap_system_roles(self) -> None:
        """Create default system roles if not already present."""
        defaults = [
            RolePolicy.create("admin",    frozenset({"*"}),                   is_system_role=True,
                              description="Full platform access"),
            RolePolicy.create("agent",    frozenset({"model.invoke", "data.read", "memory.write"}),
                              is_system_role=True,
                              description="Standard AI agent capabilities"),
            RolePolicy.create("model",    frozenset({"model.invoke", "data.read"}),
                              is_system_role=True,
                              description="AI model capabilities"),
            RolePolicy.create("observer", frozenset({"data.read", "audit.read"}),
                              is_system_role=True,
                              description="Read-only observation"),
            RolePolicy.create("readonly", frozenset({"data.read"}),
                              is_system_role=True,
                              description="Minimum read-only access"),
        ]
        for role in defaults:
            existing = [r for r in self._ac.list_roles() if r.name == role.name]
            if not existing:
                self._ac.add_role(role)

    # ── role management ───────────────────────────────────────────────────────

    def create_role(self, role: RolePolicy) -> None:
        existing = [r for r in self._ac.list_roles() if r.name == role.name]
        if existing:
            raise AIRoleAlreadyExistsError(f"Role {role.name!r} already exists")
        self._ac.add_role(role)

    def delete_role(self, role_id: str) -> None:
        role = self._ac.get_role(role_id)
        if role is None:
            raise AIRoleNotFoundError(f"Role {role_id!r} not found")
        self._ac.remove_role(role_id)

    def list_roles(self) -> List[RolePolicy]:
        return self._ac.list_roles()

    def get_role_by_name(self, name: str) -> Optional[RolePolicy]:
        for r in self._ac.list_roles():
            if r.name == name:
                return r
        return None

    # ── assignments ───────────────────────────────────────────────────────────

    def assign_role(self, principal_id: str, role_name: str) -> None:
        role = self.get_role_by_name(role_name)
        if role is None:
            raise AIRoleNotFoundError(f"Role {role_name!r} not found")
        self._ac.assign_role(principal_id, role.role_id)

    def revoke_role(self, principal_id: str, role_name: str) -> None:
        role = self.get_role_by_name(role_name)
        if role is None:
            raise AIRoleNotFoundError(f"Role {role_name!r} not found")
        self._ac.revoke_role(principal_id, role.role_id)

    # ── authorization ─────────────────────────────────────────────────────────

    def authorize(self, principal_id: str, capability: str) -> None:
        """
        Authorize ``principal_id`` for ``capability``.

        :raises AIPermissionDeniedError: if not authorized.
        """
        if not self._ac.is_authorized(principal_id, capability):
            raise AIPermissionDeniedError(
                f"Principal {principal_id!r} not authorized for capability {capability!r}"
            )

    def is_authorized(self, principal_id: str, capability: str) -> bool:
        return self._ac.is_authorized(principal_id, capability)

    # ── restrictions ──────────────────────────────────────────────────────────

    def add_restriction(self, restriction: CapabilityRestriction) -> None:
        self._ac.add_restriction(restriction)

    def get_restriction(self, principal_id: str) -> Optional[CapabilityRestriction]:
        return self._ac.get_restriction(principal_id)

    @property
    def access_control(self) -> AccessControl:
        return self._ac
