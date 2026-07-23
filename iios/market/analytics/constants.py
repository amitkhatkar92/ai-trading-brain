"""
constants.py — iios.market.analytics
======================================
Enumerations, identifiers, and defaults for the Market Analytics &
Intelligence Framework.

C12 Market Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, FrozenSet, Tuple

# ---------------------------------------------------------------------------
# System identifiers
# ---------------------------------------------------------------------------
ANALYTICS_SYSTEM_ID:   str = "iios:market:analytics"
REGIME_SYSTEM_ID:      str = "iios:market:analytics:regime"
BREADTH_SYSTEM_ID:     str = "iios:market:analytics:breadth"
SECTOR_SYSTEM_ID:      str = "iios:market:analytics:sector"
VOLATILITY_SYSTEM_ID:  str = "iios:market:analytics:volatility"
FORECAST_SYSTEM_ID:    str = "iios:market:analytics:forecast"
SCORING_SYSTEM_ID:     str = "iios:market:analytics:scoring"
INTELLIGENCE_SYSTEM_ID: str = "iios:market:analytics:intelligence"
FACTORY_SYSTEM_ID:     str = "iios:market:analytics:factory"
REGISTRY_SYSTEM_ID:    str = "iios:market:analytics:registry"

# ---------------------------------------------------------------------------
# Versioning
# ---------------------------------------------------------------------------
VERSION:        str = "1.0.0"
SCHEMA_VERSION: str = "1.0"
MODEL_VERSION:  str = "1.0.0"

# ---------------------------------------------------------------------------
# Actors
# ---------------------------------------------------------------------------
ACTOR_ANALYTICS_ENGINE: str = "iios:market:analytics:engine"
ACTOR_REGIME:           str = "iios:market:analytics:regime"
ACTOR_BREADTH:          str = "iios:market:analytics:breadth"
ACTOR_SECTOR:           str = "iios:market:analytics:sector"
ACTOR_FORECAST:         str = "iios:market:analytics:forecast"
ACTOR_SCORING:          str = "iios:market:analytics:scoring"
ACTOR_SYSTEM:           str = "iios:system"
ACTOR_OPERATOR:         str = "operator"

# ---------------------------------------------------------------------------
# Default parameters
# ---------------------------------------------------------------------------
DEFAULT_MAX_ANALYTICS:     int   = 10_000
DEFAULT_MAX_HISTORY:       int   = 1_000
DEFAULT_LOOKBACK_DAYS:     int   = 252
DEFAULT_SHORT_LOOKBACK:    int   = 20
DEFAULT_MEDIUM_LOOKBACK:   int   = 50
DEFAULT_LONG_LOOKBACK:     int   = 200
DEFAULT_ANALYTICS_TIMEOUT_S: float = 60.0
DEFAULT_MIN_DATA_POINTS:   int   = 5
DEFAULT_CORRELATION_WINDOW: int  = 60
DEFAULT_VOLATILITY_WINDOW:  int  = 20
DEFAULT_MOMENTUM_WINDOW:    int  = 14
DEFAULT_BREADTH_WINDOW:     int  = 10
DEFAULT_SMOOTHING_FACTOR:   float = 0.1
DEFAULT_CONFIDENCE_LEVEL:   float = 0.95

# Score bands (0–100)
SCORE_STRONG_BULL:   float = 80.0
SCORE_BULL:          float = 60.0
SCORE_NEUTRAL:       float = 40.0
SCORE_BEAR:          float = 20.0

# Market health thresholds
BREADTH_HEALTHY:     float = 0.60   # >60% advancing = healthy
BREADTH_UNHEALTHY:   float = 0.40   # <40% advancing = unhealthy
VOLATILITY_LOW:      float = 0.10   # <10% annualised = low vol
VOLATILITY_HIGH:     float = 0.25   # >25% annualised = high vol
VOLATILITY_EXTREME:  float = 0.40   # >40% = extreme

# Sector count used in breadth models
DEFAULT_SECTOR_COUNT: int = 11

# Minimum bars needed for technical analytics
MIN_BARS_TREND:      int = 20
MIN_BARS_MOMENTUM:   int = 14
MIN_BARS_PATTERN:    int = 5


# ---------------------------------------------------------------------------
# AnalyticsDomain — 14 domains
# ---------------------------------------------------------------------------
class AnalyticsDomain(str, Enum):
    """Classification of market analytics domains."""
    MARKET_REGIME       = "market_regime"
    TREND_ANALYSIS      = "trend_analysis"
    MARKET_BREADTH      = "market_breadth"
    SECTOR_ROTATION     = "sector_rotation"
    SECTOR_STRENGTH     = "sector_strength"
    INDEX_ANALYSIS      = "index_analysis"
    MARKET_MOMENTUM     = "market_momentum"
    VOLATILITY          = "volatility"
    LIQUIDITY           = "liquidity"
    MARKET_CORRELATION  = "market_correlation"
    MARKET_SENTIMENT    = "market_sentiment"
    ECONOMIC_IMPACT     = "economic_impact"
    GLOBAL_MARKET       = "global_market"
    INTERMARKET         = "intermarket"


# ---------------------------------------------------------------------------
# MarketRegime — 6 regimes
# ---------------------------------------------------------------------------
class MarketRegime(str, Enum):
    """Current market regime classification."""
    STRONG_BULL   = "strong_bull"
    BULL          = "bull"
    NEUTRAL       = "neutral"
    BEAR          = "bear"
    STRONG_BEAR   = "strong_bear"
    UNKNOWN       = "unknown"


# ---------------------------------------------------------------------------
# TrendDirection
# ---------------------------------------------------------------------------
class TrendDirection(str, Enum):
    """Trend direction classification."""
    STRONG_UP   = "strong_up"
    UP          = "up"
    SIDEWAYS    = "sideways"
    DOWN        = "down"
    STRONG_DOWN = "strong_down"
    UNKNOWN     = "unknown"


# ---------------------------------------------------------------------------
# TrendStrength
# ---------------------------------------------------------------------------
class TrendStrength(str, Enum):
    """Magnitude of current trend."""
    VERY_STRONG = "very_strong"
    STRONG      = "strong"
    MODERATE    = "moderate"
    WEAK        = "weak"
    NONE        = "none"


# ---------------------------------------------------------------------------
# VolatilityRegime
# ---------------------------------------------------------------------------
class VolatilityRegime(str, Enum):
    """Volatility regime classification."""
    EXTREME  = "extreme"
    HIGH     = "high"
    ELEVATED = "elevated"
    NORMAL   = "normal"
    LOW      = "low"


# ---------------------------------------------------------------------------
# LiquidityCondition
# ---------------------------------------------------------------------------
class LiquidityCondition(str, Enum):
    """Market liquidity condition."""
    ABUNDANT  = "abundant"
    ADEQUATE  = "adequate"
    TIGHT     = "tight"
    STRESSED  = "stressed"
    CRISIS    = "crisis"
    UNKNOWN   = "unknown"


# ---------------------------------------------------------------------------
# SentimentCategory
# ---------------------------------------------------------------------------
class SentimentCategory(str, Enum):
    """Market sentiment classification."""
    EXTREME_GREED = "extreme_greed"
    GREED         = "greed"
    NEUTRAL       = "neutral"
    FEAR          = "fear"
    EXTREME_FEAR  = "extreme_fear"
    UNKNOWN       = "unknown"


# ---------------------------------------------------------------------------
# ForecastType
# ---------------------------------------------------------------------------
class ForecastType(str, Enum):
    """Type of market forecast."""
    SHORT_TERM        = "short_term"
    INTRADAY          = "intraday"
    SWING             = "swing"
    TREND_CONTINUATION = "trend_continuation"
    TREND_REVERSAL    = "trend_reversal"
    VOLATILITY        = "volatility"
    LIQUIDITY         = "liquidity"


# ---------------------------------------------------------------------------
# ForecastHorizon
# ---------------------------------------------------------------------------
class ForecastHorizon(str, Enum):
    """Forecast time horizon."""
    INTRADAY = "intraday"
    DAY      = "day"
    WEEK     = "week"
    MONTH    = "month"


FORECAST_HORIZON_BARS: Dict[ForecastHorizon, int] = {
    ForecastHorizon.INTRADAY: 1,
    ForecastHorizon.DAY:      1,
    ForecastHorizon.WEEK:     5,
    ForecastHorizon.MONTH:    21,
}


# ---------------------------------------------------------------------------
# ForecastDirection
# ---------------------------------------------------------------------------
class ForecastDirection(str, Enum):
    """Forecast direction for market movement."""
    BULLISH  = "bullish"
    NEUTRAL  = "neutral"
    BEARISH  = "bearish"
    UNKNOWN  = "unknown"


# ---------------------------------------------------------------------------
# PatternType
# ---------------------------------------------------------------------------
class PatternType(str, Enum):
    """Technical pattern classification."""
    BREAKOUT            = "breakout"
    BREAKDOWN           = "breakdown"
    CONSOLIDATION       = "consolidation"
    REVERSAL_TOP        = "reversal_top"
    REVERSAL_BOTTOM     = "reversal_bottom"
    CONTINUATION        = "continuation"
    EXHAUSTION          = "exhaustion"
    NONE_DETECTED       = "none_detected"


# ---------------------------------------------------------------------------
# CorrelationStrength
# ---------------------------------------------------------------------------
class CorrelationStrength(str, Enum):
    """Correlation magnitude classification."""
    STRONG_POSITIVE  = "strong_positive"
    MODERATE_POSITIVE = "moderate_positive"
    WEAK             = "weak"
    MODERATE_NEGATIVE = "moderate_negative"
    STRONG_NEGATIVE  = "strong_negative"


# ---------------------------------------------------------------------------
# AnalyticsStatus
# ---------------------------------------------------------------------------
class AnalyticsStatus(str, Enum):
    """Lifecycle state of an analytics run."""
    CREATED    = "created"
    PROCESSING = "processing"
    COMPLETED  = "completed"
    FAILED     = "failed"
    CANCELLED  = "cancelled"


# ---------------------------------------------------------------------------
# AnalyticsEventType — 10 domain events
# ---------------------------------------------------------------------------
class AnalyticsEventType(str, Enum):
    """Domain events emitted by the analytics framework."""
    ANALYTICS_STARTED              = "analytics_started"
    DATASETS_LOADED                = "datasets_loaded"
    REGIME_DETECTED                = "regime_detected"
    SECTOR_ANALYSIS_COMPLETED      = "sector_analysis_completed"
    BREADTH_ANALYSIS_COMPLETED     = "breadth_analysis_completed"
    FORECAST_GENERATED             = "forecast_generated"
    SCORES_CALCULATED              = "scores_calculated"
    ANALYTICS_VALIDATED            = "analytics_validated"
    ANALYTICS_PUBLISHED            = "analytics_published"
    ANALYTICS_FAILED               = "analytics_failed"


# ---------------------------------------------------------------------------
# ValidationCode
# ---------------------------------------------------------------------------
class ValidationCode(str, Enum):
    """Validation check identifiers."""
    INPUT_CONSISTENT       = "input_consistent"
    DATA_INTEGRITY         = "data_integrity"
    MODEL_CONSISTENT       = "model_consistent"
    CALCULATION_INTEGRITY  = "calculation_integrity"
    ANALYTICS_COMPLETE     = "analytics_complete"
    FORECAST_CONSISTENT    = "forecast_consistent"
    SCORE_CONSISTENT       = "score_consistent"
    POLICY_APPROVED        = "policy_approved"


# ---------------------------------------------------------------------------
# Regime score lookup (for scoring engine)
# ---------------------------------------------------------------------------
REGIME_BASE_SCORES: Dict[MarketRegime, float] = {
    MarketRegime.STRONG_BULL: 90.0,
    MarketRegime.BULL:        70.0,
    MarketRegime.NEUTRAL:     50.0,
    MarketRegime.BEAR:        30.0,
    MarketRegime.STRONG_BEAR: 10.0,
    MarketRegime.UNKNOWN:     50.0,
}

# Volatility regime penalty (subtracted from overall score)
VOLATILITY_SCORE_PENALTY: Dict[VolatilityRegime, float] = {
    VolatilityRegime.LOW:      0.0,
    VolatilityRegime.NORMAL:   0.0,
    VolatilityRegime.ELEVATED: 5.0,
    VolatilityRegime.HIGH:     10.0,
    VolatilityRegime.EXTREME:  20.0,
}
