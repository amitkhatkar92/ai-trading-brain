"""
agent_descriptor.py -- iios.ai.agent_framework.registry
=========================================================
:class:`AgentDescriptor` — lightweight, serialisable agent summary used for
discovery, listing, and indexing.

Contains no reference to the live :class:`BaseAIAgent` instance so it can be
safely serialised or transferred across process boundaries.

A5 AI Agent Framework — Phase 3, Module 5
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, FrozenSet

if TYPE_CHECKING:
    from ..base.base_agent import BaseAIAgent


@dataclass(frozen=True)
class AgentDescriptor:
    """
    Lightweight, serialisable descriptor used by the registry index.

    Built from a live agent via :meth:`from_agent`.
    """

    agent_id:             str
    agent_name:           str
    agent_type:           str
    version:              str
    is_active:            bool
    is_shutdown:          bool
    registered_at:        float
    health_status:        str
    capabilities_summary: FrozenSet[str]   # CapabilityType.value strings
    tags:                 FrozenSet[str]
    description:          str

    @classmethod
    def from_agent(cls, agent: "BaseAIAgent") -> "AgentDescriptor":
        """Snapshot the current state of *agent* into a descriptor."""
        spec = agent.spec
        return cls(
            agent_id             = spec.agent_id,
            agent_name           = spec.agent_name,
            agent_type           = spec.agent_type,
            version              = spec.version,
            is_active            = agent.is_active,
            is_shutdown          = agent.is_shutdown,
            registered_at        = time.time(),
            health_status        = agent.health.status.value,
            capabilities_summary = frozenset(
                c.capability_type.value for c in spec.capabilities.capabilities
            ),
            tags                 = spec.metadata.tags,
            description          = spec.metadata.description,
        )
