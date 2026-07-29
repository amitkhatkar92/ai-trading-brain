"""
capability_policy.py -- iios.ai.agent_framework.policy
========================================================
:class:`CapabilityPolicy`        — base protocol.
:class:`DefaultCapabilityPolicy` — allow any task type (no enforcement).
:class:`StrictCapabilityPolicy`  — require the agent to have a matching
                                   :class:`CapabilityType` for each task type.

A5 AI Agent Framework — Phase 3, Module 5
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Dict

from ..core.agent_capabilities import CapabilityType
from ..exceptions               import AICapabilityNotPermittedError

if TYPE_CHECKING:
    from ..base.base_agent   import BaseAIAgent
    from ..engine.agent_task import AgentTask


class CapabilityPolicy(ABC):
    """Abstract capability policy evaluated before task dispatch."""

    @abstractmethod
    def check(self, agent: "BaseAIAgent", task: "AgentTask") -> None:
        """Raise :class:`AICapabilityNotPermittedError` if not permitted."""


class DefaultCapabilityPolicy(CapabilityPolicy):
    """Permissive policy — any agent can handle any task type."""

    def check(self, agent: "BaseAIAgent", task: "AgentTask") -> None:
        pass


class StrictCapabilityPolicy(CapabilityPolicy):
    """
    Enforce that the agent holds a declared capability for the task type.

    ``task_type_map`` maps task type strings to required
    :class:`CapabilityType` values.  Task types not in the map pass through.
    """

    def __init__(
        self,
        task_type_map: Dict[str, CapabilityType],
    ) -> None:
        self._map = task_type_map

    def check(self, agent: "BaseAIAgent", task: "AgentTask") -> None:
        required = self._map.get(task.task_type)
        if required is None:
            return  # unmapped task types are allowed
        if not agent.spec.capabilities.has_capability(required):
            raise AICapabilityNotPermittedError(
                agent_id   = agent.agent_id,
                capability = required.value,
            )
