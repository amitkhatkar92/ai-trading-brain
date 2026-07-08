"""iios/decision_optimization/optimization_constants.py"""
from __future__ import annotations

from enum import Enum


class ObjectiveType(Enum):
    MAXIMIZE = "maximize"
    MINIMIZE = "minimize"
    TARGET   = "target"


class ObjectiveAggregation(Enum):
    WEIGHTED_SUM     = "weighted_sum"
    WEIGHTED_PRODUCT = "weighted_product"
    PARETO           = "pareto"
    HIERARCHICAL     = "hierarchical"
    LEXICOGRAPHIC    = "lexicographic"


class ConstraintType(Enum):
    HARD       = "hard"
    SOFT       = "soft"
    RESOURCE   = "resource"
    TIME       = "time"
    RISK       = "risk"
    COMPLIANCE = "compliance"


class OptimizationStatus(Enum):
    OPTIMAL    = "optimal"
    FEASIBLE   = "feasible"
    INFEASIBLE = "infeasible"
    TIMEOUT    = "timeout"
    EMPTY      = "empty"
    ERROR      = "error"


class AlgorithmType(Enum):
    GREEDY          = "greedy"
    WEIGHTED_SUM    = "weighted_sum"
    CONSTRAINT      = "constraint"
    HEURISTIC       = "heuristic"
    EVOLUTIONARY    = "evolutionary"
    MULTI_OBJECTIVE = "multi_objective"
    DYNAMIC         = "dynamic"
    CUSTOM          = "custom"


class OptimizationMode(Enum):
    STRICT      = "strict"
    LENIENT     = "lenient"
    BEST_EFFORT = "best_effort"
    AUDIT       = "audit"


# ── Engine metadata ────────────────────────────────────────────────────────────
OPTIMIZATION_ENGINE_VERSION   = "1.0.0"
OPTIMIZATION_ENGINE_SYSTEM_ID = "iios:optimization:engine"

# ── Limits ─────────────────────────────────────────────────────────────────────
MAX_CANDIDATES_PER_REQUEST  = 500
MAX_OBJECTIVES_PER_REQUEST  = 50
MAX_CONSTRAINTS_PER_REQUEST = 200
MAX_OPTIMIZATION_HISTORY    = 50_000
MAX_ALGORITHMS_IN_REGISTRY  = 1_000
MAX_OBJECTIVES_IN_REGISTRY  = 5_000
MAX_CONSTRAINTS_IN_REGISTRY = 10_000

# ── Defaults ───────────────────────────────────────────────────────────────────
DEFAULT_ALGORITHM_TYPE    = AlgorithmType.GREEDY
DEFAULT_OPTIMIZATION_MODE = OptimizationMode.LENIENT
DEFAULT_OBJECTIVE_WEIGHT  = 1.0
DEFAULT_SIMULATION_TRIALS = 100
DEFAULT_SENSITIVITY_STEPS = 10
