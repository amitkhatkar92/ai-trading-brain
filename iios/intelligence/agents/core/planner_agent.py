"""
iios/intelligence/agents/core/planner_agent.py
===============================================
PlannerAgent — generic planning agent stub.

Override execute() to implement goal decomposition, task planning,
multi-step scheduling, or constraint satisfaction.
"""

from __future__ import annotations

from ..agent_constants import AgentType, SupervisionPolicy
from .base_agent import AgentRequest, AgentResponse, BaseAgent

__all__ = ["PlannerAgent"]


class PlannerAgent(BaseAgent):
    """
    Framework agent for planning tasks.

    Subclass and override execute() to implement:
    - Goal decomposition
    - Multi-step execution plans
    - Resource allocation plans
    - Schedule optimization
    """

    def __init__(
        self,
        agent_id: str,
        name:     str         = "Planner Agent",
        config:   dict | None = None,
        **kwargs,
    ) -> None:
        super().__init__(
            agent_id           = agent_id,
            agent_type         = AgentType.PLANNING,
            name               = name,
            config             = config,
            supervision_policy = kwargs.pop(
                "supervision_policy", SupervisionPolicy.RESTART_ON_FAILURE
            ),
            **kwargs,
        )

    def execute(self, request: AgentRequest) -> AgentResponse:
        """
        Default implementation — returns a trivial single-step plan.

        Override with real planning logic.
        """
        goal = request.payload.get("goal", "unknown")
        return AgentResponse(
            request_id = request.request_id,
            agent_id   = self.agent_id,
            success    = True,
            result     = {
                "goal":  goal,
                "steps": [{"step": 1, "action": "execute_directly", "goal": goal}],
            },
            confidence = 0.7,
            reasoning  = "Default single-step plan",
        )
