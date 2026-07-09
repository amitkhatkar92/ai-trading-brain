"""iios/investment/market/market_constants.py
All enumerations and numeric constants for the Market Intelligence Engine.
"""
from __future__ import annotations

from enum import Enum


class MarketStatus(str, Enum):
    OPEN            = "open"
    CLOSED          = "closed"
    PRE_OPEN        = "pre_open"
    POST_MARKET     = "post_market"
    HOLIDAY         = "holiday"
    SPECIAL_SESSION = "special_session"
    HALTED          = "halted"
    UNKNOWN         = "unknown"


class MarketRegime(str, Enum):
    BULL            = "bull"
    BEAR            = "bear"
    SIDEWAYS        = "sideways"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY  = "low_volatility"
    EXPANSION       = "expansion"
    CONTRACTION     = "contraction"
    RECOVERY        = "recovery"
    CRISIS          = "crisis"
    CUSTOM          = "custom"
    UNKNOWN         = "unknown"


class TrendDirection(str, Enum):
    UP        = "up"
    DOWN      = "down"
    SIDEWAYS  = "sideways"
    UNDEFINED = "undefined"


class MarketStrength(str, Enum):
    VERY_STRONG = "very_strong"
    STRONG      = "strong"
    MODERATE    = "moderate"
    WEAK        = "weak"
    VERY_WEAK   = "very_weak"
    NEUTRAL     = "neutral"


class LiquidityLevel(str, Enum):
    VERY_HIGH = "very_high"
    HIGH      = "high"
    MODERATE  = "moderate"
    LOW       = "low"
    VERY_LOW  = "very_low"
    ILLIQUID  = "illiquid"


class VolatilityLevel(str, Enum):
    EXTREME  = "extreme"
    HIGH     = "high"
    MODERATE = "moderate"
    LOW      = "low"
    VERY_LOW = "very_low"


class SentimentLevel(str, Enum):
    EXTREME_GREED = "extreme_greed"
    GREED         = "greed"
    NEUTRAL       = "neutral"
    FEAR          = "fear"
    EXTREME_FEAR  = "extreme_fear"


class MarketPhase(str, Enum):
    ACCUMULATION = "accumulation"
    MARKUP       = "markup"
    DISTRIBUTION = "distribution"
    MARKDOWN     = "markdown"
    UNKNOWN      = "unknown"


class BreadthCondition(str, Enum):
    VERY_BROAD  = "very_broad"
    BROAD       = "broad"
    MODERATE    = "moderate"
    NARROW      = "narrow"
    VERY_NARROW = "very_narrow"


class CorrelationRegime(str, Enum):
    HIGH_CORRELATION = "high_correlation"
    MODERATE         = "moderate"
    LOW_CORRELATION  = "low_correlation"
    DECORRELATED     = "decorrelated"


# ── Engine metadata ───────────────────────────────────────────────────────────
MARKET_ENGINE_VERSION   = "1.0.0"
MARKET_ENGINE_SYSTEM_ID = "iios:market:engine"

# ── Operational defaults ──────────────────────────────────────────────────────
DEFAULT_SNAPSHOT_TTL_SEC     = 60.0
DEFAULT_HISTORY_SIZE         = 10_000
DEFAULT_SNAPSHOT_HISTORY     = 100       # per-market snapshot ring buffer
DEFAULT_REGIME_WINDOW        = 252       # trading days
DEFAULT_VOLATILITY_WINDOW    = 20
DEFAULT_CORRELATION_WINDOW   = 60
DEFAULT_BREADTH_WINDOW       = 10
DEFAULT_MAX_MARKETS          = 500
DEFAULT_MAX_ANALYZERS        = 200
DEFAULT_CONFIDENCE_THRESHOLD = 0.50
MIN_HISTORY_FOR_REGIME       = 10
MIN_HISTORY_FOR_VOLATILITY   = 5
ANNUAL_TRADING_DAYS          = 252.0
