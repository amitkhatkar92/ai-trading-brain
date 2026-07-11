"""iios/investment/market/correlation/correlation_regime.py
Regime data builders and helpers.
"""
from __future__ import annotations

from iios.investment.market.correlation.models import (
    CorrelationRegimeSnapshot,
    CorrelationRegimeType,
)


def build_regime_snapshot(
    regime: CorrelationRegimeType,
    confidence: float,
    duration_bars: int,
    previous_regime: CorrelationRegimeType | None,
    avg_correlation: float,
    transition_probability: float,
    regime_score: float,
) -> CorrelationRegimeSnapshot:
    return CorrelationRegimeSnapshot(
        regime=regime,
        confidence=max(0.0, min(1.0, confidence)),
        duration_bars=max(0, duration_bars),
        previous_regime=previous_regime,
        avg_correlation=max(-1.0, min(1.0, avg_correlation)),
        transition_probability=max(0.0, min(1.0, transition_probability)),
        regime_score=max(0.0, min(100.0, regime_score)),
    )


# Severity ordering for transition magnitude
_SEVERITY: dict[CorrelationRegimeType, int] = {
    CorrelationRegimeType.INDEPENDENT:           0,
    CorrelationRegimeType.WEAKLY_CORRELATED:     1,
    CorrelationRegimeType.RISK_ON:               2,
    CorrelationRegimeType.MODERATELY_CORRELATED: 3,
    CorrelationRegimeType.RISK_OFF:              4,
    CorrelationRegimeType.HIGHLY_CORRELATED:     5,
    CorrelationRegimeType.CORRELATION_BREAKDOWN: 6,
    CorrelationRegimeType.FLIGHT_TO_SAFETY:      7,
    CorrelationRegimeType.INVERSE_CORRELATION:   2,
    CorrelationRegimeType.UNKNOWN:               3,
}


def regime_severity(regime: CorrelationRegimeType) -> int:
    return _SEVERITY.get(regime, 3)
