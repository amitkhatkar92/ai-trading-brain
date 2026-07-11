"""iios/investment/market/integration/market_confidence.py
Computes overall market intelligence confidence (0-100).

Confidence represents how much the downstream IIOS components should trust
this snapshot. It is NOT a buy/sell signal.
"""
from __future__ import annotations

from iios.investment.market.integration.aggregation_state import AggregationState
from iios.investment.market.integration.models import (
    ConflictSeverity,
    ConflictSummary,
    QualityScore,
)

_CRITICAL_PENALTY   = 25.0
_HIGH_PENALTY       = 12.0
_MEDIUM_PENALTY     = 5.0
_LOW_PENALTY        = 2.0
_UNRESOLVED_FACTOR  = 1.5    # unresolved conflicts hurt more

_VOL_PENALTY_EXTREME  = 15.0
_VOL_PENALTY_ELEVATED = 5.0

_MISSING_PENALTY_PER_ENGINE = 8.0
_MAX_MISSING_PENALTY        = 40.0


class MarketConfidenceEngine:
    """Computes a single confidence score from quality + conflict + state signals."""

    def compute(
        self,
        state:     AggregationState,
        quality:   QualityScore,
        conflicts: ConflictSummary,
    ) -> float:
        # Start from quality overall
        base = quality.overall

        # Penalty for unresolved conflicts
        for c in conflicts.conflicts:
            if not c.resolved:
                if c.severity is ConflictSeverity.CRITICAL:
                    base -= _CRITICAL_PENALTY * _UNRESOLVED_FACTOR
                elif c.severity is ConflictSeverity.HIGH:
                    base -= _HIGH_PENALTY * _UNRESOLVED_FACTOR
                elif c.severity is ConflictSeverity.MEDIUM:
                    base -= _MEDIUM_PENALTY * _UNRESOLVED_FACTOR
                else:
                    base -= _LOW_PENALTY * _UNRESOLVED_FACTOR
            else:
                # Resolved conflicts add minor penalty (noise existed)
                if c.severity is ConflictSeverity.CRITICAL:
                    base -= _CRITICAL_PENALTY * 0.3
                elif c.severity is ConflictSeverity.HIGH:
                    base -= _HIGH_PENALTY * 0.3

        # Volatility regime penalty
        if state.volatility_regime == "extreme":
            base -= _VOL_PENALTY_EXTREME
        elif state.volatility_regime == "elevated":
            base -= _VOL_PENALTY_ELEVATED

        # Missing engine penalty
        missing_count = len(state.missing_engines)
        missing_pen   = min(missing_count * _MISSING_PENALTY_PER_ENGINE, _MAX_MISSING_PENALTY)
        base -= missing_pen

        return round(min(max(base, 0.0), 100.0), 2)
