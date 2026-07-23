"""
market_pattern_engine.py — iios.market.analytics
==================================================
Technical pattern detection sub-engine.

C12 Market Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .constants import ForecastDirection, PatternType
from .market_analytics_context import MarketAnalyticsContext
from .market_analytics_response import PatternResult


def _combined(index_prices: Dict[str, List[float]]) -> List[float]:
    series = [v for v in index_prices.values() if v]
    if not series:
        return []
    min_len = min(len(s) for s in series)
    trimmed = [s[-min_len:] for s in series]
    return [sum(bar) / len(bar) for bar in zip(*trimmed)]


class MarketPatternEngine:
    """
    Stateless pattern detection sub-engine.

    Detects simple price patterns from aggregated index prices:
    - Ascending/descending channel
    - Double top/bottom (approximate)
    - Breakout / breakdown
    """

    _MIN_BARS = 10

    def run(
        self,
        context:      MarketAnalyticsContext,
        request_data: Dict[str, Any],
    ) -> Optional[PatternResult]:
        index_prices: Dict[str, List[float]] = request_data.get("index_prices", {})
        prices = _combined(index_prices)

        if len(prices) < self._MIN_BARS:
            return None

        short_n = min(context.short_lookback, len(prices))
        recent  = prices[-short_n:]

        # Support and resistance from recent range
        support    = min(recent)
        resistance = max(recent)
        current    = prices[-1]

        # Breakout detection
        lookback_n = min(context.medium_lookback, len(prices) - 1)
        prior_high = max(prices[-(lookback_n + 1):-1])
        prior_low  = min(prices[-(lookback_n + 1):-1])

        if current > prior_high * 1.01:
            pattern_type = PatternType.BREAKOUT
            confidence   = min(0.80, (current / prior_high - 1.0) * 10.0 + 0.50)
            target       = current + (current - prior_low) * 0.5
        elif current < prior_low * 0.99:
            pattern_type = PatternType.BREAKDOWN
            confidence   = min(0.80, (prior_low / current - 1.0) * 10.0 + 0.50)
            target       = current - (prior_high - current) * 0.5
        else:
            # Check ascending / descending channel
            slope = self._slope(recent)
            if slope > 0.0005:
                pattern_type = PatternType.CONTINUATION
                confidence   = 0.50
                target       = resistance + (resistance - support) * 0.3
            elif slope < -0.0005:
                pattern_type = PatternType.BREAKDOWN
                confidence   = 0.50
                target       = support - (resistance - support) * 0.3
            else:
                pattern_type = PatternType.CONSOLIDATION
                confidence   = 0.40
                target       = (support + resistance) / 2.0

        return PatternResult(
            pattern_type     = pattern_type,
            confidence       = confidence,
            support_level    = support,
            resistance_level = resistance,
            target_price     = target,
            description      = (
                f"Pattern: {pattern_type.value} "
                f"(conf={confidence:.0%}, support={support:.2f}, resist={resistance:.2f})"
            ),
        )

    @staticmethod
    def _slope(prices: List[float]) -> float:
        n = len(prices)
        if n < 2:
            return 0.0
        x_mean = (n - 1) / 2.0
        y_mean = sum(prices) / n
        num    = sum((i - x_mean) * (p - y_mean) for i, p in enumerate(prices))
        den    = sum((i - x_mean) ** 2 for i in range(n))
        if den == 0:
            return 0.0
        raw = num / den
        return raw / y_mean if y_mean != 0 else 0.0
