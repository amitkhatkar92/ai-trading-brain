"""iios/investment/portfolio/construction/construction_types.py

Shared enumerations and type constants for the Portfolio Construction Engine.
Every enum in this module is a (str, Enum) for JSON-serialisable values.
"""
from __future__ import annotations

from enum import Enum


class ConstructionStatus(str, Enum):
    """Lifecycle state of a single portfolio construction run."""

    PENDING     = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED   = "completed"
    FAILED      = "failed"
    CANCELLED   = "cancelled"
    STALE       = "stale"

    @property
    def is_terminal(self) -> bool:
        return self in (
            ConstructionStatus.COMPLETED,
            ConstructionStatus.FAILED,
            ConstructionStatus.CANCELLED,
        )

    @property
    def is_successful(self) -> bool:
        return self == ConstructionStatus.COMPLETED


class ConstructionType(str, Enum):
    """Portfolio construction methodology — determines how positions are combined."""

    LONG_ONLY      = "long_only"        # Long positions only, fully invested
    LONG_SHORT     = "long_short"       # Long + short positions with net long bias
    MARKET_NEUTRAL = "market_neutral"   # Long/short with ~zero net exposure
    SECTOR         = "sector"           # Single-sector concentration
    ETF_LIKE       = "etf_like"         # Broad, index-replicating style
    MULTI_ASSET    = "multi_asset"      # Multiple asset classes
    INCOME         = "income"           # Dividend / yield focused
    GROWTH         = "growth"           # Capital appreciation focused
    CUSTOM         = "custom"           # Custom / pluggable template


class WeightingMethod(str, Enum):
    """Deterministic weight-assignment methodology — no optimisation."""

    EQUAL         = "equal"           # 1/N per holding (investable fraction)
    CONVICTION    = "conviction"      # Proportional to recommendation conviction
    CONFIDENCE    = "confidence"      # Proportional to decision confidence
    RISK_ADJUSTED = "risk_adjusted"   # confidence × (1 − risk_score)
    SECTOR_EQUAL  = "sector_equal"    # Equal weight per sector, equal sectors
    COMPOSITE     = "composite"       # 40% conviction + 40% confidence + 20% risk-adj
    MANUAL        = "manual"          # Weights supplied in the recommendation


class ConstructionDirection(str, Enum):
    """Direction of a portfolio holding."""

    LONG    = "long"
    SHORT   = "short"
    NEUTRAL = "neutral"


class SelectionCriterion(str, Enum):
    """Primary ranking criterion used when selecting securities."""

    CONVICTION    = "conviction"
    CONFIDENCE    = "confidence"
    RISK_ADJUSTED = "risk_adjusted"
    COMPOSITE     = "composite"


class ConstraintType(str, Enum):
    """Category of an institutional portfolio constraint."""

    MAX_HOLDINGS      = "max_holdings"
    MIN_HOLDINGS      = "min_holdings"
    MAX_WEIGHT        = "max_weight"
    MIN_WEIGHT        = "min_weight"
    SECTOR_LIMIT      = "sector_limit"
    INDUSTRY_LIMIT    = "industry_limit"
    ASSET_CLASS_LIMIT = "asset_class_limit"
    LIQUIDITY         = "liquidity"
    MARKET_CAP        = "market_cap"
    ESG               = "esg"
    CASH_RESERVE      = "cash_reserve"
    LEVERAGE          = "leverage"
    CUSTOM            = "custom"


class ConstraintSeverity(str, Enum):
    """How strictly a constraint must be honoured."""

    HARD = "hard"   # Must not be violated — blocks construction
    SOFT = "soft"   # Should not be violated; override requires explicit reason
    INFO = "info"   # Informational / monitoring only


class ConstraintOutcome(str, Enum):
    """Result of evaluating a single constraint against a blueprint."""

    PASSED      = "passed"
    VIOLATED    = "violated"
    WARNING     = "warning"
    NOT_CHECKED = "not_checked"

    @property
    def is_blocking(self) -> bool:
        return self == ConstraintOutcome.VIOLATED


class ValidationCategory(str, Enum):
    """High-level category of a validation rule."""

    COMPLETENESS          = "completeness"
    CONSISTENCY           = "consistency"
    CONSTRAINT_COMPLIANCE = "constraint_compliance"
    POLICY_COMPLIANCE     = "policy_compliance"
    INTEGRITY             = "integrity"
    READINESS             = "readiness"


class ValidationOutcome(str, Enum):
    """Result of a single validation check."""

    PASSED  = "passed"
    WARNING = "warning"
    FAILED  = "failed"

    @property
    def is_blocking(self) -> bool:
        return self == ValidationOutcome.FAILED


class QualityDimension(str, Enum):
    """Dimensions contributing to the overall construction quality score."""

    COMPLETENESS             = "completeness"
    CONSISTENCY              = "consistency"
    CONSTRAINT_COMPLIANCE    = "constraint_compliance"
    RECOMMENDATION_ALIGNMENT = "recommendation_alignment"
    POLICY_COMPLIANCE        = "policy_compliance"
    DIVERSITY                = "diversity"
    READINESS                = "readiness"


class AssetClass(str, Enum):
    """Canonical asset class taxonomy used throughout construction."""

    EQUITY      = "equity"
    DEBT        = "debt"
    COMMODITY   = "commodity"
    CURRENCY    = "currency"
    REAL_ESTATE = "real_estate"
    DERIVATIVE  = "derivative"
    CASH        = "cash"
    ALTERNATIVE = "alternative"
    UNKNOWN     = "unknown"


class MarketCapCategory(str, Enum):
    """Market capitalisation classification."""

    LARGE_CAP = "large_cap"
    MID_CAP   = "mid_cap"
    SMALL_CAP = "small_cap"
    MICRO_CAP = "micro_cap"
    UNKNOWN   = "unknown"


class HealthStatus(str, Enum):
    """Operational health of the construction engine or a portfolio."""

    HEALTHY   = "healthy"
    DEGRADED  = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN   = "unknown"


# ---------------------------------------------------------------------------
# Numeric constants
# ---------------------------------------------------------------------------

#: Minimum weight any single holding may carry (0.1%)
MIN_SLOT_WEIGHT: float = 0.001

#: Maximum iterations for weight-capping redistribution
WEIGHT_CAP_MAX_ITER: int = 20

#: Tolerance for weight normalisation checks (sum must be within this of 1.0)
WEIGHT_SUM_TOLERANCE: float = 1e-6

#: Schema version for PortfolioBlueprint serialisation
BLUEPRINT_SCHEMA_VERSION: str = "1.0.0"

#: Schema version for ConstructionResult serialisation
RESULT_SCHEMA_VERSION: str = "1.0.0"
