"""
iios/intelligence/agents/agent_registry.py
==========================================
AgentRegistry — thread-safe registry of all AI agents within IIOS.

Every agent must be registered here before it can be used.
The registry maintains status, provides discovery by type/tag,
and tracks the single canonical instance of each agent.

Singleton: get_agent_registry() / reset_agent_registry()
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Optional

from .agent_constants import AgentType, AgentStatus, MAX_AGENTS
from .agent_exceptions import (
    AgentNotFoundError, AgentAlreadyRegisteredError, AgentUnavailableError,
)
from .core.base_agent import BaseAgent

log = logging.getLogger(__name__)

__all__ = [
    "AgentRegistration",
    "AgentRegistry",
    "get_agent_registry",
    "reset_agent_registry",
]


@dataclass
class AgentRegistration:
    """Metadata record for a registered agent."""
    agent:       BaseAgent
    registered_by: str  = "system"
    tags:          list[str] = field(default_factory=list)

    @property
    def agent_id(self) -> str:
        return self.agent.agent_id

    @property
    def agent_type(self) -> AgentType:
        return self.agent.agent_type

    @property
    def status(self) -> AgentStatus:
        return self.agent.status

    def to_dict(self) -> dict:
        return {
            "agent_id":      self.agent_id,
            "agent_type":    self.agent_type.value,
            "name":          self.agent.name,
            "status":        self.status.value,
            "tags":          list(set(self.tags + self.agent.tags)),
            "registered_by": self.registered_by,
        }


class AgentRegistry:
    """
    Thread-safe registry of all AI agents within IIOS.

    Key operations
    --------------
    register(agent)               — register an agent
    unregister(agent_id)          — remove an agent
    get(agent_id)                 — retrieve by ID
    get_by_type(agent_type)       — list all agents of a type
    get_by_tag(tag)               — list agents with a tag
    get_ready(agent_type)         — list IDLE/RUNNING agents of a type
    best(agent_type)              — single best (highest-priority) ready agent
    """

    def __init__(self) -> None:
        self._lock:  threading.RLock = threading.RLock()
        self._agents: dict[str, AgentRegistration] = {}

    def register(
        self,
        agent:         BaseAgent,
        overwrite:     bool = False,
        registered_by: str  = "system",
        tags:          list[str] | None = None,
    ) -> AgentRegistration:
        with self._lock:
            if len(self._agents) >= MAX_AGENTS and agent.agent_id not in self._agents:
                raise OverflowError(
                    f"Agent registry at capacity ({MAX_AGENTS})"
                )
            if agent.agent_id in self._agents and not overwrite:
                raise AgentAlreadyRegisteredError(agent.agent_id)
            reg = AgentRegistration(
                agent=agent,
                registered_by=registered_by,
                tags=list(tags or []),
            )
            self._agents[agent.agent_id] = reg
            log.debug("Registered agent %r (%s)", agent.agent_id, agent.agent_type.value)
            return reg

    def unregister(self, agent_id: str) -> bool:
        with self._lock:
            return self._agents.pop(agent_id, None) is not None

    def get(self, agent_id: str) -> BaseAgent:
        with self._lock:
            reg = self._agents.get(agent_id)
        if reg is None:
            raise AgentNotFoundError(agent_id)
        return reg.agent

    def get_registration(self, agent_id: str) -> AgentRegistration:
        with self._lock:
            reg = self._agents.get(agent_id)
        if reg is None:
            raise AgentNotFoundError(agent_id)
        return reg

    def has(self, agent_id: str) -> bool:
        with self._lock:
            return agent_id in self._agents

    def get_by_type(self, agent_type: AgentType) -> list[BaseAgent]:
        with self._lock:
            return [
                r.agent for r in self._agents.values()
                if r.agent_type == agent_type
            ]

    def get_ready(self, agent_type: Optional[AgentType] = None) -> list[BaseAgent]:
        with self._lock:
            return [
                r.agent for r in self._agents.values()
                if r.agent.is_ready
                and (agent_type is None or r.agent_type == agent_type)
            ]

    def get_by_tag(self, tag: str) -> list[BaseAgent]:
        with self._lock:
            return [
                r.agent for r in self._agents.values()
                if tag in r.tags or tag in r.agent.tags
            ]

    def all_agents(self) -> list[BaseAgent]:
        with self._lock:
            return [r.agent for r in self._agents.values()]

    def all_registrations(self) -> list[AgentRegistration]:
        with self._lock:
            return list(self._agents.values())

    def best(self, agent_type: AgentType) -> Optional[BaseAgent]:
        """Return the first ready agent of the given type."""
        ready = self.get_ready(agent_type)
        return ready[0] if ready else None

    def count_by_type(self) -> dict[str, int]:
        with self._lock:
            counts: dict[str, int] = {}
            for r in self._agents.values():
                key = r.agent_type.value
                counts[key] = counts.get(key, 0) + 1
            return counts

    def stats(self) -> dict:
        with self._lock:
            total  = len(self._agents)
            active = sum(
                1 for r in self._agents.values()
                if r.status in (AgentStatus.IDLE, AgentStatus.RUNNING)
            )
            return {
                "total":    total,
                "active":   active,
                "by_type":  self.count_by_type(),
                "capacity": MAX_AGENTS,
            }

    def clear(self) -> None:
        with self._lock:
            self._agents.clear()


# ── Singleton ─────────────────────────────────────────────────────────────────

_reg_lock = threading.Lock()
_reg_inst: Optional[AgentRegistry] = None


def get_agent_registry() -> AgentRegistry:
    global _reg_inst
    if _reg_inst is None:
        with _reg_lock:
            if _reg_inst is None:
                _reg_inst = AgentRegistry()
    return _reg_inst


def reset_agent_registry() -> None:
    global _reg_inst
    with _reg_lock:
        _reg_inst = None
