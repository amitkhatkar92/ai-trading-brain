"""
market_analytics_response.py — iios.market.analytics
======================================================
Immutable analytics report value objects.

C12 Market Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .constants import (
    VERSION,
    AnalyticsDomain,
    AnalyticsStatus,
    ForecastDirection,
    ForecastHorizon,
    ForecastType,
    LiquidityCondition,
    MarketRegime,
    PatternType,
    SentimentCategory,
    TrendDirection,
    TrendStrength,
    VolatilityRegime,
)


# ---------------------------------------------------------------------------
# Domain result value objects
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RegimeResult:
    regime:             MarketRegime
    confidence:         float
    trend_direction:    TrendDirection
    trend_strength:     TrendStrength
    regime_duration_bars: int
    description:        str = ""
    metadata:           Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "regime":               self.regime.value,
            "confidence":           round(self.confidence, 4),
            "trend_direction":      self.trend_direction.value,
            "trend_strength":       self.trend_strength.value,
            "regime_duration_bars": self.regime_duration_bars,
            "description":          self.description,
        }


@dataclass(frozen=True)
class BreadthResult:
    advance_decline_ratio:  float
    advancing_pct:          float
    declining_pct:          float
    unchanged_pct:          float
    new_highs:              int
    new_lows:               int
    breadth_score:          float
    is_healthy:             bool
    description:            str = ""
    metadata:               Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "advance_decline_ratio": round(self.advance_decline_ratio, 4),
            "advancing_pct":         round(self.advancing_pct, 4),
            "declining_pct":         round(self.declining_pct, 4),
            "new_highs":             self.new_highs,
            "new_lows":              self.new_lows,
            "breadth_score":         round(self.breadth_score, 2),
            "is_healthy":            self.is_healthy,
            "description":           self.description,
        }


@dataclass(frozen=True)
class SectorResult:
    sector_name:    str
    performance:    float
    relative_strength: float
    momentum_score: float
    volume_ratio:   float
    rank:           int
    trend:          TrendDirection
    metadata:       Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sector_name":       self.sector_name,
            "performance":       round(self.performance, 4),
            "relative_strength": round(self.relative_strength, 4),
            "momentum_score":    round(self.momentum_score, 4),
            "volume_ratio":      round(self.volume_ratio, 4),
            "rank":              self.rank,
            "trend":             self.trend.value,
        }


@dataclass(frozen=True)
class VolatilityResult:
    realised_vol:       float
    implied_vol:        float
    vol_regime:         VolatilityRegime
    vol_percentile:     float
    vol_trend:          TrendDirection
    vol_score:          float
    description:        str = ""
    metadata:           Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "realised_vol":    round(self.realised_vol, 4),
            "implied_vol":     round(self.implied_vol, 4),
            "vol_regime":      self.vol_regime.value,
            "vol_percentile":  round(self.vol_percentile, 4),
            "vol_trend":       self.vol_trend.value,
            "vol_score":       round(self.vol_score, 2),
            "description":     self.description,
        }


@dataclass(frozen=True)
class MomentumResult:
    rsi:             float
    roc:             float
    momentum_score:  float
    trend:           TrendDirection
    overbought:      bool
    oversold:        bool
    divergence:      bool
    description:     str = ""
    metadata:        Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rsi":            round(self.rsi, 2),
            "roc":            round(self.roc, 4),
            "momentum_score": round(self.momentum_score, 2),
            "trend":          self.trend.value,
            "overbought":     self.overbought,
            "oversold":       self.oversold,
            "divergence":     self.divergence,
            "description":    self.description,
        }


@dataclass(frozen=True)
class LiquidityResult:
    condition:          LiquidityCondition
    liquidity_score:    float
    avg_volume:         float
    volume_trend:       TrendDirection
    turnover_ratio:     float
    bid_ask_spread_est: float
    description:        str = ""
    metadata:           Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "condition":           self.condition.value,
            "liquidity_score":     round(self.liquidity_score, 2),
            "avg_volume":          round(self.avg_volume, 2),
            "volume_trend":        self.volume_trend.value,
            "turnover_ratio":      round(self.turnover_ratio, 4),
            "bid_ask_spread_est":  round(self.bid_ask_spread_est, 4),
            "description":         self.description,
        }


@dataclass(frozen=True)
class SentimentResult:
    category:         SentimentCategory
    sentiment_score:  float
    put_call_ratio:   float
    fear_greed_index: float
    institutional_bias: float
    description:      str = ""
    metadata:         Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category":           self.category.value,
            "sentiment_score":    round(self.sentiment_score, 2),
            "put_call_ratio":     round(self.put_call_ratio, 4),
            "fear_greed_index":   round(self.fear_greed_index, 2),
            "institutional_bias": round(self.institutional_bias, 4),
            "description":        self.description,
        }


@dataclass(frozen=True)
class CorrelationResult:
    exchange_correlation:  float
    global_correlation:    float
    sector_avg_correlation: float
    correlation_regime:    str
    dispersion_score:      float
    metadata:              Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "exchange_correlation":   round(self.exchange_correlation, 4),
            "global_correlation":     round(self.global_correlation, 4),
            "sector_avg_correlation": round(self.sector_avg_correlation, 4),
            "correlation_regime":     self.correlation_regime,
            "dispersion_score":       round(self.dispersion_score, 4),
        }


@dataclass(frozen=True)
class IndexResult:
    index_name:       str
    current_price:    float
    change_pct:       float
    trend:            TrendDirection
    ma_short:         float
    ma_medium:        float
    ma_long:          float
    above_ma_short:   bool
    above_ma_medium:  bool
    above_ma_long:    bool
    strength_score:   float
    metadata:         Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index_name":       self.index_name,
            "current_price":    round(self.current_price, 2),
            "change_pct":       round(self.change_pct, 4),
            "trend":            self.trend.value,
            "ma_short":         round(self.ma_short, 2),
            "ma_medium":        round(self.ma_medium, 2),
            "ma_long":          round(self.ma_long, 2),
            "above_ma_short":   self.above_ma_short,
            "above_ma_medium":  self.above_ma_medium,
            "above_ma_long":    self.above_ma_long,
            "strength_score":   round(self.strength_score, 2),
        }


@dataclass(frozen=True)
class RotationResult:
    leading_sectors:   Tuple[str, ...]
    lagging_sectors:   Tuple[str, ...]
    rotation_score:    float
    rotation_phase:    str
    description:       str = ""
    metadata:          Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "leading_sectors": list(self.leading_sectors),
            "lagging_sectors": list(self.lagging_sectors),
            "rotation_score":  round(self.rotation_score, 2),
            "rotation_phase":  self.rotation_phase,
            "description":     self.description,
        }


@dataclass(frozen=True)
class PatternResult:
    pattern_type:   PatternType
    confidence:     float
    support_level:  float
    resistance_level: float
    target_price:   float
    description:    str = ""
    metadata:       Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_type":     self.pattern_type.value,
            "confidence":       round(self.confidence, 4),
            "support_level":    round(self.support_level, 2),
            "resistance_level": round(self.resistance_level, 2),
            "target_price":     round(self.target_price, 2),
            "description":      self.description,
        }


@dataclass(frozen=True)
class ForecastResult:
    forecast_type:    ForecastType
    horizon:          ForecastHorizon
    direction:        ForecastDirection
    confidence:       float
    expected_return:  float
    upside_target:    float
    downside_target:  float
    rationale:        str = ""
    metadata:         Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "forecast_type":   self.forecast_type.value,
            "horizon":         self.horizon.value,
            "direction":       self.direction.value,
            "confidence":      round(self.confidence, 4),
            "expected_return": round(self.expected_return, 4),
            "upside_target":   round(self.upside_target, 2),
            "downside_target": round(self.downside_target, 2),
            "rationale":       self.rationale,
        }


@dataclass(frozen=True)
class MarketScores:
    health_score:          float
    regime_confidence:     float
    sector_strength_score: float
    trend_strength_score:  float
    breadth_score:         float
    liquidity_score:       float
    volatility_score:      float
    momentum_score:        float
    overall_score:         float
    metadata:              Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "health_score":          round(self.health_score, 2),
            "regime_confidence":     round(self.regime_confidence, 4),
            "sector_strength_score": round(self.sector_strength_score, 2),
            "trend_strength_score":  round(self.trend_strength_score, 2),
            "breadth_score":         round(self.breadth_score, 2),
            "liquidity_score":       round(self.liquidity_score, 2),
            "volatility_score":      round(self.volatility_score, 2),
            "momentum_score":        round(self.momentum_score, 2),
            "overall_score":         round(self.overall_score, 2),
        }


# ---------------------------------------------------------------------------
# Primary analytics report
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MarketAnalyticsReport:
    """
    Immutable comprehensive market analytics output.

    Fields
    ------
    report_id :           Unique report identifier.
    analytics_id :        Analytics run correlation identifier.
    market_analysis_id :  Market analysis identifier.
    exchange :            Exchange identifier.
    status :              Analytics completion status.
    regime :              Market regime classification result.
    breadth :             Market breadth analysis result.
    sector_results :      Per-sector analysis results.
    rotation :            Sector rotation result.
    volatility :          Volatility analysis result.
    momentum :            Momentum analysis result.
    liquidity :           Liquidity analysis result.
    sentiment :           Sentiment analysis result.
    correlation :         Correlation analysis result.
    index_results :       Per-index analysis results.
    pattern :             Technical pattern detection result.
    forecasts :           Market forecasts.
    scores :              Composite market scores.
    elapsed_s :           Total analytics elapsed time.
    is_success :          True when pipeline completed without errors.
    error_message :       Non-empty when is_success is False.
    created_at :          Wall-clock report generation time.
    metadata :            Supplementary metadata.
    framework_version :   Framework version string.
    """
    report_id:            str
    analytics_id:         str
    market_analysis_id:   str
    exchange:             str
    status:               AnalyticsStatus
    regime:               Optional[RegimeResult]
    breadth:              Optional[BreadthResult]
    sector_results:       Tuple[SectorResult, ...]
    rotation:             Optional[RotationResult]
    volatility:           Optional[VolatilityResult]
    momentum:             Optional[MomentumResult]
    liquidity:            Optional[LiquidityResult]
    sentiment:            Optional[SentimentResult]
    correlation:          Optional[CorrelationResult]
    index_results:        Tuple[IndexResult, ...]
    pattern:              Optional[PatternResult]
    forecasts:            Tuple[ForecastResult, ...]
    scores:               Optional[MarketScores]
    elapsed_s:            float
    is_success:           bool             = True
    error_message:        str              = ""
    created_at:           float            = field(default_factory=time.time)
    metadata:             Dict[str, Any]   = field(default_factory=dict)
    framework_version:    str              = VERSION

    @classmethod
    def create_success(
        cls,
        analytics_id:       str,
        market_analysis_id: str,
        exchange:           str,
        elapsed_s:          float,
        *,
        report_id:      Optional[str]              = None,
        regime:         Optional[RegimeResult]     = None,
        breadth:        Optional[BreadthResult]    = None,
        sector_results: Tuple[SectorResult, ...]   = (),
        rotation:       Optional[RotationResult]   = None,
        volatility:     Optional[VolatilityResult] = None,
        momentum:       Optional[MomentumResult]   = None,
        liquidity:      Optional[LiquidityResult]  = None,
        sentiment:      Optional[SentimentResult]  = None,
        correlation:    Optional[CorrelationResult] = None,
        index_results:  Tuple[IndexResult, ...]    = (),
        pattern:        Optional[PatternResult]    = None,
        forecasts:      Tuple[ForecastResult, ...] = (),
        scores:         Optional[MarketScores]     = None,
        metadata:       Optional[Dict[str, Any]]   = None,
    ) -> "MarketAnalyticsReport":
        return cls(
            report_id          = report_id or str(uuid.uuid4()),
            analytics_id       = analytics_id,
            market_analysis_id = market_analysis_id,
            exchange           = exchange,
            status             = AnalyticsStatus.COMPLETED,
            regime             = regime,
            breadth            = breadth,
            sector_results     = tuple(sector_results),
            rotation           = rotation,
            volatility         = volatility,
            momentum           = momentum,
            liquidity          = liquidity,
            sentiment          = sentiment,
            correlation        = correlation,
            index_results      = tuple(index_results),
            pattern            = pattern,
            forecasts          = tuple(forecasts),
            scores             = scores,
            elapsed_s          = elapsed_s,
            is_success         = True,
            metadata           = dict(metadata or {}),
        )

    @classmethod
    def create_failure(
        cls,
        analytics_id:       str,
        market_analysis_id: str,
        exchange:           str,
        error_message:      str,
        elapsed_s:          float,
        *,
        report_id: Optional[str]            = None,
        metadata:  Optional[Dict[str, Any]] = None,
    ) -> "MarketAnalyticsReport":
        return cls(
            report_id          = report_id or str(uuid.uuid4()),
            analytics_id       = analytics_id,
            market_analysis_id = market_analysis_id,
            exchange           = exchange,
            status             = AnalyticsStatus.FAILED,
            regime             = None,
            breadth            = None,
            sector_results     = (),
            rotation           = None,
            volatility         = None,
            momentum           = None,
            liquidity          = None,
            sentiment          = None,
            correlation        = None,
            index_results      = (),
            pattern            = None,
            forecasts          = (),
            scores             = None,
            elapsed_s          = elapsed_s,
            is_success         = False,
            error_message      = error_message,
            metadata           = dict(metadata or {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":           self.report_id,
            "analytics_id":        self.analytics_id,
            "market_analysis_id":  self.market_analysis_id,
            "exchange":            self.exchange,
            "status":              self.status.value,
            "is_success":          self.is_success,
            "error_message":       self.error_message,
            "elapsed_s":           round(self.elapsed_s, 4),
            "regime":              self.regime.to_dict() if self.regime else None,
            "breadth":             self.breadth.to_dict() if self.breadth else None,
            "sector_results":      [s.to_dict() for s in self.sector_results],
            "rotation":            self.rotation.to_dict() if self.rotation else None,
            "volatility":          self.volatility.to_dict() if self.volatility else None,
            "momentum":            self.momentum.to_dict() if self.momentum else None,
            "liquidity":           self.liquidity.to_dict() if self.liquidity else None,
            "sentiment":           self.sentiment.to_dict() if self.sentiment else None,
            "correlation":         self.correlation.to_dict() if self.correlation else None,
            "index_results":       [i.to_dict() for i in self.index_results],
            "pattern":             self.pattern.to_dict() if self.pattern else None,
            "forecasts":           [f.to_dict() for f in self.forecasts],
            "scores":              self.scores.to_dict() if self.scores else None,
            "created_at":          self.created_at,
            "framework_version":   self.framework_version,
        }
