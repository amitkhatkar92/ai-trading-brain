"""iios/investment/portfolio/portfolio_constants.py"""
from __future__ import annotations

from enum import Enum


class PortfolioType(str, Enum):
    EQUITY               = "equity"
    FIXED_INCOME         = "fixed_income"
    MULTI_ASSET          = "multi_asset"
    DERIVATIVES          = "derivatives"
    COMMODITIES          = "commodities"
    CRYPTO               = "crypto"
    HEDGE                = "hedge"
    BALANCED             = "balanced"
    GROWTH               = "growth"
    INCOME               = "income"
    INDEX                = "index"
    ETF                  = "etf"
    CUSTOM               = "custom"
    UNKNOWN              = "unknown"


class PortfolioStatus(str, Enum):
    ACTIVE               = "active"
    INACTIVE             = "inactive"
    SUSPENDED            = "suspended"
    CLOSED               = "closed"
    DRAFT                = "draft"
    LIQUIDATING          = "liquidating"
    UNKNOWN              = "unknown"


class PortfolioObjective(str, Enum):
    GROWTH               = "growth"
    INCOME               = "income"
    CAPITAL_PRESERVATION = "capital_preservation"
    BALANCED             = "balanced"
    TOTAL_RETURN         = "total_return"
    SPECULATION          = "speculation"
    HEDGING              = "hedging"
    UNKNOWN              = "unknown"


class AssetClass(str, Enum):
    EQUITY               = "equity"
    DEBT                 = "debt"
    COMMODITY            = "commodity"
    CURRENCY             = "currency"
    REAL_ESTATE          = "real_estate"
    DERIVATIVE           = "derivative"
    CASH                 = "cash"
    ALTERNATIVE          = "alternative"
    UNKNOWN              = "unknown"


class RiskLevel(str, Enum):
    VERY_LOW             = "very_low"
    LOW                  = "low"
    MODERATE             = "moderate"
    HIGH                 = "high"
    VERY_HIGH            = "very_high"
    UNKNOWN              = "unknown"


class PositionType(str, Enum):
    LONG                 = "long"
    SHORT                = "short"
    FLAT                 = "flat"


class PositionStatus(str, Enum):
    OPEN                 = "open"
    CLOSED               = "closed"
    PARTIAL              = "partial"
    PENDING              = "pending"


class AllocationStatus(str, Enum):
    WITHIN_LIMITS        = "within_limits"
    OVERALLOCATED        = "overallocated"
    UNDERALLOCATED       = "underallocated"
    UNKNOWN              = "unknown"


class DrawdownSeverity(str, Enum):
    NONE                 = "none"
    MINOR                = "minor"
    MODERATE             = "moderate"
    SIGNIFICANT          = "significant"
    SEVERE               = "severe"
    CRITICAL             = "critical"


class PortfolioHealthStatus(str, Enum):
    EXCELLENT            = "excellent"
    GOOD                 = "good"
    FAIR                 = "fair"
    POOR                 = "poor"
    CRITICAL             = "critical"
    UNKNOWN              = "unknown"


class RiskCategory(str, Enum):
    MARKET               = "market"
    CREDIT               = "credit"
    LIQUIDITY            = "liquidity"
    OPERATIONAL          = "operational"
    CONCENTRATION        = "concentration"
    VOLATILITY           = "volatility"
    CORRELATION          = "correlation"
    TAIL                 = "tail"
    CURRENCY             = "currency"
    COUNTRY              = "country"
    COUNTERPARTY         = "counterparty"
    UNKNOWN              = "unknown"


class ExposureType(str, Enum):
    LONG                 = "long"
    SHORT                = "short"
    GROSS                = "gross"
    NET                  = "net"


# ── Engine metadata ───────────────────────────────────────────────────────────

PORTFOLIO_ENGINE_VERSION   = "1.0.0"
PORTFOLIO_ENGINE_SYSTEM_ID = "iios:portfolio:engine"

# ── Capacity ──────────────────────────────────────────────────────────────────

DEFAULT_BASE_CURRENCY          = "INR"
DEFAULT_MAX_PORTFOLIOS         = 1_000
DEFAULT_MAX_POSITIONS          = 10_000
DEFAULT_SNAPSHOT_HISTORY       = 200
DEFAULT_MAX_HISTORY            = 10_000
DEFAULT_SNAPSHOT_TTL_SEC       = 300.0

# ── Risk / allocation limits ──────────────────────────────────────────────────

DEFAULT_MAX_SINGLE_WEIGHT      = 0.25   # 25% max single position
DEFAULT_MIN_CASH_PCT           = 0.05   # 5% minimum cash
DEFAULT_MAX_SECTOR_PCT         = 0.40   # 40% max single sector
DEFAULT_MAX_COUNTRY_PCT        = 0.60   # 60% max single country
DEFAULT_MAX_ASSET_CLASS_PCT    = 0.80   # 80% max single asset class

# ── Drawdown severity thresholds (fractions) ──────────────────────────────────

DRAWDOWN_MINOR_THRESHOLD       = 0.02
DRAWDOWN_MODERATE_THRESHOLD    = 0.05
DRAWDOWN_SIGNIFICANT_THRESHOLD = 0.10
DRAWDOWN_SEVERE_THRESHOLD      = 0.20
DRAWDOWN_CRITICAL_THRESHOLD    = 0.35

# ── Health score thresholds ───────────────────────────────────────────────────

HEALTH_EXCELLENT_THRESHOLD     = 80.0
HEALTH_GOOD_THRESHOLD          = 65.0
HEALTH_FAIR_THRESHOLD          = 50.0
HEALTH_POOR_THRESHOLD          = 35.0
