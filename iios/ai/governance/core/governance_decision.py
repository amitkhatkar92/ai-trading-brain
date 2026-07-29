"""
governance_decision.py -- iios.ai.governance.core
===================================================
:class:`GovernanceDecisionType` — decision outcome.
:class:`GovernanceDecision`     — immutable governance decision record.

A8 AI Governance Platform — Phase 3, Module 8
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any, FrozenSet, Optional, Tuple

from .governance_context  import GovernanceContext
from .governance_metadata import GovernanceSeverity


class GovernanceDecisionType(str, Enum):
    """Outcome classification of a governance decision."""
    ALLOW    = "allow"
    DENY     = "deny"
    REQUIRE_APPROVAL = "require_approval"
    ESCALATE = "escalate"
    MONITOR  = "monitor"

    def is_blocking(self) -> bool:
        return self in (GovernanceDecisionType.DENY, GovernanceDecisionType.ESCALATE)


@dataclass(frozen=True)
class GovernanceDecision:
    """
    Immutable record of one governance decision.

    ``decision_type`` — outcome (ALLOW/DENY/REQUIRE_APPROVAL/ESCALATE/MONITOR).
    ``rationale``     — human-readable explanation of the decision.
    ``policy_ids``    — set of policy IDs that contributed to this decision.
    ``conditions``    — conditions that must be met if decision is ALLOW/MONITOR.
    """

    decision_id:   str
    context_id:    str
    decision_type: GovernanceDecisionType
    rationale:     str
    policy_ids:    FrozenSet[str]
    conditions:    FrozenSet[Tuple[str, Any]]
    severity:      GovernanceSeverity
    decided_at:    float
    decided_by:    str
    notes:         str

    @classmethod
    def allow(
        cls,
        context:    GovernanceContext,
        rationale:  str              = "Allowed by policy",
        policy_ids: FrozenSet[str]   = frozenset(),
        decided_by: str              = "policy_engine",
        **conditions: Any,
    ) -> "GovernanceDecision":
        return cls(
            decision_id   = str(uuid.uuid4()),
            context_id    = context.context_id,
            decision_type = GovernanceDecisionType.ALLOW,
            rationale     = rationale,
            policy_ids    = frozenset(policy_ids),
            conditions    = frozenset(conditions.items()),
            severity      = GovernanceSeverity.INFO,
            decided_at    = time.time(),
            decided_by    = decided_by,
            notes         = "",
        )

    @classmethod
    def deny(
        cls,
        context:    GovernanceContext,
        rationale:  str              = "Denied by policy",
        policy_ids: FrozenSet[str]   = frozenset(),
        severity:   GovernanceSeverity = GovernanceSeverity.HIGH,
        decided_by: str              = "policy_engine",
    ) -> "GovernanceDecision":
        return cls(
            decision_id   = str(uuid.uuid4()),
            context_id    = context.context_id,
            decision_type = GovernanceDecisionType.DENY,
            rationale     = rationale,
            policy_ids    = frozenset(policy_ids),
            conditions    = frozenset(),
            severity      = severity,
            decided_at    = time.time(),
            decided_by    = decided_by,
            notes         = "",
        )

    @classmethod
    def escalate(
        cls,
        context:    GovernanceContext,
        rationale:  str              = "Escalation required",
        policy_ids: FrozenSet[str]   = frozenset(),
        decided_by: str              = "risk_engine",
    ) -> "GovernanceDecision":
        return cls(
            decision_id   = str(uuid.uuid4()),
            context_id    = context.context_id,
            decision_type = GovernanceDecisionType.ESCALATE,
            rationale     = rationale,
            policy_ids    = frozenset(policy_ids),
            conditions    = frozenset(),
            severity      = GovernanceSeverity.CRITICAL,
            decided_at    = time.time(),
            decided_by    = decided_by,
            notes         = "",
        )

    def is_allowed(self) -> bool:
        return self.decision_type == GovernanceDecisionType.ALLOW

    def is_denied(self) -> bool:
        return self.decision_type.is_blocking()
