"""
market_regime_classifier.py — iios.market.analytics
=====================================================
Pure regime classification logic (no I/O, fully deterministic).

C12 Market Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

from typing import List, Tuple

from .constants import (
    MarketRegime,
    TrendDirection,
    TrendStrength,
)


def _mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _sma(prices: List[float], window: int) -> float:
    """Simple moving average over the last *window* elements."""
    if len(prices) < window:
        return _mean(prices)
    return _mean(prices[-window:])


def _linear_slope(values: List[float]) -> float:
    """Normalised slope of a simple OLS line through the last N values."""
    n = len(values)
    if n < 2:
        return 0.0
    x_mean = (n - 1) / 2.0
    y_mean = _mean(values)
    numerator   = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    if denominator == 0.0:
        return 0.0
    raw_slope = numerator / denominator
    # Normalise by mean to get pct-per-bar
    return raw_slope / y_mean if y_mean != 0 else 0.0


def classify_trend_direction(prices: List[float], short: int, long: int) -> TrendDirection:
    if len(prices) < 2:
        return TrendDirection.SIDEWAYS
    current   = prices[-1]
    sma_short = _sma(prices, short)
    sma_long  = _sma(prices, long)
    if current > sma_short > sma_long:
        return TrendDirection.STRONG_UP
    if current > sma_long:
        return TrendDirection.UP
    if current < sma_short < sma_long:
        return TrendDirection.STRONG_DOWN
    if current < sma_long:
        return TrendDirection.DOWN
    return TrendDirection.SIDEWAYS


def classify_trend_strength(prices: List[float], window: int = 20) -> TrendStrength:
    if len(prices) < 2:
        return TrendStrength.NEUTRAL
    slope = abs(_linear_slope(prices[-window:]))
    if slope > 0.005:
        return TrendStrength.VERY_STRONG
    if slope > 0.003:
        return TrendStrength.STRONG
    if slope > 0.001:
        return TrendStrength.MODERATE
    if slope > 0.0002:
        return TrendStrength.WEAK
    return TrendStrength.NONE


def classify_regime(
    prices:           List[float],
    breadth_healthy:  bool,
    short_window:     int = 20,
    medium_window:    int = 50,
    long_window:      int = 200,
) -> Tuple[MarketRegime, float, TrendDirection, TrendStrength]:
    """
    Returns (regime, confidence, trend_direction, trend_strength).

    Confidence is a heuristic in [0.0, 1.0].
    """
    if not prices:
        return MarketRegime.UNKNOWN, 0.0, TrendDirection.SIDEWAYS, TrendStrength.NONE

    trend     = classify_trend_direction(prices, short_window, long_window)
    strength  = classify_trend_strength(prices, medium_window)
    current   = prices[-1]
    sma_short = _sma(prices, short_window)
    sma_med   = _sma(prices, medium_window)
    sma_long  = _sma(prices, long_window)

    above_short  = current > sma_short
    above_med    = current > sma_med
    above_long   = current > sma_long

    # Regime logic
    bullish_ma   = sum([above_short, above_med, above_long])
    bearish_ma   = 3 - bullish_ma

    if bullish_ma == 3 and breadth_healthy and strength in (TrendStrength.STRONG, TrendStrength.VERY_STRONG):
        regime     = MarketRegime.STRONG_BULL
        confidence = 0.85
    elif bullish_ma >= 2:
        regime     = MarketRegime.BULL
        confidence = 0.65 + 0.1 * (bullish_ma - 2)
    elif bearish_ma == 3 and not breadth_healthy and strength in (TrendStrength.STRONG, TrendStrength.VERY_STRONG):
        regime     = MarketRegime.STRONG_BEAR
        confidence = 0.85
    elif bearish_ma >= 2:
        regime     = MarketRegime.BEAR
        confidence = 0.65 + 0.1 * (bearish_ma - 2)
    else:
        regime     = MarketRegime.NEUTRAL
        confidence = 0.50

    # Breadth penalty when inconsistent
    if regime in (MarketRegime.BULL, MarketRegime.STRONG_BULL) and not breadth_healthy:
        confidence *= 0.75
    if regime in (MarketRegime.BEAR, MarketRegime.STRONG_BEAR) and breadth_healthy:
        confidence *= 0.75

    return regime, min(confidence, 1.0), trend, strength
