"""iios/investment/market/volatility/risk_score.py
Stateless functions for computing individual risk component scores (0-1).
"""
from __future__ import annotations

from iios.investment.market.volatility.models import (
    BehaviourSnapshot,
    VolatilityBehaviour,
    VolatilityRegimeType,
    VolatilityState,
)


def execution_risk_score(
    state: VolatilityState,
    behaviour: BehaviourSnapshot,
    regime: VolatilityRegimeType,
) -> float:
    """
    Execution risk: how difficult it is to fill orders at expected prices.
    Driven by normalised vol and expansion behaviour.
    """
    base = state.normalized_volatility * 0.60
    expansion_add = behaviour.expansion_score * 0.25
    shock_add = 0.15 if regime in (VolatilityRegimeType.SHOCK, VolatilityRegimeType.EXTREME) else 0.0
    return min(1.0, base + expansion_add + shock_add)


def gap_risk_score(
    state: VolatilityState,
    behaviour: BehaviourSnapshot,
) -> float:
    """
    Gap risk: probability and magnitude of price gaps, especially overnight.
    Driven by persistence and range ratio.
    """
    persistence_part = state.volatility_persistence * 0.40
    range_part = min(0.40, (state.bar_range_ratio - 1.0) / 4.0) if state.bar_range_ratio > 1.0 else 0.0
    vol_part = state.normalized_volatility * 0.20
    return min(1.0, persistence_part + range_part + vol_part)


def overnight_risk_score(
    state: VolatilityState,
    regime: VolatilityRegimeType,
) -> float:
    """
    Overnight risk: potential adverse move between session close and next open.
    """
    base = state.normalized_volatility * 0.50
    if regime in (VolatilityRegimeType.SHOCK, VolatilityRegimeType.EXTREME):
        base = min(0.90, base + 0.40)
    elif regime == VolatilityRegimeType.HIGH:
        base = min(0.80, base + 0.20)
    elif regime in (VolatilityRegimeType.RECOVERY,):
        base = min(0.70, base + 0.10)
    return min(1.0, base)


def portfolio_risk_score(
    state: VolatilityState,
    regime: VolatilityRegimeType,
) -> float:
    """Portfolio risk: vol contribution to aggregate portfolio variance."""
    base = state.normalized_volatility * 0.60
    regime_add = {
        VolatilityRegimeType.SHOCK:    0.35,
        VolatilityRegimeType.EXTREME:  0.25,
        VolatilityRegimeType.HIGH:     0.15,
        VolatilityRegimeType.ELEVATED: 0.05,
    }.get(regime, 0.0)
    return min(1.0, base + regime_add)


def market_risk_score(
    state: VolatilityState,
    behaviour: BehaviourSnapshot,
) -> float:
    """Overall market risk from a volatility perspective."""
    base = state.normalized_volatility * 0.70
    accel_add = max(0.0, behaviour.acceleration) * 0.20
    persist_add = state.volatility_persistence * 0.10
    return min(1.0, base + accel_add + persist_add)


def strategy_risk_score(
    state: VolatilityState,
    regime: VolatilityRegimeType,
    behaviour: BehaviourSnapshot,
) -> float:
    """
    Generic strategy risk (independent of strategy type).
    Strategy-specific risk is handled by the strategy mapper.
    """
    base = state.normalized_volatility * 0.50
    instability = (1.0 - state.volatility_stability) * 0.30
    expansion_add = behaviour.expansion_score * 0.20
    return min(1.0, base + instability + expansion_add)
