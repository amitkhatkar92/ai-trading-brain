"""
market_regime_engine.py — iios.market.analytics
================================================
Regime detection sub-engine.

C12 Market Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

from typing import Any, Dict, List

from .constants import (
    DEFAULT_LONG_LOOKBACK,
    DEFAULT_MEDIUM_LOOKBACK,
    DEFAULT_SHORT_LOOKBACK,
    BREADTH_HEALTHY,
    MarketRegime,
    TrendDirection,
    TrendStrength,
)
from .market_analytics_context import MarketAnalyticsContext
from .market_analytics_response import RegimeResult
from .market_regime_classifier import classify_regime


class MarketRegimeEngine:
    """
    Stateless regime detection sub-engine.

    Reads ``index_prices`` from *request_data* dict.  Returns a
    :class:`~.market_analytics_response.RegimeResult`.
    """

    def run(
        self,
        context:      MarketAnalyticsContext,
        request_data: Dict[str, Any],
    ) -> RegimeResult:
        index_prices: Dict[str, List[float]] = request_data.get("index_prices", {})
        breadth_data: Dict[str, Any]         = request_data.get("breadth_data", {})

        # Aggregate all price series into one combined series (simple mean)
        combined: List[float] = self._aggregate(index_prices)

        # Compute breadth healthy flag from breadth data if available
        breadth_healthy = self._is_breadth_healthy(breadth_data)

        if not combined:
            return RegimeResult(
                regime             = MarketRegime.UNKNOWN,
                confidence         = 0.0,
                trend_direction    = TrendDirection.SIDEWAYS,
                trend_strength     = TrendStrength.NONE,
                regime_duration_bars = 0,
                description        = "No price data available",
            )

        regime, confidence, trend, strength = classify_regime(
            prices          = combined,
            breadth_healthy = breadth_healthy,
            short_window    = context.short_lookback,
            medium_window   = context.medium_lookback,
            long_window     = context.long_lookback,
        )

        description = (
            f"{regime.value} regime detected with {confidence:.0%} confidence; "
            f"trend={trend.value}, strength={strength.value}"
        )

        return RegimeResult(
            regime             = regime,
            confidence         = confidence,
            trend_direction    = trend,
            trend_strength     = strength,
            regime_duration_bars = self._estimate_duration(combined, context.short_lookback),
            description        = description,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _aggregate(index_prices: Dict[str, List[float]]) -> List[float]:
        """Average all index series to one combined series."""
        if not index_prices:
            return []
        series = [v for v in index_prices.values() if v]
        if not series:
            return []
        min_len = min(len(s) for s in series)
        if min_len == 0:
            return []
        trimmed = [s[-min_len:] for s in series]
        return [sum(bar) / len(bar) for bar in zip(*trimmed)]

    @staticmethod
    def _is_breadth_healthy(breadth_data: Dict[str, Any]) -> bool:
        ratio = breadth_data.get("advance_decline_ratio", BREADTH_HEALTHY)
        return float(ratio) >= BREADTH_HEALTHY

    @staticmethod
    def _estimate_duration(prices: List[float], window: int) -> int:
        """Estimate consecutive bars in the current trend."""
        if len(prices) < 2:
            return 0
        direction = 1 if prices[-1] >= prices[-2] else -1
        count = 0
        for i in range(len(prices) - 1, 0, -1):
            bar_dir = 1 if prices[i] >= prices[i - 1] else -1
            if bar_dir == direction:
                count += 1
            else:
                break
        return count
