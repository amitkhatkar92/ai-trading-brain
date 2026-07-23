"""
market_analytics_manager.py — iios.market.analytics
=====================================================
Pipeline orchestrator — coordinates all sub-engines.

C12 Market Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple

from .market_analytics_context import MarketAnalyticsContext
from .market_analytics_request import MarketAnalyticsRequest
from .market_analytics_response import (
    BreadthResult,
    CorrelationResult,
    ForecastResult,
    IndexResult,
    LiquidityResult,
    MarketAnalyticsReport,
    MarketScores,
    MomentumResult,
    PatternResult,
    RegimeResult,
    RotationResult,
    SectorResult,
    SentimentResult,
    VolatilityResult,
)
from .market_breadth_engine   import MarketBreadthEngine
from .market_correlation_engine import MarketCorrelationEngine
from .market_forecasting_engine import MarketForecastingEngine
from .market_index_engine     import MarketIndexEngine
from .market_intelligence_engine import (
    _key_opportunities,
    _key_risks,
    generate_intelligence_summary,
)
from .market_liquidity_engine import MarketLiquidityEngine
from .market_momentum_engine  import MarketMomentumEngine
from .market_pattern_engine   import MarketPatternEngine
from .market_regime_engine    import MarketRegimeEngine
from .market_rotation_engine  import MarketRotationEngine
from .market_scoring_engine   import MarketScoringEngine
from .market_sector_engine    import MarketSectorEngine
from .market_sentiment_engine import MarketSentimentEngine
from .market_volatility_engine import MarketVolatilityEngine


class MarketAnalyticsManager:
    """
    Orchestrates all market analytics sub-engines in a deterministic
    sequential pipeline.  All sub-engines are stateless; the manager
    creates one instance per lifetime (no per-call instantiation cost
    after initialisation).

    No I/O is performed here.  All data arrives via the request dict.
    """

    def __init__(self) -> None:
        self._regime_engine      = MarketRegimeEngine()
        self._breadth_engine     = MarketBreadthEngine()
        self._sector_engine      = MarketSectorEngine()
        self._rotation_engine    = MarketRotationEngine()
        self._index_engine       = MarketIndexEngine()
        self._volatility_engine  = MarketVolatilityEngine()
        self._correlation_engine = MarketCorrelationEngine()
        self._sentiment_engine   = MarketSentimentEngine()
        self._liquidity_engine   = MarketLiquidityEngine()
        self._momentum_engine    = MarketMomentumEngine()
        self._forecasting_engine = MarketForecastingEngine()
        self._pattern_engine     = MarketPatternEngine()
        self._scoring_engine     = MarketScoringEngine()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(self, request: MarketAnalyticsRequest) -> MarketAnalyticsReport:
        t0 = time.monotonic()

        # Build the flat data dict consumed by sub-engines
        data: Dict[str, Any] = {
            "index_prices":     request.index_prices,
            "sector_data":      request.sector_data,
            "breadth_data":     request.breadth_data,
            "volume_data":      request.volume_data,
            "volatility_data":  request.volatility_data,
            "economic_data":    request.economic_data,
            "global_data":      request.global_data,
            "historical_data":  request.historical_data,
        }
        ctx = request.context

        # --- phase 1: independent analyses ---
        regime     = self._safe(self._regime_engine.run,       ctx, data)
        breadth    = self._safe(self._breadth_engine.run,      ctx, data)
        volatility = self._safe(self._volatility_engine.run,   ctx, data)
        momentum   = self._safe(self._momentum_engine.run,     ctx, data)
        liquidity  = self._safe(self._liquidity_engine.run,    ctx, data)
        sentiment  = self._safe(self._sentiment_engine.run,    ctx, data)
        correlation = self._safe(self._correlation_engine.run, ctx, data)
        index_list: List[IndexResult] = self._index_engine.run(ctx, data)
        sector_list: List[SectorResult] = self._sector_engine.run(ctx, data)

        # --- phase 2: dependent analyses ---
        rotation = None
        if sector_list:
            rotation = self._rotation_engine.run(ctx, sector_list)

        forecasts: Tuple[ForecastResult, ...] = self._forecasting_engine.run(
            ctx, data, regime=regime
        )

        pattern: Optional[PatternResult] = self._pattern_engine.run(ctx, data)

        # --- phase 3: scoring ---
        scores = self._scoring_engine.run(
            regime=regime,
            breadth=breadth,
            volatility=volatility,
            momentum=momentum,
            liquidity=liquidity,
        )

        elapsed = time.monotonic() - t0

        return MarketAnalyticsReport.create_success(
            analytics_id       = request.analytics_id,
            market_analysis_id = request.market_analysis_id,
            exchange           = request.exchange,
            elapsed_s          = elapsed,
            regime             = regime,
            breadth            = breadth,
            sector_results     = tuple(sector_list),
            rotation           = rotation,
            volatility         = volatility,
            momentum           = momentum,
            liquidity          = liquidity,
            sentiment          = sentiment,
            correlation        = correlation,
            index_results      = tuple(index_list),
            pattern            = pattern,
            forecasts          = forecasts,
            scores             = scores,
            metadata           = dict(request.metadata),
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _safe(fn, ctx, data):  # type: ignore[override]
        """Run a sub-engine; return None on unexpected error."""
        try:
            return fn(ctx, data)
        except Exception:
            return None
