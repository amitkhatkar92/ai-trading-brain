"""iios/investment/market/integration/conflict_classifier.py
Assigns deterministic severity to conflicts based on context.
Can override or confirm severity from ConsistencyRules.
"""
from __future__ import annotations

from iios.investment.market.integration.aggregation_state import AggregationState
from iios.investment.market.integration.models import Conflict, ConflictSeverity, ConflictType

# Context-based severity adjustments: (ConflictType → upgrade_condition)
# If condition is True, severity is elevated to next level.
_UPGRADES = {
    ConflictType.TREND_REGIME: lambda s: s.market_regime == "crisis",
    ConflictType.OPPORTUNITY_RISK: lambda s: (
        s.market_regime == "crisis" or s.volatility_regime == "extreme"
    ),
}


class ConflictClassifier:
    """Re-classifies conflict severity using state context."""

    def classify(self, conflict: Conflict, state: AggregationState) -> Conflict:
        upgrade_fn = _UPGRADES.get(conflict.conflict_type)
        if upgrade_fn:
            try:
                if upgrade_fn(state):
                    conflict.severity = _upgrade(conflict.severity)
            except Exception:
                pass
        return conflict


_ORDER = [
    ConflictSeverity.LOW,
    ConflictSeverity.MEDIUM,
    ConflictSeverity.HIGH,
    ConflictSeverity.CRITICAL,
]


def _upgrade(severity: ConflictSeverity) -> ConflictSeverity:
    idx = _ORDER.index(severity)
    return _ORDER[min(idx + 1, len(_ORDER) - 1)]
