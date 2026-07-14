"""iios/investment/portfolio/optimization/optimization_types.py

Shared enumerations and constants for the Portfolio Optimization Engine.
"""
from __future__ import annotations

from enum import Enum


class OptimizationMethod(str, Enum):
    """Algorithm used to compute optimal weights."""

    MEAN_VARIANCE             = "mean_variance"
    MINIMUM_VARIANCE          = "minimum_variance"
    MAXIMUM_SHARPE            = "maximum_sharpe"
    MAXIMUM_SORTINO           = "maximum_sortino"
    MAXIMUM_CALMAR            = "maximum_calmar"
    RISK_PARITY               = "risk_parity"
    EQUAL_RISK_CONTRIBUTION   = "equal_risk_contribution"
    MAXIMUM_DIVERSIFICATION   = "maximum_diversification"
    BLACK_LITTERMAN           = "black_litterman"
    HIERARCHICAL_RISK_PARITY  = "hierarchical_risk_parity"
    EQUAL_WEIGHT              = "equal_weight"
    MAXIMUM_UTILITY           = "maximum_utility"
    MINIMUM_TURNOVER          = "minimum_turnover"
    CUSTOM                    = "custom"


class ObjectiveType(str, Enum):
    """The optimization objective to maximize/minimize."""

    MAXIMIZE_RETURN          = "maximize_return"
    MINIMIZE_RISK            = "minimize_risk"
    MAXIMIZE_SHARPE          = "maximize_sharpe"
    MAXIMIZE_SORTINO         = "maximize_sortino"
    MAXIMIZE_CALMAR          = "maximize_calmar"
    MAXIMIZE_DIVERSIFICATION = "maximize_diversification"
    MINIMIZE_TURNOVER        = "minimize_turnover"
    MAXIMIZE_UTILITY         = "maximize_utility"
    MULTI_OBJECTIVE          = "multi_objective"


class OptimizationRunStatus(str, Enum):
    """Lifecycle status of a single optimization run."""

    PENDING     = "pending"
    IN_PROGRESS = "in_progress"
    CONVERGED   = "converged"
    PARTIAL     = "partial"      # Converged but with soft constraint violations
    FAILED      = "failed"
    CANCELLED   = "cancelled"

    @property
    def is_terminal(self) -> bool:
        return self in (
            OptimizationRunStatus.CONVERGED,
            OptimizationRunStatus.PARTIAL,
            OptimizationRunStatus.FAILED,
            OptimizationRunStatus.CANCELLED,
        )

    @property
    def is_successful(self) -> bool:
        return self in (OptimizationRunStatus.CONVERGED, OptimizationRunStatus.PARTIAL)


class ConstraintOutcome(str, Enum):
    """Result of a single constraint check."""

    SATISFIED = "satisfied"
    VIOLATED  = "violated"
    WARNING   = "warning"
    INFEASIBLE= "infeasible"


class OptimizationQualityGrade(str, Enum):
    """Letter grade for optimization quality."""

    A = "A"   # ≥ 0.90
    B = "B"   # ≥ 0.75
    C = "C"   # ≥ 0.60
    D = "D"   # ≥ 0.45
    F = "F"   # < 0.45


class ConvergenceStatus(str, Enum):
    """Numerical convergence status."""

    CONVERGED  = "converged"
    MAX_ITER   = "max_iter"
    DIVERGED   = "diverged"
    ANALYTICAL = "analytical"   # Closed-form solution — always converged
    TRIVIAL    = "trivial"      # e.g. single asset


class WeightChangeStatus(str, Enum):
    """How much the optimizer moved weights."""

    LARGE    = "large"    # > 20 % max absolute change
    MODERATE = "moderate" # 5–20 %
    SMALL    = "small"    # 1–5 %
    MINIMAL  = "minimal"  # < 1 % — essentially unchanged


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

OPTIMIZATION_PLAN_SCHEMA_VERSION:   str   = "1.0.0"
OPTIMIZATION_RESULT_SCHEMA_VERSION: str   = "1.0.0"

#: Default risk-aversion parameter for mean-variance (lambda)
DEFAULT_RISK_AVERSION:             float = 2.0

#: Default gradient-descent learning rate
DEFAULT_LEARNING_RATE:             float = 0.01

#: Default maximum gradient-descent iterations
DEFAULT_MAX_ITERATIONS:            int   = 1_000

#: Convergence tolerance (L∞ norm of weight change per step)
DEFAULT_CONVERGENCE_TOLERANCE:     float = 1e-6

#: Minimum weight for any active position
DEFAULT_MIN_WEIGHT:                float = 0.0

#: Maximum weight for any single position
DEFAULT_MAX_WEIGHT:                float = 0.25

#: Governance gate for quality score (below this = plan not ready)
DEFAULT_QUALITY_GATE:              float = 0.55

#: Conservation tolerance for weight sum
WEIGHT_SUM_TOLERANCE:              float = 1e-4
