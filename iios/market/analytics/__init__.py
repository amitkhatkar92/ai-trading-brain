"""
iios.market.analytics — Market Analytics & Intelligence Framework
=================================================================
C12 Market Intelligence — Phase 1, Module 4

Public API
----------
Engine
    MarketAnalyticsEngine      — primary entry point (LifecycleAwareMixin)

Request / Response
    MarketAnalyticsContext     — analytics parameters / configuration
    MarketAnalyticsRequest     — fully assembled analytics request
    MarketAnalyticsReport      — immutable analytics output

Domain results
    RegimeResult
    BreadthResult
    SectorResult
    VolatilityResult
    MomentumResult
    LiquidityResult
    SentimentResult
    CorrelationResult
    IndexResult
    RotationResult
    PatternResult
    ForecastResult
    MarketScores

Exceptions
    MarketAnalyticsError
    MarketAnalyticsEngineNotRunningError
    MarketAnalyticsValidationError
    MarketAnalyticsNotApprovedError
    MarketAnalyticsNotFoundError
    MarketAnalyticsDataError
    MarketRegimeError
    MarketForecastError
    MarketAnalyticsRegistryError
    MarketAnalyticsCapacityError

Enumerations (constants)
    AnalyticsDomain, MarketRegime, TrendDirection, TrendStrength,
    VolatilityRegime, LiquidityCondition, SentimentCategory,
    ForecastType, ForecastHorizon, ForecastDirection,
    PatternType, CorrelationStrength, AnalyticsStatus,
    AnalyticsEventType, ValidationCode

Events
    MarketAnalyticsEvent
    analytics_started_event, datasets_loaded_event, regime_detected_event,
    sector_analysis_completed_event, breadth_analysis_completed_event,
    forecast_generated_event, scores_calculated_event,
    analytics_validated_event, analytics_published_event,
    analytics_failed_event

Infrastructure
    MarketAnalyticsFactory
    MarketAnalyticsValidator
    MarketAnalyticsRegistry
    MarketAnalyticsStatistics
    MarketAnalyticsHistory
"""

from .constants import (
    ANALYTICS_SYSTEM_ID,
    VERSION,
    AnalyticsDomain,
    AnalyticsEventType,
    AnalyticsStatus,
    CorrelationStrength,
    ForecastDirection,
    ForecastHorizon,
    ForecastType,
    LiquidityCondition,
    MarketRegime,
    PatternType,
    SentimentCategory,
    TrendDirection,
    TrendStrength,
    ValidationCode,
    VolatilityRegime,
)
from .exceptions import (
    MarketAnalyticsCapacityError,
    MarketAnalyticsDataError,
    MarketAnalyticsEngineNotRunningError,
    MarketAnalyticsError,
    MarketAnalyticsNotApprovedError,
    MarketAnalyticsNotFoundError,
    MarketAnalyticsRegistryError,
    MarketAnalyticsValidationError,
    MarketForecastError,
    MarketRegimeError,
)
from .market_analytics_context  import MarketAnalyticsContext
from .market_analytics_engine   import MarketAnalyticsEngine
from .market_analytics_events   import (
    MarketAnalyticsEvent,
    analytics_failed_event,
    analytics_published_event,
    analytics_started_event,
    analytics_validated_event,
    breadth_analysis_completed_event,
    datasets_loaded_event,
    forecast_generated_event,
    regime_detected_event,
    scores_calculated_event,
    sector_analysis_completed_event,
)
from .market_analytics_factory  import MarketAnalyticsFactory
from .market_analytics_history  import MarketAnalyticsHistory
from .market_analytics_registry import MarketAnalyticsRegistry
from .market_analytics_request  import MarketAnalyticsRequest
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
from .market_analytics_statistics import MarketAnalyticsStatistics
from .market_analytics_validator  import (
    AnalyticsValidationCheckResult,
    AnalyticsValidationResult,
    MarketAnalyticsValidator,
)

__all__ = [
    # Engine
    "MarketAnalyticsEngine",
    # Version
    "VERSION",
    "ANALYTICS_SYSTEM_ID",
    # Context / Request
    "MarketAnalyticsContext",
    "MarketAnalyticsRequest",
    # Report
    "MarketAnalyticsReport",
    # Domain results
    "RegimeResult",
    "BreadthResult",
    "SectorResult",
    "VolatilityResult",
    "MomentumResult",
    "LiquidityResult",
    "SentimentResult",
    "CorrelationResult",
    "IndexResult",
    "RotationResult",
    "PatternResult",
    "ForecastResult",
    "MarketScores",
    # Exceptions
    "MarketAnalyticsError",
    "MarketAnalyticsEngineNotRunningError",
    "MarketAnalyticsValidationError",
    "MarketAnalyticsNotApprovedError",
    "MarketAnalyticsNotFoundError",
    "MarketAnalyticsDataError",
    "MarketRegimeError",
    "MarketForecastError",
    "MarketAnalyticsRegistryError",
    "MarketAnalyticsCapacityError",
    # Enumerations
    "AnalyticsDomain",
    "MarketRegime",
    "TrendDirection",
    "TrendStrength",
    "VolatilityRegime",
    "LiquidityCondition",
    "SentimentCategory",
    "ForecastType",
    "ForecastHorizon",
    "ForecastDirection",
    "PatternType",
    "CorrelationStrength",
    "AnalyticsStatus",
    "AnalyticsEventType",
    "ValidationCode",
    # Events
    "MarketAnalyticsEvent",
    "analytics_started_event",
    "datasets_loaded_event",
    "regime_detected_event",
    "sector_analysis_completed_event",
    "breadth_analysis_completed_event",
    "forecast_generated_event",
    "scores_calculated_event",
    "analytics_validated_event",
    "analytics_published_event",
    "analytics_failed_event",
    # Infrastructure
    "MarketAnalyticsFactory",
    "MarketAnalyticsValidator",
    "AnalyticsValidationResult",
    "AnalyticsValidationCheckResult",
    "MarketAnalyticsRegistry",
    "MarketAnalyticsStatistics",
    "MarketAnalyticsHistory",
]
