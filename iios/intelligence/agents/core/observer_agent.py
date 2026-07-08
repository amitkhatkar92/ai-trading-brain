"""
iios/intelligence/agents/core/observer_agent.py
================================================
ObserverAgent — generic observation/monitoring agent stub.

Override execute() to implement market observation, anomaly detection,
event detection, or data aggregation logic.
"""

from __future__ import annotations

from ..agent_constants import AgentType, SupervisionPolicy
from .base_agent import AgentRequest, AgentResponse, BaseAgent

__all__ = ["ObserverAgent"]


class ObserverAgent(BaseAgent):
    """
    Framework agent for observation and monitoring tasks.

    Subclass and override execute() to implement:
    - Market data observation
    - Anomaly detection
    - Event detection and notification
    - State aggregation
    """

    def __init__(
        self,
        agent_id: str,
        name:     str         = "Observer Agent",
        config:   dict | None = None,
        **kwargs,
    ) -> None:
        super().__init__(
            agent_id           = agent_id,
            agent_type         = AgentType.OBSERVATION,
            name               = name,
            config             = config,
            supervision_policy = kwargs.pop(
                "supervision_policy", SupervisionPolicy.RESTART_ALWAYS
            ),
            **kwargs,
        )
        self._observation_count = 0

    def execute(self, request: AgentRequest) -> AgentResponse:
        """
        Default implementation — counts observations.

        Override with real observation/detection logic.
        """
        self._observation_count += 1
        return AgentResponse(
            request_id = request.request_id,
            agent_id   = self.agent_id,
            success    = True,
            result     = {
                "observed":           True,
                "observation_count":  self._observation_count,
                "data":               request.payload,
            },
            confidence = 0.95,
            reasoning  = "Default pass-through observation",
        )
