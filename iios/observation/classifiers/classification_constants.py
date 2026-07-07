"""
iios/observation/classifiers/classification_constants.py
=========================================================
Enumerations and constants for the Observation Classification Engine.
"""
from __future__ import annotations

from enum import Enum
from typing import Final

__all__ = [
    "EntityType", "EventType", "AssetClass", "Sector",
    "TimeHorizon", "Importance", "RiskLevel", "Geography",
    "ClassificationStatus", "OntologyCategory",
    "MIN_CLASSIFICATION_CONFIDENCE",
    "DEFAULT_CLASSIFIER_WEIGHT",
    "MAX_CLASSIFICATION_LABELS",
    "CLASSIFICATION_NAMESPACE",
    "SYSTEM_CLASSIFIER",
]


class EntityType(str, Enum):
    """Type of the primary entity referenced in the observation."""
    INSTRUMENT       = "instrument"
    INDEX            = "index"
    SECTOR           = "sector"
    CURRENCY         = "currency"
    COMMODITY        = "commodity"
    FUND             = "fund"
    DERIVATIVE       = "derivative"
    EXCHANGE         = "exchange"
    COMPANY          = "company"
    PERSON           = "person"
    EVENT            = "event"
    SYSTEM           = "system"
    PORTFOLIO        = "portfolio"
    STRATEGY         = "strategy"
    UNKNOWN          = "unknown"


class EventType(str, Enum):
    """Specific financial/system event this observation represents."""
    PRICE_MOVE       = "price_move"
    VOLUME_SPIKE     = "volume_spike"
    BREAKOUT         = "breakout"
    EARNINGS_RELEASE = "earnings_release"
    DIVIDEND         = "dividend"
    STOCK_SPLIT      = "stock_split"
    MERGER_ACQUISITION = "merger_acquisition"
    IPO              = "ipo"
    REGULATORY       = "regulatory"
    MACRO_RELEASE    = "macro_release"
    NEWS_BREAK       = "news_break"
    MARKET_OPEN      = "market_open"
    MARKET_CLOSE     = "market_close"
    CIRCUIT_BREAKER  = "circuit_breaker"
    ORDER_PLACED     = "order_placed"
    ORDER_FILLED     = "order_filled"
    RISK_BREACH      = "risk_breach"
    SYSTEM_EVENT     = "system_event"
    UNKNOWN          = "unknown"


class AssetClass(str, Enum):
    """Broad asset class of the primary instrument."""
    EQUITY           = "equity"
    FIXED_INCOME     = "fixed_income"
    DERIVATIVE       = "derivative"
    FOREX            = "forex"
    COMMODITY        = "commodity"
    CRYPTO           = "crypto"
    REAL_ESTATE      = "real_estate"
    CASH             = "cash"
    UNKNOWN          = "unknown"


class Sector(str, Enum):
    """Market sector classification (GICS-inspired)."""
    TECHNOLOGY       = "technology"
    FINANCIALS       = "financials"
    HEALTHCARE       = "healthcare"
    ENERGY           = "energy"
    CONSUMER_STAPLES = "consumer_staples"
    CONSUMER_DISC    = "consumer_discretionary"
    INDUSTRIALS      = "industrials"
    MATERIALS        = "materials"
    UTILITIES        = "utilities"
    COMMUNICATION    = "communication"
    REAL_ESTATE      = "real_estate"
    UNKNOWN          = "unknown"


class TimeHorizon(str, Enum):
    """Temporal scope the observation is relevant for."""
    TICK             = "tick"           # sub-second
    INTRADAY         = "intraday"       # <1 day
    DAILY            = "daily"
    WEEKLY           = "weekly"
    MONTHLY          = "monthly"
    QUARTERLY        = "quarterly"
    ANNUAL           = "annual"
    LONG_TERM        = "long_term"      # multi-year
    UNKNOWN          = "unknown"


class Importance(str, Enum):
    """Estimated importance / market impact of the observation."""
    CRITICAL         = "critical"
    HIGH             = "high"
    MEDIUM           = "medium"
    LOW              = "low"
    MINIMAL          = "minimal"


class RiskLevel(str, Enum):
    """Implied risk level of the event or observation."""
    EXTREME          = "extreme"
    HIGH             = "high"
    MEDIUM           = "medium"
    LOW              = "low"
    MINIMAL          = "minimal"


class Geography(str, Enum):
    """Primary geographic market the observation concerns."""
    INDIA            = "india"
    USA              = "usa"
    EUROPE           = "europe"
    ASIA_PACIFIC     = "asia_pacific"
    EMERGING         = "emerging"
    GLOBAL           = "global"
    UNKNOWN          = "unknown"


class ClassificationStatus(str, Enum):
    """Lifecycle state of the classification process."""
    UNCLASSIFIED     = "unclassified"
    IN_PROGRESS      = "in_progress"
    CLASSIFIED       = "classified"
    PARTIAL          = "partial"          # some dimensions failed
    FAILED           = "failed"
    SKIPPED          = "skipped"


class OntologyCategory(str, Enum):
    """Ontology domain for the observation."""
    FINANCIAL        = "financial"
    ECONOMIC         = "economic"
    CORPORATE        = "corporate"
    TECHNICAL        = "technical"
    FUNDAMENTAL      = "fundamental"
    SENTIMENT        = "sentiment"
    REGULATORY       = "regulatory"
    OPERATIONAL      = "operational"
    UNKNOWN          = "unknown"


# ── Numeric constants ─────────────────────────────────────────────────────────

MIN_CLASSIFICATION_CONFIDENCE: Final[float] = 0.30
DEFAULT_CLASSIFIER_WEIGHT:     Final[float] = 1.0
MAX_CLASSIFICATION_LABELS:     Final[int]   = 32
MAX_CLASSIFIER_HISTORY:        Final[int]   = 500

# ── String constants ──────────────────────────────────────────────────────────

CLASSIFICATION_NAMESPACE: Final[str] = "iios.classification"
SYSTEM_CLASSIFIER:        Final[str] = "iios:classifier:system"
CLASSIFICATION_ATTR_KEY:  Final[str] = "classification_output"
