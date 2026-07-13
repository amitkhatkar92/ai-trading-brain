"""iios/investment/strategy/evaluation/performance_metrics.py
Immutable result type carrying all performance metrics for one evaluation.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class PerformanceMetrics:
    """
    Full set of performance metrics for a single strategy evaluation.
    All rate/ratio values are dimensionless or annualised fractions.
    """

    # Return metrics
    total_return:       float   = 0.0   # (end / start) - 1
    annualized_return:  float   = 0.0   # CAGR
    alpha:              float   = 0.0   # Jensen's alpha (annualised)
    beta:               float   = 0.0   # regression beta vs benchmark
    information_ratio:  float   = 0.0   # active return / tracking error
    sharpe_ratio:       float   = 0.0   # annualised Sharpe
    sortino_ratio:      float   = 0.0   # annualised Sortino (downside dev)
    calmar_ratio:       float   = 0.0   # CAGR / |max drawdown|
    treynor_ratio:      float   = 0.0   # excess return per unit of beta

    # Trade-aggregate metrics
    profit_factor:      float   = 0.0   # gross profit / gross loss
    recovery_factor:    float   = 0.0   # total PnL / |max dd in currency|
    expectancy:         float   = 0.0   # expected PnL per trade

    # Context stored for downstream grading
    n_periods:          int     = 0     # equity curve length
    duration_years:     float   = 0.0
    n_trades:           int     = 0
    risk_free_rate:     float   = 0.06

    # ── convenience ─────────────────────────────────────────────────────────

    @property
    def has_benchmark(self) -> bool:
        return self.beta != 0.0

    @property
    def excess_return(self) -> float:
        return self.annualized_return - self.risk_free_rate

    @property
    def is_finite(self) -> bool:
        """True if no metric is ±inf or NaN."""
        return all(
            math.isfinite(v)
            for v in (
                self.total_return,
                self.annualized_return,
                self.sharpe_ratio,
                self.sortino_ratio,
                self.calmar_ratio,
            )
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_return":       self.total_return,
            "annualized_return":  self.annualized_return,
            "alpha":              self.alpha,
            "beta":               self.beta,
            "information_ratio":  self.information_ratio,
            "sharpe_ratio":       self.sharpe_ratio,
            "sortino_ratio":      self.sortino_ratio,
            "calmar_ratio":       self.calmar_ratio,
            "treynor_ratio":      self.treynor_ratio,
            "profit_factor":      self.profit_factor,
            "recovery_factor":    self.recovery_factor,
            "expectancy":         self.expectancy,
            "n_periods":          self.n_periods,
            "duration_years":     self.duration_years,
            "n_trades":           self.n_trades,
        }
