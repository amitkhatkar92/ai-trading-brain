"""
iios/intelligence/agents/core/decision_agent.py
================================================
DecisionAgent — generic decision agent stub.

Override execute() to implement decision-making logic
(rule-based, ML, RL, Bayesian, etc.).
"""

from __future__ import annotations

from ..agent_constants import AgentType, SupervisionPolicy
from .base_agent import AgentRequest, AgentResponse, BaseAgent

__all__ = ["DecisionAgent"]


class DecisionAgent(BaseAgent):
    """
    Framework agent for decision tasks.

    Subclass and override execute() to implement:
    - Trade entry/exit decisions
    - Position-sizing decisions
    - Risk approval / rejection
    - Strategy selection
    """

    def __init__(
        self,
        agent_id: str,
        name:     str         = "Decision Agent",
        config:   dict | None = None,
        **kwargs,
    ) -> None:
        super().__init__(
            agent_id           = agent_id,
            agent_type         = AgentType.DECISION,
            name               = name,
            config             = config,
            supervision_policy = kwargs.pop(
                "supervision_policy", SupervisionPolicy.RESTART_ON_FAILURE
            ),
            **kwargs,
        )

    def execute(self, request: AgentRequest) -> AgentResponse:
        """
        Default implementation — defers to payload['decision'] if present.

        Override with real decision logic.
        """
        decision = request.payload.get("decision", "NO_ACTION")
        return AgentResponse(
            request_id = request.request_id,
            agent_id   = self.agent_id,
            success    = True,
            result     = {"decision": decision, "approved": True},
            confidence = 0.5,
            reasoning  = "Default pass-through decision",
        )
