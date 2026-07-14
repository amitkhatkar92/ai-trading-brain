"""iios/investment/strategy/debate/agent_registry.py
Thread-safe registry for debate participants.
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from iios.investment.strategy.debate.debate_constants import ParticipantRole
from iios.investment.strategy.debate.participant_profile import ParticipantProfile
from iios.investment.strategy.debate.participant_roles import (
    BaseDebateAgent,
    ROLE_CLASS_MAP,
)


class AgentRegistry:
    """Thread-safe registry mapping participant_id → (agent, profile)."""

    def __init__(self) -> None:
        self._lock:     threading.RLock                              = threading.RLock()
        self._agents:   Dict[str, BaseDebateAgent]                   = {}
        self._profiles: Dict[str, ParticipantProfile]               = {}

    def register(self, agent: BaseDebateAgent) -> None:
        with self._lock:
            pid = agent.participant_id
            self._agents[pid]   = agent
            self._profiles[pid] = agent.profile

    def get(self, participant_id: str) -> Optional[BaseDebateAgent]:
        with self._lock:
            return self._agents.get(participant_id)

    def get_profile(self, participant_id: str) -> Optional[ParticipantProfile]:
        with self._lock:
            return self._profiles.get(participant_id)

    def by_role(self, role: ParticipantRole) -> List[BaseDebateAgent]:
        with self._lock:
            return [a for a in self._agents.values() if a.role == role]

    def all_agents(self) -> List[BaseDebateAgent]:
        with self._lock:
            return list(self._agents.values())

    def all_profiles(self) -> List[ParticipantProfile]:
        with self._lock:
            return list(self._profiles.values())

    def remove(self, participant_id: str) -> None:
        with self._lock:
            self._agents.pop(participant_id, None)
            self._profiles.pop(participant_id, None)

    def count(self) -> int:
        with self._lock:
            return len(self._agents)

    def participant_ids(self) -> List[str]:
        with self._lock:
            return list(self._agents.keys())


def create_default_registry() -> AgentRegistry:
    """Create a registry populated with all 10 built-in agents."""
    registry = AgentRegistry()
    for role, cls in ROLE_CLASS_MAP.items():
        if role == ParticipantRole.CUSTOM:
            continue
        agent = cls()
        registry.register(agent)
    return registry
