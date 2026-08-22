"""iios/investment/strategy/strategy_constants.py
Constants and enumerations for the Strategy Intelligence Engine.
Error code prefix: SI-
"""
from __future__ import annotations

from enum import Enum


class StrategyCategory(str, Enum):
    """Broad strategy taxonomy — extensible via CUSTOM."""
    MOMENTUM         = "momentum"
    TREND_FOLLOWING  = "trend_following"
    MEAN_REVERSION   = "mean_reversion"
    BREAKOUT         = "breakout"
    RETEST           = "retest"
    SWING            = "swing"
    POSITION         = "position"
    OPTIONS          = "options"
    VOLATILITY       = "volatility"
    MARKET_NEUTRAL   = "market_neutral"
    LONG_ONLY        = "long_only"
    LONG_SHORT       = "long_short"
    SECTOR_ROTATION  = "sector_rotation"
    MACRO            = "macro"
    MULTI_FACTOR     = "multi_factor"
    CUSTOM           = "custom"
    UNKNOWN          = "unknown"


class StrategyStatus(str, Enum):
    """Full lifecycle state of a registered strategy."""
    DRAFT          = "draft"
    TESTING        = "testing"
    PAPER_TRADING  = "paper_trading"
    VALIDATION     = "validation"
    APPROVED       = "approved"
    PRODUCTION     = "production"
    SUSPENDED      = "suspended"
    DEPRECATED     = "deprecated"
    ARCHIVED       = "archived"
    RETIRED        = "retired"
    UNKNOWN        = "unknown"


class StrategyRiskLevel(str, Enum):
    VERY_LOW  = "very_low"
    LOW       = "low"
    MODERATE  = "moderate"
    HIGH      = "high"
    VERY_HIGH = "very_high"
    UNKNOWN   = "unknown"


class StrategyTimeframe(str, Enum):
    SCALP      = "scalp"         # < 1 hour
    INTRADAY   = "intraday"      # within 1 session
    SWING      = "swing"         # 2–20 days
    POSITIONAL = "positional"    # 20–90 days
    LONG_TERM  = "long_term"     # > 90 days
    UNKNOWN    = "unknown"


class AssetClass(str, Enum):
    EQUITY      = "equity"
    OPTIONS     = "options"
    FUTURES     = "futures"
    FOREX       = "forex"
    CRYPTO      = "crypto"
    BONDS       = "bonds"
    COMMODITIES = "commodities"
    MIXED       = "mixed"
    UNKNOWN     = "unknown"


class MarketRegime(str, Enum):
    BULL            = "bull"
    BEAR            = "bear"
    SIDEWAYS        = "sideways"
    VOLATILE        = "volatile"
    TRENDING        = "trending"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY  = "low_volatility"
    UNKNOWN         = "unknown"


class RegimeCompatibility(str, Enum):
    OPTIMAL      = "optimal"
    COMPATIBLE   = "compatible"
    NEUTRAL      = "neutral"
    SUBOPTIMAL   = "suboptimal"
    INCOMPATIBLE = "incompatible"
    UNKNOWN      = "unknown"


class StrategyGrade(str, Enum):
    A_PLUS  = "A+"
    A       = "A"
    B       = "B"
    C       = "C"
    D       = "D"
    F       = "F"
    UNKNOWN = "unknown"


class StrategyRecommendation(str, Enum):
    STRONG_INCLUDE = "strong_include"
    INCLUDE        = "include"
    MONITOR        = "monitor"
    REDUCE         = "reduce"
    EXCLUDE        = "exclude"
    UNKNOWN        = "unknown"


class LifecycleEvent(str, Enum):
    CREATED             = "created"
    STARTED_TESTING     = "started_testing"
    STARTED_PAPER       = "started_paper_trading"
    STARTED_VALIDATION  = "started_validation"
    APPROVED            = "approved"
    PROMOTED_PRODUCTION = "promoted_to_production"
    SUSPENDED           = "suspended"
    RESUMED             = "resumed"
    DEPRECATED          = "deprecated"
    ARCHIVED            = "archived"
    RETIRED             = "retired"
    PARAMETER_ADAPTED   = "parameter_adapted"
    REGIME_ADAPTED      = "regime_adapted"
    VERSION_BUMPED      = "version_bumped"
    EVALUATED           = "evaluated"


class AdaptationType(str, Enum):
    REGIME    = "regime"
    PARAMETER = "parameter"
    RISK      = "risk"
    VOLATILITY = "volatility"
    PERFORMANCE = "performance"
    CUSTOM    = "custom"


# ── Engine identity ────────────────────────────────────────────────────────────
STRATEGY_ENGINE_VERSION   = "1.0.0"
STRATEGY_ENGINE_SYSTEM_ID = "iios:strategy:engine"

# ── Registry limits ────────────────────────────────────────────────────────────
DEFAULT_MAX_STRATEGIES = 10_000
DEFAULT_MAX_VERSIONS   = 100

# ── History defaults ───────────────────────────────────────────────────────────
DEFAULT_HISTORY_SIZE     = 10_000
DEFAULT_SNAPSHOT_HISTORY = 200
DEFAULT_SNAPSHOT_TTL_SEC = 3_600.0

# ── Evaluation thresholds ──────────────────────────────────────────────────────
MIN_WIN_RATE        = 0.45     # 45 %
MIN_SHARPE          = 0.50
MAX_DRAWDOWN        = 0.25     # 25 %
MIN_TRADES_FOR_EVAL = 10
MIN_PROFIT_FACTOR   = 1.20
TARGET_WIN_RATE     = 0.55     # 55 %
TARGET_SHARPE       = 1.00
TARGET_DRAWDOWN     = 0.10     # 10 %

# ── Score weights (must sum to 1.0) ───────────────────────────────────────────
PERFORMANCE_WEIGHT = 0.40
RISK_WEIGHT        = 0.30
STABILITY_WEIGHT   = 0.20
REGIME_WEIGHT      = 0.10

# ── Valid lifecycle transitions ────────────────────────────────────────────────
LIFECYCLE_TRANSITIONS: dict[str, frozenset[str]] = {
    StrategyStatus.DRAFT.value:         frozenset({StrategyStatus.TESTING.value}),
    StrategyStatus.TESTING.value:       frozenset({StrategyStatus.PAPER_TRADING.value,
                                                    StrategyStatus.DRAFT.value}),
    StrategyStatus.PAPER_TRADING.value: frozenset({StrategyStatus.VALIDATION.value,
                                                    StrategyStatus.TESTING.value}),
    StrategyStatus.VALIDATION.value:    frozenset({StrategyStatus.APPROVED.value,
                                                    StrategyStatus.PAPER_TRADING.value}),
    StrategyStatus.APPROVED.value:      frozenset({StrategyStatus.PRODUCTION.value,
                                                    StrategyStatus.VALIDATION.value}),
    StrategyStatus.PRODUCTION.value:    frozenset({StrategyStatus.SUSPENDED.value,
                                                    StrategyStatus.DEPRECATED.value}),
    StrategyStatus.SUSPENDED.value:     frozenset({StrategyStatus.PRODUCTION.value,
                                                    StrategyStatus.DEPRECATED.value}),
    StrategyStatus.DEPRECATED.value:    frozenset({StrategyStatus.ARCHIVED.value,
                                                    StrategyStatus.RETIRED.value}),
    StrategyStatus.ARCHIVED.value:      frozenset({StrategyStatus.RETIRED.value}),
    StrategyStatus.RETIRED.value:       frozenset(),
}
