"""iios/investment/portfolio/optimization/objective_engine.py

Evaluates how well an objective is achieved by a set of weights.
Returns a scalar objective score and detailed breakdown.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.portfolio.optimization.optimization_engine import AssetProxy
from iios.investment.portfolio.optimization.optimization_types import ObjectiveType


@dataclass(frozen=True)
class ObjectiveEvaluation:
    """Result of evaluating an objective function at a given weight vector."""

    objective_type:       ObjectiveType = ObjectiveType.MAXIMIZE_SHARPE
    value:                float         = 0.0   # Objective function value
    expected_return:      float         = 0.0   # Σ w_i μ_i
    portfolio_risk:       float         = 0.0   # sqrt(Σ w_i² σ_i²)
    portfolio_variance:   float         = 0.0   # Σ w_i² σ_i²
    diversification_ratio:float         = 0.0   # avg σ / portfolio σ
    sharpe_proxy:         float         = 0.0   # return / risk
    sortino_proxy:        float         = 0.0   # return / downside_risk
    calmar_proxy:         float         = 0.0   # return / max_drawdown_proxy
    turnover:             float         = 0.0   # Σ |w_i - w_prior_i|
    description:          str           = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "objective_type":       self.objective_type.value,
            "value":                round(self.value, 8),
            "expected_return":      round(self.expected_return, 6),
            "portfolio_risk":       round(self.portfolio_risk, 6),
            "portfolio_variance":   round(self.portfolio_variance, 6),
            "diversification_ratio":round(self.diversification_ratio, 4),
            "sharpe_proxy":         round(self.sharpe_proxy, 6),
            "sortino_proxy":        round(self.sortino_proxy, 6),
            "calmar_proxy":         round(self.calmar_proxy, 6),
            "turnover":             round(self.turnover, 6),
        }


class ObjectiveEvaluator:
    """
    Computes all objective metrics for a given (assets, weights) pair.
    Stateless. No external I/O.
    """

    def evaluate(
        self,
        weights:      Dict[str, float],
        assets:       List[AssetProxy],
        objective:    ObjectiveType,
        risk_aversion:float = 2.0,
    ) -> ObjectiveEvaluation:
        """Evaluates all metrics and returns the primary `value` for `objective`."""

        n          = len(assets)
        asset_map  = {a.symbol: a for a in assets}

        # Portfolio-level aggregates
        exp_ret    = 0.0   # Σ w_i μ_i
        port_var   = 0.0   # Σ w_i² σ_i²  (diagonal Σ)
        down_var   = 0.0   # Σ w_i² DR_i²  (downside risk proxy)
        drawdown   = 0.0   # Σ w_i² DD_i   (drawdown proxy)
        avg_sigma  = 0.0   # Σ w_i σ_i      (weighted avg σ)
        turnover   = 0.0

        for sym, w in weights.items():
            a = asset_map.get(sym)
            if a is None:
                continue
            mu         = max(0.0, a.expected_return)
            sigma      = max(1e-8, a.risk)
            down_sigma = max(1e-8, a.risk * (1.0 - a.confidence + 0.01))
            dd_proxy   = max(1e-8, a.risk ** 2 * (1.0 - a.confidence + 0.01))

            exp_ret   += w * mu
            port_var  += w * w * sigma * sigma
            down_var  += w * w * down_sigma * down_sigma
            drawdown  += w * dd_proxy
            avg_sigma += w * sigma
            turnover  += abs(w - max(0.0, a.prior_weight))

        port_risk    = math.sqrt(max(0.0, port_var))
        down_risk    = math.sqrt(max(0.0, down_var))
        sharpe       = exp_ret / max(1e-8, port_risk)
        sortino      = exp_ret / max(1e-8, down_risk)
        calmar       = exp_ret / max(1e-8, drawdown)
        div_ratio    = avg_sigma / max(1e-8, port_risk) if port_risk > 0 else 1.0

        # Map objective type to the scalar value to return
        value = self._objective_value(
            objective, exp_ret, port_risk, port_var,
            sharpe, sortino, calmar, div_ratio, turnover, risk_aversion, weights
        )

        return ObjectiveEvaluation(
            objective_type        = objective,
            value                 = value,
            expected_return       = exp_ret,
            portfolio_risk        = port_risk,
            portfolio_variance    = port_var,
            diversification_ratio = div_ratio,
            sharpe_proxy          = sharpe,
            sortino_proxy         = sortino,
            calmar_proxy          = calmar,
            turnover              = turnover,
        )

    def _objective_value(
        self,
        objective:    ObjectiveType,
        exp_ret:      float,
        port_risk:    float,
        port_var:     float,
        sharpe:       float,
        sortino:      float,
        calmar:       float,
        div_ratio:    float,
        turnover:     float,
        risk_aversion:float,
        weights:      Dict[str, float],
    ) -> float:
        if objective == ObjectiveType.MAXIMIZE_RETURN:
            return exp_ret
        if objective == ObjectiveType.MINIMIZE_RISK:
            return -port_risk   # Negate: we compare as "higher is better"
        if objective == ObjectiveType.MAXIMIZE_SHARPE:
            return sharpe
        if objective == ObjectiveType.MAXIMIZE_SORTINO:
            return sortino
        if objective == ObjectiveType.MAXIMIZE_CALMAR:
            return calmar
        if objective == ObjectiveType.MAXIMIZE_DIVERSIFICATION:
            return div_ratio
        if objective == ObjectiveType.MINIMIZE_TURNOVER:
            return -turnover
        if objective == ObjectiveType.MAXIMIZE_UTILITY:
            return exp_ret - 0.5 * risk_aversion * port_var
        if objective == ObjectiveType.MULTI_OBJECTIVE:
            return 0.5 * sharpe + 0.5 * div_ratio
        return sharpe
