"""
market_analytics_factory.py — iios.market.analytics
=====================================================
Object factory helpers for the Market Analytics Framework.

C12 Market Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional, Tuple

from .constants import (
    DEFAULT_BREADTH_WINDOW,
    DEFAULT_CONFIDENCE_LEVEL,
    DEFAULT_CORRELATION_WINDOW,
    DEFAULT_LONG_LOOKBACK,
    DEFAULT_LOOKBACK_DAYS,
    DEFAULT_MEDIUM_LOOKBACK,
    DEFAULT_MOMENTUM_WINDOW,
    DEFAULT_SHORT_LOOKBACK,
    DEFAULT_VOLATILITY_WINDOW,
    AnalyticsDomain,
    ForecastHorizon,
)
from .market_analytics_context import MarketAnalyticsContext
from .market_analytics_request import MarketAnalyticsRequest


class MarketAnalyticsFactory:
    """
    Lightweight factory that assembles
    :class:`~.market_analytics_context.MarketAnalyticsContext` and
    :class:`~.market_analytics_request.MarketAnalyticsRequest` objects from
    caller-supplied raw data dictionaries.
    """

    # ------------------------------------------------------------------
    # Context
    # ------------------------------------------------------------------

    @staticmethod
    def create_context(
        analytics_id:       str,
        market_analysis_id: str,
        exchange:           str,
        *,
        domains:           Optional[Tuple[AnalyticsDomain, ...]] = None,
        forecast_horizon:  ForecastHorizon = ForecastHorizon.DAY,
        lookback_days:     int  = DEFAULT_LOOKBACK_DAYS,
        short_lookback:    int  = DEFAULT_SHORT_LOOKBACK,
        medium_lookback:   int  = DEFAULT_MEDIUM_LOOKBACK,
        long_lookback:     int  = DEFAULT_LONG_LOOKBACK,
        volatility_window: int  = DEFAULT_VOLATILITY_WINDOW,
        momentum_window:   int  = DEFAULT_MOMENTUM_WINDOW,
        breadth_window:    int  = DEFAULT_BREADTH_WINDOW,
        correlation_window: int = DEFAULT_CORRELATION_WINDOW,
        confidence_level:  float = DEFAULT_CONFIDENCE_LEVEL,
        source:            str  = "factory",
        correlation_id:    Optional[str] = None,
        metadata:          Optional[Dict[str, Any]] = None,
    ) -> MarketAnalyticsContext:
        return MarketAnalyticsContext.create(
            analytics_id       = analytics_id,
            market_analysis_id = market_analysis_id,
            exchange           = exchange,
            context_id         = str(uuid.uuid4()),
            domains            = domains or tuple(AnalyticsDomain),
            forecast_horizon   = forecast_horizon,
            lookback_days      = lookback_days,
            short_lookback     = short_lookback,
            medium_lookback    = medium_lookback,
            long_lookback      = long_lookback,
            volatility_window  = volatility_window,
            momentum_window    = momentum_window,
            breadth_window     = breadth_window,
            correlation_window = correlation_window,
            confidence_level   = confidence_level,
            source             = source,
            correlation_id     = correlation_id or str(uuid.uuid4()),
            metadata           = metadata or {},
        )

    # ------------------------------------------------------------------
    # Request
    # ------------------------------------------------------------------

    @staticmethod
    def create_request(
        analytics_id:        str,
        market_analysis_id:  str,
        exchange:            str,
        context:             MarketAnalyticsContext,
        *,
        policy_approved:     bool = False,
        policy_response:     Optional[Dict[str, Any]] = None,
        index_prices:        Optional[Dict[str, List[float]]] = None,
        sector_data:         Optional[Dict[str, Any]] = None,
        breadth_data:        Optional[Dict[str, Any]] = None,
        volume_data:         Optional[Dict[str, Any]] = None,
        volatility_data:     Optional[Dict[str, Any]] = None,
        economic_data:       Optional[Dict[str, Any]] = None,
        global_data:         Optional[Dict[str, Any]] = None,
        corporate_actions:   Optional[Dict[str, Any]] = None,
        historical_data:     Optional[Dict[str, Any]] = None,
        metadata:            Optional[Dict[str, Any]] = None,
    ) -> MarketAnalyticsRequest:
        return MarketAnalyticsRequest.create(
            analytics_id       = analytics_id,
            market_analysis_id = market_analysis_id,
            exchange           = exchange,
            request_id         = str(uuid.uuid4()),
            context            = context,
            policy_approved    = policy_approved,
            policy_response    = policy_response or {},
            index_prices       = index_prices or {},
            sector_data        = sector_data or {},
            breadth_data       = breadth_data or {},
            volume_data        = volume_data or {},
            volatility_data    = volatility_data or {},
            economic_data      = economic_data or {},
            global_data        = global_data or {},
            corporate_actions  = corporate_actions or {},
            historical_data    = historical_data or {},
            metadata           = metadata or {},
        )
