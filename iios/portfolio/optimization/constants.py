"""
constants.py — iios.portfolio.optimization
===========================================
Enumerations, defaults, and identifiers for the Institutional Portfolio
Optimization Framework.

C10 Portfolio Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

from enum import Enum, IntEnum
from typing import FrozenSet

# ---------------------------------------------------------------------------
# System identifiers
# ---------------------------------------------------------------------------
OPTIMIZATION_SYSTEM_ID: str = "iios:portfolio:optimization"
VERSION:                str = "1.0.0"

ACTOR_OPTIMIZER:  str = "iios:portfolio:optimization:optimizer"
ACTOR_ENGINE:     str = "iios:portfolio:optimization:engine"
ACTOR_MANAGER:    str = "iios:portfolio:optimization:manager"
ACTOR_SELECTOR:   str = "iios:portfolio:optimization:selector"

# ---------------------------------------------------------------------------
# Default limits
# ---------------------------------------------------------------------------
DEFAULT_MAX_CANDIDATES:   int = 500
DEFAULT_MAX_STRATEGIES:   int = 100
DEFAULT_MAX_HISTORY:      int = 1_000
DEFAULT_MAX_OPTIMIZATIONS: int = 10_000
DEFAULT_MAX_SOLUTIONS:    int = 200

DEFAULT_STRATEGY_NAME: str = "default"


# ---------------------------------------------------------------------------
# OptimizationObjective — ten institutional objectives
# ---------------------------------------------------------------------------
class OptimizationObjective(str, Enum):
    MAXIMIZE_RISK_ADJUSTED_RETURN = "maximize_risk_adjusted_return"
    MAXIMIZE_CAPITAL_EFFICIENCY   = "maximize_capital_efficiency"
    MAXIMIZE_DIVERSIFICATION      = "maximize_diversification"
    MINIMIZE_PORTFOLIO_RISK       = "minimize_portfolio_risk"
    MINIMIZE_DRAWDOWN             = "minimize_drawdown"
    MINIMIZE_CONCENTRATION        = "minimize_concentration"
    MINIMIZE_TURNOVER             = "minimize_turnover"
    MAXIMIZE_LIQUIDITY            = "maximize_liquidity"
    MAXIMIZE_PORTFOLIO_STABILITY  = "maximize_portfolio_stability"
    MAXIMIZE_POLICY_COMPLIANCE    = "maximize_policy_compliance"


# ---------------------------------------------------------------------------
# OptimizationStrategy — twelve strategy types
# ---------------------------------------------------------------------------
class OptimizationStrategyType(str, Enum):
    STRATEGIC_ASSET_ALLOCATION   = "strategic_asset_allocation"
    TACTICAL_ASSET_ALLOCATION    = "tactical_asset_allocation"
    RISK_PARITY                  = "risk_parity"
    EQUAL_WEIGHT                 = "equal_weight"
    MARKET_CAP_WEIGHT            = "market_cap_weight"
    VOLATILITY_TARGETING         = "volatility_targeting"
    MEAN_VARIANCE_OPTIMIZATION   = "mean_variance_optimization"
    MULTI_OBJECTIVE_OPTIMIZATION = "multi_objective_optimization"
    CONSTRAINT_SATISFACTION      = "constraint_satisfaction"
    PARETO_RANKING               = "pareto_ranking"
    LEXICOGRAPHIC_OPTIMIZATION   = "lexicographic_optimization"
    CUSTOM_STRATEGY              = "custom_strategy"


# ---------------------------------------------------------------------------
# ConstraintType — twelve constraint domains
# ---------------------------------------------------------------------------
class ConstraintType(str, Enum):
    CAPITAL       = "capital"
    EXPOSURE      = "exposure"
    RISK          = "risk"
    DIVERSIFICATION = "diversification"
    LIQUIDITY     = "liquidity"
    SECTOR        = "sector"
    INDUSTRY      = "industry"
    CASH          = "cash"
    COMPLIANCE    = "compliance"
    OPERATIONAL   = "operational"
    INFRASTRUCTURE = "infrastructure"
    CUSTOM        = "custom"


# ---------------------------------------------------------------------------
# AllocationCapability — eight allocation domains
# ---------------------------------------------------------------------------
class AllocationCapability(str, Enum):
    CAPITAL   = "capital_allocation"
    ASSET     = "asset_allocation"
    SECTOR    = "sector_allocation"
    INDUSTRY  = "industry_allocation"
    STRATEGY  = "strategy_allocation"
    CASH      = "cash_allocation"
    RESERVE   = "reserve_allocation"
    EXPOSURE  = "exposure_allocation"


# ---------------------------------------------------------------------------
# RebalancingCapability — six rebalancing types
# ---------------------------------------------------------------------------
class RebalancingCapability(str, Enum):
    THRESHOLD     = "threshold_rebalancing"
    PERIODIC      = "periodic_rebalancing"
    EVENT_DRIVEN  = "event_driven_rebalancing"
    RISK_TRIGGERED = "risk_triggered_rebalancing"
    CAPITAL_TRIGGERED = "capital_triggered_rebalancing"
    MANUAL        = "manual_rebalancing"


# ---------------------------------------------------------------------------
# ScoringMethod — four scoring approaches
# ---------------------------------------------------------------------------
class ScoringMethod(str, Enum):
    WEIGHTED   = "weighted"
    NORMALIZED = "normalized"
    COMPOSITE  = "composite"
    PARETO     = "pareto"


# ---------------------------------------------------------------------------
# OptimizationEventType — ten lifecycle events
# ---------------------------------------------------------------------------
class OptimizationEventType(str, Enum):
    OPTIMIZATION_STARTED   = "optimization_started"
    CANDIDATES_LOADED      = "portfolio_candidates_loaded"
    OBJECTIVES_LOADED      = "objectives_loaded"
    CONSTRAINTS_LOADED     = "constraints_loaded"
    ALLOCATION_GENERATED   = "allocation_generated"
    REBALANCING_GENERATED  = "rebalancing_generated"
    OPTIMIZATION_COMPLETED = "optimization_completed"
    PORTFOLIO_SELECTED     = "portfolio_selected"
    SOLUTION_VALIDATED     = "solution_validated"
    OPTIMIZATION_FAILED    = "optimization_failed"


# ---------------------------------------------------------------------------
# OptimizationStatus — lifecycle of one optimization run
# ---------------------------------------------------------------------------
class OptimizationStatus(str, Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    CANCELLED = "cancelled"


# ---------------------------------------------------------------------------
# CandidateStatus — lifecycle of a portfolio candidate
# ---------------------------------------------------------------------------
class CandidateStatus(str, Enum):
    PENDING   = "pending"
    APPROVED  = "approved"
    REJECTED  = "rejected"
    SELECTED  = "selected"
    DISCARDED = "discarded"


# ---------------------------------------------------------------------------
# StrategyStatus
# ---------------------------------------------------------------------------
class StrategyStatus(str, Enum):
    ACTIVE     = "active"
    INACTIVE   = "inactive"
    DEPRECATED = "deprecated"
    DRAFT      = "draft"
