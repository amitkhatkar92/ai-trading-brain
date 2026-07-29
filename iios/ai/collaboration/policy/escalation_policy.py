"""
escalation_policy.py -- iios.ai.collaboration.policy
======================================================
Abstract :class:`EscalationPolicy` and :class:`DefaultEscalationPolicy`.

A6 Multi-Agent Collaboration Framework — Phase 3, Module 6
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..core.collaboration_context     import CollaborationContext
from ..escalation.escalation_rule     import EscalationTrigger
from ..exceptions.collaboration_exceptions import AICollaborationPolicyViolationError


class EscalationPolicy(ABC):
    """Abstract policy governing when and how escalations are triggered."""

    @abstractmethod
    def validate_escalation(
        self,
        ctx:          CollaborationContext,
        trigger:      EscalationTrigger,
        requested_by: str,
    ) -> None:
        """Raise if the escalation is not permitted."""
        ...

    @abstractmethod
    def should_auto_escalate(
        self,
        ctx:          CollaborationContext,
        trigger:      EscalationTrigger,
    ) -> bool: ...


class DefaultEscalationPolicy(EscalationPolicy):
    """
    Default escalation policy.

    * Any participant may request a MANUAL escalation.
    * Only CONSENSUS_FAILED and ROUND_LIMIT_EXCEEDED can auto-escalate.
    * Session must be in an active state to escalate.
    """

    _AUTO_TRIGGERS = frozenset({
        EscalationTrigger.CONSENSUS_FAILED,
        EscalationTrigger.ROUND_LIMIT_EXCEEDED,
        EscalationTrigger.TIMEOUT,
    })

    def validate_escalation(
        self,
        ctx:          CollaborationContext,
        trigger:      EscalationTrigger,
        requested_by: str,
    ) -> None:
        if not ctx.status.is_active():
            raise AICollaborationPolicyViolationError(
                f"Cannot escalate session '{ctx.session_id}' in status '{ctx.status.value}'."
            )

    def should_auto_escalate(
        self,
        ctx:     CollaborationContext,
        trigger: EscalationTrigger,
    ) -> bool:
        return trigger in self._AUTO_TRIGGERS
