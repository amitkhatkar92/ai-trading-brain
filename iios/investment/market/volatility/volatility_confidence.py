"""iios/investment/market/volatility/volatility_confidence.py
Stateful VolatilityConfidenceCalculator: wraps confidence_score.compute_confidence
and exposes a consistent interface for the main engine.
"""
from __future__ import annotations

from typing import Dict

from iios.investment.market.volatility.models import (
    BehaviourSnapshot,
    ConfidenceScore,
    VolatilityEstimate,
    VolatilityRegimeSnapshot,
    VolatilityState,
)
from iios.investment.market.volatility.confidence_score import compute_confidence


class VolatilityConfidenceCalculator:
    """Delegates to compute_confidence; stateless wrapper for DI."""

    def calculate(
        self,
        state: VolatilityState,
        regime_snap: VolatilityRegimeSnapshot,
        behaviour: BehaviourSnapshot,
        estimates: "Dict[str, VolatilityEstimate]",
    ) -> ConfidenceScore:
        return compute_confidence(state, regime_snap, behaviour, estimates)
