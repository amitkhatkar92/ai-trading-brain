"""
iios/observation/enrichment/enrichment_constants.py
====================================================
Enumerations and constants for the Observation Enrichment Engine.
"""
from __future__ import annotations

from enum import Enum
from typing import Final

__all__ = [
    "EnricherStage", "EnricherCategory", "SemanticLabel", "LinkType", "ContextType",
    "MAX_TAGS", "MAX_KEYWORDS", "MAX_LINKS", "MAX_ENRICHMENT_HISTORY",
    "ENRICHMENT_NAMESPACE", "ENRICHMENT_ATTR_KEY",
]


class EnricherStage(str, Enum):
    """Pipeline stage when an enricher should run."""
    PRE       = "pre"        # before semantic analysis
    SEMANTIC  = "semantic"   # semantic labelling and keyword extraction
    CONTEXT   = "context"    # temporal and market context
    LINKING   = "linking"    # entity / xref / ontology links
    POST      = "post"       # final clean-up / normalisation


class EnricherCategory(str, Enum):
    """Functional category of an enricher."""
    TAG        = "tag"
    KEYWORD    = "keyword"
    SEMANTIC   = "semantic"
    TEMPORAL   = "temporal"
    ENTITY     = "entity"
    ONTOLOGY   = "ontology"
    XREF       = "xref"
    MARKET     = "market"


class SemanticLabel(str, Enum):
    """Trading-domain semantic labels applied during enrichment."""
    BULLISH              = "bullish"
    BEARISH              = "bearish"
    NEUTRAL              = "neutral"
    VOLATILE             = "volatile"
    TRENDING_UP          = "trending_up"
    TRENDING_DOWN        = "trending_down"
    MOMENTUM             = "momentum"
    REVERSAL             = "reversal"
    BREAKOUT             = "breakout"
    CONSOLIDATION        = "consolidation"
    OVERSOLD             = "oversold"
    OVERBOUGHT           = "overbought"
    HIGH_VOLUME          = "high_volume"
    LOW_LIQUIDITY        = "low_liquidity"
    POSITIVE_SURPRISE    = "positive_surprise"
    NEGATIVE_SURPRISE    = "negative_surprise"
    IN_LINE              = "in_line"
    RISK_ON              = "risk_on"
    RISK_OFF             = "risk_off"
    UNKNOWN              = "unknown"


class LinkType(str, Enum):
    """Type of cross-reference link from an observation to an entity."""
    ENTITY       = "entity"         # links to a company / instrument entity
    RELATIONSHIP = "relationship"   # links to a relationship
    EVENT        = "event"          # links to a calendar/corporate event
    KNOWLEDGE    = "knowledge"      # links to a knowledge graph node
    OBSERVATION  = "observation"    # links to another observation
    REGIME       = "regime"         # links to a market regime
    STRATEGY     = "strategy"       # links to a trading strategy
    RISK         = "risk"           # links to a risk factor


class ContextType(str, Enum):
    """Type of context attribute added by enrichers."""
    MARKET_SESSION = "market_session"
    TRADING_DAY    = "trading_day"
    MARKET_OPEN    = "market_open"
    WEEKDAY        = "weekday"
    QUARTER        = "quarter"
    MONTH          = "month"
    TIMESTAMP_ZONE = "timestamp_zone"


# ── Numeric constants ─────────────────────────────────────────────────────────

MAX_TAGS:               Final[int] = 50
MAX_KEYWORDS:           Final[int] = 20
MAX_LINKS:              Final[int] = 100
MAX_ENRICHMENT_HISTORY: Final[int] = 500

# ── String constants ──────────────────────────────────────────────────────────

ENRICHMENT_NAMESPACE: Final[str] = "iios.enrichment"
ENRICHMENT_ATTR_KEY:  Final[str] = "enrichment_output"
