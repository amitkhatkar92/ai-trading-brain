"""
market_momentum_engine.py — iios.market.analytics
===================================================
Momentum analysis sub-engine (RSI, ROC).

C12 Market Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

from typing import Any, Dict, List

from .constants import DEFAULT_MOMENTUM_WINDOW, TrendDirection
from .market_analytics_context import MarketAnalyticsContext
from .market_analytics_response import MomentumResult


def _rsi(prices: List[float], period: int = 14) -> float:
    """Wilder RSI in [0, 100]."""
    if len(prices) < period + 1:
        return 50.0
    deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    gains  = [max(d, 0.0) for d in deltas[-period:]]
    losses = [abs(min(d, 0.0)) for d in deltas[-period:]]
    avg_g  = sum(gains)  / period
    avg_l  = sum(losses) / period
    if avg_l == 0.0:
        return 100.0
    rs = avg_g / avg_l
    return 100.0 - 100.0 / (1.0 + rs)


def _roc(prices: List[float], period: int = 14) -> float:
    """Rate of change over *period* bars."""
    if len(prices) < period + 1:
        return 0.0
    base = prices[-(period + 1)]
    if base == 0.0:
        return 0.0
    return (prices[-1] - base) / base


class MarketMomentumEngine:
    """
    Stateless momentum analysis sub-engine.

    Uses aggregated index price series.
    """

    def run(
        self,
        context:      MarketAnalyticsContext,
        request_data: Dict[str, Any],
    ) -> MomentumResult:
        index_prices: Dict[str, List[float]] = request_data.get("index_prices", {})

        combined = self._combined(index_prices)
        period   = context.momentum_window

        if len(combined) < 2:
            return self._neutral()

        rsi_val  = _rsi(combined, period)
        roc_val  = _roc(combined, period)

        momentum_score = min(100.0, max(0.0,
            rsi_val * 0.6 + (roc_val * 500.0 + 50.0) * 0.4
        ))

        overbought = rsi_val >= 70.0
        oversold   = rsi_val <= 30.0
        divergence = False  # stub — no divergence detection without separate price/indicator series

        if roc_val > 0.01:
            trend = TrendDirection.UP
        elif roc_val < -0.01:
            trend = TrendDirection.DOWN
        else:
            trend = TrendDirection.SIDEWAYS

        return MomentumResult(
            rsi            = rsi_val,
            roc            = roc_val,
            momentum_score = momentum_score,
            trend          = trend,
            overbought     = overbought,
            oversold       = oversold,
            divergence     = divergence,
            description    = (
                f"RSI={rsi_val:.1f}, ROC={roc_val:.3f} "
                f"({'overbought' if overbought else 'oversold' if oversold else 'neutral'})"
            ),
        )

    @staticmethod
    def _combined(index_prices: Dict[str, List[float]]) -> List[float]:
        series = [v for v in index_prices.values() if v]
        if not series:
            return []
        min_len = min(len(s) for s in series)
        trimmed = [s[-min_len:] for s in series]
        return [sum(bar) / len(bar) for bar in zip(*trimmed)]

    @staticmethod
    def _neutral() -> MomentumResult:
        return MomentumResult(
            rsi=50.0, roc=0.0, momentum_score=50.0,
            trend=TrendDirection.SIDEWAYS,
            overbought=False, oversold=False, divergence=False,
            description="No price data — neutral momentum defaults",
        )
