"""
permission_profile.py -- iios.ai.agent_framework.roles
========================================================
:class:`PermissionProfile` — maps a role to its default resource grants.

A5 AI Agent Framework — Phase 3, Module 5
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Dict, FrozenSet, Tuple

from ..core.agent_permissions import PermissionLevel


@dataclass(frozen=True)
class PermissionProfile:
    """
    Declares the default resource-level grants for a role.

    ``grants`` is a frozenset of ``(resource, PermissionLevel)`` pairs.
    """

    profile_id: str
    name:       str
    grants:     FrozenSet[Tuple[str, PermissionLevel]]

    @classmethod
    def create(
        cls,
        name:   str,
        grants: Dict[str, PermissionLevel],
    ) -> "PermissionProfile":
        return cls(
            profile_id = str(uuid.uuid4()),
            name       = name,
            grants     = frozenset(grants.items()),
        )

    @classmethod
    def empty(cls, name: str = "empty") -> "PermissionProfile":
        return cls.create(name, {})

    def grants_as_dict(self) -> Dict[str, PermissionLevel]:
        return dict(self.grants)

    def has_grant(self, resource: str, level: PermissionLevel) -> bool:
        for r, l in self.grants:
            if r == resource and l.satisfies(level):
                return True
        return False
