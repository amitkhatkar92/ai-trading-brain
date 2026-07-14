"""iios/investment/portfolio/optimization/optimization_metrics.py

Detailed metrics computed from a completed OptimizationPlan.
"""
from __future__ import annotations

import math
import statistics
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from iios.investment.portfolio.optimization.optimization_plan import OptimizationPlan


@dataclass(frozen=True)
class OptimizationMetrics:
    """Aggregate performance and risk metrics for one OptimizationPlan."""

    metrics_id:                  str   = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:                str   = ""
    plan_id:                     str   = ""

    # Capital
    total_capital:               float = 0.0
    optimized_invested:          float = 0.0
    utilisation_rate:            float = 0.0

    # Returns
    expected_return:             float = 0.0   # Σ w_i μ_i
    prior_expected_return:       float = 0.0

    # Risk
    portfolio_risk:              float = 0.0   # sqrt(Σ w_i² σ_i²)
    prior_portfolio_risk:        float = 0.0

    # Risk-adjusted
    sharpe_proxy:                float = 0.0
    prior_sharpe_proxy:          float = 0.0
    return_improvement_pct:      float = 0.0   # % change in E[R]
    risk_reduction_pct:          float = 0.0   # % reduction in risk
    sharpe_improvement_pct:      float = 0.0   # % change in Sharpe

    # Diversification
    diversification_ratio:       float = 0.0
    hhi:                         float = 0.0
    effective_n:                 float = 0.0

    # Turnover
    total_turnover:              float = 0.0
    max_weight_change:           float = 0.0
    positions_increased:         int   = 0
    positions_decreased:         int   = 0
    positions_unchanged:         int   = 0

    # Count
    total_positions:             int   = 0
    sector_count:                int   = 0
    asset_class_count:           int   = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metrics_id":              self.metrics_id,
            "portfolio_id":            self.portfolio_id,
            "plan_id":                 self.plan_id,
            "total_capital":           round(self.total_capital, 2),
            "optimized_invested":      round(self.optimized_invested, 2),
            "utilisation_rate":        round(self.utilisation_rate, 4),
            "expected_return":         round(self.expected_return, 6),
            "prior_expected_return":   round(self.prior_expected_return, 6),
            "portfolio_risk":          round(self.portfolio_risk, 6),
            "prior_portfolio_risk":    round(self.prior_portfolio_risk, 6),
            "sharpe_proxy":            round(self.sharpe_proxy, 6),
            "prior_sharpe_proxy":      round(self.prior_sharpe_proxy, 6),
            "return_improvement_pct":  round(self.return_improvement_pct, 4),
            "risk_reduction_pct":      round(self.risk_reduction_pct, 4),
            "sharpe_improvement_pct":  round(self.sharpe_improvement_pct, 4),
            "diversification_ratio":   round(self.diversification_ratio, 4),
            "hhi":                     round(self.hhi, 6),
            "effective_n":             round(self.effective_n, 2),
            "total_turnover":          round(self.total_turnover, 6),
            "max_weight_change":       round(self.max_weight_change, 6),
            "positions_increased":     self.positions_increased,
            "positions_decreased":     self.positions_decreased,
            "positions_unchanged":     self.positions_unchanged,
            "total_positions":         self.total_positions,
            "sector_count":            self.sector_count,
            "asset_class_count":       self.asset_class_count,
        }


def compute_optimization_metrics(plan: OptimizationPlan) -> OptimizationMetrics:
    """Computes OptimizationMetrics from a completed plan."""

    positions = list(plan.positions)
    n         = len(positions)
    total     = plan.total_capital

    if n == 0:
        return OptimizationMetrics(
            portfolio_id = plan.portfolio_id,
            plan_id      = plan.plan_id,
            total_capital= total,
        )

    # Expected returns (optimized vs prior)
    exp_ret   = sum(p.optimized_weight * p.expected_return_proxy for p in positions)
    prior_ret = sum(p.prior_weight * p.expected_return_proxy for p in positions)

    # Risk (portfolio risk = sqrt(Σ w² σ²))
    port_var  = sum(p.optimized_weight ** 2 * p.risk_proxy ** 2 for p in positions)
    prior_var = sum(p.prior_weight ** 2 * p.risk_proxy ** 2 for p in positions)
    port_risk = math.sqrt(max(0.0, port_var))
    prior_risk= math.sqrt(max(0.0, prior_var))

    # Sharpe proxies
    sharpe      = exp_ret / max(1e-8, port_risk)
    prior_sharpe= prior_ret / max(1e-8, prior_risk)

    def _pct_change(new: float, old: float) -> float:
        if abs(old) < 1e-10:
            return 0.0
        return (new - old) / abs(old)

    # Diversification ratio
    avg_sigma = sum(p.optimized_weight * p.risk_proxy for p in positions)
    div_ratio = avg_sigma / max(1e-8, port_risk) if port_risk > 0 else 1.0

    # HHI
    hhi = sum(p.optimized_weight ** 2 for p in positions)
    eff_n = 1.0 / hhi if hhi > 0 else 0.0

    # Turnover
    weight_changes = [abs(p.weight_change) for p in positions]
    max_change     = max(weight_changes) if weight_changes else 0.0
    turnover       = sum(weight_changes)

    sectors    = {p.sector for p in positions}
    asset_cls  = {p.asset_class for p in positions}

    n_inc   = sum(1 for p in positions if p.is_increased)
    n_dec   = sum(1 for p in positions if p.is_decreased)
    n_same  = sum(1 for p in positions if p.is_unchanged)

    return OptimizationMetrics(
        portfolio_id           = plan.portfolio_id,
        plan_id                = plan.plan_id,
        total_capital          = total,
        optimized_invested     = plan.optimized_invested,
        utilisation_rate       = plan.utilisation_rate,
        expected_return        = exp_ret,
        prior_expected_return  = prior_ret,
        portfolio_risk         = port_risk,
        prior_portfolio_risk   = prior_risk,
        sharpe_proxy           = sharpe,
        prior_sharpe_proxy     = prior_sharpe,
        return_improvement_pct = _pct_change(exp_ret, prior_ret),
        risk_reduction_pct     = _pct_change(prior_risk, port_risk),   # positive = reduced
        sharpe_improvement_pct = _pct_change(sharpe, prior_sharpe),
        diversification_ratio  = div_ratio,
        hhi                    = hhi,
        effective_n            = eff_n,
        total_turnover         = turnover,
        max_weight_change      = max_change,
        positions_increased    = n_inc,
        positions_decreased    = n_dec,
        positions_unchanged    = n_same,
        total_positions        = n,
        sector_count           = len(sectors),
        asset_class_count      = len(asset_cls),
    )
