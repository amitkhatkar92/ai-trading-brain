"""iios/investment/company/growth/earnings_growth.py
Earnings and net income growth analysis engine.
"""
from __future__ import annotations

from typing import List, Optional

from iios.investment.company.growth.growth_profile import (
    CAGRProfile, EarningsGrowthProfile, GrowthTrend, classify_growth,
)
from iios.investment.company.growth.growth_statistics import (
    cagr, cagr_from_series, yoy_growth, growth_rates_from_series,
    trend_from_growth_rates, trend_from_direction_string,
)
from iios.investment.company.growth.eps_growth import compute_eps_cagr_profile


class EarningsGrowthEngine:
    """
    Compute earnings / EPS / net-income growth intelligence.
    Consumes from EarningsSnapshot and FinancialSnapshot aggregates.
    """

    def compute(
        self,
        cagr_eps:            Optional[float] = None,   # EarningsSnapshot.trend.cagr_eps
        eps_direction:       Optional[str]  = None,   # EarningsSnapshot.trend.eps_direction
        avg_net_margin:      Optional[float] = None,   # EarningsSnapshot.profitability.avg_net_margin
        net_margin:          Optional[float] = None,   # EarningsSnapshot.profitability.net_margin
        eps_volatility:      Optional[float] = None,   # EarningsSnapshot.risk.eps_volatility
        net_income:          Optional[float] = None,   # FinancialSnapshot.income_metrics.net_income
        current_revenue:     Optional[float] = None,   # FinancialSnapshot.revenue
        eps_series:          Optional[List[float]] = None,
        net_income_series:   Optional[List[float]] = None,
        history_depth:       int = 0,
    ) -> EarningsGrowthProfile:
        explanation: List[str] = []

        # ── EPS CAGR ────────────────────────────────────────────────────────────
        eps_cagr_profile = compute_eps_cagr_profile(
            cagr_eps=cagr_eps,
            eps_direction=eps_direction,
            eps_series=eps_series,
            history_depth=history_depth,
        )
        if eps_cagr_profile.best_available is not None:
            explanation.append(f"EPS CAGR: {eps_cagr_profile.best_available:.1%}")

        # ── Net income CAGR ──────────────────────────────────────────────────────
        ni_cagr_profile = self._net_income_cagr(net_income_series, history_depth, explanation)

        # ── YoY EPS ─────────────────────────────────────────────────────────────
        # Use eps_series if available
        yoy_eps: Optional[float] = None
        if eps_series and len(eps_series) >= 2:
            yoy_eps = yoy_growth(eps_series[-1], eps_series[-2])

        # ── Trend ──────────────────────────────────────────────────────────────
        trend = eps_cagr_profile.trend
        if trend == GrowthTrend.INSUFFICIENT_DATA and eps_direction:
            trend = trend_from_direction_string(eps_direction)

        if trend != GrowthTrend.INSUFFICIENT_DATA:
            explanation.append(f"Earnings trend: {trend.value}")
        else:
            explanation.append("Insufficient data to determine earnings trend")

        return EarningsGrowthProfile(
            eps_cagr=eps_cagr_profile,
            net_income_cagr=ni_cagr_profile,
            yoy_eps=yoy_eps,
            trend=trend,
            explanation=explanation,
        )

    def _net_income_cagr(
        self,
        ni_series:   Optional[List[float]],
        depth:       int,
        explanation: List[str],
    ) -> CAGRProfile:
        if not ni_series or len(ni_series) < 2:
            return CAGRProfile(periods_used=depth)
        n = len(ni_series)
        rates = growth_rates_from_series(ni_series)
        trend = trend_from_growth_rates(rates) if rates else GrowthTrend.INSUFFICIENT_DATA
        c1  = cagr(ni_series[-2], ni_series[-1], 1)  if n >= 2 else None
        c3  = cagr(ni_series[-4], ni_series[-1], 3)  if n >= 4 else None
        c5  = cagr(ni_series[-6], ni_series[-1], 5)  if n >= 6 else None
        best = c5 or c3 or c1
        if best is not None:
            explanation.append(f"Net income CAGR (best): {best:.1%}")
        return CAGRProfile(
            cagr_1y=c1, cagr_3y=c3, cagr_5y=c5,
            best_available=best, trend=trend, periods_used=n,
            label=classify_growth(best),
        )
