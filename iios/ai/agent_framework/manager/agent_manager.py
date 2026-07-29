"""
agent_manager.py -- iios.ai.agent_framework.manager
=====================================================
:class:`AgentManager` — high-level agent lifecycle management.

The manager sits above the registry and provides a single, stable API for:
* Creating, registering, starting, suspending, and stopping agents.
* Querying health, metrics, and discovery by capability.
* Publishing lifecycle events to the shared :class:`AgentEventBus`.

A5 AI Agent Framework — Phase 3, Module 5
"""
from __future__ import annotations

from typing import List

from ..base.base_agent  import BaseAIAgent
from ..core.agent_capabilities import CapabilityType
from ..core.agent_health       import AgentHealth
from ..core.agent_metrics      import AgentMetrics
from ..core.agent_spec         import AgentSpec
from ..events.agent_event_bus  import AgentEventBus
from ..events.agent_events     import (
    AgentRegisteredEvent,
    AgentStartedEvent,
    AgentStoppedEvent,
    AgentSuspendedEvent,
    AgentResumedEvent,
)
from ..exceptions              import AIAgentNotFoundError
from ..registry.agent_descriptor import AgentDescriptor
from ..registry.agent_factory    import AgentFactory
from ..registry.agent_registry   import AgentRegistry


class AgentManager:
    """
    High-level lifecycle manager for the agent framework.

    Usage::

        mgr = AgentManager(registry, factory, event_bus)
        agent = mgr.create_and_register(spec)
        mgr.start_agent(agent.agent_id)
        mgr.stop_agent(agent.agent_id)
    """

    def __init__(
        self,
        registry:  AgentRegistry,
        factory:   AgentFactory,
        event_bus: AgentEventBus,
    ) -> None:
        self._registry  = registry
        self._factory   = factory
        self._event_bus = event_bus

    # ── Registration ──────────────────────────────────────────────────────────

    def register_agent(self, agent: BaseAIAgent) -> AgentDescriptor:
        """
        Register an already-constructed *agent*.

        Publishes :class:`AgentRegisteredEvent`.
        Returns the agent's :class:`AgentDescriptor`.
        """
        self._registry.register(agent)
        self._event_bus.publish(
            AgentRegisteredEvent.create(
                agent_id   = agent.agent_id,
                agent_name = agent.agent_name,
                agent_type = agent.agent_type,
            )
        )
        return AgentDescriptor.from_agent(agent)

    def create_agent(self, spec: AgentSpec) -> BaseAIAgent:
        """
        Create an agent from *spec* using the factory.

        Does NOT register the agent — call :meth:`register_agent` afterwards.
        """
        return self._factory.create(spec)

    def create_and_register(self, spec: AgentSpec) -> BaseAIAgent:
        """Create via factory, then register.  Convenience wrapper."""
        agent = self._factory.create(spec)
        self.register_agent(agent)
        return agent

    # ── Lifecycle operations ──────────────────────────────────────────────────

    def start_agent(self, agent_id: str) -> None:
        """Activate the agent.  Publishes :class:`AgentStartedEvent`."""
        agent = self._registry.get(agent_id)
        agent.activate()
        self._event_bus.publish(AgentStartedEvent.create(agent_id))

    def stop_agent(self, agent_id: str) -> None:
        """Shut down the agent permanently.  Publishes :class:`AgentStoppedEvent`."""
        agent = self._registry.get(agent_id)
        agent.shutdown()
        self._event_bus.publish(AgentStoppedEvent.create(agent_id))

    def suspend_agent(self, agent_id: str) -> None:
        """Suspend the agent temporarily.  Publishes :class:`AgentSuspendedEvent`."""
        agent = self._registry.get(agent_id)
        agent.suspend()
        self._event_bus.publish(AgentSuspendedEvent.create(agent_id))

    def resume_agent(self, agent_id: str) -> None:
        """Resume a suspended agent.  Publishes :class:`AgentResumedEvent`."""
        agent = self._registry.get(agent_id)
        agent.resume()
        self._event_bus.publish(AgentResumedEvent.create(agent_id))

    # ── Discovery ─────────────────────────────────────────────────────────────

    def find_agent(self, agent_id: str) -> BaseAIAgent:
        """Return the live agent by ID.  Raises if not found."""
        return self._registry.get(agent_id)

    def find_agents_by_capability(
        self,
        capability_type: CapabilityType,
    ) -> List[AgentDescriptor]:
        """Return descriptors for all agents that have *capability_type*."""
        return [
            AgentDescriptor.from_agent(a)
            for a in self._registry.find_by_capability(capability_type)
        ]

    def list_agents(self) -> List[AgentDescriptor]:
        """Return descriptors for all registered agents."""
        return self._registry.list_all()

    # ── Health / metrics ──────────────────────────────────────────────────────

    def get_agent_health(self, agent_id: str) -> AgentHealth:
        """Return the current health of the agent."""
        return self._registry.get(agent_id).get_health()

    def get_agent_metrics(self, agent_id: str) -> AgentMetrics:
        """Return the current metrics of the agent."""
        return self._registry.get(agent_id).metrics
