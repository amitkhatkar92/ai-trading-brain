"""
iios/intelligence/agents/agent_factory.py
==========================================
AgentFactory — creates agents from class references or registered templates.

Provides a single creation point so that:
  - Agent IDs are validated
  - Agents are immediately registered
  - Default configs can be applied
  - The registry is always up-to-date

Singleton: get_agent_factory() / reset_agent_factory()
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Optional, Type

from .agent_constants import AgentType, SupervisionPolicy
from .agent_exceptions import AgentAlreadyRegisteredError
from .core.base_agent import BaseAgent
from .agent_registry import AgentRegistry, get_agent_registry

log = logging.getLogger(__name__)

__all__ = [
    "AgentFactory",
    "get_agent_factory",
    "reset_agent_factory",
]


class AgentFactory:
    """
    Creates and registers AI agents.

    Usage
    -----
    factory = get_agent_factory()

    # Create directly from a class
    agent = factory.create(
        cls        = ReasoningAgent,
        agent_id   = "reasoning.main",
        name       = "Main Reasoner",
        config     = {"depth": 5},
        initialize = True,
    )

    # Create from a registered template
    factory.register_template("my_template", ReasoningAgent, {"depth": 3})
    agent = factory.create_from_template("my_template", "reasoning.inst2")
    """

    def __init__(self, registry: Optional[AgentRegistry] = None) -> None:
        self._registry  = registry or get_agent_registry()
        self._lock      = threading.RLock()
        self._templates: dict[str, tuple[Type[BaseAgent], dict]] = {}
        self._created   = 0

    def create(
        self,
        cls:              Type[BaseAgent],
        agent_id:         str,
        name:             str                = "",
        config:           Optional[dict]     = None,
        tags:             list[str] | None   = None,
        metadata:         Optional[dict]     = None,
        supervision_policy: SupervisionPolicy = SupervisionPolicy.RESTART_ON_FAILURE,
        initialize:       bool               = True,
        overwrite:        bool               = False,
        registered_by:    str                = "factory",
    ) -> BaseAgent:
        """
        Instantiate cls, register it, optionally call initialize().

        Returns the newly created agent.
        """
        agent = cls(
            agent_id           = agent_id,
            name               = name or cls.__name__,
            config             = config,
            supervision_policy = supervision_policy,
            tags               = tags or [],
            metadata           = metadata or {},
        )
        self._registry.register(
            agent,
            overwrite     = overwrite,
            registered_by = registered_by,
            tags          = tags or [],
        )
        if initialize:
            agent.initialize()
        with self._lock:
            self._created += 1
        log.debug("Created agent %r (%s)", agent_id, cls.__name__)
        return agent

    def register_template(
        self,
        template_name: str,
        cls:           Type[BaseAgent],
        default_config: dict | None = None,
    ) -> None:
        """Register a reusable agent template."""
        with self._lock:
            self._templates[template_name] = (cls, default_config or {})

    def create_from_template(
        self,
        template_name: str,
        agent_id:      str,
        name:          str                = "",
        config:        Optional[dict]     = None,
        initialize:    bool               = True,
        overwrite:     bool               = False,
    ) -> BaseAgent:
        """Create an agent from a registered template."""
        with self._lock:
            entry = self._templates.get(template_name)
        if entry is None:
            raise KeyError(f"Unknown template: {template_name!r}")
        cls, default_config = entry
        merged_config = {**default_config, **(config or {})}
        return self.create(
            cls        = cls,
            agent_id   = agent_id,
            name       = name or template_name,
            config     = merged_config,
            initialize = initialize,
            overwrite  = overwrite,
        )

    def stats(self) -> dict:
        with self._lock:
            return {
                "created":   self._created,
                "templates": list(self._templates.keys()),
            }


# ── Singleton ─────────────────────────────────────────────────────────────────

_factory_lock = threading.Lock()
_factory_inst: Optional[AgentFactory] = None


def get_agent_factory() -> AgentFactory:
    global _factory_inst
    if _factory_inst is None:
        with _factory_lock:
            if _factory_inst is None:
                _factory_inst = AgentFactory()
    return _factory_inst


def reset_agent_factory() -> None:
    global _factory_inst
    with _factory_lock:
        _factory_inst = None
