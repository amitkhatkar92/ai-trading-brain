"""
agent_spec.py -- iios.ai.agent_framework.core
==============================================
:class:`AgentSpec` — the mandatory enterprise specification that every AI
agent must declare.

An :class:`AgentSpec` combines all other core primitives into a single,
immutable, self-describing record.  The framework refuses to register an
agent that lacks a valid spec.

A5 AI Agent Framework — Phase 3, Module 5
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from .agent_capabilities import AgentCapabilities, AgentCapability
from .agent_config       import AgentConfiguration
from .agent_health       import AgentHealth
from .agent_identity     import AgentIdentity, AgentMetadata
from .agent_metrics      import AgentMetrics
from .agent_permissions  import AgentPermissions


@dataclass(frozen=True)
class AgentSpec:
    """
    The complete, immutable specification of one AI agent.

    Fields
    ------
    metadata:     :class:`AgentMetadata`      — identity + author + tags
    capabilities: :class:`AgentCapabilities`  — what this agent can do
    configuration: :class:`AgentConfiguration` — runtime settings
    permissions:  :class:`AgentPermissions`   — resource access grants

    This is the **mandatory enterprise standard** — every future specialist
    agent must declare an :class:`AgentSpec` before it can be registered.
    """

    metadata:      AgentMetadata
    capabilities:  AgentCapabilities
    configuration: AgentConfiguration
    permissions:   AgentPermissions

    # ── Convenience properties ────────────────────────────────────────────────

    @property
    def agent_id(self) -> str:
        return self.metadata.identity.agent_id

    @property
    def agent_name(self) -> str:
        return self.metadata.identity.agent_name

    @property
    def agent_type(self) -> str:
        return self.metadata.identity.agent_type

    @property
    def version(self) -> str:
        return self.metadata.identity.version

    @property
    def qualified_name(self) -> str:
        return self.metadata.identity.qualified_name

    # ── Factory ───────────────────────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        identity:      AgentIdentity,
        description:   str                      = "",
        author:        str                      = "system",
        tags:          Iterable[str]            = (),
        capabilities:  Optional[AgentCapabilities]  = None,
        configuration: Optional[AgentConfiguration] = None,
        permissions:   Optional[AgentPermissions]   = None,
    ) -> "AgentSpec":
        """
        Convenience factory.  Defaults to empty capabilities, empty config,
        and empty permissions when the caller omits them.

        Example::

            spec = AgentSpec.create(
                identity      = AgentIdentity.create("MarketAnalyst", "MarketAnalystAgent"),
                description   = "Analyses market conditions.",
                capabilities  = AgentCapabilities.create(
                    AgentCapability.create(CapabilityType.ANALYSIS, "Market Analysis"),
                ),
            )
        """
        metadata = AgentMetadata.create(identity, description, author, tags)
        caps     = capabilities  or AgentCapabilities.empty()
        config   = configuration or AgentConfiguration.empty(identity.agent_id)
        perms    = permissions   or AgentPermissions.empty()
        return cls(
            metadata      = metadata,
            capabilities  = caps,
            configuration = config,
            permissions   = perms,
        )

    # ── Derived helpers ───────────────────────────────────────────────────────

    def initial_health(self) -> AgentHealth:
        """Return a HEALTHY snapshot suitable for a freshly created agent."""
        return AgentHealth.healthy(self.agent_id, "Initialized")

    def initial_metrics(self) -> AgentMetrics:
        """Return zeroed metrics for a freshly created agent."""
        return AgentMetrics.empty(self.agent_id)
