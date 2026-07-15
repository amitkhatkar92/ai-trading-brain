"""iios/investment/portfolio/performance/return_analysis.py

Core return analysis: absolute, relative, and period returns.
"""
from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.portfolio.performance.performance_types import (
    RISK_FREE_RATE_ANNUAL, TRADING_DAYS, ReturnPeriod,
    PerformancePosition, portfolio_return, portfolio_expected_return,
)


@dataclass(frozen=True)
class ReturnAnalysis:
    """Comprehensive return analysis for a portfolio over an evaluation period."""

    result_id:            str          = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:         str          = ""
    period:               ReturnPeriod = ReturnPeriod.ANNUAL

    # Period return
    total_period_return:  float        = 0.0   # actual or estimated period return
    expected_return:      float        = 0.0   # forward-looking

    # vs risk-free
    excess_return:        float        = 0.0   # total_period_return - risk_free_period

    # Annualised
    annualized_return:    float        = 0.0

    # Decomposition
    n_positions:          int          = 0
    top_contributor:      str          = ""
    top_contribution:     float        = 0.0
    bottom_contributor:   str          = ""
    bottom_contribution:  float        = 0.0

    # Data quality
    uses_estimated_returns: bool       = False

    warnings:             tuple        = field(default_factory=tuple)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_period_return":    round(self.total_period_return, 4),
            "excess_return":          round(self.excess_return, 4),
            "annualized_return":      round(self.annualized_return, 4),
            "expected_return":        round(self.expected_return, 4),
            "top_contributor":        self.top_contributor,
            "top_contribution":       round(self.top_contribution, 4),
            "uses_estimated_returns": self.uses_estimated_returns,
            "warnings":               list(self.warnings),
        }


def analyze_returns(
    positions:       List[PerformancePosition],
    portfolio_id:    str          = "",
    period:          ReturnPeriod = ReturnPeriod.ANNUAL,
    period_years:    float        = 1.0,
    nav_series:      Optional[List[float]] = None,
) -> ReturnAnalysis:
    """
    Compute return analysis for the given positions and evaluation period.

    If nav_series is provided (length >= 2), actual returns are used.
    Otherwise, period_return fields on positions are used, or estimated.
    """
    if not positions:
        return ReturnAnalysis(portfolio_id=portfolio_id, period=period)

    # Determine return source
    if nav_series and len(nav_series) >= 2:
        total_ret = (nav_series[-1] / nav_series[0]) - 1.0
        uses_estimated = False
        # Distribute return proportionally to positions (best-effort)
        positions = list(positions)
    else:
        uses_estimated = all(p.period_return == 0.0 for p in positions)
        if uses_estimated:
            # Estimate: scale expected annual return to period
            scale = period_years
            positions = [
                PerformancePosition(
                    symbol=p.symbol, weight=p.weight,
                    sector=p.sector, industry=p.industry,
                    asset_class=p.asset_class, country=p.country,
                    currency=p.currency, strategy_id=p.strategy_id,
                    period_return=p.expected_return_annual * scale,
                    expected_return_annual=p.expected_return_annual,
                    risk_score=p.risk_score, conviction=p.conviction,
                    confidence=p.confidence, liquidity=p.liquidity,
                    benchmark_period_return=p.benchmark_period_return,
                )
                for p in positions
            ]
        total_ret = portfolio_return(positions)

    exp_ret  = portfolio_expected_return(positions)

    # Risk-free period return
    rf_period = RISK_FREE_RATE_ANNUAL * period_years
    excess    = total_ret - rf_period

    # Annualize
    ann_return = _annualize(total_ret, period_years)

    # Attribution: top / bottom contributors
    contribs = sorted(positions, key=lambda p: p.contribution, reverse=True)
    top_p    = contribs[0]
    bot_p    = contribs[-1]

    warnings = []
    if total_ret < -0.15:
        warnings.append(f"Portfolio down {total_ret:.1%} over period — significant loss")
    elif total_ret < -0.05:
        warnings.append(f"Portfolio down {total_ret:.1%} over period")
    if uses_estimated:
        warnings.append("Returns are estimated from conviction proxies — no actual NAV data")

    return ReturnAnalysis(
        portfolio_id          = portfolio_id,
        period                = period,
        total_period_return   = round(total_ret, 6),
        expected_return       = round(exp_ret, 6),
        excess_return         = round(excess, 6),
        annualized_return     = round(ann_return, 6),
        n_positions           = len(positions),
        top_contributor       = top_p.symbol,
        top_contribution      = round(top_p.contribution, 6),
        bottom_contributor    = bot_p.symbol,
        bottom_contribution   = round(bot_p.contribution, 6),
        uses_estimated_returns= uses_estimated,
        warnings              = tuple(warnings),
    )


def _annualize(period_return: float, period_years: float) -> float:
    """Convert period return to annualized return (CAGR)."""
    if period_years <= 0:
        return 0.0
    if period_years == 1.0:
        return period_return
    return (1.0 + period_return) ** (1.0 / period_years) - 1.0


def total_return_from_nav(nav_series: List[float]) -> float:
    """Compute total return from NAV series."""
    if len(nav_series) < 2:
        return 0.0
    return (nav_series[-1] / nav_series[0]) - 1.0


def period_returns_from_nav(nav_series: List[float]) -> List[float]:
    """Compute sequential period returns from NAV series."""
    if len(nav_series) < 2:
        return []
    return [(nav_series[i] / nav_series[i - 1]) - 1.0 for i in range(1, len(nav_series))]
