"""
market_volatility_engine.py — iios.market.analytics
=====================================================
Volatility analysis sub-engine.

C12 Market Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import math
from typing import Any, Dict, List

from .constants import (
    DEFAULT_VOLATILITY_WINDOW,
    VOLATILITY_EXTREME,
    VOLATILITY_HIGH,
    VOLATILITY_LOW,
    TrendDirection,
    VolatilityRegime,
)
from .market_analytics_context import MarketAnalyticsContext
from .market_analytics_response import VolatilityResult


def _returns(prices: List[float]) -> List[float]:
    result = []
    for i in range(1, len(prices)):
        if prices[i - 1] != 0:
            result.append((prices[i] - prices[i - 1]) / prices[i - 1])
    return result


def _std(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    var  = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
    return math.sqrt(var)


def _percentile(values: List[float], target: float) -> float:
    """Return the percentile rank of *target* in *values* (0–1)."""
    if not values:
        return 0.5
    below = sum(1 for v in values if v <= target)
    return below / len(values)


class MarketVolatilityEngine:
    """
    Stateless volatility analysis sub-engine.

    Uses ``index_prices`` and optionally ``volatility_data`` (for
    implied vol) from *request_data*.
    """

    _TRADING_DAYS = 252

    def run(
        self,
        context:      MarketAnalyticsContext,
        request_data: Dict[str, Any],
    ) -> VolatilityResult:
        index_prices: Dict[str, List[float]] = request_data.get("index_prices", {})
        vol_data:     Dict[str, Any]         = request_data.get("volatility_data", {})

        prices = self._combined(index_prices)

        if len(prices) < 2:
            return self._neutral_result(vol_data)

        rets    = _returns(prices)
        window  = context.volatility_window
        recent  = rets[-window:] if len(rets) >= window else rets

        daily_std = _std(recent)
        ann_vol   = daily_std * math.sqrt(self._TRADING_DAYS)
        pctile    = _percentile(
            [_std(rets[max(0, i - window):i]) * math.sqrt(self._TRADING_DAYS)
             for i in range(window, len(rets) + 1)],
            ann_vol,
        )

        implied_vol = float(vol_data.get("implied_vol", ann_vol))
        regime      = self._classify(ann_vol)
        vol_trend   = self._vol_trend(rets, window)
        vol_score   = self._score(regime)

        return VolatilityResult(
            realised_vol    = daily_std,
            implied_vol     = implied_vol,
            vol_regime      = regime,
            vol_percentile  = pctile,
            vol_trend       = vol_trend,
            vol_score       = vol_score,
            description     = (
                f"Annualised vol={ann_vol:.2%} ({regime.value}); "
                f"implied={implied_vol:.2%}"
            ),
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _combined(index_prices: Dict[str, List[float]]) -> List[float]:
        series = [v for v in index_prices.values() if v]
        if not series:
            return []
        min_len = min(len(s) for s in series)
        trimmed = [s[-min_len:] for s in series]
        return [sum(bar) / len(bar) for bar in zip(*trimmed)]

    @staticmethod
    def _classify(ann_vol: float) -> VolatilityRegime:
        if ann_vol >= VOLATILITY_EXTREME:
            return VolatilityRegime.EXTREME
        if ann_vol >= VOLATILITY_HIGH:
            return VolatilityRegime.HIGH
        if ann_vol >= 0.15:
            return VolatilityRegime.ELEVATED
        if ann_vol >= VOLATILITY_LOW:
            return VolatilityRegime.NORMAL
        return VolatilityRegime.LOW

    @staticmethod
    def _score(regime: VolatilityRegime) -> float:
        """Higher vol → lower score (vol is a risk)."""
        mapping = {
            VolatilityRegime.EXTREME:  10.0,
            VolatilityRegime.HIGH:     30.0,
            VolatilityRegime.ELEVATED: 50.0,
            VolatilityRegime.NORMAL:   75.0,
            VolatilityRegime.LOW:      90.0,
        }
        return mapping.get(regime, 50.0)

    @staticmethod
    def _vol_trend(rets: List[float], window: int) -> TrendDirection:
        if len(rets) < window * 2:
            return TrendDirection.SIDEWAYS
        recent_vol = _std(rets[-window:])
        prior_vol  = _std(rets[-window * 2:-window])
        if recent_vol > prior_vol * 1.1:
            return TrendDirection.UP
        if recent_vol < prior_vol * 0.9:
            return TrendDirection.DOWN
        return TrendDirection.SIDEWAYS

    @staticmethod
    def _neutral_result(vol_data: Dict[str, Any]) -> VolatilityResult:
        return VolatilityResult(
            realised_vol    = 0.0,
            implied_vol     = float(vol_data.get("implied_vol", 0.0)),
            vol_regime      = VolatilityRegime.NORMAL,
            vol_percentile  = 0.5,
            vol_trend       = TrendDirection.SIDEWAYS,
            vol_score       = 75.0,
            description     = "No price data — neutral vol defaults",
        )
