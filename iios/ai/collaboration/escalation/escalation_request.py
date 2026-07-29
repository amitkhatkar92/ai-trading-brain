"""
escalation_request.py -- iios.ai.collaboration.escalation
===========================================================
:class:`EscalationStatus`  — request life-cycle states.
:class:`EscalationRequest` — mutable escalation record.

A6 Multi-Agent Collaboration Framework — Phase 3, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .escalation_rule import EscalationTrigger


class EscalationStatus(str, Enum):
    PENDING   = "pending"
    REVIEWING = "reviewing"
    RESOLVED  = "resolved"
    REJECTED  = "rejected"

    def is_terminal(self) -> bool:
        return self in (EscalationStatus.RESOLVED, EscalationStatus.REJECTED)


@dataclass
class EscalationRequest:
    """
    Mutable escalation record created when a session cannot reach consensus
    or a policy rule is triggered.

    Mutated by :class:`EscalationManager` when the escalation is reviewed
    or resolved.
    """

    request_id:   str
    session_id:   str
    trigger:      EscalationTrigger
    reason:       str
    requested_by: str
    escalate_to:  Optional[str]
    status:       EscalationStatus
    created_at:   float
    updated_at:   float
    resolution:   Optional[str]

    @classmethod
    def create(
        cls,
        session_id:   str,
        trigger:      EscalationTrigger,
        reason:       str,
        requested_by: str,
        escalate_to:  Optional[str] = None,
    ) -> "EscalationRequest":
        now = time.time()
        return cls(
            request_id   = str(uuid.uuid4()),
            session_id   = session_id,
            trigger      = trigger,
            reason       = reason,
            requested_by = requested_by,
            escalate_to  = escalate_to,
            status       = EscalationStatus.PENDING,
            created_at   = now,
            updated_at   = now,
            resolution   = None,
        )

    def update_status(self, status: EscalationStatus, resolution: Optional[str] = None) -> None:
        self.status     = status
        self.updated_at = time.time()
        if resolution:
            self.resolution = resolution

    def is_terminal(self) -> bool:
        return self.status.is_terminal()
