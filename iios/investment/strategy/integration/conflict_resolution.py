"""iios/investment/strategy/integration/conflict_resolution.py
Resolution logic for classified Conflict objects.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.strategy.integration.integration_constants import (
    ConflictSeverity,
    IntelligenceSource,
    ResolutionStrategy,
)
from iios.investment.strategy.integration.aggregation_state import (
    IntelligenceUpdate,
    StrategyAggregationState,
)
from iios.investment.strategy.integration.conflict_classifier import Conflict


class ConflictResolver:
    """
    Attempts to resolve each Conflict using its assigned ResolutionStrategy.
    Conflicts that cannot be resolved deterministically are marked ESCALATE.
    """

    def resolve(
        self,
        conflict: Conflict,
        state:    StrategyAggregationState,
    ) -> Tuple[bool, str]:
        """
        Returns (resolved, notes).
        resolved=True means the conflict was automatically resolved.
        """
        latest  = state.all_latest()
        upd_a   = latest.get(conflict.source_a)
        upd_b   = latest.get(conflict.source_b)

        if upd_a is None or upd_b is None:
            conflict.resolve("Resolved: one source no longer present.")
            return True, "Source no longer present."

        strategy = conflict.resolution_strategy

        if strategy == ResolutionStrategy.HIGHER_CONFIDENCE:
            return self._resolve_higher_confidence(conflict, upd_a, upd_b)
        if strategy == ResolutionStrategy.MOST_RECENT:
            return self._resolve_most_recent(conflict, upd_a, upd_b)
        if strategy == ResolutionStrategy.RISK_FIRST:
            return self._resolve_risk_first(conflict, upd_a, upd_b)
        if strategy == ResolutionStrategy.CONSERVATIVE:
            return self._resolve_conservative(conflict, upd_a, upd_b)
        # ESCALATE
        return False, "Requires human review — escalated."

    @staticmethod
    def _resolve_higher_confidence(
        conflict: Conflict,
        a: IntelligenceUpdate,
        b: IntelligenceUpdate,
    ) -> Tuple[bool, str]:
        winner = "source_a" if a.confidence >= b.confidence else "source_b"
        notes  = (
            f"Resolved via HIGHER_CONFIDENCE: {winner} wins "
            f"({a.confidence:.0f}% vs {b.confidence:.0f}%)."
        )
        conflict.resolve(notes)
        return True, notes

    @staticmethod
    def _resolve_most_recent(
        conflict: Conflict,
        a: IntelligenceUpdate,
        b: IntelligenceUpdate,
    ) -> Tuple[bool, str]:
        winner = "source_a" if a.timestamp >= b.timestamp else "source_b"
        notes  = f"Resolved via MOST_RECENT: {winner} wins."
        conflict.resolve(notes)
        return True, notes

    @staticmethod
    def _resolve_risk_first(
        conflict: Conflict,
        a: IntelligenceUpdate,
        b: IntelligenceUpdate,
    ) -> Tuple[bool, str]:
        risk_is_a = a.source == IntelligenceSource.RISK
        winner    = "source_a (risk)" if risk_is_a else "source_b (risk)"
        notes     = f"Resolved via RISK_FIRST: {winner} takes precedence."
        conflict.resolve(notes)
        return True, notes

    @staticmethod
    def _resolve_conservative(
        conflict: Conflict,
        a: IntelligenceUpdate,
        b: IntelligenceUpdate,
    ) -> Tuple[bool, str]:
        # Conservative: prefer the lower score / more restrictive signal
        score_a = float(a.payload.get("score", 50.0))
        score_b = float(b.payload.get("score", 50.0))
        winner  = "source_a" if score_a <= score_b else "source_b"
        notes   = f"Resolved via CONSERVATIVE: {winner} selected (lower score preferred)."
        conflict.resolve(notes)
        return True, notes

    def resolve_all(
        self,
        conflicts: List[Conflict],
        state:     StrategyAggregationState,
    ) -> Tuple[List[Conflict], List[Conflict]]:
        """Return (resolved, unresolved) lists."""
        resolved:   List[Conflict] = []
        unresolved: List[Conflict] = []
        for c in conflicts:
            ok, _ = self.resolve(c, state)
            (resolved if ok else unresolved).append(c)
        return resolved, unresolved
