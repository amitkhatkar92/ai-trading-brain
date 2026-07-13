"""iios/investment/company/earnings/earnings_persistence.py
Evaluates how persistent and recurring earnings are — distinguishes
structural/recurring earnings from one-off/non-recurring items.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.company.earnings.earnings_report import EarningsReport
from iios.investment.company.earnings.earnings_statistics import (
    safe_mean, _clean, r_squared, linear_slope,
)


@dataclass
class PersistenceMetrics:
    """Describes how persistent (recurring) earnings are."""

    # Cash backing of earnings (avg of ocf_to_ni)
    avg_cash_conversion:  Optional[float] = None   # ratio >1 = better
    cash_backed_periods:  int = 0   # periods where ocf_to_ni >= 0.8

    # Accruals quality (avg and trend)
    avg_accruals_ratio:   Optional[float] = None   # ideally near 0
    accruals_trend:       Optional[str]   = None   # "improving"|"worsening"|"stable"

    # EPS AR(1) coefficient — how well past EPS predicts future EPS
    eps_ar1:              Optional[float] = None   # 0=random, 1=highly persistent

    # R² of earnings vs time (trend fit quality)
    earnings_r_squared:   Optional[float] = None

    # High-accruals red flags
    high_accrual_periods: int = 0

    score: float = 0.0   # 0–100
    flags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "avg_cash_conversion":  self.avg_cash_conversion,
            "cash_backed_periods":  self.cash_backed_periods,
            "avg_accruals_ratio":   self.avg_accruals_ratio,
            "accruals_trend":       self.accruals_trend,
            "eps_ar1":              self.eps_ar1,
            "earnings_r_squared":   self.earnings_r_squared,
            "high_accrual_periods": self.high_accrual_periods,
            "score":                round(self.score, 1),
            "flags":                self.flags,
        }


def _ar1(values: List[float]) -> Optional[float]:
    """Estimate AR(1) coefficient via OLS on (y_t-1, y_t) pairs."""
    if len(values) < 4:
        return None
    x_vals = values[:-1]
    y_vals = values[1:]
    n  = len(x_vals)
    xm = sum(x_vals) / n
    ym = sum(y_vals) / n
    num = sum((x_vals[i] - xm) * (y_vals[i] - ym) for i in range(n))
    den = sum((x_vals[i] - xm) ** 2 for i in range(n))
    return num / den if den != 0 else None


class EarningsPersistenceAnalyzer:
    """Evaluates recurring vs non-recurring nature of earnings."""

    def analyze(self, history: List[EarningsReport]) -> PersistenceMetrics:
        m = PersistenceMetrics()
        if not history:
            return m

        # Cash conversion
        ocf_ratios = _clean([r.ocf_to_net_income for r in history])
        if ocf_ratios:
            m.avg_cash_conversion = sum(ocf_ratios) / len(ocf_ratios)
            m.cash_backed_periods = sum(1 for v in ocf_ratios if v >= 0.8)

        # Accruals
        accruals = _clean([r.accruals_ratio for r in history])
        if accruals:
            m.avg_accruals_ratio   = sum(accruals) / len(accruals)
            m.high_accrual_periods = sum(1 for v in accruals if v > 0.10)
            # Trend: is accruals improving (going down) or worsening (going up)?
            if len(accruals) >= 3:
                slope = linear_slope(accruals)
                if slope < -0.005:
                    m.accruals_trend = "improving"
                elif slope > 0.005:
                    m.accruals_trend = "worsening"
                else:
                    m.accruals_trend = "stable"

        # EPS AR(1)
        eps_vals = _clean([r.effective_eps() for r in history])
        if len(eps_vals) >= 4:
            m.eps_ar1 = _ar1(eps_vals)
        if len(eps_vals) >= 3:
            m.earnings_r_squared = r_squared(eps_vals)

        # Score
        score = 50.0

        if m.avg_cash_conversion is not None:
            # 100% bonus for high cash conversion
            score += min(25.0, 25.0 * (m.avg_cash_conversion - 0.5))

        if m.avg_accruals_ratio is not None:
            # Penalise high accruals
            penalty = max(0.0, m.avg_accruals_ratio * 200)   # 0.10 → -20 pts
            score -= min(25.0, penalty)
            if m.high_accrual_periods > 2:
                m.flags.append(f"persistent_high_accruals:{m.high_accrual_periods}_periods")

        if m.eps_ar1 is not None:
            # High AR1 = persistent earnings = good
            score += 10.0 * max(0.0, m.eps_ar1 - 0.3)   # bonus above 0.3

        m.score = max(0.0, min(100.0, score))
        return m
