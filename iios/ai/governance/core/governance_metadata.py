"""
governance_metadata.py -- iios.ai.governance.core
===================================================
:class:`GovernanceStatus` — lifecycle status of a governance decision.
:class:`GovernanceSeverity` — severity levels for governance actions.
:class:`GovernanceMetadata` — immutable header for a governance decision.

A8 AI Governance Platform — Phase 3, Module 8
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any, FrozenSet, Optional, Tuple


class GovernanceStatus(str, Enum):
    """Lifecycle status of a governance decision."""
    PENDING   = "pending"
    APPROVED  = "approved"
    DENIED    = "denied"
    ESCALATED = "escalated"
    EXPIRED   = "expired"

    def is_terminal(self) -> bool:
        return self in (
            GovernanceStatus.APPROVED,
            GovernanceStatus.DENIED,
            GovernanceStatus.EXPIRED,
        )


class GovernanceSeverity(str, Enum):
    """Severity classification for governance events."""
    INFO     = "info"
    LOW      = "low"
    MEDIUM   = "medium"
    HIGH     = "high"
    CRITICAL = "critical"

    def score(self) -> int:
        return {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}[self.value]


class GovernanceDomain(str, Enum):
    """Domain that a governance action targets."""
    POLICY      = "policy"
    PERMISSION  = "permission"
    AUDIT       = "audit"
    COMPLIANCE  = "compliance"
    RISK        = "risk"
    EXPLAINABILITY = "explainability"
    OPERATIONAL = "operational"


@dataclass(frozen=True)
class GovernanceMetadata:
    """
    Immutable header attached to every governance decision or action.

    ``subject_id``  — agent/model/session requesting governance evaluation.
    ``initiated_by`` — identity that triggered this governance action.
    """

    governance_id: str
    domain:        GovernanceDomain
    subject_id:    str
    initiated_by:  str
    severity:      GovernanceSeverity
    created_at:    float
    description:   str
    tags:          FrozenSet[str]
    metadata:      FrozenSet[Tuple[str, Any]]

    @classmethod
    def create(
        cls,
        domain:       GovernanceDomain,
        subject_id:   str,
        initiated_by: str,
        severity:     GovernanceSeverity = GovernanceSeverity.INFO,
        description:  str               = "",
        tags:         FrozenSet[str]    = frozenset(),
        **metadata: Any,
    ) -> "GovernanceMetadata":
        return cls(
            governance_id = str(uuid.uuid4()),
            domain        = domain,
            subject_id    = subject_id,
            initiated_by  = initiated_by,
            severity      = severity,
            created_at    = time.time(),
            description   = description,
            tags          = frozenset(tags),
            metadata      = frozenset(metadata.items()),
        )
