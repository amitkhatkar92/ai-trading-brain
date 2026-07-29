"""
agent_permissions.py -- iios.ai.agent_framework.core
=====================================================
:class:`PermissionLevel` — ordered permission levels.
:class:`AgentPermission`  — single immutable permission grant.
:class:`AgentPermissions` — immutable permission set for one agent.

A5 AI Agent Framework — Phase 3, Module 5
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import FrozenSet

from ..exceptions import AIPermissionDeniedError


# Ordered from lowest (0) to highest (4)
_LEVEL_ORDER = {
    "none":    0,
    "read":    1,
    "write":   2,
    "execute": 3,
    "admin":   4,
}


class PermissionLevel(str, Enum):
    """
    Ordered permission levels used for resource access control.

    Higher levels implicitly include all lower ones when tested via
    :meth:`AgentPermissions.has_permission`.
    """

    NONE    = "none"
    READ    = "read"
    WRITE   = "write"
    EXECUTE = "execute"
    ADMIN   = "admin"

    def rank(self) -> int:
        """Numeric rank — higher = more permissive."""
        return _LEVEL_ORDER[self.value]

    def satisfies(self, required: "PermissionLevel") -> bool:
        """Return True if this level is at least as permissive as *required*."""
        return self.rank() >= required.rank()


@dataclass(frozen=True)
class AgentPermission:
    """
    A single, immutable permission grant for one resource.

    ``resource`` is a logical name such as ``"market_data"``,
    ``"portfolio"``, ``"risk"`` or ``"*"`` (all resources).
    """

    permission_id: str
    resource:      str
    level:         PermissionLevel
    granted_at:    float
    granted_by:    str

    @classmethod
    def create(
        cls,
        resource:   str,
        level:      PermissionLevel,
        granted_by: str = "system",
    ) -> "AgentPermission":
        return cls(
            permission_id = str(uuid.uuid4()),
            resource      = resource,
            level         = level,
            granted_at    = time.time(),
            granted_by    = granted_by,
        )


@dataclass(frozen=True)
class AgentPermissions:
    """
    Immutable permission set for one agent.

    All mutation returns a *new* instance.  Thread-safe for reads.
    """

    permissions: FrozenSet[AgentPermission]

    @classmethod
    def create(cls, *permissions: AgentPermission) -> "AgentPermissions":
        """Build from zero or more :class:`AgentPermission` instances."""
        return cls(permissions=frozenset(permissions))

    @classmethod
    def empty(cls) -> "AgentPermissions":
        """Return an empty (no access) permission set."""
        return cls(permissions=frozenset())

    def has_permission(self, resource: str, required_level: PermissionLevel) -> bool:
        """
        Return True if the agent holds at least *required_level* on *resource*.

        Checks ``resource`` first; if not found checks wildcard ``"*"``.
        """
        for p in self.permissions:
            if p.resource in (resource, "*"):
                if p.level.satisfies(required_level):
                    return True
        return False

    def assert_permission(self, resource: str, required_level: PermissionLevel) -> None:
        """Raise :class:`AIPermissionDeniedError` if permission is not held."""
        if not self.has_permission(resource, required_level):
            raise AIPermissionDeniedError(resource=resource, required=required_level.value)

    def grant(self, permission: AgentPermission) -> "AgentPermissions":
        """Return a new set with *permission* added."""
        return AgentPermissions(permissions=self.permissions | {permission})

    def revoke(self, resource: str) -> "AgentPermissions":
        """Return a new set with all permissions for *resource* removed."""
        return AgentPermissions(
            permissions=frozenset(p for p in self.permissions if p.resource != resource)
        )

    def count(self) -> int:
        return len(self.permissions)
