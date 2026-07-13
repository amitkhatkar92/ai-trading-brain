"""iios/investment/company/earnings/earnings_quality_statistics.py
Statistical aggregation of earnings quality across all stored periods.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.company.earnings.earnings_report import EarningsReport
from iios.investment.company.earnings.earnings_statistics import (
    safe_mean, safe_stdev, _clean,
)


@dataclass
class EarningsQualityStatistics:
    """
    Aggregate statistics computed from all available EarningsReports.
    Used by downstream intelligence engines for portfolio analytics.
    """
    periods_assessed:   int = 0

    # Mean values
    mean_eps:           Optional[float] = None
    mean_revenue:       Optional[float] = None
    mean_gross_margin:  Optional[float] = None
    mean_ebitda_margin: Optional[float] = None
    mean_net_margin:    Optional[float] = None
    mean_roe:           Optional[float] = None
    mean_roic:          Optional[float] = None
    mean_ocf_to_ni:     Optional[float] = None
    mean_accruals:      Optional[float] = None

    # Dispersion
    stdev_eps:          Optional[float] = None
    stdev_net_margin:   Optional[float] = None

    # Extremes
    max_eps:            Optional[float] = None
    min_eps:            Optional[float] = None
    max_net_margin:     Optional[float] = None
    min_net_margin:     Optional[float] = None

    # Quality rates
    profitable_rate:    float = 0.0   # fraction of periods with positive NI
    cash_backed_rate:   float = 0.0   # fraction with ocf_to_ni >= 0.8
    high_accruals_rate: float = 0.0   # fraction with high accruals

    flags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "periods_assessed":   self.periods_assessed,
            "mean_eps":           self.mean_eps,
            "mean_net_margin":    self.mean_net_margin,
            "mean_roe":           self.mean_roe,
            "mean_roic":          self.mean_roic,
            "mean_ocf_to_ni":     self.mean_ocf_to_ni,
            "mean_accruals":      self.mean_accruals,
            "stdev_eps":          self.stdev_eps,
            "stdev_net_margin":   self.stdev_net_margin,
            "max_eps":            self.max_eps,
            "min_eps":            self.min_eps,
            "max_net_margin":     self.max_net_margin,
            "min_net_margin":     self.min_net_margin,
            "profitable_rate":    round(self.profitable_rate, 3),
            "cash_backed_rate":   round(self.cash_backed_rate, 3),
            "high_accruals_rate": round(self.high_accruals_rate, 3),
            "flags":              self.flags,
        }


class EarningsQualityStatisticsEngine:
    """Computes aggregate quality statistics from earnings history."""

    def compute(self, history: List[EarningsReport]) -> EarningsQualityStatistics:
        s = EarningsQualityStatistics(periods_assessed=len(history))
        if not history:
            return s

        n = len(history)
        eps_vals    = [r.effective_eps() for r in history]
        rev_vals    = [r.revenue        for r in history]
        gm_vals     = [r.gross_margin   for r in history]
        em_vals     = [r.ebitda_margin  for r in history]
        nm_vals     = [r.net_margin     for r in history]
        roe_vals    = [r.roe            for r in history]
        roic_vals   = [r.roic           for r in history]
        ocf_vals    = [r.ocf_to_net_income for r in history]
        acc_vals    = [r.accruals_ratio for r in history]

        s.mean_eps           = safe_mean(eps_vals)
        s.mean_revenue       = safe_mean(rev_vals)
        s.mean_gross_margin  = safe_mean(gm_vals)
        s.mean_ebitda_margin = safe_mean(em_vals)
        s.mean_net_margin    = safe_mean(nm_vals)
        s.mean_roe           = safe_mean(roe_vals)
        s.mean_roic          = safe_mean(roic_vals)
        s.mean_ocf_to_ni     = safe_mean(ocf_vals)
        s.mean_accruals      = safe_mean(acc_vals)

        s.stdev_eps        = safe_stdev(eps_vals)
        s.stdev_net_margin = safe_stdev(nm_vals)

        clean_eps = _clean(eps_vals)
        clean_nm  = _clean(nm_vals)
        if clean_eps:
            s.max_eps = max(clean_eps)
            s.min_eps = min(clean_eps)
        if clean_nm:
            s.max_net_margin = max(clean_nm)
            s.min_net_margin = min(clean_nm)

        s.profitable_rate    = sum(1 for r in history if r.is_profitable()) / n
        s.cash_backed_rate   = sum(1 for r in history if r.is_cash_backed)  / n
        s.high_accruals_rate = sum(1 for r in history if r.has_high_accruals) / n

        if s.high_accruals_rate > 0.5:
            s.flags.append("majority_high_accruals")
        if s.profitable_rate < 0.8:
            s.flags.append(f"low_profitability_rate:{s.profitable_rate:.0%}")

        return s
