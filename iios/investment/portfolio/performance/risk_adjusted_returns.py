"""iios/investment/portfolio/performance/risk_adjusted_returns.py

Risk-adjusted return metrics: Sharpe, Sortino, Treynor, Calmar, Omega.
"""
from __future__ import annotations

import math
import statistics
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.portfolio.performance.performance_types import (
    RISK_FREE_RATE_ANNUAL, TRADING_DAYS, downside_deviation,
    portfolio_vol_proxy, PerformancePosition,
)


@dataclass(frozen=True)
class RiskAdjustedReturns:
    """All risk-adjusted return metrics for a portfolio."""

    result_id:        str   = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:     str   = ""

    # Inputs used
    portfolio_return: float = 0.0   # annualized
    annual_vol:       float = 0.0
    risk_free:        float = RISK_FREE_RATE_ANNUAL
    beta:             float = 1.0
    max_drawdown:     float = 0.0   # positive value (e.g. 0.15 = 15%)

    # Ratios
    sharpe_ratio:     float = 0.0
    sortino_ratio:    float = 0.0
    treynor_ratio:    float = 0.0   # excess return / beta
    calmar_ratio:     float = 0.0   # annualized return / max_drawdown
    omega_ratio:      float = 0.0   # probability weighted ratio
    recovery_factor:  float = 0.0   # total return / max_drawdown

    # Data availability
    used_return_series: bool = False
    n_periods:        int   = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "portfolio_return": round(self.portfolio_return, 4),
            "annual_vol":       round(self.annual_vol, 4),
            "sharpe_ratio":     round(self.sharpe_ratio, 4),
            "sortino_ratio":    round(self.sortino_ratio, 4),
            "treynor_ratio":    round(self.treynor_ratio, 4),
            "calmar_ratio":     round(self.calmar_ratio, 4),
            "omega_ratio":      round(self.omega_ratio, 4),
            "recovery_factor":  round(self.recovery_factor, 4),
            "max_drawdown":     round(self.max_drawdown, 4),
        }


def compute_risk_adjusted_returns(
    positions:        List[PerformancePosition],
    portfolio_return: float,
    portfolio_vol:    Optional[float] = None,
    beta:             float = 1.0,
    max_drawdown:     float = 0.0,
    portfolio_id:     str   = "",
    return_series:    Optional[List[float]] = None,
    periods_per_year: int   = 12,
) -> RiskAdjustedReturns:
    """
    Compute all risk-adjusted ratios.

    ``portfolio_return`` = annualized.
    ``max_drawdown`` = positive fraction (e.g. 0.15).
    ``return_series`` = optional list of period returns for Sortino / Omega.
    """
    vol = portfolio_vol if portfolio_vol is not None else portfolio_vol_proxy(positions)
    if vol <= 0:
        vol = 0.01   # floor to avoid division by zero

    excess = portfolio_return - RISK_FREE_RATE_ANNUAL

    # Sharpe
    sharpe = excess / vol

    # Sortino
    if return_series:
        dd = downside_deviation(return_series, target=RISK_FREE_RATE_ANNUAL / periods_per_year)
        dd_annual = dd * math.sqrt(periods_per_year)
    else:
        dd_annual = vol * 0.7   # proxy: downside dev ≈ 70% of total vol
    sortino = excess / dd_annual if dd_annual > 1e-10 else 0.0

    # Treynor
    treynor = excess / beta if abs(beta) > 1e-10 else 0.0

    # Calmar
    calmar  = portfolio_return / max_drawdown if max_drawdown > 1e-10 else 0.0

    # Omega ratio (return / (risk × vol factor))
    # Omega = E[max(R-T, 0)] / E[max(T-R, 0)] where T = risk_free
    if return_series and len(return_series) > 1:
        target = RISK_FREE_RATE_ANNUAL / periods_per_year
        gains  = [max(r - target, 0) for r in return_series]
        losses = [max(target - r, 0) for r in return_series]
        omega  = sum(gains) / max(sum(losses), 1e-12)
    else:
        # Proxy: map sharpe to omega
        omega = 1.0 + sharpe * 0.5 if sharpe > -2.0 else 0.1

    # Recovery factor
    recovery = portfolio_return / max_drawdown if max_drawdown > 1e-10 else 0.0

    return RiskAdjustedReturns(
        portfolio_id       = portfolio_id,
        portfolio_return   = round(portfolio_return, 6),
        annual_vol         = round(vol, 6),
        beta               = round(beta, 4),
        max_drawdown       = round(max_drawdown, 4),
        sharpe_ratio       = round(sharpe, 4),
        sortino_ratio      = round(sortino, 4),
        treynor_ratio      = round(treynor, 4),
        calmar_ratio       = round(calmar, 4),
        omega_ratio        = round(max(0.0, omega), 4),
        recovery_factor    = round(recovery, 4),
        used_return_series = return_series is not None,
        n_periods          = len(return_series) if return_series else 0,
    )
