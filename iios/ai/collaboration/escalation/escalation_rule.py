"""
escalation_rule.py -- iios.ai.collaboration.escalation
========================================================
:class:`EscalationTrigger` — conditions that can trigger escalation.
:class:`EscalationRule`    — immutable rule configuration.

A6 Multi-Agent Collaboration Framework — Phase 3, Module 6
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import Enum
from typing import FrozenSet, Optional


class EscalationTrigger(str, Enum):
    """Conditions that can trigger an escalation request."""

    CONSENSUS_FAILED      = "consensus_failed"
    ROUND_LIMIT_EXCEEDED  = "round_limit_exceeded"
    TIMEOUT               = "timeout"
    MANUAL                = "manual"
    RISK_THRESHOLD        = "risk_threshold"
    CONFLICT_OF_INTEREST  = "conflict_of_interest"
    CUSTOM                = "custom"


@dataclass(frozen=True)
class EscalationRule:
    """
    Immutable policy rule that determines *when* and *how* to escalate.

    Fields
    ------
    rule_id          — UUID
    name             — human-readable name
    triggers         — set of :class:`EscalationTrigger` that activate this rule
    escalate_to      — agent_id or role to escalate to (None = framework decides)
    auto_close       — if True, session is automatically closed after escalation
    priority         — 1 (highest) – 10 (lowest)
    """

    rule_id:      str
    name:         str
    triggers:     FrozenSet[EscalationTrigger]
    escalate_to:  Optional[str]
    auto_close:   bool
    priority:     int

    @classmethod
    def create(
        cls,
        name:         str,
        triggers:     FrozenSet[EscalationTrigger],
        escalate_to:  Optional[str]            = None,
        auto_close:   bool                     = False,
        priority:     int                      = 5,
    ) -> "EscalationRule":
        return cls(
            rule_id     = str(uuid.uuid4()),
            name        = name,
            triggers    = frozenset(triggers),
            escalate_to = escalate_to,
            auto_close  = auto_close,
            priority    = max(1, min(10, priority)),
        )

    def matches(self, trigger: EscalationTrigger) -> bool:
        return trigger in self.triggers
