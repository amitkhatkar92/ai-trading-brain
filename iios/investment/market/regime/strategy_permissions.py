"""iios/investment/market/regime/strategy_permissions.py
Strategy type constants and per-regime strategy permissions.
"""
from __future__ import annotations

from typing import ClassVar, Dict, List

from iios.investment.market.regime.models import RegimeType, StrategyCompatibility


class StrategyType:
    """Strategy type string constants used across IIOS."""

    TREND_FOLLOWING = "trend_following"
    MEAN_REVERSION  = "mean_reversion"
    BREAKOUT        = "breakout"
    MOMENTUM        = "momentum"
    COUNTER_TREND   = "counter_trend"
    RANGE_BOUND     = "range_bound"
    VOLATILITY      = "volatility"
    SCALPING        = "scalping"
    SWING           = "swing"
    POSITION        = "position"
    ARBITRAGE       = "arbitrage"
    DEFENSIVE       = "defensive"

    ALL: ClassVar[List[str]] = [
        TREND_FOLLOWING,
        MEAN_REVERSION,
        BREAKOUT,
        MOMENTUM,
        COUNTER_TREND,
        RANGE_BOUND,
        VOLATILITY,
        SCALPING,
        SWING,
        POSITION,
        ARBITRAGE,
        DEFENSIVE,
    ]


REGIME_PERMISSIONS: Dict[RegimeType, StrategyCompatibility] = {
    RegimeType.BULL: StrategyCompatibility(
        regime=RegimeType.BULL,
        allowed=[
            StrategyType.TREND_FOLLOWING, StrategyType.BREAKOUT,
            StrategyType.MOMENTUM, StrategyType.SWING, StrategyType.POSITION,
        ],
        discouraged=[StrategyType.MEAN_REVERSION, StrategyType.COUNTER_TREND],
        blocked=[StrategyType.DEFENSIVE],
        preferred_timeframes=["1d", "4h"],
        preferred_risk_profile="aggressive",
        max_position_size_pct=1.0,
    ),
    RegimeType.BEAR: StrategyCompatibility(
        regime=RegimeType.BEAR,
        allowed=[
            StrategyType.COUNTER_TREND, StrategyType.DEFENSIVE,
            StrategyType.MEAN_REVERSION,
        ],
        discouraged=[
            StrategyType.TREND_FOLLOWING, StrategyType.BREAKOUT,
            StrategyType.MOMENTUM,
        ],
        blocked=[StrategyType.POSITION],
        preferred_timeframes=["1d", "4h"],
        preferred_risk_profile="conservative",
        max_position_size_pct=0.5,
    ),
    RegimeType.SIDEWAYS: StrategyCompatibility(
        regime=RegimeType.SIDEWAYS,
        allowed=[
            StrategyType.RANGE_BOUND, StrategyType.MEAN_REVERSION,
            StrategyType.SCALPING,
        ],
        discouraged=[StrategyType.TREND_FOLLOWING, StrategyType.POSITION],
        blocked=[],
        preferred_timeframes=["1h", "4h"],
        preferred_risk_profile="moderate",
        max_position_size_pct=0.75,
    ),
    RegimeType.TRENDING: StrategyCompatibility(
        regime=RegimeType.TRENDING,
        allowed=[
            StrategyType.TREND_FOLLOWING, StrategyType.MOMENTUM,
            StrategyType.BREAKOUT, StrategyType.SWING,
        ],
        discouraged=[StrategyType.MEAN_REVERSION, StrategyType.RANGE_BOUND],
        blocked=[],
        preferred_timeframes=["1d", "4h"],
        preferred_risk_profile="moderate",
        max_position_size_pct=1.0,
    ),
    RegimeType.RANGING: StrategyCompatibility(
        regime=RegimeType.RANGING,
        allowed=[
            StrategyType.RANGE_BOUND, StrategyType.MEAN_REVERSION,
            StrategyType.SCALPING,
        ],
        discouraged=[StrategyType.TREND_FOLLOWING, StrategyType.BREAKOUT],
        blocked=[],
        preferred_timeframes=["1h", "15m"],
        preferred_risk_profile="moderate",
        max_position_size_pct=0.75,
    ),
    RegimeType.EXPANSION: StrategyCompatibility(
        regime=RegimeType.EXPANSION,
        allowed=[
            StrategyType.BREAKOUT, StrategyType.TREND_FOLLOWING,
            StrategyType.MOMENTUM, StrategyType.VOLATILITY,
        ],
        discouraged=[
            StrategyType.MEAN_REVERSION, StrategyType.RANGE_BOUND,
            StrategyType.SCALPING,
        ],
        blocked=[],
        preferred_timeframes=["4h", "1d"],
        preferred_risk_profile="aggressive",
        max_position_size_pct=1.0,
    ),
    RegimeType.CONTRACTION: StrategyCompatibility(
        regime=RegimeType.CONTRACTION,
        allowed=[StrategyType.RANGE_BOUND, StrategyType.SCALPING],
        discouraged=[
            StrategyType.TREND_FOLLOWING, StrategyType.BREAKOUT,
            StrategyType.MOMENTUM,
        ],
        blocked=[],
        preferred_timeframes=["15m", "1h"],
        preferred_risk_profile="conservative",
        max_position_size_pct=0.5,
    ),
    RegimeType.RECOVERY: StrategyCompatibility(
        regime=RegimeType.RECOVERY,
        allowed=[
            StrategyType.TREND_FOLLOWING, StrategyType.MEAN_REVERSION,
            StrategyType.SWING,
        ],
        discouraged=[StrategyType.COUNTER_TREND],
        blocked=[],
        preferred_timeframes=["1d"],
        preferred_risk_profile="moderate",
        max_position_size_pct=0.75,
    ),
    RegimeType.DISTRIBUTION: StrategyCompatibility(
        regime=RegimeType.DISTRIBUTION,
        allowed=[
            StrategyType.COUNTER_TREND, StrategyType.DEFENSIVE,
            StrategyType.MEAN_REVERSION,
        ],
        discouraged=[StrategyType.TREND_FOLLOWING, StrategyType.BREAKOUT],
        blocked=[StrategyType.POSITION],
        preferred_timeframes=["1d", "4h"],
        preferred_risk_profile="conservative",
        max_position_size_pct=0.5,
    ),
    RegimeType.ACCUMULATION: StrategyCompatibility(
        regime=RegimeType.ACCUMULATION,
        allowed=[
            StrategyType.MEAN_REVERSION, StrategyType.RANGE_BOUND,
            StrategyType.SWING,
        ],
        discouraged=[StrategyType.COUNTER_TREND, StrategyType.SCALPING],
        blocked=[],
        preferred_timeframes=["1d"],
        preferred_risk_profile="moderate",
        max_position_size_pct=0.75,
    ),
    RegimeType.VOLATILE: StrategyCompatibility(
        regime=RegimeType.VOLATILE,
        allowed=[StrategyType.VOLATILITY, StrategyType.SCALPING],
        discouraged=[StrategyType.POSITION, StrategyType.SWING],
        blocked=[],
        preferred_timeframes=["15m", "1h"],
        preferred_risk_profile="conservative",
        max_position_size_pct=0.5,
    ),
    RegimeType.CALM: StrategyCompatibility(
        regime=RegimeType.CALM,
        allowed=[
            StrategyType.TREND_FOLLOWING, StrategyType.BREAKOUT,
            StrategyType.POSITION, StrategyType.SWING,
        ],
        discouraged=[StrategyType.VOLATILITY, StrategyType.SCALPING],
        blocked=[],
        preferred_timeframes=["1d", "4h"],
        preferred_risk_profile="moderate",
        max_position_size_pct=1.0,
    ),
    RegimeType.TRANSITION: StrategyCompatibility(
        regime=RegimeType.TRANSITION,
        allowed=[StrategyType.DEFENSIVE],
        discouraged=[
            StrategyType.TREND_FOLLOWING, StrategyType.BREAKOUT,
            StrategyType.MOMENTUM,
        ],
        blocked=[StrategyType.POSITION],
        preferred_timeframes=["1d"],
        preferred_risk_profile="conservative",
        max_position_size_pct=0.25,
    ),
    RegimeType.CRISIS: StrategyCompatibility(
        regime=RegimeType.CRISIS,
        allowed=[StrategyType.DEFENSIVE],
        discouraged=[],
        blocked=[
            StrategyType.TREND_FOLLOWING, StrategyType.BREAKOUT,
            StrategyType.MOMENTUM, StrategyType.SWING, StrategyType.POSITION,
            StrategyType.SCALPING, StrategyType.MEAN_REVERSION,
            StrategyType.RANGE_BOUND, StrategyType.COUNTER_TREND,
            StrategyType.VOLATILITY, StrategyType.ARBITRAGE,
        ],
        preferred_timeframes=["1d"],
        preferred_risk_profile="defensive",
        max_position_size_pct=0.0,
    ),
    RegimeType.UNKNOWN: StrategyCompatibility(
        regime=RegimeType.UNKNOWN,
        allowed=[],
        discouraged=[],
        blocked=[
            StrategyType.TREND_FOLLOWING, StrategyType.BREAKOUT,
            StrategyType.MOMENTUM, StrategyType.SWING, StrategyType.POSITION,
            StrategyType.SCALPING, StrategyType.MEAN_REVERSION,
            StrategyType.RANGE_BOUND, StrategyType.COUNTER_TREND,
            StrategyType.VOLATILITY, StrategyType.ARBITRAGE,
            StrategyType.DEFENSIVE,
        ],
        preferred_timeframes=[],
        preferred_risk_profile="none",
        max_position_size_pct=0.0,
    ),
}
