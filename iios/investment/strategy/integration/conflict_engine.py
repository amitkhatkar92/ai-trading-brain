"""iios/investment/strategy/integration/conflict_engine.py
ConflictEngine: detects, classifies, resolves, and persists conflicts.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.strategy.integration.aggregation_state import StrategyAggregationState
from iios.investment.strategy.integration.conflict_classifier import (
    Conflict,
    ConflictClassifier,
)
from iios.investment.strategy.integration.conflict_detector import ConflictDetector
from iios.investment.strategy.integration.conflict_history import ConflictHistory
from iios.investment.strategy.integration.conflict_resolution import ConflictResolver
from iios.investment.strategy.integration.integration_constants import ConflictSeverity

_log = logging.getLogger(__name__)


class ConflictEngine:
    """
    Orchestrates the full conflict lifecycle for one validation pass:
    1. Detect conflicts (via rules + detector)
    2. Classify into Conflict objects
    3. Attempt resolution
    4. Persist to history
    5. Return active (unresolved) conflicts
    """

    def __init__(
        self,
        detector:   Optional[ConflictDetector]  = None,
        classifier: Optional[ConflictClassifier] = None,
        resolver:   Optional[ConflictResolver]   = None,
        history:    Optional[ConflictHistory]    = None,
    ) -> None:
        self._detector   = detector   or ConflictDetector()
        self._classifier = classifier or ConflictClassifier()
        self._resolver   = resolver   or ConflictResolver()
        self._history    = history    or ConflictHistory()

    def process(
        self,
        state: StrategyAggregationState,
    ) -> Tuple[List[Conflict], List[Conflict]]:
        """
        Run full conflict pipeline for a strategy.
        Returns (resolved_conflicts, unresolved_conflicts).
        """
        failures  = self._detector.detect(state)
        conflicts = self._classifier.classify(state.strategy_id, failures)

        if not conflicts:
            return [], []

        resolved, unresolved = self._resolver.resolve_all(conflicts, state)

        self._history.record_all(conflicts)

        if unresolved:
            _log.warning(
                "Strategy %s has %d unresolved conflict(s): %s",
                state.strategy_id,
                len(unresolved),
                [c.conflict_type.value for c in unresolved],
            )

        return resolved, unresolved

    def active_conflicts(self, strategy_id: str) -> List[Conflict]:
        return self._history.active(strategy_id)

    def history_for(self, strategy_id: str) -> List[Conflict]:
        return self._history.for_strategy(strategy_id)

    def has_blocking_conflict(self, strategy_id: str) -> bool:
        return any(
            c.severity == ConflictSeverity.CRITICAL and not c.is_resolved
            for c in self._history.active(strategy_id)
        )

    def stats(self, strategy_id: Optional[str] = None) -> Dict[str, Any]:
        return {
            "total_recorded": self._history.count(),
            "active":         self._history.active_count(strategy_id),
            "resolved":       len(self._history.resolved(strategy_id)),
        }
