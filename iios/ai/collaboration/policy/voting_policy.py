"""
voting_policy.py -- iios.ai.collaboration.policy
==================================================
Abstract :class:`VotingPolicy` and :class:`DefaultVotingPolicy`.

A6 Multi-Agent Collaboration Framework — Phase 3, Module 6
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..core.collaboration_context import CollaborationContext
from ..exceptions.collaboration_exceptions import AICollaborationPolicyViolationError


class VotingPolicy(ABC):
    """Abstract policy applied before and during voting."""

    @abstractmethod
    def validate_vote(
        self,
        ctx:        CollaborationContext,
        agent_id:   str,
        confidence: float,
    ) -> None:
        """Raise :class:`AICollaborationPolicyViolationError` if the vote is invalid."""
        ...

    @abstractmethod
    def default_strategy(self) -> str: ...


class DefaultVotingPolicy(VotingPolicy):
    """
    Default voting policy.

    * Only participants with ``can_vote()`` == True may vote.
    * Confidence must be in [0.0, 1.0].
    * Default consensus strategy: majority.
    """

    def validate_vote(
        self,
        ctx:        CollaborationContext,
        agent_id:   str,
        confidence: float,
    ) -> None:
        if not (0.0 <= confidence <= 1.0):
            raise AICollaborationPolicyViolationError(
                f"Confidence must be in [0.0, 1.0]; got {confidence}."
            )
        participant = next(
            (p for p in ctx.participants if p.agent_id == agent_id), None
        )
        if participant is None:
            raise AICollaborationPolicyViolationError(
                f"Agent '{agent_id}' is not a participant in session '{ctx.session_id}'."
            )
        if not participant.can_vote():
            raise AICollaborationPolicyViolationError(
                f"Agent '{agent_id}' (role={participant.role.value}) cannot vote."
            )

    def default_strategy(self) -> str:
        return "majority"
