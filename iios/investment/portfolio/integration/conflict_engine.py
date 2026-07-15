"""iios/investment/portfolio/integration/conflict_engine.py

Orchestrates the full conflict pipeline: detect → classify → resolve.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.portfolio.integration.conflict_classifier import (
    ClassifiedConflict, ConflictClassifier,
)
from iios.investment.portfolio.integration.conflict_detector import (
    ConflictDetector, DetectedConflict,
)
from iios.investment.portfolio.integration.conflict_history import ConflictHistory
from iios.investment.portfolio.integration.conflict_resolution import (
    ConflictResolutionResult, ConflictResolver,
)
from iios.investment.portfolio.integration.integration_types import (
    ConflictResolutionStatus, ConflictSeverity, IntegrationParameters,
)


@dataclass(frozen=True)
class ConflictReport:
    portfolio_id:     str                                   = ""
    n_detected:       int                                   = 0
    n_resolved:       int                                   = 0
    n_escalated:      int                                   = 0
    n_ignored:        int                                   = 0
    n_critical:       int                                   = 0
    n_high:           int                                   = 0
    has_unresolved:   bool                                  = False
    conflicts:        Tuple[DetectedConflict, ...]          = field(default_factory=tuple)
    resolutions:      Tuple[ConflictResolutionResult, ...]  = field(default_factory=tuple)
    primary_conflict: Optional[str]                         = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "n_detected":      self.n_detected,
            "n_resolved":      self.n_resolved,
            "n_escalated":     self.n_escalated,
            "n_critical":      self.n_critical,
            "n_high":          self.n_high,
            "has_unresolved":  self.has_unresolved,
            "primary_conflict": self.primary_conflict,
        }


class ConflictEngine:
    """Orchestrates detect → classify → resolve for a single portfolio."""

    def __init__(self, params: Optional[IntegrationParameters] = None) -> None:
        self._params     = params or IntegrationParameters()
        self._detector   = ConflictDetector()
        self._classifier = ConflictClassifier()
        self._resolver   = ConflictResolver()
        self._history    = ConflictHistory()

    def process(
        self,
        merged:       Dict[str, Any],
        portfolio_id: str = "",
    ) -> ConflictReport:
        # Detect
        conflicts: List[DetectedConflict] = self._detector.detect(merged, portfolio_id)
        for c in conflicts:
            self._history.add_conflict(c)

        # Classify
        classified: List[ClassifiedConflict] = self._classifier.classify(conflicts)

        # Resolve
        resolutions: List[ConflictResolutionResult] = []
        for cc in classified:
            result = self._resolver.resolve(cc)
            resolutions.append(result)
            self._history.add_resolution(portfolio_id, result)

        n_resolved  = sum(1 for r in resolutions if r.status == ConflictResolutionStatus.RESOLVED)
        n_escalated = sum(1 for r in resolutions if r.status == ConflictResolutionStatus.ESCALATED)
        n_ignored   = sum(1 for r in resolutions if r.status == ConflictResolutionStatus.IGNORED)
        n_critical  = sum(1 for c in conflicts if c.severity == ConflictSeverity.CRITICAL)
        n_high      = sum(1 for c in conflicts if c.severity == ConflictSeverity.HIGH)

        primary_conflict = classified[0].conflict.description if classified else None

        return ConflictReport(
            portfolio_id    = portfolio_id,
            n_detected      = len(conflicts),
            n_resolved      = n_resolved,
            n_escalated     = n_escalated,
            n_ignored       = n_ignored,
            n_critical      = n_critical,
            n_high          = n_high,
            has_unresolved  = n_escalated > 0,
            conflicts       = tuple(conflicts),
            resolutions     = tuple(resolutions),
            primary_conflict = primary_conflict,
        )

    def recent_conflicts(
        self,
        portfolio_id: str,
        n: int = 20,
    ) -> List[DetectedConflict]:
        return self._history.recent_conflicts(portfolio_id, n)

    def recent_resolutions(
        self,
        portfolio_id: str,
        n: int = 20,
    ) -> List[ConflictResolutionResult]:
        return self._history.recent_resolutions(portfolio_id, n)
