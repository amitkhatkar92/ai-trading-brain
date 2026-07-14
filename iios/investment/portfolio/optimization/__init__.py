"""iios/investment/portfolio/optimization

Institutional Portfolio Optimization Engine (IPOE).

Exports all public symbols from the optimization package.
"""
# Types & constants
from iios.investment.portfolio.optimization.optimization_types import (
    ConvergenceStatus,
    ObjectiveType,
    OptimizationMethod,
    OptimizationQualityGrade,
    OptimizationRunStatus,
    WeightChangeStatus,
    OPTIMIZATION_PLAN_SCHEMA_VERSION,
    OPTIMIZATION_RESULT_SCHEMA_VERSION,
    DEFAULT_RISK_AVERSION,
    DEFAULT_MAX_ITERATIONS,
    DEFAULT_MIN_WEIGHT,
    DEFAULT_MAX_WEIGHT,
    DEFAULT_QUALITY_GATE,
    WEIGHT_SUM_TOLERANCE,
)

# Plan / result types
from iios.investment.portfolio.optimization.optimization_plan import (
    OptimizationObjective,
    OptimizedPosition,
    OptimizationRequest,
    OptimizationPlan,
    OptimizationResult,
)

# Constraints
from iios.investment.portfolio.optimization.optimization_constraints import (
    ConstraintSeverity,
    ConstraintType,
    OptimizationConstraint,
    OptimizationConstraintSet,
    budget_constraint,
    default_constraint_set,
    leverage_constraint,
    position_weight_constraint,
    sector_constraint,
    turnover_constraint,
)

# Core engine components
from iios.investment.portfolio.optimization.optimization_engine import (
    AssetProxy,
    ConvergenceResult,
    OptimizationAlgorithm,
)
from iios.investment.portfolio.optimization.optimization_registry import (
    OptimizationRegistry,
    get_default_registry,
)
from iios.investment.portfolio.optimization.constraint_solver import (
    ConstraintAdjustment,
    ConstraintSolution,
    ConstraintSolver,
)
from iios.investment.portfolio.optimization.constraint_validator import (
    ConstraintCheck,
    ConstraintValidationReport,
    ConstraintValidator,
)
from iios.investment.portfolio.optimization.objective_engine import (
    ObjectiveEvaluation,
    ObjectiveEvaluator,
)
from iios.investment.portfolio.optimization.optimization_validator import (
    OptimizationValidationReport,
    OptimizationValidator,
    ValidationFinding,
)
from iios.investment.portfolio.optimization.optimization_quality import (
    OptimizationDimensionScore,
    OptimizationQualityAssessor,
    OptimizationQualityReport,
)
from iios.investment.portfolio.optimization.optimization_score import (
    OptimizationScore,
    OptimizationScoreCalculator,
    OptimizationScoreHistory,
)
from iios.investment.portfolio.optimization.optimization_metrics import (
    OptimizationMetrics,
    compute_optimization_metrics,
)
from iios.investment.portfolio.optimization.optimization_health import (
    HealthStatus,
    OptimizationHealthCheck,
    OptimizationHealthMonitor,
    OptimizationHealthReport,
)
from iios.investment.portfolio.optimization.optimization_policy import (
    AGGRESSIVE_OPTIMIZATION_POLICY,
    BALANCED_OPTIMIZATION_POLICY,
    CONSERVATIVE_OPTIMIZATION_POLICY,
    RISK_PARITY_POLICY,
    OptimizationPolicy,
)
from iios.investment.portfolio.optimization.optimization_snapshot import (
    OptimizationHistory,
    OptimizationRecord,
    OptimizationSnapshot,
    OptimizedHolding,
)
from iios.investment.portfolio.optimization.optimization_statistics import (
    OptimizationRunMetric,
    OptimizationStatistics,
    OptimizationStatisticsSnapshot,
)
from iios.investment.portfolio.optimization.optimization_readiness import (
    OptimizationReadinessAssessment,
    OptimizationReadinessValidator,
)

# Main engine
from iios.investment.portfolio.optimization.portfolio_optimization_engine import (
    OptimizationIntegrationRefs,
    PortfolioOptimizationEngine,
)

__all__ = [
    # types
    "ConvergenceStatus",
    "ObjectiveType",
    "OptimizationMethod",
    "OptimizationQualityGrade",
    "OptimizationRunStatus",
    "WeightChangeStatus",
    "OPTIMIZATION_PLAN_SCHEMA_VERSION",
    "OPTIMIZATION_RESULT_SCHEMA_VERSION",
    "DEFAULT_RISK_AVERSION",
    "DEFAULT_MAX_ITERATIONS",
    "DEFAULT_MIN_WEIGHT",
    "DEFAULT_MAX_WEIGHT",
    "DEFAULT_QUALITY_GATE",
    "WEIGHT_SUM_TOLERANCE",
    # plan
    "OptimizationObjective",
    "OptimizedPosition",
    "OptimizationRequest",
    "OptimizationPlan",
    "OptimizationResult",
    # constraints
    "ConstraintSeverity",
    "ConstraintType",
    "OptimizationConstraint",
    "OptimizationConstraintSet",
    "budget_constraint",
    "default_constraint_set",
    "leverage_constraint",
    "position_weight_constraint",
    "sector_constraint",
    "turnover_constraint",
    # engine components
    "AssetProxy",
    "ConvergenceResult",
    "OptimizationAlgorithm",
    "OptimizationRegistry",
    "get_default_registry",
    "ConstraintAdjustment",
    "ConstraintSolution",
    "ConstraintSolver",
    "ConstraintCheck",
    "ConstraintValidationReport",
    "ConstraintValidator",
    "ObjectiveEvaluation",
    "ObjectiveEvaluator",
    "ValidationFinding",
    "OptimizationValidationReport",
    "OptimizationValidator",
    "OptimizationDimensionScore",
    "OptimizationQualityAssessor",
    "OptimizationQualityReport",
    "OptimizationScore",
    "OptimizationScoreCalculator",
    "OptimizationScoreHistory",
    "OptimizationMetrics",
    "compute_optimization_metrics",
    # health
    "HealthStatus",
    "OptimizationHealthCheck",
    "OptimizationHealthMonitor",
    "OptimizationHealthReport",
    # policy
    "AGGRESSIVE_OPTIMIZATION_POLICY",
    "BALANCED_OPTIMIZATION_POLICY",
    "CONSERVATIVE_OPTIMIZATION_POLICY",
    "RISK_PARITY_POLICY",
    "OptimizationPolicy",
    # snapshot / history
    "OptimizationHistory",
    "OptimizationRecord",
    "OptimizationSnapshot",
    "OptimizedHolding",
    # statistics
    "OptimizationRunMetric",
    "OptimizationStatistics",
    "OptimizationStatisticsSnapshot",
    # readiness
    "OptimizationReadinessAssessment",
    "OptimizationReadinessValidator",
    # main engine
    "OptimizationIntegrationRefs",
    "PortfolioOptimizationEngine",
]

