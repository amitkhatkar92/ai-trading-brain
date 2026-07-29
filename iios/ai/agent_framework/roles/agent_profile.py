"""
agent_profile.py -- iios.ai.agent_framework.roles
===================================================
:class:`AgentProfile` — binds an agent to a role, a capability profile,
and a permission profile.

A5 AI Agent Framework — Phase 3, Module 5
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass

from .agent_role          import AgentRole
from .capability_profile  import CapabilityProfile
from .permission_profile  import PermissionProfile


@dataclass(frozen=True)
class AgentProfile:
    """
    Immutable enterprise profile combining role, capabilities, and permissions.

    Used by the framework to configure a new agent before registration.
    """

    profile_id:          str
    agent_id:            str
    role:                AgentRole
    capability_profile:  CapabilityProfile
    permission_profile:  PermissionProfile
    created_at:          float

    @classmethod
    def create(
        cls,
        agent_id:           str,
        role:               AgentRole,
        capability_profile: CapabilityProfile,
        permission_profile: PermissionProfile,
    ) -> "AgentProfile":
        return cls(
            profile_id         = str(uuid.uuid4()),
            agent_id           = agent_id,
            role               = role,
            capability_profile = capability_profile,
            permission_profile = permission_profile,
            created_at         = time.time(),
        )
