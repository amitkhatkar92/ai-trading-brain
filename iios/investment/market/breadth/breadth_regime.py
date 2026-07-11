"""iios/investment/market/breadth/breadth_regime.py
Data builders and helpers for the breadth regime layer.
"""
from __future__ import annotations

from iios.investment.market.breadth.models import (
    BreadthRegimeSnapshot,
    BreadthRegimeType,
)


def build_regime_snapshot(
    regime: BreadthRegimeType,
    confidence: float,
    duration_bars: int,
    previous_regime: BreadthRegimeType | None,
    transition_probability: float,
    regime_score: float,
) -> BreadthRegimeSnapshot:
    return BreadthRegimeSnapshot(
        regime=regime,
        confidence=max(0.0, min(1.0, confidence)),
        duration_bars=max(0, duration_bars),
        previous_regime=previous_regime,
        transition_probability=max(0.0, min(1.0, transition_probability)),
        regime_score=max(0.0, min(100.0, regime_score)),
    )


# Severity ordering for transition magnitude
_SEVERITY: dict[BreadthRegimeType, int] = {
    BreadthRegimeType.VERY_WEAK_PARTICIPATION: 0,
    BreadthRegimeType.BROAD_SELLOFF:           1,
    BreadthRegimeType.NARROW_SELLOFF:          2,
    BreadthRegimeType.WEAK_PARTICIPATION:      3,
    BreadthRegimeType.NEUTRAL:                 4,
    BreadthRegimeType.NARROW_RALLY:            5,
    BreadthRegimeType.HEALTHY_PARTICIPATION:   6,
    BreadthRegimeType.STRONG_PARTICIPATION:    7,
    BreadthRegimeType.BROAD_RALLY:             8,
    BreadthRegimeType.UNKNOWN:                 4,
}


def regime_severity(regime: BreadthRegimeType) -> int:
    return _SEVERITY.get(regime, 4)
