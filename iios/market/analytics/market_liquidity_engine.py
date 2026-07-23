"""
market_liquidity_engine.py — iios.market.analytics
====================================================
Liquidity analysis sub-engine.

C12 Market Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

from typing import Any, Dict, List

from .constants import LiquidityCondition, TrendDirection
from .market_analytics_context import MarketAnalyticsContext
from .market_analytics_response import LiquidityResult


class MarketLiquidityEngine:
    """
    Stateless liquidity analysis sub-engine.

    Reads ``volume_data`` from *request_data*. Expects optional keys:
    ``volumes: List[float]``, ``avg_volume: float``, ``turnover: float``,
    ``spread_bps: float``.
    """

    def run(
        self,
        context:      MarketAnalyticsContext,
        request_data: Dict[str, Any],
    ) -> LiquidityResult:
        vd: Dict[str, Any] = request_data.get("volume_data", {})

        volumes:        List[float] = vd.get("volumes", [])
        provided_avg:   float       = float(vd.get("avg_volume",   0.0))
        turnover:       float       = float(vd.get("turnover",     0.0))
        spread_bps:     float       = float(vd.get("spread_bps",   10.0))  # basis points

        if volumes:
            current_vol = volumes[-1]
            hist_vols   = volumes[:-1]
            hist_avg    = sum(hist_vols) / len(hist_vols) if hist_vols else current_vol
            vol_ratio   = current_vol / hist_avg if hist_avg > 0 else 1.0
            avg_vol     = hist_avg
        elif provided_avg > 0:
            vol_ratio = 1.0
            avg_vol   = provided_avg
        else:
            vol_ratio = 1.0
            avg_vol   = 0.0

        vol_trend = self._trend(volumes)

        # Turnover ratio normalised: 1.0 = typical
        turnover_ratio = turnover / max(avg_vol, 1.0) if avg_vol > 0 else 1.0

        # Spread: lower = more liquid (spread in bps, 10 bps = typical)
        spread_score = max(0.0, min(100.0, (1.0 - spread_bps / 100.0) * 100.0))

        liquidity_score = min(100.0, max(0.0, (
            vol_ratio  * 40.0 +
            spread_score * 0.4 +
            min(turnover_ratio, 2.0) * 20.0 / 2.0
        )))

        condition = self._condition(liquidity_score)

        return LiquidityResult(
            condition          = condition,
            liquidity_score    = liquidity_score,
            avg_volume         = avg_vol,
            volume_trend       = vol_trend,
            turnover_ratio     = turnover_ratio,
            bid_ask_spread_est = spread_bps / 10_000.0,
            description        = (
                f"Liquidity: {condition.value} "
                f"(score={liquidity_score:.1f}, vol_ratio={vol_ratio:.2f})"
            ),
        )

    @staticmethod
    def _trend(volumes: List[float]) -> TrendDirection:
        if len(volumes) < 5:
            return TrendDirection.SIDEWAYS
        recent = volumes[-5:]
        if recent[-1] > recent[0] * 1.1:
            return TrendDirection.UP
        if recent[-1] < recent[0] * 0.9:
            return TrendDirection.DOWN
        return TrendDirection.SIDEWAYS

    @staticmethod
    def _condition(score: float) -> LiquidityCondition:
        if score >= 80.0:
            return LiquidityCondition.ABUNDANT
        if score >= 60.0:
            return LiquidityCondition.ADEQUATE
        if score >= 40.0:
            return LiquidityCondition.ADEQUATE
        if score >= 20.0:
            return LiquidityCondition.TIGHT
        return LiquidityCondition.STRESSED
