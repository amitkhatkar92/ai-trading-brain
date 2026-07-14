"""iios/investment/portfolio/optimization/optimization_policy.py

Policy objects governing HOW optimization is performed.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict

from iios.investment.portfolio.optimization.optimization_types import (
    DEFAULT_MAX_ITERATIONS,
    DEFAULT_RISK_AVERSION,
    ObjectiveType,
    OptimizationMethod,
)


@dataclass(frozen=True)
class OptimizationPolicy:
    """
    Master policy governing the optimization process.
    Passed to PortfolioOptimizationEngine to configure defaults.
    """

    policy_id:          str                = field(default_factory=lambda: str(uuid.uuid4()))
    policy_name:        str                = "default"
    method:             OptimizationMethod = OptimizationMethod.MAXIMUM_SHARPE
    objective:          ObjectiveType      = ObjectiveType.MAXIMIZE_SHARPE
    currency:           str                = "INR"

    # Position weight limits
    min_position_weight:float              = 0.0
    max_position_weight:float              = 0.25

    # Exposure limits
    max_sector_weight:  float              = 0.40
    max_industry_weight:float              = 0.25
    max_asset_class_weight: float          = 0.80

    # Risk
    risk_aversion:      float              = DEFAULT_RISK_AVERSION
    max_leverage:       float              = 1.0

    # Convergence
    max_iterations:     int                = DEFAULT_MAX_ITERATIONS
    convergence_tol:    float              = 1e-6
    learning_rate:      float              = 0.01

    # Turnover limit (1.0 = unconstrained)
    max_turnover:       float              = 1.0

    # Governance gate
    quality_gate:       float              = 0.55
    allow_degradation:  bool               = False   # If True, accept plans with obj_impr < 0

    description:        str                = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id":            self.policy_id,
            "policy_name":          self.policy_name,
            "method":               self.method.value,
            "objective":            self.objective.value,
            "currency":             self.currency,
            "min_position_weight":  self.min_position_weight,
            "max_position_weight":  self.max_position_weight,
            "max_sector_weight":    self.max_sector_weight,
            "max_industry_weight":  self.max_industry_weight,
            "max_asset_class_weight":self.max_asset_class_weight,
            "risk_aversion":        self.risk_aversion,
            "max_leverage":         self.max_leverage,
            "max_iterations":       self.max_iterations,
            "convergence_tol":      self.convergence_tol,
            "max_turnover":         self.max_turnover,
            "quality_gate":         self.quality_gate,
            "allow_degradation":    self.allow_degradation,
            "description":          self.description,
        }


# ---------------------------------------------------------------------------
# Built-in policies
# ---------------------------------------------------------------------------

CONSERVATIVE_OPTIMIZATION_POLICY = OptimizationPolicy(
    policy_name         = "conservative",
    method              = OptimizationMethod.MINIMUM_VARIANCE,
    objective           = ObjectiveType.MINIMIZE_RISK,
    max_position_weight = 0.10,
    max_sector_weight   = 0.30,
    risk_aversion       = 4.0,
    max_turnover        = 0.20,
    description         = "Conservative: minimize risk, tight constraints",
)

BALANCED_OPTIMIZATION_POLICY = OptimizationPolicy(
    policy_name         = "balanced",
    method              = OptimizationMethod.MAXIMUM_SHARPE,
    objective           = ObjectiveType.MAXIMIZE_SHARPE,
    max_position_weight = 0.20,
    max_sector_weight   = 0.40,
    risk_aversion       = 2.0,
    max_turnover        = 0.50,
    description         = "Balanced: maximize Sharpe, moderate constraints",
)

AGGRESSIVE_OPTIMIZATION_POLICY = OptimizationPolicy(
    policy_name         = "aggressive",
    method              = OptimizationMethod.MEAN_VARIANCE,
    objective           = ObjectiveType.MAXIMIZE_RETURN,
    max_position_weight = 0.30,
    max_sector_weight   = 0.50,
    risk_aversion       = 1.0,
    max_turnover        = 1.0,
    description         = "Aggressive: maximize return, looser constraints",
)

RISK_PARITY_POLICY = OptimizationPolicy(
    policy_name         = "risk_parity",
    method              = OptimizationMethod.RISK_PARITY,
    objective           = ObjectiveType.MAXIMIZE_DIVERSIFICATION,
    max_position_weight = 0.25,
    max_sector_weight   = 0.45,
    risk_aversion       = 2.0,
    max_turnover        = 0.40,
    description         = "Risk Parity: equal risk contribution across positions",
)
