"""iios/investment/company/earnings/earnings_volatility.py
Volatility of earnings, margins, and returns across periods.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.company.earnings.earnings_report import EarningsReport
from iios.investment.company.earnings.earnings_statistics import (
    safe_stdev, coefficient_of_variation, growth_rates, _clean,
)


@dataclass
class VolatilityMetrics:
    # Coefficient of variation of EPS growth rates
    eps_growth_cv:     Optional[float] = None
    # Stdev of net margin (pp)
    net_margin_stdev:  Optional[float] = None
    # Stdev of revenue growth
    revenue_growth_cv: Optional[float] = None
    # Stdev of OCF (as % of avg OCF)
    ocf_cv:            Optional[float] = None

    # Periods with negative EPS
    loss_periods:     int = 0
    total_periods:    int = 0
    loss_rate:        float = 0.0   # 0-1

    # Cyclicality score (based on all volatility measures)
    cyclicality_score: float = 0.0   # 0=stable, 100=highly cyclical

    def to_dict(self) -> Dict[str, Any]:
        return {
            "eps_growth_cv":     self.eps_growth_cv,
            "net_margin_stdev":  self.net_margin_stdev,
            "revenue_growth_cv": self.revenue_growth_cv,
            "ocf_cv":            self.ocf_cv,
            "loss_periods":      self.loss_periods,
            "total_periods":     self.total_periods,
            "loss_rate":         round(self.loss_rate, 3),
            "cyclicality_score": round(self.cyclicality_score, 1),
        }


class EarningsVolatilityAnalyzer:
    """Measures earnings volatility from historical reports."""

    def analyze(self, history: List[EarningsReport]) -> VolatilityMetrics:
        m = VolatilityMetrics(total_periods=len(history))
        if not history:
            return m

        eps_vals     = [r.effective_eps() for r in history]
        net_margins  = [r.net_margin for r in history]
        revenues     = [r.revenue for r in history]
        ocf_vals     = [r.operating_cash_flow for r in history]

        # EPS growth CV
        eps_rates = growth_rates(eps_vals)
        m.eps_growth_cv     = coefficient_of_variation(eps_rates)

        # Net margin stdev (in pp)
        clean_nm = _clean(net_margins)
        m.net_margin_stdev  = safe_stdev(net_margins)

        # Revenue growth CV
        rev_rates = growth_rates(revenues)
        m.revenue_growth_cv = coefficient_of_variation(rev_rates)

        # OCF CV
        m.ocf_cv = coefficient_of_variation(ocf_vals)

        # Loss rate
        m.loss_periods = sum(1 for r in history if not r.is_profitable())
        if m.total_periods > 0:
            m.loss_rate = m.loss_periods / m.total_periods

        # Cyclicality score (composite)
        components = []
        for cv in [m.eps_growth_cv, m.revenue_growth_cv, m.ocf_cv]:
            if cv is not None:
                # CV of 1.0 (100%) → score 100; 0 → score 0
                components.append(min(100.0, cv * 100.0))
        components.append(m.loss_rate * 100.0)
        m.cyclicality_score = sum(components) / len(components) if components else 0.0

        return m
