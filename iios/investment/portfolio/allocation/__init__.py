"""iios/investment/portfolio/allocation/__init__.py

Public surface of the Portfolio Allocation package.
Old (legacy) engine symbols are preserved for backward compatibility.
New Institutional Portfolio Allocation Engine symbols are exported here.
"""

# ── Legacy (backward-compatible) ─────────────────────────────────────────────
from iios.investment.portfolio.allocation.allocation_constraints import AllocationConstraints
from iios.investment.portfolio.allocation.allocation_report import AllocationReport
from iios.investment.portfolio.allocation.capital_allocator import CapitalAllocator
from iios.investment.portfolio.allocation.allocation_engine import AllocationEngine

# ── Types / constants ─────────────────────────────────────────────────────────
from iios.investment.portfolio.allocation.allocation_types import (
    AllocationMethod,
    AllocationRunStatus,
    AllocationDirection,
    CapitalDistributionStatus,
    AllocationQualityGrade,
    ExposureStatus,
    MIN_POSITION_DOLLARS,
    CAPITAL_CONSERVATION_TOLERANCE,
    ALLOCATION_PLAN_SCHEMA_VERSION,
    ALLOCATION_RESULT_SCHEMA_VERSION,
    DEFAULT_CASH_RESERVE_PCT,
    DEFAULT_MAX_POSITION_WEIGHT,
    DEFAULT_MIN_POSITION_WEIGHT,
)

# ── Plan models ───────────────────────────────────────────────────────────────
from iios.investment.portfolio.allocation.allocation_plan import (
    PositionAllocation,
    CashAllocation,
    AllocationRequest,
    AllocationPlan,
    AllocationResult,
)

# ── Snapshot + history ────────────────────────────────────────────────────────
from iios.investment.portfolio.allocation.allocation_snapshot import (
    AllocationHolding,
    AllocationSnapshot,
)
from iios.investment.portfolio.allocation.allocation_history import (
    AllocationRecord,
    AllocationHistory,
)

# ── Statistics ────────────────────────────────────────────────────────────────
from iios.investment.portfolio.allocation.allocation_statistics import (
    AllocationRunMetric,
    AllocationStatisticsSnapshot,
    AllocationStatistics,
)

# ── Policy ────────────────────────────────────────────────────────────────────
from iios.investment.portfolio.allocation.allocation_policy import (
    CashPolicy,
    PositionSizingPolicy,
    ExposurePolicy,
    AllocationPolicy,
    CONSERVATIVE_POLICY,
    BALANCED_POLICY,
    AGGRESSIVE_POLICY,
)

# ── Rules ─────────────────────────────────────────────────────────────────────
from iios.investment.portfolio.allocation.allocation_rules import (
    AllocationRule,
    AllocationRuleApplication,
    MinPositionSizeRule,
    MaxPositionCapRule,
    CashReserveRule,
    NegativeLongBlockRule,
    default_rule_chain,
)

# ── Exposure limits ───────────────────────────────────────────────────────────
from iios.investment.portfolio.allocation.exposure_limits import (
    ExposureCheck,
    ExposureLimitChecker,
)

# ── Allocators ────────────────────────────────────────────────────────────────
from iios.investment.portfolio.allocation.position_allocator import PositionAllocator
from iios.investment.portfolio.allocation.cash_manager import CashPosition, CashManager

# ── Validation ────────────────────────────────────────────────────────────────
from iios.investment.portfolio.allocation.allocation_validator import (
    AllocationFinding,
    AllocationValidationReport,
    AllocationValidator,
    build_allocation_report,
)

# ── Quality ───────────────────────────────────────────────────────────────────
from iios.investment.portfolio.allocation.allocation_quality import (
    AllocationDimensionScore,
    AllocationQualityReport,
    AllocationQualityAssessor,
)

# ── Score ─────────────────────────────────────────────────────────────────────
from iios.investment.portfolio.allocation.allocation_score import (
    AllocationScore,
    AllocationScoreCalculator,
    AllocationScoreHistory,
)

# ── Metrics ───────────────────────────────────────────────────────────────────
from iios.investment.portfolio.allocation.allocation_metrics import (
    AllocationMetrics,
    compute_allocation_metrics,
)

# ── Health ────────────────────────────────────────────────────────────────────
from iios.investment.portfolio.allocation.allocation_health import (
    HealthStatus,
    AllocationHealthCheck,
    AllocationHealthReport,
    AllocationHealthMonitor,
)

# ── Readiness ─────────────────────────────────────────────────────────────────
from iios.investment.portfolio.allocation.allocation_readiness import (
    AllocationReadinessAssessment,
    AllocationReadinessValidator,
)

# ── Engine ────────────────────────────────────────────────────────────────────
from iios.investment.portfolio.allocation.portfolio_allocation_engine import (
    AllocationIntegrationRefs,
    PortfolioAllocationEngine,
)

__all__ = [
    # Legacy
    "AllocationConstraints", "AllocationReport", "CapitalAllocator", "AllocationEngine",

    # Types
    "AllocationMethod", "AllocationRunStatus", "AllocationDirection",
    "CapitalDistributionStatus", "AllocationQualityGrade", "ExposureStatus",
    "MIN_POSITION_DOLLARS", "CAPITAL_CONSERVATION_TOLERANCE",
    "ALLOCATION_PLAN_SCHEMA_VERSION", "ALLOCATION_RESULT_SCHEMA_VERSION",
    "DEFAULT_CASH_RESERVE_PCT", "DEFAULT_MAX_POSITION_WEIGHT", "DEFAULT_MIN_POSITION_WEIGHT",

    # Plan models
    "PositionAllocation", "CashAllocation", "AllocationRequest",
    "AllocationPlan", "AllocationResult",

    # Snapshot + history
    "AllocationHolding", "AllocationSnapshot",
    "AllocationRecord", "AllocationHistory",

    # Statistics
    "AllocationRunMetric", "AllocationStatisticsSnapshot", "AllocationStatistics",

    # Policy
    "CashPolicy", "PositionSizingPolicy", "ExposurePolicy", "AllocationPolicy",
    "CONSERVATIVE_POLICY", "BALANCED_POLICY", "AGGRESSIVE_POLICY",

    # Rules
    "AllocationRule", "AllocationRuleApplication",
    "MinPositionSizeRule", "MaxPositionCapRule",
    "CashReserveRule", "NegativeLongBlockRule", "default_rule_chain",

    # Exposure
    "ExposureCheck", "ExposureLimitChecker",

    # Allocators
    "PositionAllocator", "CashPosition", "CashManager",

    # Validation
    "AllocationFinding", "AllocationValidationReport",
    "AllocationValidator", "build_allocation_report",

    # Quality
    "AllocationDimensionScore", "AllocationQualityReport", "AllocationQualityAssessor",

    # Score
    "AllocationScore", "AllocationScoreCalculator", "AllocationScoreHistory",

    # Metrics
    "AllocationMetrics", "compute_allocation_metrics",

    # Health
    "HealthStatus", "AllocationHealthCheck", "AllocationHealthReport", "AllocationHealthMonitor",

    # Readiness
    "AllocationReadinessAssessment", "AllocationReadinessValidator",

    # Engine
    "AllocationIntegrationRefs", "PortfolioAllocationEngine",
]
