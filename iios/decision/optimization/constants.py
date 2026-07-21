"""
constants.py — iios.decision.optimization
==========================================
Enumerations, precedence maps, and configuration constants for the
Decision Optimization Framework.

C9 Decision Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

from enum import Enum, IntEnum

# ── Identity ─────────────────────────────────────────────────────────────────

OPTIMIZATION_SYSTEM_ID = "iios:decision:optimization"
VERSION                = "1.0.0"
SCHEMA_VERSION         = "1.0"

# ── Actors ───────────────────────────────────────────────────────────────────

ACTOR_ENGINE    = "iios:optimization:engine"
ACTOR_MANAGER   = "iios:optimization:manager"
ACTOR_OPTIMIZER = "iios:optimization:optimizer"
ACTOR_SYSTEM    = "iios:optimization:system"
ACTOR_OPERATOR  = "iios:optimization:operator"

# ── Capacity / tuning defaults ────────────────────────────────────────────────

DEFAULT_MAX_OBJECTIVES  = 100
DEFAULT_MAX_CONSTRAINTS = 200
DEFAULT_MAX_CANDIDATES  = 500
DEFAULT_MAX_STRATEGIES  = 50
DEFAULT_MAX_HISTORY     = 2_000
DEFAULT_STRATEGY_ID     = "default_weighted_score"
EMA_ALPHA               = 0.1
THROUGHPUT_WINDOW_S     = 60.0

# ── Objective types (10) ──────────────────────────────────────────────────────

class OptimizationObjectiveType(str, Enum):
    MAXIMIZE_EXPECTED_RETURN      = "maximize_expected_return"
    MINIMIZE_RISK                 = "minimize_risk"
    MAXIMIZE_RISK_ADJUSTED_RETURN = "maximize_risk_adjusted_return"
    MINIMIZE_DRAWDOWN             = "minimize_drawdown"
    MAXIMIZE_CAPITAL_EFFICIENCY   = "maximize_capital_efficiency"
    MINIMIZE_EXECUTION_COST       = "minimize_execution_cost"
    MINIMIZE_PORTFOLIO_EXPOSURE   = "minimize_portfolio_exposure"
    MAXIMIZE_LIQUIDITY            = "maximize_liquidity"
    MAXIMIZE_OPERATIONAL_STABILITY = "maximize_operational_stability"
    MAXIMIZE_POLICY_COMPLIANCE    = "maximize_policy_compliance"

# ── Strategy types (8) ────────────────────────────────────────────────────────

class OptimizationStrategyType(str, Enum):
    WEIGHTED_SCORE          = "weighted_score"
    PRIORITY_BASED          = "priority_based"
    CONSTRAINT_SATISFACTION = "constraint_satisfaction"
    RULE_BASED              = "rule_based"
    MULTI_OBJECTIVE         = "multi_objective"
    PARETO_RANKING          = "pareto_ranking"
    LEXICOGRAPHIC           = "lexicographic"
    CUSTOM                  = "custom"

# ── Constraint types (10) ────────────────────────────────────────────────────

class ConstraintType(str, Enum):
    RISK           = "risk"
    CAPITAL        = "capital"
    EXPOSURE       = "exposure"
    LIQUIDITY      = "liquidity"
    COMPLIANCE     = "compliance"
    OPERATIONAL    = "operational"
    INFRASTRUCTURE = "infrastructure"
    PORTFOLIO      = "portfolio"
    STRATEGY       = "strategy"
    CUSTOM         = "custom"

# ── Constraint operators ──────────────────────────────────────────────────────

class ConstraintOperator(str, Enum):
    LT         = "lt"
    LTE        = "lte"
    GT         = "gt"
    GTE        = "gte"
    EQ         = "eq"
    BETWEEN    = "between"
    EXISTS     = "exists"
    NOT_EXISTS = "not_exists"

# ── Optimization status ───────────────────────────────────────────────────────

class OptimizationStatus(str, Enum):
    PENDING     = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED   = "completed"
    FAILED      = "failed"

# ── Events (8) ────────────────────────────────────────────────────────────────

class OptimizationEventType(str, Enum):
    OPTIMIZATION_STARTED  = "optimization_started"
    CANDIDATES_LOADED     = "candidates_loaded"
    OBJECTIVES_LOADED     = "objectives_loaded"
    CONSTRAINTS_LOADED    = "constraints_loaded"
    OPTIMIZATION_COMPLETED = "optimization_completed"
    SOLUTION_SELECTED     = "solution_selected"
    SOLUTION_VALIDATED    = "solution_validated"
    OPTIMIZATION_FAILED   = "optimization_failed"

# ── Validation codes (7) ──────────────────────────────────────────────────────

class OptimizationValidationCode(str, Enum):
    CANDIDATE_VALIDITY       = "candidate_validity"
    OBJECTIVE_CONSISTENCY    = "objective_consistency"
    CONSTRAINT_CONSISTENCY   = "constraint_consistency"
    OPTIMIZATION_COMPLETENESS = "optimization_completeness"
    RANKING_INTEGRITY        = "ranking_integrity"
    SOLUTION_INTEGRITY       = "solution_integrity"
    CONTEXT_CONSISTENCY      = "context_consistency"

# ── Objective direction sets ──────────────────────────────────────────────────

MAXIMIZE_OBJECTIVES: frozenset[OptimizationObjectiveType] = frozenset({
    OptimizationObjectiveType.MAXIMIZE_EXPECTED_RETURN,
    OptimizationObjectiveType.MAXIMIZE_RISK_ADJUSTED_RETURN,
    OptimizationObjectiveType.MAXIMIZE_CAPITAL_EFFICIENCY,
    OptimizationObjectiveType.MAXIMIZE_LIQUIDITY,
    OptimizationObjectiveType.MAXIMIZE_OPERATIONAL_STABILITY,
    OptimizationObjectiveType.MAXIMIZE_POLICY_COMPLIANCE,
})

MINIMIZE_OBJECTIVES: frozenset[OptimizationObjectiveType] = frozenset({
    OptimizationObjectiveType.MINIMIZE_RISK,
    OptimizationObjectiveType.MINIMIZE_DRAWDOWN,
    OptimizationObjectiveType.MINIMIZE_EXECUTION_COST,
    OptimizationObjectiveType.MINIMIZE_PORTFOLIO_EXPOSURE,
})

# ── Default field mappings ─────────────────────────────────────────────────────

OBJECTIVE_FIELD_DEFAULTS: dict[OptimizationObjectiveType, str] = {
    OptimizationObjectiveType.MAXIMIZE_EXPECTED_RETURN:       "expected_return",
    OptimizationObjectiveType.MINIMIZE_RISK:                  "risk_score",
    OptimizationObjectiveType.MAXIMIZE_RISK_ADJUSTED_RETURN:  "risk_adjusted_return",
    OptimizationObjectiveType.MINIMIZE_DRAWDOWN:              "drawdown_estimate",
    OptimizationObjectiveType.MAXIMIZE_CAPITAL_EFFICIENCY:    "capital_efficiency",
    OptimizationObjectiveType.MINIMIZE_EXECUTION_COST:        "execution_cost",
    OptimizationObjectiveType.MINIMIZE_PORTFOLIO_EXPOSURE:    "portfolio_exposure",
    OptimizationObjectiveType.MAXIMIZE_LIQUIDITY:             "liquidity_score",
    OptimizationObjectiveType.MAXIMIZE_OPERATIONAL_STABILITY: "operational_stability",
    OptimizationObjectiveType.MAXIMIZE_POLICY_COMPLIANCE:     "policy_compliance_score",
}
