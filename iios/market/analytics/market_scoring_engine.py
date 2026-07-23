"""
market_scoring_engine.py — iios.market.analytics
==================================================
Composite market scoring engine.

C12 Market Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

from typing import Optional

from .constants import REGIME_BASE_SCORES, VOLATILITY_SCORE_PENALTY
from .market_analytics_response import (
    BreadthResult,
    LiquidityResult,
    MarketScores,
    MomentumResult,
    RegimeResult,
    VolatilityResult,
)


def _clamp(val: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, val))


class MarketScoringEngine:
    """
    Stateless scoring engine.

    Aggregates domain results into a
    :class:`~.market_analytics_response.MarketScores` object.
    """

    def run(
        self,
        regime:     Optional[RegimeResult]     = None,
        breadth:    Optional[BreadthResult]    = None,
        volatility: Optional[VolatilityResult] = None,
        momentum:   Optional[MomentumResult]   = None,
        liquidity:  Optional[LiquidityResult]  = None,
    ) -> MarketScores:
        # ------------------------------------------------------------------
        # Regime contribution
        # ------------------------------------------------------------------
        regime_confidence = 0.5
        trend_score       = 50.0
        if regime is not None:
            base             = REGIME_BASE_SCORES.get(regime.regime, 50.0)
            regime_confidence = regime.confidence
            trend_score      = _clamp(
                base * regime.confidence + 50.0 * (1.0 - regime.confidence)
            )

        # ------------------------------------------------------------------
        # Breadth
        # ------------------------------------------------------------------
        breadth_score = breadth.breadth_score if breadth is not None else 50.0

        # ------------------------------------------------------------------
        # Volatility
        # ------------------------------------------------------------------
        vol_score = 75.0
        if volatility is not None:
            vol_score = volatility.vol_score
            penalty   = VOLATILITY_SCORE_PENALTY.get(volatility.vol_regime, 0.0)
            vol_score = _clamp(vol_score - penalty)

        # ------------------------------------------------------------------
        # Momentum
        # ------------------------------------------------------------------
        momentum_score = momentum.momentum_score if momentum is not None else 50.0

        # ------------------------------------------------------------------
        # Liquidity
        # ------------------------------------------------------------------
        liquidity_score = liquidity.liquidity_score if liquidity is not None else 60.0

        # ------------------------------------------------------------------
        # Sector strength (proxy — no direct input here, use breadth)
        # ------------------------------------------------------------------
        sector_strength_score = _clamp(
            breadth_score * 0.6 + trend_score * 0.4
        )

        # ------------------------------------------------------------------
        # Health = weighted combination of all signals
        # ------------------------------------------------------------------
        health_score = _clamp(
            trend_score        * 0.25 +
            breadth_score      * 0.20 +
            vol_score          * 0.20 +
            momentum_score     * 0.15 +
            liquidity_score    * 0.20
        )

        # ------------------------------------------------------------------
        # Overall = health + mild momentum boost
        # ------------------------------------------------------------------
        overall_score = _clamp(
            health_score       * 0.70 +
            momentum_score     * 0.15 +
            sector_strength_score * 0.15
        )

        return MarketScores(
            health_score          = health_score,
            regime_confidence     = regime_confidence,
            sector_strength_score = sector_strength_score,
            trend_strength_score  = trend_score,
            breadth_score         = breadth_score,
            liquidity_score       = liquidity_score,
            volatility_score      = vol_score,
            momentum_score        = momentum_score,
            overall_score         = overall_score,
        )
