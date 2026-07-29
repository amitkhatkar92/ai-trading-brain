"""
debate_policy.py -- iios.ai.collaboration.policy
==================================================
Abstract :class:`DebatePolicy` and :class:`DefaultDebatePolicy`.

A6 Multi-Agent Collaboration Framework — Phase 3, Module 6
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..core.collaboration_context import CollaborationContext
from ..exceptions.collaboration_exceptions import AICollaborationPolicyViolationError


class DebatePolicy(ABC):
    """Abstract policy applied before and during a debate."""

    @abstractmethod
    def validate_start(self, ctx: CollaborationContext) -> None:
        """Raise :class:`AICollaborationPolicyViolationError` if debate cannot start."""
        ...

    @abstractmethod
    def validate_submission(
        self,
        ctx:      CollaborationContext,
        agent_id: str,
        round_no: int,
    ) -> None:
        """Raise if *agent_id* cannot submit in *round_no*."""
        ...

    @abstractmethod
    def max_rounds(self) -> int: ...


class DefaultDebatePolicy(DebatePolicy):
    """
    Default debate policy.

    * At least 2 active participants required to start.
    * Any ACTIVE participant may submit in any round.
    * max_rounds = 3.
    """

    _MIN_PARTICIPANTS = 2
    _MAX_ROUNDS       = 3

    def validate_start(self, ctx: CollaborationContext) -> None:
        if ctx.active_participant_count < self._MIN_PARTICIPANTS:
            raise AICollaborationPolicyViolationError(
                f"Debate requires at least {self._MIN_PARTICIPANTS} active participants; "
                f"found {ctx.active_participant_count}."
            )

    def validate_submission(
        self,
        ctx:      CollaborationContext,
        agent_id: str,
        round_no: int,
    ) -> None:
        participant = next(
            (p for p in ctx.participants if p.agent_id == agent_id), None
        )
        if participant is None:
            raise AICollaborationPolicyViolationError(
                f"Agent '{agent_id}' is not a participant in session '{ctx.session_id}'."
            )
        if not participant.can_debate():
            raise AICollaborationPolicyViolationError(
                f"Agent '{agent_id}' (role={participant.role.value}) cannot debate."
            )

    def max_rounds(self) -> int:
        return self._MAX_ROUNDS
