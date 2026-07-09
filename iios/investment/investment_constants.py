"""iios/investment/investment_constants.py
Investment Intelligence Engine Core constants.
Error-code prefix: II-
"""
from __future__ import annotations

from enum import Enum


class AssetClass(str, Enum):
    EQUITY           = "equity"
    ETF              = "etf"
    INDEX            = "index"
    MUTUAL_FUND      = "mutual_fund"
    BOND             = "bond"
    COMMODITY        = "commodity"
    CURRENCY         = "currency"
    CRYPTO           = "crypto"
    DERIVATIVE       = "derivative"
    OPTION           = "option"
    FUTURE           = "future"
    STRUCTURED       = "structured"


class InvestmentObjective(str, Enum):
    GROWTH       = "growth"
    INCOME       = "income"
    PRESERVATION = "preservation"
    BALANCED     = "balanced"
    SPECULATION  = "speculation"
    HEDGING      = "hedging"


class TimeHorizon(str, Enum):
    INTRADAY     = "intraday"        # < 1 day
    SHORT_TERM   = "short_term"      # 1 day – 3 months
    MEDIUM_TERM  = "medium_term"     # 3 months – 1 year
    LONG_TERM    = "long_term"       # 1 – 5 years
    VERY_LONG    = "very_long"       # > 5 years


class RiskProfile(str, Enum):
    CONSERVATIVE = "conservative"
    MODERATE     = "moderate"
    AGGRESSIVE   = "aggressive"
    SPECULATIVE  = "speculative"


class IntelligenceType(str, Enum):
    """Domain engines that can plug into the Investment Intelligence Engine."""
    MARKET      = "market"
    COMPANY     = "company"
    SECTOR      = "sector"
    MACRO       = "macro"
    PORTFOLIO   = "portfolio"
    STRATEGY    = "strategy"
    RISK        = "risk"
    EXECUTION   = "execution"
    CUSTOM      = "custom"


class AnalysisStatus(str, Enum):
    PENDING     = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED   = "completed"
    FAILED      = "failed"
    CANCELLED   = "cancelled"
    EXPIRED     = "expired"


class WorkflowStatus(str, Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    CANCELLED = "cancelled"


class SessionStatus(str, Enum):
    ACTIVE    = "active"
    CLOSED    = "closed"
    EXPIRED   = "expired"


INVESTMENT_ENGINE_VERSION   = "1.0.0"
INVESTMENT_ENGINE_SYSTEM_ID = "iios:investment:engine"

MAX_REGISTRY_SIZE           = 10_000
MAX_HISTORY_SIZE            = 50_000
MAX_SESSION_RESULTS         = 1_000
DEFAULT_WORKFLOW_TIMEOUT_SEC = 30.0
DEFAULT_MAX_WORKERS         = 4
DEFAULT_CONFIDENCE          = 0.0
