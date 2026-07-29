"""
participant.py -- iios.ai.collaboration.core
=============================================
:class:`ParticipantStatus` — participant life-cycle states.
:class:`Participant`       — immutable participant record.

Agents are identified by their A5 ``agent_id`` and ``agent_type``.
A6 stores a snapshot of identity at invitation time; it does not hold a
reference to the live ``BaseAIAgent`` object.

A6 Multi-Agent Collaboration Framework — Phase 3, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from enum import Enum

from .agent_role_assignment import CollaborationRole


class ParticipantStatus(str, Enum):
    """Life-cycle status of a single session participant."""

    INVITED    = "invited"
    ACTIVE     = "active"
    RESPONDED  = "responded"
    ABSTAINED  = "abstained"
    REMOVED    = "removed"


@dataclass(frozen=True)
class Participant:
    """
    Immutable snapshot of one agent's participation in a session.

    All mutation returns a new instance.  ``weight`` controls voting
    power in weighted consensus strategies (default 1.0 = equal weight).
    """

    participant_id: str
    agent_id:       str
    agent_name:     str
    agent_type:     str
    role:           CollaborationRole
    status:         ParticipantStatus
    joined_at:      float
    weight:         float

    @classmethod
    def create(
        cls,
        agent_id:   str,
        agent_name: str,
        agent_type: str,
        role:       CollaborationRole,
        weight:     float = 1.0,
    ) -> "Participant":
        return cls(
            participant_id = str(uuid.uuid4()),
            agent_id       = agent_id,
            agent_name     = agent_name,
            agent_type     = agent_type,
            role           = role,
            status         = ParticipantStatus.INVITED,
            joined_at      = time.time(),
            weight         = weight,
        )

    def with_status(self, status: ParticipantStatus) -> "Participant":
        """Return a new :class:`Participant` with ``status`` updated."""
        return Participant(
            participant_id = self.participant_id,
            agent_id       = self.agent_id,
            agent_name     = self.agent_name,
            agent_type     = self.agent_type,
            role           = self.role,
            status         = status,
            joined_at      = self.joined_at,
            weight         = self.weight,
        )

    def with_role(self, role: CollaborationRole) -> "Participant":
        """Return a new :class:`Participant` with ``role`` updated."""
        return Participant(
            participant_id = self.participant_id,
            agent_id       = self.agent_id,
            agent_name     = self.agent_name,
            agent_type     = self.agent_type,
            role           = role,
            status         = self.status,
            joined_at      = self.joined_at,
            weight         = self.weight,
        )

    def can_vote(self) -> bool:
        return self.role.can_vote() and self.status not in (
            ParticipantStatus.ABSTAINED, ParticipantStatus.REMOVED
        )

    def can_debate(self) -> bool:
        return self.role.can_debate() and self.status not in (
            ParticipantStatus.ABSTAINED, ParticipantStatus.REMOVED
        )
