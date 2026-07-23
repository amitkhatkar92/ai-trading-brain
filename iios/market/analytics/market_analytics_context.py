"""
market_analytics_context.py — iios.market.analytics
=====================================================
Immutable analytics configuration context.

C12 Market Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

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
    VERSION,
    AnalyticsDomain,
    ForecastHorizon,
)


@dataclass(frozen=True)
class MarketAnalyticsContext:
    """
    Immutable analytics configuration context.

    Carries all analytical parameters required by the analytics pipeline.

    Fields
    ------
    context_id :         Unique identifier.
    analytics_id :       Analytics run correlation identifier.
    market_analysis_id : Target market analysis identifier.
    exchange :           Exchange identifier (e.g. ``"NSE"``).
    domains :            Analytics domains to run (empty = all).
    forecast_horizon :   Forecast time horizon.
    lookback_days :      Historical lookback window (days).
    short_lookback :     Short moving-average period.
    medium_lookback :    Medium moving-average period.
    long_lookback :      Long moving-average period.
    volatility_window :  Volatility calculation window.
    momentum_window :    Momentum calculation window.
    breadth_window :     Breadth smoothing window.
    correlation_window : Correlation calculation window.
    confidence_level :   Statistical confidence level.
    source :             Requesting component identifier.
    correlation_id :     Upstream correlation identifier.
    metadata :           Supplementary metadata.
    framework_version :  Framework version string.
    """
    context_id:          str
    analytics_id:        str
    market_analysis_id:  str
    exchange:            str
    domains:             Tuple[AnalyticsDomain, ...]   = field(default_factory=tuple)
    forecast_horizon:    ForecastHorizon               = ForecastHorizon.DAY
    lookback_days:       int                           = DEFAULT_LOOKBACK_DAYS
    short_lookback:      int                           = DEFAULT_SHORT_LOOKBACK
    medium_lookback:     int                           = DEFAULT_MEDIUM_LOOKBACK
    long_lookback:       int                           = DEFAULT_LONG_LOOKBACK
    volatility_window:   int                           = DEFAULT_VOLATILITY_WINDOW
    momentum_window:     int                           = DEFAULT_MOMENTUM_WINDOW
    breadth_window:      int                           = DEFAULT_BREADTH_WINDOW
    correlation_window:  int                           = DEFAULT_CORRELATION_WINDOW
    confidence_level:    float                         = DEFAULT_CONFIDENCE_LEVEL
    source:              str                           = ""
    correlation_id:      str                           = ""
    metadata:            Dict[str, Any]                = field(default_factory=dict)
    framework_version:   str                           = VERSION

    @classmethod
    def create(
        cls,
        analytics_id:       str,
        market_analysis_id: str,
        exchange:           str,
        *,
        context_id:         Optional[str]                        = None,
        domains:            Optional[Tuple[AnalyticsDomain, ...]] = None,
        forecast_horizon:   ForecastHorizon                      = ForecastHorizon.DAY,
        lookback_days:      int                                   = DEFAULT_LOOKBACK_DAYS,
        short_lookback:     int                                   = DEFAULT_SHORT_LOOKBACK,
        medium_lookback:    int                                   = DEFAULT_MEDIUM_LOOKBACK,
        long_lookback:      int                                   = DEFAULT_LONG_LOOKBACK,
        volatility_window:  int                                   = DEFAULT_VOLATILITY_WINDOW,
        momentum_window:    int                                   = DEFAULT_MOMENTUM_WINDOW,
        breadth_window:     int                                   = DEFAULT_BREADTH_WINDOW,
        correlation_window: int                                   = DEFAULT_CORRELATION_WINDOW,
        confidence_level:   float                                 = DEFAULT_CONFIDENCE_LEVEL,
        source:             str                                   = "",
        correlation_id:     str                                   = "",
        metadata:           Optional[Dict[str, Any]]              = None,
    ) -> "MarketAnalyticsContext":
        return cls(
            context_id         = context_id or str(uuid.uuid4()),
            analytics_id       = analytics_id,
            market_analysis_id = market_analysis_id,
            exchange           = exchange,
            domains            = tuple(domains or []),
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
            correlation_id     = correlation_id,
            metadata           = dict(metadata or {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id":          self.context_id,
            "analytics_id":        self.analytics_id,
            "market_analysis_id":  self.market_analysis_id,
            "exchange":            self.exchange,
            "domains":             [d.value for d in self.domains],
            "forecast_horizon":    self.forecast_horizon.value,
            "lookback_days":       self.lookback_days,
            "volatility_window":   self.volatility_window,
            "momentum_window":     self.momentum_window,
            "short_lookback":      self.short_lookback,
            "medium_lookback":     self.medium_lookback,
            "long_lookback":       self.long_lookback,
            "breadth_window":      self.breadth_window,
            "correlation_window":  self.correlation_window,
            "confidence_level":    self.confidence_level,
            "framework_version":   self.framework_version,
        }
