"""
agent_role_assignment.py -- iios.ai.collaboration.core
========================================================
:class:`CollaborationRole`    — roles within a collaboration session.
:class:`AgentRoleAssignment`  — immutable record linking agent to role.

A6 Multi-Agent Collaboration Framework — Phase 3, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from enum import Enum


class CollaborationRole(str, Enum):
    """
    Roles an agent can hold within a collaboration session.

    LEAD        — drives the session, sets agenda
    ANALYST     — primary contributor, submits arguments
    CHALLENGER  — actively challenges other positions
    MODERATOR   — enforces rules, manages rounds
    OBSERVER    — watches but does not vote
    VOTER       — participates in voting only (no debate)
    """

    LEAD       = "lead"
    ANALYST    = "analyst"
    CHALLENGER = "challenger"
    MODERATOR  = "moderator"
    OBSERVER   = "observer"
    VOTER      = "voter"

    def can_vote(self) -> bool:
        return self not in (CollaborationRole.OBSERVER, CollaborationRole.MODERATOR)

    def can_debate(self) -> bool:
        return self not in (CollaborationRole.OBSERVER, CollaborationRole.VOTER)


@dataclass(frozen=True)
class AgentRoleAssignment:
    """Immutable record of an agent's role in one session."""

    assignment_id: str
    session_id:    str
    agent_id:      str
    role:          CollaborationRole
    assigned_at:   float
    assigned_by:   str

    @classmethod
    def create(
        cls,
        session_id:  str,
        agent_id:    str,
        role:        CollaborationRole,
        assigned_by: str = "system",
    ) -> "AgentRoleAssignment":
        return cls(
            assignment_id = str(uuid.uuid4()),
            session_id    = session_id,
            agent_id      = agent_id,
            role          = role,
            assigned_at   = time.time(),
            assigned_by   = assigned_by,
        )


# ---------------------------------------------------------------------------
# Default role mapping for specialist agents (A5 compatibility)
# ---------------------------------------------------------------------------

SPECIALIST_DEFAULT_ROLES: dict = {
    "MarketAnalystAgent":      CollaborationRole.ANALYST,
    "TechnicalAnalystAgent":   CollaborationRole.ANALYST,
    "FundamentalAnalystAgent": CollaborationRole.ANALYST,
    "MacroAnalystAgent":       CollaborationRole.ANALYST,
    "NewsAnalystAgent":        CollaborationRole.ANALYST,
    "SentimentAnalystAgent":   CollaborationRole.ANALYST,
    "RiskAnalystAgent":        CollaborationRole.CHALLENGER,
    "PortfolioAnalystAgent":   CollaborationRole.ANALYST,
    "ComplianceAnalystAgent":  CollaborationRole.CHALLENGER,
    "ResearchAnalystAgent":    CollaborationRole.ANALYST,
    "OptionsAnalystAgent":     CollaborationRole.ANALYST,
    "CryptoAnalystAgent":      CollaborationRole.ANALYST,
    "AuditAgent":              CollaborationRole.OBSERVER,
    "LearningAgent":           CollaborationRole.OBSERVER,
}
