"""
iios/intelligence/agents/core/reasoning_agent.py
=================================================
ReasoningAgent — generic reasoning agent stub.

Override execute() to plug in a real reasoning engine
(e.g. chain-of-thought, tree-of-thought, symbolic reasoning).
"""

from __future__ import annotations

from ..agent_constants import AgentType, SupervisionPolicy
from .base_agent import AgentRequest, AgentResponse, BaseAgent

__all__ = ["ReasoningAgent"]


class ReasoningAgent(BaseAgent):
    """
    Framework agent for logical reasoning tasks.

    Subclass and override execute() to implement specific reasoning
    strategies (forward chaining, backward chaining, abductive, etc.).
    """

    def __init__(
        self,
        agent_id: str,
        name:     str             = "Reasoning Agent",
        config:   dict | None     = None,
        **kwargs,
    ) -> None:
        super().__init__(
            agent_id           = agent_id,
            agent_type         = AgentType.REASONING,
            name               = name,
            config             = config,
            supervision_policy = kwargs.pop(
                "supervision_policy", SupervisionPolicy.RESTART_ON_FAILURE
            ),
            **kwargs,
        )

    def execute(self, request: AgentRequest) -> AgentResponse:
        """
        Default implementation — applies no reasoning.

        Override to integrate a real reasoning engine.
        """
        return AgentResponse(
            request_id = request.request_id,
            agent_id   = self.agent_id,
            success    = True,
            result     = {"reasoned": True, "payload": request.payload},
            confidence = 0.7,
            reasoning  = "Default pass-through reasoning",
        )
