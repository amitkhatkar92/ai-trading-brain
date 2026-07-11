"""iios/investment/market/volatility/volatility_regime.py
Data builders and snapshot helpers for the volatility regime layer.
"""
from __future__ import annotations

from iios.investment.market.volatility.models import (
    VolatilityRegimeSnapshot,
    VolatilityRegimeType,
    VolatilityTransitionType,
)


def build_regime_snapshot(
    regime: VolatilityRegimeType,
    confidence: float,
    duration_bars: int,
    previous_regime: VolatilityRegimeType | None,
    transition_type: VolatilityTransitionType,
    transition_probability: float,
    regime_score: float,
) -> VolatilityRegimeSnapshot:
    """Construct a VolatilityRegimeSnapshot with all fields validated."""
    return VolatilityRegimeSnapshot(
        regime=regime,
        confidence=max(0.0, min(1.0, confidence)),
        duration_bars=max(0, duration_bars),
        previous_regime=previous_regime,
        transition_type=transition_type,
        transition_probability=max(0.0, min(1.0, transition_probability)),
        regime_score=max(0.0, min(100.0, regime_score)),
    )


# ── Regime ordering (for transition direction) ───────────────────────────────

_SEVERITY_ORDER = {
    VolatilityRegimeType.VERY_LOW:    0,
    VolatilityRegimeType.LOW:         1,
    VolatilityRegimeType.COMPRESSION: 2,
    VolatilityRegimeType.NORMAL:      3,
    VolatilityRegimeType.ELEVATED:    4,
    VolatilityRegimeType.EXPANSION:   5,
    VolatilityRegimeType.HIGH:        6,
    VolatilityRegimeType.EXTREME:     7,
    VolatilityRegimeType.SHOCK:       8,
    VolatilityRegimeType.RECOVERY:    5,  # mid-level
    VolatilityRegimeType.UNKNOWN:     3,
}


def regime_severity(regime: VolatilityRegimeType) -> int:
    return _SEVERITY_ORDER.get(regime, 3)


def infer_transition_type(
    current: VolatilityRegimeType,
    previous: VolatilityRegimeType | None,
    relative_vol: float,
) -> VolatilityTransitionType:
    """Infer transition direction from regime change + relative vol."""
    if previous is None or current == previous:
        if relative_vol > 1.3:
            return VolatilityTransitionType.SPIKING
        if relative_vol < 0.75:
            return VolatilityTransitionType.COLLAPSING
        if relative_vol > 1.05:
            return VolatilityTransitionType.RISING
        if relative_vol < 0.95:
            return VolatilityTransitionType.FALLING
        return VolatilityTransitionType.STABLE

    cur_sev = regime_severity(current)
    prev_sev = regime_severity(previous)
    delta = cur_sev - prev_sev

    if relative_vol > 1.5 or (delta >= 2):
        return VolatilityTransitionType.SPIKING
    if relative_vol < 0.6 or (delta <= -2):
        return VolatilityTransitionType.COLLAPSING
    if delta > 0:
        return VolatilityTransitionType.RISING
    if delta < 0:
        return VolatilityTransitionType.FALLING
    return VolatilityTransitionType.STABLE
