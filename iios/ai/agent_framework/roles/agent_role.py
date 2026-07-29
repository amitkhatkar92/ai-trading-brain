"""
agent_role.py -- iios.ai.agent_framework.roles
===============================================
:class:`RoleType`  — enumeration of enterprise agent roles.
:class:`AgentRole` — immutable role definition.

A5 AI Agent Framework — Phase 3, Module 5
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import Enum
from typing import FrozenSet

from ..core.agent_capabilities import CapabilityType


class RoleType(str, Enum):
    """Enterprise agent role types.  Values are persisted — do not rename."""

    ANALYST    = "analyst"
    PLANNER    = "planner"
    RESEARCHER = "researcher"
    ADVISOR    = "advisor"
    MONITOR    = "monitor"
    AUDITOR    = "auditor"
    LEARNER    = "learner"
    CUSTOM     = "custom"


@dataclass(frozen=True)
class AgentRole:
    """
    Immutable definition of an enterprise agent role.

    ``default_capabilities`` specifies the :class:`CapabilityType` values
    that agents in this role are expected to have.
    ``default_resources`` specifies the resource names granted at EXECUTE
    level by default (used by :class:`PermissionProfile`).
    """

    role_id:              str
    role_type:            RoleType
    name:                 str
    description:          str
    default_capabilities: FrozenSet[CapabilityType]
    default_resources:    FrozenSet[str]

    @classmethod
    def create(
        cls,
        role_type:            RoleType,
        name:                 str,
        description:          str                       = "",
        default_capabilities: FrozenSet[CapabilityType] = frozenset(),
        default_resources:    FrozenSet[str]            = frozenset(),
    ) -> "AgentRole":
        return cls(
            role_id              = str(uuid.uuid4()),
            role_type            = role_type,
            name                 = name,
            description          = description,
            default_capabilities = frozenset(default_capabilities),
            default_resources    = frozenset(default_resources),
        )
