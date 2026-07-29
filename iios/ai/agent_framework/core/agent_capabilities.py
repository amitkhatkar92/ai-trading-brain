"""
agent_capabilities.py -- iios.ai.agent_framework.core
=======================================================
:class:`CapabilityType` — extensible enum of all supported agent capabilities.
:class:`AgentCapability` — single capability declaration.
:class:`AgentCapabilities` — immutable set of capabilities for one agent.

A5 AI Agent Framework — Phase 3, Module 5
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import Enum
from typing import FrozenSet, List


class CapabilityType(str, Enum):
    """
    Enumeration of enterprise capability types.

    Extend by adding new members — existing members must never be renamed
    because they are persisted in agent specs and event payloads.
    """

    ANALYSIS         = "analysis"
    PLANNING         = "planning"
    REASONING        = "reasoning"
    CLASSIFICATION   = "classification"
    RESEARCH         = "research"
    RECOMMENDATION   = "recommendation"
    SUMMARIZATION    = "summarization"
    PREDICTION       = "prediction"
    CUSTOM           = "custom"


@dataclass(frozen=True)
class AgentCapability:
    """
    A single, immutable capability declaration.

    Use :meth:`create` to generate a capability with a random ID.
    The ``capability_type`` field acts as the primary semantic classifier;
    ``name`` provides a human-readable label for the dashboard.
    """

    capability_id:   str
    capability_type: CapabilityType
    name:            str
    description:     str
    version:         str

    @classmethod
    def create(
        cls,
        capability_type: CapabilityType,
        name:            str,
        description:     str = "",
        version:         str = "1.0.0",
    ) -> "AgentCapability":
        return cls(
            capability_id   = str(uuid.uuid4()),
            capability_type = capability_type,
            name            = name,
            description     = description,
            version         = version,
        )


@dataclass(frozen=True)
class AgentCapabilities:
    """
    Immutable set of :class:`AgentCapability` objects owned by one agent.

    Queried by the framework to route tasks, enforce policies, and
    populate the registry's capability index.
    """

    capabilities: FrozenSet[AgentCapability]

    @classmethod
    def create(cls, *capabilities: AgentCapability) -> "AgentCapabilities":
        """Build from zero or more :class:`AgentCapability` instances."""
        return cls(capabilities=frozenset(capabilities))

    @classmethod
    def empty(cls) -> "AgentCapabilities":
        """Return an empty capability set."""
        return cls(capabilities=frozenset())

    def has_capability(self, capability_type: CapabilityType) -> bool:
        """Return True if at least one capability of this type is present."""
        return any(c.capability_type == capability_type for c in self.capabilities)

    def by_type(self, capability_type: CapabilityType) -> List[AgentCapability]:
        """Return all capabilities matching ``capability_type``."""
        return [c for c in self.capabilities if c.capability_type == capability_type]

    def add(self, capability: AgentCapability) -> "AgentCapabilities":
        """Return a new set with ``capability`` added."""
        return AgentCapabilities(capabilities=self.capabilities | {capability})

    def capability_types(self) -> FrozenSet[CapabilityType]:
        """Return the set of unique :class:`CapabilityType` values present."""
        return frozenset(c.capability_type for c in self.capabilities)

    def count(self) -> int:
        return len(self.capabilities)
