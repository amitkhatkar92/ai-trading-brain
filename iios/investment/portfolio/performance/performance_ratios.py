"""iios/investment/portfolio/performance/performance_ratios.py

Extended performance ratio suite.
"""
from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.portfolio.performance.performance_types import (
    RISK_FREE_RATE_ANNUAL, PerformancePosition, portfolio_vol_proxy,
)
from iios.investment.portfolio.performance.risk_adjusted_returns import (
    RiskAdjustedReturns,
)


@dataclass(frozen=True)
class PerformanceRatios:
    """Full suite of performance ratios."""

    result_id:                 str   = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:              str   = ""

    # Core ratios
    sharpe:                    float = 0.0
    sortino:                   float = 0.0
    treynor:                   float = 0.0
    calmar:                    float = 0.0
    omega:                     float = 0.0

    # Benchmark-relative
    information_ratio:         float = 0.0   # (return - bmk) / tracking_error

    # Extended
    modigliani_ratio:          float = 0.0   # M² = (sharpe × bmk_vol) + risk_free
    upside_potential_ratio:    float = 0.0   # upside / downside dev
    sterling_ratio:            float = 0.0   # (return - risk_free) / max_drawdown
    ulcer_index:               float = 0.0   # RMS of drawdowns

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sharpe":              round(self.sharpe, 4),
            "sortino":             round(self.sortino, 4),
            "treynor":             round(self.treynor, 4),
            "calmar":              round(self.calmar, 4),
            "omega":               round(self.omega, 4),
            "information_ratio":   round(self.information_ratio, 4),
            "modigliani_ratio":    round(self.modigliani_ratio, 4),
            "upside_potential_ratio": round(self.upside_potential_ratio, 4),
        }


def compute_all_ratios(
    risk_adjusted:    RiskAdjustedReturns,
    benchmark_return: float      = 0.0,
    benchmark_vol:    float      = 0.16,
    tracking_error:   float      = 0.05,
    return_series:    Optional[List[float]] = None,
    periods_per_year: int        = 12,
    portfolio_id:     str        = "",
) -> PerformanceRatios:
    """
    Compute extended performance ratios from a RiskAdjustedReturns result
    plus benchmark context.
    """
    sharpe    = risk_adjusted.sharpe_ratio
    sortino   = risk_adjusted.sortino_ratio
    treynor   = risk_adjusted.treynor_ratio
    calmar    = risk_adjusted.calmar_ratio
    omega     = risk_adjusted.omega_ratio

    # Information ratio
    active_ret = risk_adjusted.portfolio_return - benchmark_return
    ir = active_ret / tracking_error if tracking_error > 1e-10 else 0.0

    # Modigliani (M²): adjusted to benchmark vol universe
    # M² = sharpe × σ_benchmark + R_f
    m2 = sharpe * benchmark_vol + RISK_FREE_RATE_ANNUAL

    # Upside potential ratio (using return series if available)
    if return_series and len(return_series) > 1:
        target = RISK_FREE_RATE_ANNUAL / periods_per_year
        gains  = [max(r - target, 0) for r in return_series]
        losses = [max(target - r, 0) for r in return_series]
        g_avg  = sum(gains) / len(gains)
        l_rms  = math.sqrt(sum(x**2 for x in losses) / len(losses)) if losses else 1e-10
        upr    = g_avg / max(l_rms, 1e-10)
        ulcer  = math.sqrt(sum(d**2 for d in losses) / len(losses))
    else:
        upr   = max(0.0, 1.0 + sortino * 0.5)
        ulcer = risk_adjusted.annual_vol * 0.5

    # Sterling ratio = (return - rf) / avg_annual_drawdown_proxy
    max_dd  = risk_adjusted.max_drawdown
    sterling = (risk_adjusted.portfolio_return - RISK_FREE_RATE_ANNUAL) / max_dd \
               if max_dd > 1e-10 else 0.0

    return PerformanceRatios(
        portfolio_id           = portfolio_id,
        sharpe                 = sharpe,
        sortino                = sortino,
        treynor                = treynor,
        calmar                 = calmar,
        omega                  = omega,
        information_ratio      = round(ir, 4),
        modigliani_ratio       = round(m2, 4),
        upside_potential_ratio = round(upr, 4),
        sterling_ratio         = round(sterling, 4),
        ulcer_index            = round(ulcer, 4),
    )
