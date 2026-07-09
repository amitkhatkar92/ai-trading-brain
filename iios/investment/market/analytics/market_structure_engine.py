"""iios/investment/market/analytics/market_structure_engine.py
Coordinates all structural analyzers into a single MarketStructure result.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any

from iios.investment.market.market_state.market_snapshot import MarketSnapshot
from iios.investment.market.analytics.trend_analyzer import TrendAnalyzer, TrendAnalysis
from iios.investment.market.analytics.breadth_analyzer import BreadthAnalyzer, BreadthAnalysis
from iios.investment.market.analytics.volatility_analyzer import (
    VolatilityAnalyzer,
    VolatilityAnalysis,
)
from iios.investment.market.analytics.liquidity_analyzer import (
    LiquidityAnalyzer,
    LiquidityAnalysis,
)
from iios.investment.market.analytics.correlation_analyzer import (
    CorrelationAnalyzer,
    CorrelationAnalysis,
)


@dataclass
class MarketStructure:
    """Composite result from all structural analyzers."""

    trend:        TrendAnalysis       = field(default_factory=TrendAnalysis)
    breadth:      BreadthAnalysis     = field(default_factory=BreadthAnalysis)
    volatility:   VolatilityAnalysis  = field(default_factory=VolatilityAnalysis)
    liquidity:    LiquidityAnalysis   = field(default_factory=LiquidityAnalysis)
    correlation:  CorrelationAnalysis = field(default_factory=CorrelationAnalysis)
    health_score: float               = 50.0
    quality_score: float              = 50.0
    metadata:     dict[str, Any]      = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "trend":         self.trend.to_dict(),
            "breadth":       self.breadth.to_dict(),
            "volatility":    self.volatility.to_dict(),
            "liquidity":     self.liquidity.to_dict(),
            "correlation":   self.correlation.to_dict(),
            "health_score":  self.health_score,
            "quality_score": self.quality_score,
            "metadata":      self.metadata,
        }


class MarketStructureEngine:
    """
    Coordinates TrendAnalyzer, BreadthAnalyzer, VolatilityAnalyzer,
    LiquidityAnalyzer, CorrelationAnalyzer into a MarketStructure.

    Side effects:
      - Writes trend, strength, volatility, liquidity, breadth back onto
        the snapshot so the regime engine sees them immediately.
    """

    def __init__(
        self,
        trend_analyzer:       TrendAnalyzer       | None = None,
        breadth_analyzer:     BreadthAnalyzer     | None = None,
        volatility_analyzer:  VolatilityAnalyzer  | None = None,
        liquidity_analyzer:   LiquidityAnalyzer   | None = None,
        correlation_analyzer: CorrelationAnalyzer | None = None,
    ) -> None:
        self._lock        = threading.RLock()
        self._trend       = trend_analyzer       or TrendAnalyzer()
        self._breadth     = breadth_analyzer     or BreadthAnalyzer()
        self._volatility  = volatility_analyzer  or VolatilityAnalyzer()
        self._liquidity   = liquidity_analyzer   or LiquidityAnalyzer()
        self._correlation = correlation_analyzer or CorrelationAnalyzer()

    def analyze(
        self,
        snapshot:       MarketSnapshot,
        price_history:  list[float]              | None = None,
        return_history: list[float]              | None = None,
        return_series:  dict[str, list[float]]  | None = None,
    ) -> MarketStructure:
        # ── Trend ──────────────────────────────────────────────────────────────
        prices   = list(snapshot.prices.values())
        if price_history:
            prices = price_history + prices
        trend_r  = self._trend.analyze(prices or [1.0])

        # ── Breadth ────────────────────────────────────────────────────────────
        breadth_r = self._breadth.analyze(
            snapshot.advances, snapshot.declines, snapshot.unchanged
        )

        # ── Volatility ─────────────────────────────────────────────────────────
        returns = list(snapshot.changes.values())
        if return_history:
            returns = return_history + returns
        vol_r = self._volatility.analyze(returns or [0.0])

        # ── Liquidity ──────────────────────────────────────────────────────────
        liq_r = self._liquidity.analyze(
            snapshot.volumes,
            snapshot.spreads,
        )

        # ── Correlation ────────────────────────────────────────────────────────
        corr_r = self._correlation.analyze(return_series or {})

        # ── Composite scores ───────────────────────────────────────────────────
        health  = self._compute_health(breadth_r, vol_r, liq_r)
        quality = self._compute_quality(trend_r, breadth_r, liq_r)

        # Write back into snapshot so regime engine sees current dimensions
        snapshot.trend      = trend_r.direction
        snapshot.strength   = trend_r.strength
        snapshot.volatility = vol_r.level
        snapshot.liquidity  = liq_r.level
        snapshot.breadth    = breadth_r.condition

        return MarketStructure(
            trend         = trend_r,
            breadth       = breadth_r,
            volatility    = vol_r,
            liquidity     = liq_r,
            correlation   = corr_r,
            health_score  = health,
            quality_score = quality,
        )

    # ── score helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _compute_health(
        breadth:    BreadthAnalysis,
        volatility: VolatilityAnalysis,
        liquidity:  LiquidityAnalysis,
    ) -> float:
        # High vol is unhealthy: bonus from LOW volatility
        vol_bonus = max(0.0, 100.0 - volatility.score)
        return round(
            breadth.score   * 0.40
            + liquidity.score * 0.40
            + vol_bonus       * 0.20,
            2,
        )

    @staticmethod
    def _compute_quality(
        trend:    TrendAnalysis,
        breadth:  BreadthAnalysis,
        liquidity: LiquidityAnalysis,
    ) -> float:
        return round(
            trend.score    * 0.40
            + breadth.score  * 0.30
            + liquidity.score * 0.30,
            2,
        )
