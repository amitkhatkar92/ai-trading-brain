"""iios/investment/company/earnings/earnings_consistency.py
Checks consistency of margins and earnings across historical periods.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.company.earnings.earnings_report import EarningsReport
from iios.investment.company.earnings.earnings_statistics import (
    safe_mean, coefficient_of_variation, _clean,
)


@dataclass
class ConsistencyMetrics:
    gross_margin_cv:  Optional[float] = None   # coefficient of variation
    ebit_margin_cv:   Optional[float] = None
    net_margin_cv:    Optional[float] = None
    eps_cv:           Optional[float] = None

    # Is company consistently profitable?
    profitable_periods:  int = 0
    total_periods:       int = 0
    profitability_rate:  float = 0.0   # 0-1

    # Consecutive profitable periods
    consecutive_profits: int = 0

    score: float = 0.0   # 0–100 (100 = perfectly consistent)
    flags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gross_margin_cv":    self.gross_margin_cv,
            "net_margin_cv":      self.net_margin_cv,
            "eps_cv":             self.eps_cv,
            "profitable_periods": self.profitable_periods,
            "total_periods":      self.total_periods,
            "profitability_rate": round(self.profitability_rate, 3),
            "consecutive_profits": self.consecutive_profits,
            "score":              round(self.score, 1),
            "flags":              self.flags,
        }


class EarningsConsistencyChecker:
    """Evaluates consistency of earnings and margins across periods."""

    _HIGH_CV = 0.30   # CV > 30% = high variability
    _MED_CV  = 0.15   # CV 15-30% = medium variability

    def analyze(self, history: List[EarningsReport]) -> ConsistencyMetrics:
        m = ConsistencyMetrics(total_periods=len(history))
        if not history:
            return m

        gross_margins = [r.gross_margin for r in history]
        ebit_margins  = [r.ebit_margin  for r in history]
        net_margins   = [r.net_margin   for r in history]
        eps_values    = [r.effective_eps() for r in history]

        m.gross_margin_cv = coefficient_of_variation(gross_margins)
        m.ebit_margin_cv  = coefficient_of_variation(ebit_margins)
        m.net_margin_cv   = coefficient_of_variation(net_margins)
        m.eps_cv          = coefficient_of_variation(eps_values)

        # Profitability consistency
        m.profitable_periods = sum(1 for r in history if r.is_profitable())
        if m.total_periods > 0:
            m.profitability_rate = m.profitable_periods / m.total_periods

        # Consecutive profitable periods (from end)
        m.consecutive_profits = 0
        for r in reversed(history):
            if r.is_profitable():
                m.consecutive_profits += 1
            else:
                break

        # Score: combination of profitability rate and margin stability
        score = 100.0 * m.profitability_rate
        for cv in [m.gross_margin_cv, m.net_margin_cv, m.eps_cv]:
            if cv is None:
                continue
            if cv > self._HIGH_CV:
                score -= 15.0
                m.flags.append(f"high_variability_cv_{cv:.2f}")
            elif cv > self._MED_CV:
                score -= 7.0

        m.score = max(0.0, min(100.0, score))
        return m
