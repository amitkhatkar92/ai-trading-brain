"""iios/investment/portfolio/optimization/optimization_plan.py

Core data models for the Portfolio Optimization Engine.

OptimizationObjective  — defines what the engine is trying to achieve.
OptimizedPosition      — one position's optimized weight + dollar amount.
OptimizationRequest    — drives a single optimization run.
OptimizationPlan       — immutable output of one optimization run.
OptimizationResult     — full output of PortfolioOptimizationEngine.optimize().
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, List, Optional, Tuple

from iios.investment.portfolio.optimization.optimization_types import (
    ConvergenceStatus,
    ObjectiveType,
    OptimizationMethod,
    OptimizationQualityGrade,
    OptimizationRunStatus,
    OPTIMIZATION_PLAN_SCHEMA_VERSION,
    OPTIMIZATION_RESULT_SCHEMA_VERSION,
    WeightChangeStatus,
)


# ---------------------------------------------------------------------------
# OptimizationObjective
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class OptimizationObjective:
    """
    Specifies what the optimizer is trying to achieve.
    Primary + optional secondary objective with weights.
    """

    primary:              ObjectiveType  = ObjectiveType.MAXIMIZE_SHARPE
    secondary:            Optional[ObjectiveType] = None
    secondary_weight:     float          = 0.30   # Weight of secondary in multi-objective

    # Risk aversion (λ) for mean-variance: higher → more conservative
    risk_aversion:        float          = 2.0

    # Target annualized return (if return-constrained)
    target_return:        Optional[float] = None

    # Target risk budget (fraction of total risk)
    target_risk:          Optional[float] = None

    # Turnover penalty weight
    turnover_penalty:     float           = 0.0

    description:          str             = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary":          self.primary.value,
            "secondary":        self.secondary.value if self.secondary else None,
            "secondary_weight": self.secondary_weight,
            "risk_aversion":    self.risk_aversion,
            "target_return":    self.target_return,
            "target_risk":      self.target_risk,
            "turnover_penalty": self.turnover_penalty,
            "description":      self.description,
        }


# ---------------------------------------------------------------------------
# OptimizedPosition
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class OptimizedPosition:
    """
    A single position's weight/capital after optimization.
    Retains prior (allocation-engine) values for comparison.
    """

    symbol:               str    = ""
    name:                 str    = ""

    # Weights (fractions of total investable capital)
    prior_weight:         float  = 0.0   # From AllocationPlan
    optimized_weight:     float  = 0.0   # From optimizer
    weight_change:        float  = 0.0   # optimized - prior

    # Dollar amounts (currency from request)
    prior_capital:        float  = 0.0
    optimized_capital:    float  = 0.0
    capital_change:       float  = 0.0   # optimized - prior

    # Proxies used in optimization (from PositionAllocation)
    expected_return_proxy:float  = 0.5   # conviction from decision engine
    risk_proxy:           float  = 0.5   # risk_score from construction engine
    confidence_proxy:     float  = 0.5   # confidence from decision engine

    # Classification
    sector:               str    = "unknown"
    industry:             str    = "unknown"
    asset_class:          str    = "equity"

    # Risk-adjusted return proxy: expected_return / risk
    risk_adjusted_return: float  = 0.0

    # Contribution to portfolio objective
    objective_contribution: float = 0.0

    # Traceability
    blueprint_slot_id:    str    = ""
    recommendation_id:    str    = ""
    source_decision_id:   str    = ""
    allocation_plan_id:   str    = ""

    rank:                 int    = 0

    @property
    def is_increased(self) -> bool:
        return self.weight_change > 0.001

    @property
    def is_decreased(self) -> bool:
        return self.weight_change < -0.001

    @property
    def is_unchanged(self) -> bool:
        return abs(self.weight_change) <= 0.001

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol":                self.symbol,
            "name":                  self.name,
            "prior_weight":          round(self.prior_weight, 6),
            "optimized_weight":      round(self.optimized_weight, 6),
            "weight_change":         round(self.weight_change, 6),
            "prior_capital":         round(self.prior_capital, 2),
            "optimized_capital":     round(self.optimized_capital, 2),
            "capital_change":        round(self.capital_change, 2),
            "expected_return_proxy": round(self.expected_return_proxy, 4),
            "risk_proxy":            round(self.risk_proxy, 4),
            "confidence_proxy":      round(self.confidence_proxy, 4),
            "risk_adjusted_return":  round(self.risk_adjusted_return, 4),
            "sector":                self.sector,
            "industry":              self.industry,
            "asset_class":           self.asset_class,
            "objective_contribution":round(self.objective_contribution, 6),
            "rank":                  self.rank,
        }


# ---------------------------------------------------------------------------
# OptimizationRequest
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class OptimizationRequest:
    """Parameters driving a single portfolio optimization run."""

    request_id:           str                  = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:         str                  = ""
    allocation_plan_id:   str                  = ""   # ID of the AllocationPlan being optimized
    blueprint_id:         str                  = ""

    # Capital
    total_capital:        float                = 0.0
    currency:             str                  = "INR"

    # Method + objective
    method:               OptimizationMethod   = OptimizationMethod.MAXIMUM_SHARPE
    objective:            OptimizationObjective = field(default_factory=OptimizationObjective)

    # Position weight constraints
    min_weight:           float                = 0.0
    max_weight:           float                = 0.25

    # Exposure constraints
    max_sector_weight:    float                = 0.40
    max_industry_weight:  float                = 0.25
    max_asset_class_weight: float              = 0.80

    # Leverage
    max_gross_leverage:   float                = 1.0   # 1.0 = long only

    # Cash reserve
    cash_reserve_pct:     float                = 0.05

    # Turnover limit (max total weight change vs prior)
    max_turnover:         float                = 1.0   # 1.0 = unconstrained

    # Convergence parameters
    risk_aversion:        float                = 2.0
    max_iterations:       int                  = 1_000
    convergence_tol:      float                = 1e-6
    learning_rate:        float                = 0.01

    # Symbols to include/exclude
    symbols_allowed:      FrozenSet[str]       = field(default_factory=frozenset)
    symbols_excluded:     FrozenSet[str]       = field(default_factory=frozenset)

    # Provenance
    requested_by:         str                  = "system"
    requested_at:         float                = field(default_factory=time.time)
    metadata:             Dict[str, Any]       = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":            self.request_id,
            "portfolio_id":          self.portfolio_id,
            "allocation_plan_id":    self.allocation_plan_id,
            "blueprint_id":          self.blueprint_id,
            "total_capital":         self.total_capital,
            "currency":              self.currency,
            "method":                self.method.value,
            "objective":             self.objective.to_dict(),
            "min_weight":            self.min_weight,
            "max_weight":            self.max_weight,
            "max_sector_weight":     self.max_sector_weight,
            "max_industry_weight":   self.max_industry_weight,
            "max_asset_class_weight":self.max_asset_class_weight,
            "max_gross_leverage":    self.max_gross_leverage,
            "cash_reserve_pct":      self.cash_reserve_pct,
            "max_turnover":          self.max_turnover,
            "risk_aversion":         self.risk_aversion,
            "max_iterations":        self.max_iterations,
            "convergence_tol":       self.convergence_tol,
            "requested_by":          self.requested_by,
            "requested_at":          self.requested_at,
            "metadata":              dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# OptimizationPlan
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class OptimizationPlan:
    """
    Immutable, version-stamped result of one portfolio optimization run.

    Produced by a PortfolioOptimizationEngine.optimize() call and consumed by:
      • OptimizationValidator (integrity check)
      • Downstream execution layer (adjusts order sizes)

    Deterministic: same allocation_plan + same request → same plan.
    """

    plan_id:              str                  = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:         str                  = ""
    allocation_plan_id:   str                  = ""
    blueprint_id:         str                  = ""
    request_id:           str                  = ""
    version:              int                  = 1
    schema_version:       str                  = OPTIMIZATION_PLAN_SCHEMA_VERSION

    # Method + objective
    method:               OptimizationMethod   = OptimizationMethod.MAXIMUM_SHARPE
    objective_type:       ObjectiveType        = ObjectiveType.MAXIMIZE_SHARPE
    currency:             str                  = "INR"

    # Capital
    total_capital:        float                = 0.0
    investable_capital:   float                = 0.0
    optimized_invested:   float                = 0.0
    cash_capital:         float                = 0.0
    utilisation_rate:     float                = 0.0

    # Positions
    positions:            Tuple[OptimizedPosition, ...] = field(default_factory=tuple)

    # Convergence
    convergence:          ConvergenceStatus    = ConvergenceStatus.ANALYTICAL
    iterations:           int                  = 0
    final_gradient_norm:  float                = 0.0
    converged:            bool                 = True

    # Objective values (pre vs post)
    prior_objective_value:      float          = 0.0
    optimized_objective_value:  float          = 0.0
    objective_improvement:      float          = 0.0   # post - pre (or % improvement)

    # Weight change summary
    weight_change_status: WeightChangeStatus   = WeightChangeStatus.MINIMAL
    max_weight_change:    float                = 0.0
    total_turnover:       float                = 0.0   # sum|w_opt - w_prior|

    # Exposure summaries (optimized weights)
    sector_weights:       Dict[str, float]     = field(default_factory=dict)
    asset_class_weights:  Dict[str, float]     = field(default_factory=dict)
    industry_weights:     Dict[str, float]     = field(default_factory=dict)

    # Portfolio-level metrics (post-optimization)
    expected_return:      float                = 0.0   # conviction-weighted avg
    portfolio_risk:       float                = 0.0   # risk-weighted avg
    sharpe_proxy:         float                = 0.0   # return / risk
    diversification_ratio:float                = 0.0   # avg σ / portfolio σ
    hhi:                  float                = 0.0   # concentration index

    created_at:           float                = field(default_factory=time.time)
    created_by:           str                  = "PortfolioOptimizationEngine"
    metadata:             Dict[str, Any]       = field(default_factory=dict)

    @property
    def total_positions(self) -> int:
        return len(self.positions)

    @property
    def symbols(self) -> Tuple[str, ...]:
        return tuple(p.symbol for p in self.positions)

    @property
    def is_empty(self) -> bool:
        return len(self.positions) == 0

    def get_position(self, symbol: str) -> Optional[OptimizedPosition]:
        for p in self.positions:
            if p.symbol == symbol:
                return p
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id":                   self.plan_id,
            "portfolio_id":              self.portfolio_id,
            "allocation_plan_id":        self.allocation_plan_id,
            "blueprint_id":              self.blueprint_id,
            "request_id":                self.request_id,
            "version":                   self.version,
            "schema_version":            self.schema_version,
            "method":                    self.method.value,
            "objective_type":            self.objective_type.value,
            "currency":                  self.currency,
            "total_capital":             round(self.total_capital, 2),
            "investable_capital":        round(self.investable_capital, 2),
            "optimized_invested":        round(self.optimized_invested, 2),
            "cash_capital":              round(self.cash_capital, 2),
            "utilisation_rate":          round(self.utilisation_rate, 4),
            "total_positions":           self.total_positions,
            "convergence":               self.convergence.value,
            "iterations":                self.iterations,
            "converged":                 self.converged,
            "prior_objective_value":     round(self.prior_objective_value, 6),
            "optimized_objective_value": round(self.optimized_objective_value, 6),
            "objective_improvement":     round(self.objective_improvement, 6),
            "weight_change_status":      self.weight_change_status.value,
            "max_weight_change":         round(self.max_weight_change, 6),
            "total_turnover":            round(self.total_turnover, 6),
            "expected_return":           round(self.expected_return, 6),
            "portfolio_risk":            round(self.portfolio_risk, 6),
            "sharpe_proxy":              round(self.sharpe_proxy, 6),
            "diversification_ratio":     round(self.diversification_ratio, 4),
            "hhi":                       round(self.hhi, 6),
            "sector_weights":            {k: round(v, 4) for k, v in self.sector_weights.items()},
            "asset_class_weights":       {k: round(v, 4) for k, v in self.asset_class_weights.items()},
            "industry_weights":          {k: round(v, 4) for k, v in self.industry_weights.items()},
            "created_at":                self.created_at,
            "created_by":                self.created_by,
            "positions":                 [p.to_dict() for p in self.positions],
            "metadata":                  dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# OptimizationResult
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class OptimizationResult:
    """Full output of PortfolioOptimizationEngine.optimize()."""

    result_id:          str                    = field(default_factory=lambda: str(uuid.uuid4()))
    request_id:         str                    = ""
    portfolio_id:       str                    = ""
    allocation_plan_id: str                    = ""
    status:             OptimizationRunStatus  = OptimizationRunStatus.PENDING
    schema_version:     str                    = OPTIMIZATION_RESULT_SCHEMA_VERSION

    # Plan is present on success
    plan:               Optional[OptimizationPlan] = None

    # Validation / quality
    validation_summary: Dict[str, Any]         = field(default_factory=dict)
    quality_summary:    Dict[str, Any]         = field(default_factory=dict)
    constraint_summary: Dict[str, Any]         = field(default_factory=dict)

    warnings:           Tuple[str, ...]        = field(default_factory=tuple)
    errors:             Tuple[str, ...]        = field(default_factory=tuple)

    duration_ms:        float                  = 0.0
    created_at:         float                  = field(default_factory=time.time)
    metadata:           Dict[str, Any]         = field(default_factory=dict)

    @property
    def succeeded(self) -> bool:
        return self.status.is_successful

    @property
    def failed(self) -> bool:
        return self.status == OptimizationRunStatus.FAILED

    @property
    def has_plan(self) -> bool:
        return self.plan is not None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id":          self.result_id,
            "request_id":         self.request_id,
            "portfolio_id":       self.portfolio_id,
            "allocation_plan_id": self.allocation_plan_id,
            "status":             self.status.value,
            "schema_version":     self.schema_version,
            "plan":               self.plan.to_dict() if self.plan else None,
            "validation_summary": dict(self.validation_summary),
            "quality_summary":    dict(self.quality_summary),
            "constraint_summary": dict(self.constraint_summary),
            "warnings":           list(self.warnings),
            "errors":             list(self.errors),
            "duration_ms":        round(self.duration_ms, 2),
            "created_at":         self.created_at,
            "metadata":           dict(self.metadata),
        }

