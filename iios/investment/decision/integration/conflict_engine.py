"""iios/investment/decision/integration/conflict_engine.py
ConflictEngine — detects, classifies, resolves, and records conflicts.
"""
from __future__ import annotations

import threading
from typing import List, Optional, Tuple

from iios.investment.decision.integration.aggregation_state import _AggregationStateSnapshot
from iios.investment.decision.integration.conflict_classifier import ConflictClassifier
from iios.investment.decision.integration.conflict_detector import (
    ConflictDetector,
    DetectedConflict,
)
from iios.investment.decision.integration.conflict_history import ConflictHistory
from iios.investment.decision.integration.conflict_resolution import (
    ConflictResolver,
    ResolutionResult,
)
from iios.investment.decision.integration.integration_constants import ConflictSeverity


class ConflictReport:
    """Immutable report of all conflict activity for a single integration cycle."""

    __slots__ = (
        "decision_id",
        "all_conflicts",
        "resolved",
        "unresolved",
        "resolution_results",
        "critical_count",
        "high_count",
        "blocks_publishing",
    )

    def __init__(
        self,
        decision_id:       str,
        all_conflicts:     List[DetectedConflict],
        resolved:          List[DetectedConflict],
        unresolved:        List[DetectedConflict],
        resolution_results: List[ResolutionResult],
    ) -> None:
        object.__setattr__(self, "decision_id",        decision_id)
        object.__setattr__(self, "all_conflicts",      list(all_conflicts))
        object.__setattr__(self, "resolved",           list(resolved))
        object.__setattr__(self, "unresolved",         list(unresolved))
        object.__setattr__(self, "resolution_results", list(resolution_results))
        object.__setattr__(self, "critical_count",     sum(
            1 for c in all_conflicts if c.severity == ConflictSeverity.CRITICAL))
        object.__setattr__(self, "high_count", sum(
            1 for c in all_conflicts if c.severity == ConflictSeverity.HIGH))
        object.__setattr__(self, "blocks_publishing", any(
            c.severity.blocks_publishing and not c.is_resolved for c in unresolved))

    def __setattr__(self, name, value):
        raise AttributeError("ConflictReport is immutable")

    def to_dict(self):
        return {
            "decision_id":       self.decision_id,
            "total_conflicts":   len(self.all_conflicts),
            "resolved":          len(self.resolved),
            "unresolved":        len(self.unresolved),
            "critical_count":    self.critical_count,
            "high_count":        self.high_count,
            "blocks_publishing": self.blocks_publishing,
            "conflicts":         [c.to_dict() for c in self.all_conflicts],
        }


class ConflictEngine:
    """
    Orchestrates full conflict lifecycle: detect → classify → resolve → record.
    """

    def __init__(self) -> None:
        self._detector   = ConflictDetector()
        self._classifier = ConflictClassifier()
        self._resolver   = ConflictResolver()
        self._history    = ConflictHistory()

    def run(self, snap: _AggregationStateSnapshot) -> ConflictReport:
        """Full conflict processing pipeline for one integration cycle."""
        all_conflicts = self._detector.detect(snap)
        resolved, unresolved, results = self._resolver.resolve(all_conflicts)
        did = getattr(snap, "decision_id", "")
        self._history.record(did, all_conflicts)
        return ConflictReport(
            decision_id        = did,
            all_conflicts      = all_conflicts,
            resolved           = resolved,
            unresolved         = unresolved,
            resolution_results = results,
        )

    @property
    def history(self) -> ConflictHistory:
        return self._history
