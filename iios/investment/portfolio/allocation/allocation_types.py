"""iios/investment/portfolio/allocation/allocation_types.py

Shared enumerations and constants for the Portfolio Allocation Engine.
All enums are (str, Enum) for JSON-serialisable values.
"""
from __future__ import annotations

from enum import Enum


class AllocationMethod(str, Enum):
    """Methodology used to distribute capital across holdings."""

    BLUEPRINT_WEIGHT  = "blueprint_weight"   # Use blueprint target_weight directly
    EQUAL             = "equal"              # Equal dollars per holding
    CONVICTION        = "conviction"         # Proportional to conviction score
    CONFIDENCE        = "confidence"         # Proportional to confidence score
    RISK_ADJUSTED     = "risk_adjusted"      # confidence × (1 − risk_score)
    VOLATILITY        = "volatility"         # Inverse volatility (requires vol estimates)
    MARKET_CAP        = "market_cap"         # Proportional to market cap tier weight
    COMPOSITE         = "composite"          # Weighted blend of conviction+confidence+quality
    MANUAL            = "manual"             # Weights explicitly provided in request
    CUSTOM            = "custom"             # Pluggable custom allocator


class AllocationRunStatus(str, Enum):
    """Lifecycle of a single allocation run."""

    PENDING     = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED   = "completed"
    FAILED      = "failed"
    CANCELLED   = "cancelled"

    @property
    def is_terminal(self) -> bool:
        return self in (
            AllocationRunStatus.COMPLETED,
            AllocationRunStatus.FAILED,
            AllocationRunStatus.CANCELLED,
        )

    @property
    def is_successful(self) -> bool:
        return self == AllocationRunStatus.COMPLETED


class AllocationDirection(str, Enum):
    """Direction of a position allocation."""

    LONG    = "long"
    SHORT   = "short"
    CASH    = "cash"
    NEUTRAL = "neutral"


class CapitalDistributionStatus(str, Enum):
    """Summary status of the capital distribution."""

    FULLY_INVESTED  = "fully_invested"    # ≥ 95% deployed
    PARTIALLY_INVESTED = "partially_invested"  # 50–95% deployed
    UNDER_INVESTED  = "under_invested"    # < 50% deployed
    OVER_ALLOCATED  = "over_allocated"    # > 100% (leverage)
    CASH_HEAVY      = "cash_heavy"        # cash > 30%
    UNKNOWN         = "unknown"

    @property
    def is_healthy(self) -> bool:
        return self in (
            CapitalDistributionStatus.FULLY_INVESTED,
            CapitalDistributionStatus.PARTIALLY_INVESTED,
        )


class AllocationQualityGrade(str, Enum):
    """Letter grade for overall allocation quality."""

    A = "A"   # ≥ 0.90
    B = "B"   # ≥ 0.75
    C = "C"   # ≥ 0.60
    D = "D"   # ≥ 0.45
    F = "F"   # < 0.45


class ExposureStatus(str, Enum):
    """Compliance status of an exposure dimension."""

    WITHIN_LIMITS = "within_limits"
    AT_LIMIT      = "at_limit"
    OVER_LIMIT    = "over_limit"
    UNKNOWN       = "unknown"

    @property
    def is_compliant(self) -> bool:
        return self in (ExposureStatus.WITHIN_LIMITS, ExposureStatus.AT_LIMIT)


# ---------------------------------------------------------------------------
# Numeric constants
# ---------------------------------------------------------------------------

#: Minimum dollar amount for a position to be included
MIN_POSITION_DOLLARS: float = 1.0

#: Tolerance for capital conservation check (sum of allocations vs total_capital)
CAPITAL_CONSERVATION_TOLERANCE: float = 0.01   # $0.01

#: Schema version for AllocationPlan serialisation
ALLOCATION_PLAN_SCHEMA_VERSION: str = "1.0.0"

#: Schema version for AllocationResult serialisation
ALLOCATION_RESULT_SCHEMA_VERSION: str = "1.0.0"

#: Default minimum cash reserve as fraction of total capital
DEFAULT_CASH_RESERVE_PCT: float = 0.05

#: Default maximum single-position weight
DEFAULT_MAX_POSITION_WEIGHT: float = 0.15

#: Default minimum single-position weight
DEFAULT_MIN_POSITION_WEIGHT: float = 0.005
