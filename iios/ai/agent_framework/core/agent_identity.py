"""
agent_identity.py -- iios.ai.agent_framework.core
===================================================
:class:`AgentIdentity` — immutable identity record for every AI agent.
:class:`AgentMetadata` — full metadata including description, author, tags.

A5 AI Agent Framework — Phase 3, Module 5
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import FrozenSet, Iterable


@dataclass(frozen=True)
class AgentIdentity:
    """
    Immutable, globally-unique identity for an AI agent.

    Every agent has exactly one identity, set at construction and never
    mutated.  ``agent_id`` is a UUID; ``qualified_name`` is the
    canonical dotted identifier used in logs and events.
    """

    agent_id:   str   # UUID string
    agent_name: str   # Human-readable name, e.g. "MarketAnalyst"
    agent_type: str   # Class identifier, e.g. "MarketAnalystAgent"
    namespace:  str   # Reverse-DNS style, e.g. "iios:ai:agents"
    version:    str   # Semantic version string

    @classmethod
    def create(
        cls,
        agent_name: str,
        agent_type: str,
        namespace:  str = "iios:ai:agents",
        version:    str = "1.0.0",
    ) -> "AgentIdentity":
        """Factory — generates a new UUID and sets ``created_at``."""
        return cls(
            agent_id   = str(uuid.uuid4()),
            agent_name = agent_name,
            agent_type = agent_type,
            namespace  = namespace,
            version    = version,
        )

    @property
    def qualified_name(self) -> str:
        """``namespace:agent_name:version`` — use in logs and events."""
        return f"{self.namespace}:{self.agent_name}:{self.version}"


@dataclass(frozen=True)
class AgentMetadata:
    """
    Immutable metadata envelope attached to every agent specification.

    Wraps :class:`AgentIdentity` and adds human-readable fields used by
    the registry, dashboard, and audit tooling.
    """

    identity:    AgentIdentity
    description: str
    author:      str
    created_at:  float
    updated_at:  float
    tags:        FrozenSet[str]

    @classmethod
    def create(
        cls,
        identity:    AgentIdentity,
        description: str             = "",
        author:      str             = "system",
        tags:        Iterable[str]   = (),
    ) -> "AgentMetadata":
        now = time.time()
        return cls(
            identity    = identity,
            description = description,
            author      = author,
            created_at  = now,
            updated_at  = now,
            tags        = frozenset(tags),
        )
