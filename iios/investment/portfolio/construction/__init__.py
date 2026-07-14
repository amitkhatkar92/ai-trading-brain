"""iios/investment/portfolio/construction/__init__.py

Institutional Portfolio Construction Engine
============================================

Public surface of the construction package.

Primary entry point::

    from iios.investment.portfolio.construction import (
        PortfolioConstructionEngine,
        ConstructionRequest,
        ConstructionResult,
        InvestmentRecommendation,
    )

    engine = PortfolioConstructionEngine()
    engine.start()
    engine.register_portfolio("PF-001")
    result = engine.construct("PF-001", recommendations, request)
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------
from iios.investment.portfolio.construction.construction_types import (
    AssetClass,
    ConstructionDirection,
    ConstructionStatus,
    ConstructionType,
    ConstraintOutcome,
    ConstraintSeverity,
    ConstraintType,
    HealthStatus,
    MarketCapCategory,
    QualityDimension,
    SelectionCriterion,
    ValidationCategory,
    ValidationOutcome,
    WeightingMethod,
    BLUEPRINT_SCHEMA_VERSION,
    MIN_SLOT_WEIGHT,
    RESULT_SCHEMA_VERSION,
    WEIGHT_SUM_TOLERANCE,
)

# ---------------------------------------------------------------------------
# Blueprint models
# ---------------------------------------------------------------------------
from iios.investment.portfolio.construction.portfolio_blueprint import (
    ConstructionRequest,
    ConstructionResult,
    InvestmentRecommendation,
    PortfolioBlueprint,
    PortfolioSlot,
)

# ---------------------------------------------------------------------------
# Snapshot / history
# ---------------------------------------------------------------------------
from iios.investment.portfolio.construction.portfolio_snapshot import (
    HoldingRecord,
    PortfolioConstructionSnapshot,
)
from iios.investment.portfolio.construction.portfolio_history import (
    BlueprintRecord,
    PortfolioConstructionHistory,
)
from iios.investment.portfolio.construction.portfolio_statistics import (
    ConcentrationMetrics,
    PortfolioCompositionStats,
    QualityMetrics,
    compute_statistics,
)

# ---------------------------------------------------------------------------
# Construction framework
# ---------------------------------------------------------------------------
from iios.investment.portfolio.construction.construction_engine import (
    BlueprintAssembler,
    ConstructionEngine,
    EngineRunRecord,
    RuleChain,
    WeightAssigner,
)
from iios.investment.portfolio.construction.construction_policy import (
    InvestmentUniversePolicy,
    PolicyViolation,
)
from iios.investment.portfolio.construction.construction_rules import (
    CashReserveRule,
    ConstructionRule,
    MarketNeutralRule,
    MaxWeightCapRule,
    MinWeightFloorRule,
    RuleApplication,
)
from iios.investment.portfolio.construction.construction_constraints import (
    ConstraintDefinition,
)

# ---------------------------------------------------------------------------
# Security selection
# ---------------------------------------------------------------------------
from iios.investment.portfolio.construction.selection_policy import SelectionPolicy
from iios.investment.portfolio.construction.security_selector import (
    SecuritySelector,
    SelectionResult,
)
from iios.investment.portfolio.construction.selection_filters import (
    FilterChain,
    FilterResult,
)
from iios.investment.portfolio.construction.selection_history import (
    SelectionHistory,
    SelectionRecord,
)

# ---------------------------------------------------------------------------
# Constraint engine
# ---------------------------------------------------------------------------
from iios.investment.portfolio.construction.constraint_registry import ConstraintRegistry
from iios.investment.portfolio.construction.constraint_engine import (
    ConstraintEngine,
    ConstraintReport,
)
from iios.investment.portfolio.construction.constraint_history import ConstraintHistory
from iios.investment.portfolio.construction.constraint_validator import (
    ConstraintChecker,
    register_checker,
)

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
from iios.investment.portfolio.construction.validation_report import (
    ValidationFinding,
    ValidationReport,
    build_report,
)
from iios.investment.portfolio.construction.portfolio_validator import PortfolioValidator
from iios.investment.portfolio.construction.construction_validator import ConstructionValidator
from iios.investment.portfolio.construction.readiness_validator import (
    ReadinessAssessment,
    ReadinessValidator,
)

# ---------------------------------------------------------------------------
# Quality
# ---------------------------------------------------------------------------
from iios.investment.portfolio.construction.construction_quality import (
    ConstructionQualityAssessor,
    ConstructionQualityReport,
    DimensionScore,
)
from iios.investment.portfolio.construction.construction_score import (
    ConstructionScore,
    ScoreCalculator,
    ScoreHistory,
)
from iios.investment.portfolio.construction.construction_health import (
    ConstructionHealthMonitor,
    EngineHealthReport,
    HealthCheckResult,
)
from iios.investment.portfolio.construction.construction_statistics import (
    ConstructionStatistics,
    ConstructionStatisticsSnapshot,
    RunMetric,
)

# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------
from iios.investment.portfolio.construction.portfolio_construction_engine import (
    ConstructionIntegrationRefs,
    PortfolioConstructionEngine,
)

__all__ = [
    # Types
    "AssetClass",
    "ConstructionDirection",
    "ConstructionStatus",
    "ConstructionType",
    "ConstraintOutcome",
    "ConstraintSeverity",
    "ConstraintType",
    "HealthStatus",
    "MarketCapCategory",
    "QualityDimension",
    "SelectionCriterion",
    "ValidationCategory",
    "ValidationOutcome",
    "WeightingMethod",
    "BLUEPRINT_SCHEMA_VERSION",
    "MIN_SLOT_WEIGHT",
    "RESULT_SCHEMA_VERSION",
    "WEIGHT_SUM_TOLERANCE",
    # Blueprint models
    "ConstructionRequest",
    "ConstructionResult",
    "InvestmentRecommendation",
    "PortfolioBlueprint",
    "PortfolioSlot",
    # Snapshot / history
    "HoldingRecord",
    "PortfolioConstructionSnapshot",
    "BlueprintRecord",
    "PortfolioConstructionHistory",
    "ConcentrationMetrics",
    "PortfolioCompositionStats",
    "QualityMetrics",
    "compute_statistics",
    # Construction engine
    "BlueprintAssembler",
    "ConstructionEngine",
    "EngineRunRecord",
    "RuleChain",
    "WeightAssigner",
    # Policy
    "InvestmentUniversePolicy",
    "PolicyViolation",
    # Rules
    "CashReserveRule",
    "ConstructionRule",
    "MarketNeutralRule",
    "MaxWeightCapRule",
    "MinWeightFloorRule",
    "RuleApplication",
    "ConstraintDefinition",
    # Selection
    "SelectionPolicy",
    "SecuritySelector",
    "SelectionResult",
    "FilterChain",
    "FilterResult",
    "SelectionHistory",
    "SelectionRecord",
    # Constraints
    "ConstraintRegistry",
    "ConstraintEngine",
    "ConstraintReport",
    "ConstraintHistory",
    "ConstraintChecker",
    "register_checker",
    # Validation
    "ValidationFinding",
    "ValidationReport",
    "build_report",
    "PortfolioValidator",
    "ConstructionValidator",
    "ReadinessAssessment",
    "ReadinessValidator",
    # Quality
    "ConstructionQualityAssessor",
    "ConstructionQualityReport",
    "DimensionScore",
    "ConstructionScore",
    "ScoreCalculator",
    "ScoreHistory",
    "ConstructionHealthMonitor",
    "EngineHealthReport",
    "HealthCheckResult",
    "ConstructionStatistics",
    "ConstructionStatisticsSnapshot",
    "RunMetric",
    # Orchestrator
    "ConstructionIntegrationRefs",
    "PortfolioConstructionEngine",
]
