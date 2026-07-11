"""iios/investment/market/volatility/strategy_permissions.py
Static permission tables: which strategies are allowed in which vol regime.

Returned as Dict[StrategyType.value, bool].
"""
from __future__ import annotations

from typing import Dict

from iios.investment.market.volatility.models import StrategyType, VolatilityRegimeType


# Table: regime → set of permitted strategy type values
_PERMITTED: Dict[VolatilityRegimeType, set[str]] = {
    VolatilityRegimeType.VERY_LOW: {
        StrategyType.MEAN_REVERSION.value,
        StrategyType.SWING_TRADING.value,
        StrategyType.POSITION_TRADING.value,
        StrategyType.RETEST.value,
        StrategyType.PORTFOLIO_REBALANCING.value,
    },
    VolatilityRegimeType.COMPRESSION: {
        StrategyType.MEAN_REVERSION.value,
        StrategyType.SWING_TRADING.value,
        StrategyType.POSITION_TRADING.value,
        StrategyType.RETEST.value,
        StrategyType.BREAKOUT.value,         # compression → breakout setup
        StrategyType.PORTFOLIO_REBALANCING.value,
    },
    VolatilityRegimeType.LOW: {
        StrategyType.MEAN_REVERSION.value,
        StrategyType.SWING_TRADING.value,
        StrategyType.POSITION_TRADING.value,
        StrategyType.RETEST.value,
        StrategyType.MOMENTUM.value,
        StrategyType.PORTFOLIO_REBALANCING.value,
    },
    VolatilityRegimeType.NORMAL: {
        StrategyType.MOMENTUM.value,
        StrategyType.BREAKOUT.value,
        StrategyType.RETEST.value,
        StrategyType.MEAN_REVERSION.value,
        StrategyType.SWING_TRADING.value,
        StrategyType.POSITION_TRADING.value,
        StrategyType.OPTIONS.value,
        StrategyType.PORTFOLIO_REBALANCING.value,
    },
    VolatilityRegimeType.ELEVATED: {
        StrategyType.MOMENTUM.value,
        StrategyType.BREAKOUT.value,
        StrategyType.RETEST.value,
        StrategyType.SWING_TRADING.value,
        StrategyType.POSITION_TRADING.value,
        StrategyType.OPTIONS.value,
        StrategyType.PORTFOLIO_REBALANCING.value,
    },
    VolatilityRegimeType.EXPANSION: {
        StrategyType.MOMENTUM.value,
        StrategyType.BREAKOUT.value,
        StrategyType.SWING_TRADING.value,
        StrategyType.OPTIONS.value,
        StrategyType.POSITION_TRADING.value,
    },
    VolatilityRegimeType.HIGH: {
        StrategyType.MOMENTUM.value,
        StrategyType.BREAKOUT.value,
        StrategyType.OPTIONS.value,
    },
    VolatilityRegimeType.EXTREME: {
        StrategyType.OPTIONS.value,
    },
    VolatilityRegimeType.SHOCK: {
        StrategyType.OPTIONS.value,
    },
    VolatilityRegimeType.RECOVERY: {
        StrategyType.SWING_TRADING.value,
        StrategyType.RETEST.value,
        StrategyType.MEAN_REVERSION.value,
        StrategyType.POSITION_TRADING.value,
        StrategyType.BREAKOUT.value,
        StrategyType.OPTIONS.value,
    },
    VolatilityRegimeType.UNKNOWN: {
        StrategyType.SWING_TRADING.value,
        StrategyType.RETEST.value,
        StrategyType.POSITION_TRADING.value,
    },
}

# Recommended strategies per regime (subset of permitted)
_RECOMMENDED: Dict[VolatilityRegimeType, list[str]] = {
    VolatilityRegimeType.VERY_LOW:    [StrategyType.MEAN_REVERSION.value, StrategyType.SWING_TRADING.value],
    VolatilityRegimeType.COMPRESSION: [StrategyType.BREAKOUT.value, StrategyType.RETEST.value],
    VolatilityRegimeType.LOW:         [StrategyType.SWING_TRADING.value, StrategyType.MEAN_REVERSION.value],
    VolatilityRegimeType.NORMAL:      [StrategyType.MOMENTUM.value, StrategyType.BREAKOUT.value, StrategyType.SWING_TRADING.value],
    VolatilityRegimeType.ELEVATED:    [StrategyType.MOMENTUM.value, StrategyType.BREAKOUT.value],
    VolatilityRegimeType.EXPANSION:   [StrategyType.MOMENTUM.value, StrategyType.BREAKOUT.value],
    VolatilityRegimeType.HIGH:        [StrategyType.MOMENTUM.value, StrategyType.OPTIONS.value],
    VolatilityRegimeType.EXTREME:     [StrategyType.OPTIONS.value],
    VolatilityRegimeType.SHOCK:       [StrategyType.OPTIONS.value],
    VolatilityRegimeType.RECOVERY:    [StrategyType.RETEST.value, StrategyType.SWING_TRADING.value],
    VolatilityRegimeType.UNKNOWN:     [StrategyType.SWING_TRADING.value],
}

_ALL_STRATEGIES = [s.value for s in StrategyType]


def get_permissions(regime: VolatilityRegimeType) -> Dict[str, bool]:
    permitted = _PERMITTED.get(regime, set())
    return {s: (s in permitted) for s in _ALL_STRATEGIES}


def get_recommended(regime: VolatilityRegimeType) -> list[str]:
    return list(_RECOMMENDED.get(regime, []))


def get_restricted(regime: VolatilityRegimeType) -> list[str]:
    permitted = _PERMITTED.get(regime, set())
    return [s for s in _ALL_STRATEGIES if s not in permitted]
