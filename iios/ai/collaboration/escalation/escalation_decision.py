"""
escalation_decision.py -- iios.ai.collaboration.escalation
============================================================
:class:`EscalationDecision` — immutable decision returned when an escalation
is reviewed by a human operator or an upstream authority.

A6 Multi-Agent Collaboration Framework — Phase 3, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any, FrozenSet, Optional, Tuple


class EscalationAction(str, Enum):
    """Action taken when resolving an escalation."""

    APPROVE     = "approve"
    REJECT      = "reject"
    DEFER       = "defer"
    OVERRIDE    = "override"
    CLOSE       = "close"


@dataclass(frozen=True)
class EscalationDecision:
    """
    Immutable decision record produced when an escalation is resolved.

    ``data`` carries additional context (e.g. an override trade instruction).
    """

    decision_id: str
    request_id:  str
    session_id:  str
    action:      EscalationAction
    decided_by:  str
    rationale:   str
    decided_at:  float
    data:        FrozenSet[Tuple[str, Any]]

    @classmethod
    def create(
        cls,
        request_id:  str,
        session_id:  str,
        action:      EscalationAction,
        decided_by:  str,
        rationale:   str = "",
        **data: Any,
    ) -> "EscalationDecision":
        return cls(
            decision_id = str(uuid.uuid4()),
            request_id  = request_id,
            session_id  = session_id,
            action      = action,
            decided_by  = decided_by,
            rationale   = rationale,
            decided_at  = time.time(),
            data        = frozenset(data.items()),
        )

    def get_data(self, key: str, default: Any = None) -> Any:
        for k, v in self.data:
            if k == key:
                return v
        return default
