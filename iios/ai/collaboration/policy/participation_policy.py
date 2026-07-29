"""
participation_policy.py -- iios.ai.collaboration.policy
=========================================================
Abstract :class:`ParticipationPolicy` and :class:`DefaultParticipationPolicy`.

A6 Multi-Agent Collaboration Framework — Phase 3, Module 6
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..core.collaboration_context import CollaborationContext
from ..core.agent_role_assignment  import CollaborationRole
from ..exceptions.collaboration_exceptions import (
    AICollaborationPolicyViolationError,
    AICollaborationValidationError,
)


class ParticipationPolicy(ABC):
    """Abstract policy applied when agents join a session."""

    @abstractmethod
    def validate_invite(
        self,
        ctx:        CollaborationContext,
        agent_id:   str,
        agent_type: str,
        role:       CollaborationRole,
        weight:     float,
    ) -> None:
        """Raise if the invite violates policy."""
        ...

    @abstractmethod
    def max_participants(self) -> int: ...


class DefaultParticipationPolicy(ParticipationPolicy):
    """
    Default participation policy.

    * weight must be in (0.0, ∞).
    * No duplicate agent_id.
    * Respect CollaborationMetadata.max_participants.
    """

    def validate_invite(
        self,
        ctx:        CollaborationContext,
        agent_id:   str,
        agent_type: str,
        role:       CollaborationRole,
        weight:     float,
    ) -> None:
        if weight <= 0.0:
            raise AICollaborationValidationError(
                f"Participant weight must be > 0.0; got {weight}."
            )
        existing_ids = {p.agent_id for p in ctx.participants}
        if agent_id in existing_ids:
            raise AICollaborationPolicyViolationError(
                f"Agent '{agent_id}' is already a participant in session '{ctx.session_id}'."
            )
        if ctx.participant_count >= self.max_participants():
            raise AICollaborationPolicyViolationError(
                f"Session '{ctx.session_id}' is at max capacity ({self.max_participants()})."
            )

    def max_participants(self) -> int:
        return 20
