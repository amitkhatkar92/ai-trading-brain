"""
execution_policy.py -- iios.ai.agent_framework.policy
=======================================================
:class:`ExecutionPolicy`        — base protocol for task execution rules.
:class:`DefaultExecutionPolicy` — permissive default (always allows).
:class:`ActiveOnlyPolicy`       — reject tasks if agent is not active.
:class:`RateLimitPolicy`        — reject tasks above a per-second threshold.

A5 AI Agent Framework — Phase 3, Module 5
"""
from __future__ import annotations

import threading
import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from ..exceptions import AIAgentNotRunningError, AIAgentPolicyViolationError

if TYPE_CHECKING:
    from ..base.base_agent   import BaseAIAgent
    from ..engine.agent_task import AgentTask


class ExecutionPolicy(ABC):
    """
    Abstract execution policy.

    ``evaluate()`` is called by the engine before dispatching a task.
    Raise :class:`AIAgentPolicyViolationError` (or a subclass) to block.
    """

    @abstractmethod
    def evaluate(self, agent: "BaseAIAgent", task: "AgentTask") -> None:
        """Raise if the task must not be executed."""


class DefaultExecutionPolicy(ExecutionPolicy):
    """Permissive policy — always allows execution."""

    def evaluate(self, agent: "BaseAIAgent", task: "AgentTask") -> None:
        pass  # no restrictions


class ActiveOnlyPolicy(ExecutionPolicy):
    """Reject tasks if the target agent is not active."""

    def evaluate(self, agent: "BaseAIAgent", task: "AgentTask") -> None:
        if not agent.is_active:
            raise AIAgentNotRunningError(agent.agent_id)


class RateLimitPolicy(ExecutionPolicy):
    """
    Reject tasks when the agent is handling more than *max_per_second*
    tasks in the current second.

    Uses a simple token-bucket approach.
    """

    def __init__(self, max_per_second: int = 10) -> None:
        self._max     = max_per_second
        self._count   = 0
        self._window  = 0.0
        self._lock    = threading.Lock()

    def evaluate(self, agent: "BaseAIAgent", task: "AgentTask") -> None:
        now = time.time()
        with self._lock:
            window = int(now)
            if window != int(self._window):
                self._count  = 0
                self._window = float(window)
            self._count += 1
            if self._count > self._max:
                raise AIAgentPolicyViolationError(
                    f"Rate limit exceeded for agent {agent.agent_id!r} "
                    f"({self._count}/{self._max} per second)"
                )
