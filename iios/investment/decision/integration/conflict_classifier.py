"""iios/investment/decision/integration/conflict_classifier.py
Classifies detected conflicts into priority buckets and assigns resolution strategies.
"""
from __future__ import annotations

from typing import List, Tuple

from iios.investment.decision.integration.conflict_detector import DetectedConflict
from iios.investment.decision.integration.integration_constants import (
    ConflictResolutionStrategy,
    ConflictSeverity,
    ConflictType,
)


class ConflictClassifier:
    """
    Assigns a ConflictResolutionStrategy to each DetectedConflict and
    sorts the list by priority (CRITICAL → LOW, then by type).
    """

    # Strategy by (type, severity)
    _STRATEGY_MAP: dict = {
        (ConflictType.SUBJECT_MISMATCH,           ConflictSeverity.CRITICAL): ConflictResolutionStrategy.ESCALATE,
        (ConflictType.EVIDENCE_REASONING,          ConflictSeverity.CRITICAL): ConflictResolutionStrategy.ESCALATE,
        (ConflictType.COMMITTEE_RECOMMENDATION,    ConflictSeverity.CRITICAL): ConflictResolutionStrategy.CONSERVATIVE,
        (ConflictType.COMMITTEE_RISK,              ConflictSeverity.CRITICAL): ConflictResolutionStrategy.CONSERVATIVE,
        (ConflictType.CONFIDENCE_RISK,             ConflictSeverity.HIGH):     ConflictResolutionStrategy.CONSERVATIVE,
        (ConflictType.EVIDENCE_REASONING,          ConflictSeverity.HIGH):     ConflictResolutionStrategy.LATEST,
        (ConflictType.COMMITTEE_RISK,              ConflictSeverity.MEDIUM):   ConflictResolutionStrategy.HIGHER_WEIGHT,
        (ConflictType.DATA_STALENESS,              ConflictSeverity.MEDIUM):   ConflictResolutionStrategy.LATEST,
        (ConflictType.POLICY,                      ConflictSeverity.CRITICAL): ConflictResolutionStrategy.ESCALATE,
    }

    _SEVERITY_ORDER = {
        ConflictSeverity.CRITICAL: 0,
        ConflictSeverity.HIGH:     1,
        ConflictSeverity.MEDIUM:   2,
        ConflictSeverity.LOW:      3,
    }

    def classify(
        self, conflicts: List[DetectedConflict],
    ) -> List[Tuple[DetectedConflict, ConflictResolutionStrategy]]:
        """
        Returns conflicts paired with their resolution strategy,
        sorted highest severity first.
        """
        result = []
        for c in conflicts:
            strategy = self._resolve_strategy(c)
            result.append((c, strategy))
        result.sort(key=lambda x: (self._SEVERITY_ORDER.get(x[0].severity, 99),
                                   x[0].conflict_type.value))
        return result

    def critical_conflicts(
        self, conflicts: List[DetectedConflict],
    ) -> List[DetectedConflict]:
        return [c for c in conflicts if c.severity == ConflictSeverity.CRITICAL]

    def blocks_publishing(self, conflicts: List[DetectedConflict]) -> bool:
        return any(c.severity.blocks_publishing for c in conflicts if not c.is_resolved)

    def _resolve_strategy(self, c: DetectedConflict) -> ConflictResolutionStrategy:
        # Exact match
        key = (c.conflict_type, c.severity)
        if key in self._STRATEGY_MAP:
            return self._STRATEGY_MAP[key]
        # Fallback by severity
        if c.severity == ConflictSeverity.CRITICAL:
            return ConflictResolutionStrategy.ESCALATE
        if c.severity == ConflictSeverity.HIGH:
            return ConflictResolutionStrategy.CONSERVATIVE
        return ConflictResolutionStrategy.LATEST
