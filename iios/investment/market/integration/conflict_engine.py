"""iios/investment/market/integration/conflict_engine.py
Orchestrates conflict detection, classification and resolution.
"""
from __future__ import annotations

from iios.investment.market.integration.aggregation_state import AggregationState
from iios.investment.market.integration.conflict_classifier import ConflictClassifier
from iios.investment.market.integration.conflict_detector import ConflictDetector
from iios.investment.market.integration.conflict_history import ConflictHistory
from iios.investment.market.integration.conflict_resolution import ConflictResolver
from iios.investment.market.integration.models import (
    ConflictSeverity,
    ConflictSummary,
    ValidationReport,
)


class ConflictEngine:
    """Full conflict pipeline: detect → classify → resolve → summarise."""

    def __init__(self, history_len: int = 200) -> None:
        self._detector    = ConflictDetector()
        self._classifier  = ConflictClassifier()
        self._resolver    = ConflictResolver()
        self._history     = ConflictHistory(history_len)

    def process(
        self,
        state:  AggregationState,
        report: ValidationReport,
    ) -> ConflictSummary:
        conflicts = self._detector.detect(state, report)
        conflicts = [self._classifier.classify(c, state) for c in conflicts]
        conflicts = self._resolver.resolve(conflicts, state)

        # Tally
        total    = len(conflicts)
        critical = sum(1 for c in conflicts if c.severity is ConflictSeverity.CRITICAL)
        high     = sum(1 for c in conflicts if c.severity is ConflictSeverity.HIGH)
        medium   = sum(1 for c in conflicts if c.severity is ConflictSeverity.MEDIUM)
        low      = sum(1 for c in conflicts if c.severity is ConflictSeverity.LOW)
        resolved = sum(1 for c in conflicts if c.resolved)

        summary = ConflictSummary(
            bar_index=state.bar_index,
            total=total,
            critical=critical,
            high=high,
            medium=medium,
            low=low,
            resolved=resolved,
            unresolved=total - resolved,
            conflicts=conflicts,
        )
        self._history.append(summary)
        return summary

    @property
    def history(self) -> ConflictHistory:
        return self._history
