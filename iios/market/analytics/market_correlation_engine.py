"""
market_correlation_engine.py — iios.market.analytics
=====================================================
Correlation analysis sub-engine.

C12 Market Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

from typing import Any, Dict, List

from .market_analytics_context import MarketAnalyticsContext
from .market_analytics_response import CorrelationResult


def _correlation(x: List[float], y: List[float]) -> float:
    n = min(len(x), len(y))
    if n < 2:
        return 0.0
    xs, ys = x[-n:], y[-n:]
    mx = sum(xs) / n
    my = sum(ys) / n
    cov  = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    sx   = sum((a - mx) ** 2 for a in xs) ** 0.5
    sy   = sum((b - my) ** 2 for b in ys) ** 0.5
    denom = sx * sy
    return cov / denom if denom != 0 else 0.0


class MarketCorrelationEngine:
    """
    Stateless correlation analysis sub-engine.

    Computes pairwise correlations between all provided price series
    and summarises them into a :class:`~.market_analytics_response.CorrelationResult`.
    """

    def run(
        self,
        context:      MarketAnalyticsContext,
        request_data: Dict[str, Any],
    ) -> CorrelationResult:
        index_prices: Dict[str, List[float]] = request_data.get("index_prices", {})
        global_data:  Dict[str, Any]         = request_data.get("global_data", {})

        series = {k: v for k, v in index_prices.items() if v}
        if len(series) < 2:
            return CorrelationResult(
                exchange_correlation    = 0.0,
                global_correlation      = 0.0,
                sector_avg_correlation  = 0.0,
                correlation_regime      = "insufficient_data",
                dispersion_score        = 0.0,
            )

        keys   = list(series.keys())
        corrs: List[float] = []
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                corrs.append(_correlation(series[keys[i]], series[keys[j]]))

        avg_corr    = sum(corrs) / len(corrs) if corrs else 0.0
        global_corr = float(global_data.get("global_correlation", avg_corr))

        dispersion  = max(corrs) - min(corrs) if len(corrs) > 1 else 0.0
        regime      = self._regime(avg_corr)

        return CorrelationResult(
            exchange_correlation    = avg_corr,
            global_correlation      = global_corr,
            sector_avg_correlation  = avg_corr,
            correlation_regime      = regime,
            dispersion_score        = dispersion,
        )

    @staticmethod
    def _regime(avg_corr: float) -> str:
        if avg_corr >= 0.8:
            return "high_correlation"
        if avg_corr >= 0.5:
            return "moderate_correlation"
        if avg_corr >= 0.2:
            return "low_correlation"
        if avg_corr >= -0.2:
            return "uncorrelated"
        return "negative_correlation"
