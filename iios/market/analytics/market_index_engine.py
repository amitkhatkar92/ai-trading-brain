"""
market_index_engine.py — iios.market.analytics
================================================
Index analysis sub-engine.

C12 Market Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

from typing import Any, Dict, List

from .market_analytics_context import MarketAnalyticsContext
from .market_analytics_response import IndexResult
from .constants import TrendDirection


def _sma(prices: List[float], window: int) -> float:
    if not prices:
        return 0.0
    n = min(window, len(prices))
    return sum(prices[-n:]) / n


class MarketIndexEngine:
    """
    Stateless index analysis sub-engine.

    Reads ``index_prices`` from *request_data*. Returns one
    :class:`~.market_analytics_response.IndexResult` per index.
    """

    def run(
        self,
        context:      MarketAnalyticsContext,
        request_data: Dict[str, Any],
    ) -> List[IndexResult]:
        index_prices: Dict[str, List[float]] = request_data.get("index_prices", {})
        results = []
        for name, prices in index_prices.items():
            if not prices:
                continue
            results.append(self._analyse(name, prices, context))
        return results

    def _analyse(
        self,
        name:    str,
        prices:  List[float],
        context: MarketAnalyticsContext,
    ) -> IndexResult:
        current   = prices[-1]
        ma_short  = _sma(prices, context.short_lookback)
        ma_medium = _sma(prices, context.medium_lookback)
        ma_long   = _sma(prices, context.long_lookback)

        above_s = current > ma_short
        above_m = current > ma_medium
        above_l = current > ma_long
        bullish = sum([above_s, above_m, above_l])

        change_pct = (current - prices[0]) / prices[0] if len(prices) > 1 and prices[0] != 0 else 0.0

        if bullish == 3:
            trend = TrendDirection.STRONG_UP
        elif bullish == 2:
            trend = TrendDirection.UP
        elif bullish == 0:
            trend = TrendDirection.STRONG_DOWN
        elif bullish == 1:
            trend = TrendDirection.DOWN
        else:
            trend = TrendDirection.SIDEWAYS

        strength_score = min(100.0, max(0.0, bullish / 3.0 * 100.0))

        return IndexResult(
            index_name      = name,
            current_price   = current,
            change_pct      = change_pct,
            trend           = trend,
            ma_short        = ma_short,
            ma_medium       = ma_medium,
            ma_long         = ma_long,
            above_ma_short  = above_s,
            above_ma_medium = above_m,
            above_ma_long   = above_l,
            strength_score  = strength_score,
        )
