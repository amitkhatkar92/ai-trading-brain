"""iios/investment/decision/integration/conflict_resolution.py
Deterministic conflict resolution strategies.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import uuid

from iios.investment.decision.integration.conflict_detector import DetectedConflict
from iios.investment.decision.integration.conflict_classifier import ConflictClassifier
from iios.investment.decision.integration.integration_constants import (
    ConflictResolutionStrategy,
    ConflictSeverity,
)


@dataclass(frozen=True)
class ResolutionResult:
    conflict_id:     str
    strategy:        ConflictResolutionStrategy
    resolved:        bool
    note:            str
    resolved_at:     Optional[datetime]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conflict_id":  self.conflict_id,
            "strategy":     self.strategy.value,
            "resolved":     self.resolved,
            "note":         self.note,
            "resolved_at":  self.resolved_at.isoformat() if self.resolved_at else None,
        }


class ConflictResolver:
    """
    Attempts deterministic resolution of conflicts.
    Returns (resolved, unresolved) tuples with resolved DetectedConflict copies.
    """

    def __init__(self) -> None:
        self._classifier = ConflictClassifier()

    def resolve(
        self,
        conflicts: List[DetectedConflict],
    ) -> Tuple[List[DetectedConflict], List[DetectedConflict], List[ResolutionResult]]:
        """
        Returns:
            resolved:   conflicts that were deterministically resolved
            unresolved: conflicts that require escalation
            results:    resolution audit trail
        """
        classified   = self._classifier.classify(conflicts)
        resolved:    List[DetectedConflict]   = []
        unresolved:  List[DetectedConflict]   = []
        results:     List[ResolutionResult]   = []

        for conflict, strategy in classified:
            result = self._apply(conflict, strategy)
            results.append(result)
            if result.resolved:
                # Create a resolved copy
                resolved.append(DetectedConflict(
                    conflict_id     = conflict.conflict_id,
                    conflict_type   = conflict.conflict_type,
                    severity        = conflict.severity,
                    component_a     = conflict.component_a,
                    component_b     = conflict.component_b,
                    description     = conflict.description,
                    detail          = conflict.detail,
                    metric_a        = conflict.metric_a,
                    metric_b        = conflict.metric_b,
                    detected_at     = conflict.detected_at,
                    is_resolved     = True,
                    resolution_note = result.note,
                ))
            else:
                unresolved.append(conflict)

        return resolved, unresolved, results

    def _apply(
        self, conflict: DetectedConflict, strategy: ConflictResolutionStrategy,
    ) -> ResolutionResult:
        now = datetime.now(timezone.utc)

        if strategy == ConflictResolutionStrategy.ESCALATE:
            return ResolutionResult(
                conflict_id = conflict.conflict_id,
                strategy    = strategy,
                resolved    = False,
                note        = (
                    f"Conflict '{conflict.description}' requires human escalation — "
                    f"severity={conflict.severity.value}"
                ),
                resolved_at = None,
            )

        if strategy == ConflictResolutionStrategy.CONSERVATIVE:
            return ResolutionResult(
                conflict_id = conflict.conflict_id,
                strategy    = strategy,
                resolved    = True,
                note        = (
                    f"Applied CONSERVATIVE resolution: using more cautious "
                    f"interpretation for '{conflict.description}'"
                ),
                resolved_at = now,
            )

        if strategy == ConflictResolutionStrategy.LATEST:
            return ResolutionResult(
                conflict_id = conflict.conflict_id,
                strategy    = strategy,
                resolved    = True,
                note        = (
                    f"Applied LATEST resolution: using most recently computed "
                    f"values for '{conflict.description}'"
                ),
                resolved_at = now,
            )

        if strategy == ConflictResolutionStrategy.HIGHER_WEIGHT:
            return ResolutionResult(
                conflict_id = conflict.conflict_id,
                strategy    = strategy,
                resolved    = True,
                note        = (
                    f"Applied HIGHER_WEIGHT resolution: deferring to "
                    f"higher-authority component for '{conflict.description}'"
                ),
                resolved_at = now,
            )

        # Unknown strategy — escalate
        return ResolutionResult(
            conflict_id = conflict.conflict_id,
            strategy    = strategy,
            resolved    = False,
            note        = f"Unknown strategy {strategy.value} — escalating",
            resolved_at = None,
        )
