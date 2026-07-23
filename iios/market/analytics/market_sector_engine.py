"""
market_sector_engine.py — iios.market.analytics
================================================
Sector strength analysis sub-engine.

C12 Market Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .constants import DEFAULT_SHORT_LOOKBACK, TrendDirection
from .market_analytics_context import MarketAnalyticsContext
from .market_analytics_response import SectorResult


def _pct_change(prices: List[float]) -> float:
    if len(prices) < 2 or prices[0] == 0.0:
        return 0.0
    return (prices[-1] - prices[0]) / prices[0]


def _momentum(prices: List[float], window: int) -> float:
    """Rate of change over last *window* bars (normalised)."""
    if len(prices) < window + 1:
        return 0.0
    base = prices[-(window + 1)]
    if base == 0.0:
        return 0.0
    return (prices[-1] - base) / base


def _volume_ratio(volumes: List[float]) -> float:
    if len(volumes) < 2:
        return 1.0
    avg_hist = sum(volumes[:-1]) / len(volumes[:-1]) if volumes[:-1] else 1.0
    return volumes[-1] / avg_hist if avg_hist != 0.0 else 1.0


class MarketSectorEngine:
    """
    Stateless sector analysis sub-engine.

    Expects ``sector_data`` dict mapping sector names → sub-dict with
    optional keys ``prices: List[float]`` and ``volumes: List[float]``.
    Also reads the overall market ``index_prices`` for relative-strength.
    """

    def run(
        self,
        context:      MarketAnalyticsContext,
        request_data: Dict[str, Any],
    ) -> List[SectorResult]:
        sector_data:  Dict[str, Any]          = request_data.get("sector_data", {})
        index_prices: Dict[str, List[float]]  = request_data.get("index_prices", {})

        if not sector_data:
            return []

        # Market benchmark performance (mean of all indices)
        market_perf = self._market_performance(index_prices)

        results: List[SectorResult] = []
        for name, data in sector_data.items():
            if not isinstance(data, dict):
                continue
            prices:  List[float] = data.get("prices", [])
            volumes: List[float] = data.get("volumes", [])
            perf    = _pct_change(prices)
            rs      = (perf - market_perf) if market_perf != 0.0 else perf
            mom     = _momentum(prices, context.short_lookback)
            vr      = _volume_ratio(volumes)
            trend   = self._trend(prices, context.short_lookback, context.long_lookback)
            results.append(SectorResult(
                sector_name       = name,
                performance       = perf,
                relative_strength = rs,
                momentum_score    = mom,
                volume_ratio      = vr,
                rank              = 0,          # filled after sorting
                trend             = trend,
            ))

        # Rank by performance descending
        results.sort(key=lambda s: s.performance, reverse=True)
        ranked = [
            SectorResult(
                sector_name       = s.sector_name,
                performance       = s.performance,
                relative_strength = s.relative_strength,
                momentum_score    = s.momentum_score,
                volume_ratio      = s.volume_ratio,
                rank              = i + 1,
                trend             = s.trend,
            )
            for i, s in enumerate(results)
        ]
        return ranked

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _market_performance(index_prices: Dict[str, List[float]]) -> float:
        perfs = [_pct_change(p) for p in index_prices.values() if len(p) >= 2]
        return sum(perfs) / len(perfs) if perfs else 0.0

    @staticmethod
    def _trend(prices: List[float], short: int, long: int) -> TrendDirection:
        if len(prices) < 2:
            return TrendDirection.SIDEWAYS
        current   = prices[-1]
        sma_short = sum(prices[-short:]) / min(short, len(prices))
        sma_long  = sum(prices[-long:])  / min(long,  len(prices))
        if current > sma_short and current > sma_long:
            return TrendDirection.UP
        if current < sma_short and current < sma_long:
            return TrendDirection.DOWN
        return TrendDirection.SIDEWAYS
