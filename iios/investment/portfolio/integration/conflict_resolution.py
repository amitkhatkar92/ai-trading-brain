"""iios/investment/portfolio/integration/conflict_resolution.py

Deterministic conflict resolution — critical conflicts are escalated;
deterministic rules apply to known conflict patterns.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict

from iios.investment.portfolio.integration.conflict_classifier import ClassifiedConflict
from iios.investment.portfolio.integration.integration_types import (
    ConflictResolutionStatus, ConflictSeverity, now_utc,
)


@dataclass(frozen=True)
class ConflictResolutionResult:
    resolution_id: str  = field(default_factory=lambda: str(uuid.uuid4()))
    conflict_id:   str  = ""
    resolved_at:   str  = field(default_factory=now_utc)
    status:        ConflictResolutionStatus = ConflictResolutionStatus.UNRESOLVED
    resolution:    str  = ""
    rationale:     str  = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conflict_id": self.conflict_id,
            "status":      self.status.value,
            "resolution":  self.resolution,
            "rationale":   self.rationale,
        }


class ConflictResolver:
    """
    Applies deterministic resolution strategies to classified conflicts.
    Critical conflicts are always escalated.
    """

    def resolve(self, classified: ClassifiedConflict) -> ConflictResolutionResult:
        conflict = classified.conflict

        # Critical: always escalate for human review
        if conflict.severity == ConflictSeverity.CRITICAL:
            return ConflictResolutionResult(
                conflict_id = conflict.conflict_id,
                status      = ConflictResolutionStatus.ESCALATED,
                resolution  = "Escalated — critical severity requires human review",
                rationale   = conflict.description,
            )

        # Risk:Recommendation direction conflict — risk engine takes precedence
        if (conflict.conflict_type == "direction_conflict"
                and "risk:recommendation" in conflict.engine_pair):
            return ConflictResolutionResult(
                conflict_id = conflict.conflict_id,
                status      = ConflictResolutionStatus.RESOLVED,
                resolution  = "Risk engine override — risk constraints take precedence over recommendations",
                rationale   = "Institutional governance: risk management overrides return-seeking signals",
            )

        # Internal inconsistency — flag and use quantitative measure
        if conflict.conflict_type == "internal_inconsistency":
            return ConflictResolutionResult(
                conflict_id = conflict.conflict_id,
                status      = ConflictResolutionStatus.RESOLVED,
                resolution  = "Quantitative utilization metric adopted as primary indicator",
                rationale   = "Quantitative measures preferred over boolean flags",
            )

        # Value mismatch — adopt more conservative interpretation
        if conflict.conflict_type == "value_mismatch":
            return ConflictResolutionResult(
                conflict_id = conflict.conflict_id,
                status      = ConflictResolutionStatus.RESOLVED,
                resolution  = "Conservative metric adopted — using risk-aware interpretation",
                rationale   = "In metric conflict, favour the more conservative interpretation",
            )

        # Low/info severity — acknowledge and log
        if conflict.severity in (ConflictSeverity.LOW, ConflictSeverity.INFO):
            return ConflictResolutionResult(
                conflict_id = conflict.conflict_id,
                status      = ConflictResolutionStatus.IGNORED,
                resolution  = "Acknowledged — low severity, no action required",
                rationale   = "Below threshold for active resolution",
            )

        # Medium/High with no deterministic rule — escalate
        return ConflictResolutionResult(
            conflict_id = conflict.conflict_id,
            status      = ConflictResolutionStatus.ESCALATED,
            resolution  = "Escalated for review",
            rationale   = (
                f"Conflict type '{conflict.conflict_type}' "
                f"has no deterministic resolution rule"
            ),
        )
