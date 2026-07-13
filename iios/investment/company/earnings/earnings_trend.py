"""iios/investment/company/earnings/earnings_trend.py
Core trend detection orchestrator. Aggregates growth and margin trends.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.company.earnings.earnings_report import EarningsReport, TrendDirection, ProfitCyclePhase
from iios.investment.company.earnings.earnings_snapshot import TrendProfile
from iios.investment.company.earnings.growth_trend import GrowthTrendAnalyzer
from iios.investment.company.earnings.profit_cycle import detect_profit_cycle
from iios.investment.company.earnings.earnings_statistics import normalised_slope, trend_acceleration, _clean


class EarningsTrendAnalyzer:
    """Detects EPS, revenue, and margin trends from earnings history."""

    def __init__(self) -> None:
        self._growth = GrowthTrendAnalyzer()

    def analyze(self, history: List[EarningsReport]) -> TrendProfile:
        p = TrendProfile(periods_analyzed=len(history))

        if len(history) < 2:
            return p

        # EPS trend (prefer diluted_eps, fallback basic_eps)
        eps_field = "diluted_eps" if any(r.diluted_eps is not None for r in history) else "basic_eps"
        eps_trend    = self._growth.analyze(history, eps_field)
        rev_trend    = self._growth.analyze(history, "revenue")
        margin_trend = self._growth.analyze(history, "net_margin")

        p.eps_direction     = eps_trend.direction
        p.revenue_direction = rev_trend.direction
        p.margin_direction  = margin_trend.direction

        p.eps_growth_rates     = [r for r in eps_trend.growth_rate_series]
        p.revenue_growth_rates = [r for r in rev_trend.growth_rate_series]
        p.latest_eps_growth    = eps_trend.latest_growth
        p.cagr_eps             = eps_trend.cagr
        p.cagr_revenue         = rev_trend.cagr

        # Margin slope & acceleration
        net_margins = _clean([r.net_margin for r in history])
        if len(net_margins) >= 3:
            p.margin_slope        = normalised_slope(net_margins)
            p.margin_acceleration = trend_acceleration(net_margins)

        # Profit cycle
        p.profit_cycle_phase = detect_profit_cycle(history, field="net_margin")

        return p
