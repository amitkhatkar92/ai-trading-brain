"""
capability_profile.py -- iios.ai.agent_framework.roles
========================================================
:class:`CapabilityProfile` — maps a role to its required and optional
capability types.

A5 AI Agent Framework — Phase 3, Module 5
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import FrozenSet

from ..core.agent_capabilities import CapabilityType


@dataclass(frozen=True)
class CapabilityProfile:
    """
    Declares which capabilities are required and which are optional for
    a given role or agent configuration.
    """

    profile_id:            str
    name:                  str
    required_capabilities: FrozenSet[CapabilityType]
    optional_capabilities: FrozenSet[CapabilityType]

    @classmethod
    def create(
        cls,
        name:                  str,
        required_capabilities: FrozenSet[CapabilityType] = frozenset(),
        optional_capabilities: FrozenSet[CapabilityType] = frozenset(),
    ) -> "CapabilityProfile":
        return cls(
            profile_id            = str(uuid.uuid4()),
            name                  = name,
            required_capabilities = frozenset(required_capabilities),
            optional_capabilities = frozenset(optional_capabilities),
        )

    def satisfies(self, capabilities: FrozenSet[CapabilityType]) -> bool:
        """Return True if *capabilities* contains all required types."""
        return self.required_capabilities <= capabilities
