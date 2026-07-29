"""
agent_registry.py -- iios.ai.agent_framework.registry
=======================================================
:class:`AgentRegistry` — thread-safe in-memory registry for all agents.

Supports:
* Register / unregister agents by ID.
* Lookup by ID, name, type, and capability.
* Listing all agents as :class:`AgentDescriptor` objects.

A5 AI Agent Framework — Phase 3, Module 5
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from ..base.base_agent           import BaseAIAgent
from ..core.agent_capabilities   import CapabilityType
from ..exceptions                import (
    AIAgentAlreadyExistsError,
    AIAgentNotFoundError,
)
from .agent_descriptor           import AgentDescriptor


class AgentRegistry:
    """
    Thread-safe in-memory agent registry.

    All write operations acquire a reentrant lock.  ``get()`` and read
    operations do likewise to guarantee consistency.
    """

    def __init__(self) -> None:
        self._agents: Dict[str, BaseAIAgent] = {}
        self._lock:   threading.RLock        = threading.RLock()

    # ── Write operations ──────────────────────────────────────────────────────

    def register(self, agent: BaseAIAgent) -> None:
        """
        Register *agent*.

        Raises :class:`AIAgentAlreadyExistsError` if an agent with the same
        ID is already registered.
        """
        with self._lock:
            if agent.agent_id in self._agents:
                raise AIAgentAlreadyExistsError(agent.agent_id)
            self._agents[agent.agent_id] = agent

    def unregister(self, agent_id: str) -> None:
        """
        Remove the agent with *agent_id*.

        Raises :class:`AIAgentNotFoundError` if not registered.
        """
        with self._lock:
            if agent_id not in self._agents:
                raise AIAgentNotFoundError(agent_id)
            del self._agents[agent_id]

    # ── Read operations ───────────────────────────────────────────────────────

    def get(self, agent_id: str) -> BaseAIAgent:
        """
        Return the agent registered under *agent_id*.

        Raises :class:`AIAgentNotFoundError` if absent.
        """
        with self._lock:
            agent = self._agents.get(agent_id)
        if agent is None:
            raise AIAgentNotFoundError(agent_id)
        return agent

    def find_by_name(self, name: str) -> Optional[BaseAIAgent]:
        """Return the first agent with ``agent_name == name``, or None."""
        with self._lock:
            for agent in self._agents.values():
                if agent.agent_name == name:
                    return agent
        return None

    def find_by_type(self, agent_type: str) -> List[BaseAIAgent]:
        """Return all agents whose ``agent_type`` matches."""
        with self._lock:
            return [a for a in self._agents.values() if a.agent_type == agent_type]

    def find_by_capability(
        self,
        capability_type: CapabilityType,
    ) -> List[BaseAIAgent]:
        """Return all agents that have at least one *capability_type* capability."""
        with self._lock:
            return [
                a for a in self._agents.values()
                if a.spec.capabilities.has_capability(capability_type)
            ]

    def find_active(self) -> List[BaseAIAgent]:
        """Return all currently active agents."""
        with self._lock:
            return [a for a in self._agents.values() if a.is_active]

    def list_all(self) -> List[AgentDescriptor]:
        """Return a snapshot of all agents as :class:`AgentDescriptor` objects."""
        with self._lock:
            return [AgentDescriptor.from_agent(a) for a in self._agents.values()]

    def is_registered(self, agent_id: str) -> bool:
        with self._lock:
            return agent_id in self._agents

    def count(self) -> int:
        with self._lock:
            return len(self._agents)

    def active_count(self) -> int:
        with self._lock:
            return sum(1 for a in self._agents.values() if a.is_active)
