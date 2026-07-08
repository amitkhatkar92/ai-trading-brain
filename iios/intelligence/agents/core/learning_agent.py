"""
iios/intelligence/agents/core/learning_agent.py
================================================
LearningAgent — generic learning agent stub.

Override execute() to implement online learning, reinforcement
learning, or experience-based adaptation.
"""

from __future__ import annotations

from ..agent_constants import AgentType, SupervisionPolicy
from .base_agent import AgentRequest, AgentResponse, BaseAgent

__all__ = ["LearningAgent"]


class LearningAgent(BaseAgent):
    """
    Framework agent for learning/adaptation tasks.

    Subclass and override execute() to implement:
    - Online model updates
    - Reinforcement learning policy updates
    - Strategy performance feedback loops
    - Parameter adaptation
    """

    def __init__(
        self,
        agent_id: str,
        name:     str         = "Learning Agent",
        config:   dict | None = None,
        **kwargs,
    ) -> None:
        super().__init__(
            agent_id           = agent_id,
            agent_type         = AgentType.LEARNING,
            name               = name,
            config             = config,
            supervision_policy = kwargs.pop(
                "supervision_policy", SupervisionPolicy.RESTART_ON_FAILURE
            ),
            **kwargs,
        )
        self._experience_count = 0

    def execute(self, request: AgentRequest) -> AgentResponse:
        """
        Default implementation — increments experience counter.

        Override with real learning logic.
        """
        self._experience_count += 1
        return AgentResponse(
            request_id = request.request_id,
            agent_id   = self.agent_id,
            success    = True,
            result     = {
                "learned":           True,
                "experience_count":  self._experience_count,
            },
            confidence = 0.6,
            reasoning  = "Default pass-through learning",
        )
