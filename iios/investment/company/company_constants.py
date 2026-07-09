"""iios/investment/company/company_constants.py"""
from __future__ import annotations

from enum import Enum


class CompanyStage(str, Enum):
    STARTUP           = "startup"
    GROWTH            = "growth"
    MATURE            = "mature"
    DECLINE           = "decline"
    TURNAROUND        = "turnaround"
    SPECIAL_SITUATION = "special_situation"
    UNKNOWN           = "unknown"


class SectorClassification(str, Enum):
    TECHNOLOGY             = "technology"
    FINANCIALS             = "financials"
    HEALTHCARE             = "healthcare"
    CONSUMER_DISCRETIONARY = "consumer_discretionary"
    CONSUMER_STAPLES       = "consumer_staples"
    ENERGY                 = "energy"
    MATERIALS              = "materials"
    INDUSTRIALS            = "industrials"
    UTILITIES              = "utilities"
    REAL_ESTATE            = "real_estate"
    COMMUNICATION          = "communication"
    UNKNOWN                = "unknown"


class BusinessModel(str, Enum):
    B2B          = "b2b"
    B2C          = "b2c"
    B2G          = "b2g"
    MARKETPLACE  = "marketplace"
    PLATFORM     = "platform"
    SUBSCRIPTION = "subscription"
    ASSET_LIGHT  = "asset_light"
    ASSET_HEAVY  = "asset_heavy"
    MIXED        = "mixed"
    UNKNOWN      = "unknown"


class FinancialHealth(str, Enum):
    VERY_STRONG = "very_strong"
    STRONG      = "strong"
    MODERATE    = "moderate"
    WEAK        = "weak"
    VERY_WEAK   = "very_weak"
    DISTRESSED  = "distressed"
    UNKNOWN     = "unknown"


class GrowthProfile(str, Enum):
    HIGH_GROWTH = "high_growth"
    GROWTH      = "growth"
    MODERATE    = "moderate"
    LOW_GROWTH  = "low_growth"
    DECLINING   = "declining"
    TURNAROUND  = "turnaround"
    UNKNOWN     = "unknown"


class ValuationStatus(str, Enum):
    DEEPLY_UNDERVALUED = "deeply_undervalued"
    UNDERVALUED        = "undervalued"
    FAIR_VALUE         = "fair_value"
    OVERVALUED         = "overvalued"
    DEEPLY_OVERVALUED  = "deeply_overvalued"
    UNKNOWN            = "unknown"


class OwnershipConcentration(str, Enum):
    CONCENTRATED = "concentrated"
    MODERATE     = "moderate"
    DISTRIBUTED  = "distributed"
    UNKNOWN      = "unknown"


class GovernanceQuality(str, Enum):
    EXCELLENT = "excellent"
    GOOD      = "good"
    FAIR      = "fair"
    POOR      = "poor"
    VERY_POOR = "very_poor"
    UNKNOWN   = "unknown"


class CorporateActionType(str, Enum):
    DIVIDEND     = "dividend"
    BONUS        = "bonus"
    SPLIT        = "split"
    BUYBACK      = "buyback"
    MERGER       = "merger"
    ACQUISITION  = "acquisition"
    DEMERGER     = "demerger"
    RIGHTS_ISSUE = "rights_issue"
    FPO          = "fpo"
    IPO          = "ipo"
    OTHER        = "other"


class ListingStatus(str, Enum):
    LISTED      = "listed"
    DELISTED    = "delisted"
    SUSPENDED   = "suspended"
    UNDER_WATCH = "under_watch"
    UNKNOWN     = "unknown"


class MarketCapCategory(str, Enum):
    LARGE   = "large"
    MID     = "mid"
    SMALL   = "small"
    MICRO   = "micro"
    NANO    = "nano"
    UNKNOWN = "unknown"


class CompanyIntelligenceStatus(str, Enum):
    ACTIVE   = "active"
    STALE    = "stale"
    UPDATING = "updating"
    FAILED   = "failed"
    UNKNOWN  = "unknown"


# ── Engine metadata ───────────────────────────────────────────────────────────
COMPANY_ENGINE_VERSION   = "1.0.0"
COMPANY_ENGINE_SYSTEM_ID = "iios:company:engine"

# ── Defaults ──────────────────────────────────────────────────────────────────
DEFAULT_HISTORY_SIZE          = 10_000
DEFAULT_SNAPSHOT_HISTORY      = 100
DEFAULT_MAX_COMPANIES         = 5_000
DEFAULT_MAX_ANALYZERS         = 200
DEFAULT_CONFIDENCE_THRESHOLD  = 0.50
DEFAULT_SNAPSHOT_TTL_SEC      = 3_600.0   # 1 hour

# ── Financial thresholds ──────────────────────────────────────────────────────
HIGH_GROWTH_THRESHOLD        = 0.20
MODERATE_GROWTH_THRESHOLD    = 0.10
HEALTHY_CURRENT_RATIO        = 1.50
HEALTHY_DEBT_EQUITY          = 1.00
HIGH_PROMOTER_THRESHOLD      = 0.50
LOW_INSTITUTIONAL_THRESHOLD  = 0.10
HIGH_PLEDGE_THRESHOLD        = 0.25
BIG4_FIRMS = frozenset({"deloitte", "pwc", "ey", "kpmg", "ernst", "pricewaterhouse"})
