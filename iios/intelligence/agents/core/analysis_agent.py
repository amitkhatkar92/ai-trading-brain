"""
iios/intelligence/agents/core/analysis_agent.py
================================================
AnalysisAgent — generic analysis agent stub.

Override execute() to plug in domain-specific analysis
(technical, fundamental, sentiment, macro, etc.).
"""

from __future__ import annotations

from ..agent_constants import AgentType, SupervisionPolicy
from .base_agent import AgentRequest, AgentResponse, BaseAgent

__all__ = ["AnalysisAgent"]


class AnalysisAgent(BaseAgent):
    """
    Framework agent for analysis tasks.

    Subclass and override execute() to implement specific analysis
    workflows (time-series, cross-sectional, event-driven, etc.).
    """

    def __init__(
        self,
        agent_id: str,
        name:     str         = "Analysis Agent",
        config:   dict | None = None,
        **kwargs,
    ) -> None:
        super().__init__(
            agent_id           = agent_id,
            agent_type         = AgentType.ANALYSIS,
            name               = name,
            config             = config,
            supervision_policy = kwargs.pop(
                "supervision_policy", SupervisionPolicy.RESTART_ON_FAILURE
            ),
            **kwargs,
        )

    def execute(self, request: AgentRequest) -> AgentResponse:
        """
        Default implementation — echoes payload as analysis result.

        Override with real analysis logic.
        """
        return AgentResponse(
            request_id = request.request_id,
            agent_id   = self.agent_id,
            success    = True,
            result     = {"analysis": request.payload, "signals": []},
            confidence = 0.6,
            reasoning  = "Default pass-through analysis",
        )
