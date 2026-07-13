"""iios/investment/company/earnings/return_analysis.py
Return-on-capital metrics analysis.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.company.earnings.earnings_report import EarningsReport
from iios.investment.company.earnings.earnings_statistics import safe_mean, _clean


@dataclass
class ReturnProfile:
    """Capital returns for current period and historical context."""
    # Current
    roe:   Optional[float] = None
    roa:   Optional[float] = None
    roic:  Optional[float] = None
    roce:  Optional[float] = None

    # Historical averages
    avg_roe:  Optional[float] = None
    avg_roa:  Optional[float] = None
    avg_roic: Optional[float] = None

    # vs average
    roe_vs_avg:  Optional[float] = None
    roic_vs_avg: Optional[float] = None

    # Peak
    peak_roe:  Optional[float] = None
    peak_roic: Optional[float] = None

    # Capital efficiency flags
    is_high_return:  bool = False   # avg ROIC > 15%
    is_value_creator: bool = False  # ROIC > cost_of_capital (proxy: ROIC > 10%)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "roe":           self.roe,
            "roa":           self.roa,
            "roic":          self.roic,
            "roce":          self.roce,
            "avg_roe":       self.avg_roe,
            "avg_roa":       self.avg_roa,
            "avg_roic":      self.avg_roic,
            "roe_vs_avg":    self.roe_vs_avg,
            "roic_vs_avg":   self.roic_vs_avg,
            "peak_roe":      self.peak_roe,
            "peak_roic":     self.peak_roic,
            "is_high_return": self.is_high_return,
            "is_value_creator": self.is_value_creator,
        }


class ReturnAnalyzer:
    """Analyzes return-on-capital metrics from earnings history."""

    _HIGH_RETURN_THRESHOLD  = 15.0   # ROIC %
    _VALUE_CREATOR_THRESHOLD = 10.0  # ROIC > assumed WACC proxy

    def analyze(
        self,
        history: List[EarningsReport],
        latest: Optional[EarningsReport] = None,
    ) -> ReturnProfile:
        p = ReturnProfile()
        latest = latest or (history[-1] if history else None)

        if latest:
            p.roe  = latest.roe
            p.roa  = latest.roa
            p.roic = latest.roic
            p.roce = latest.roce

        if not history:
            return p

        p.avg_roe  = safe_mean([r.roe  for r in history])
        p.avg_roa  = safe_mean([r.roa  for r in history])
        p.avg_roic = safe_mean([r.roic for r in history])

        roic_vals = _clean([r.roic for r in history])
        roe_vals  = _clean([r.roe  for r in history])
        if roic_vals:
            p.peak_roic = max(roic_vals)
        if roe_vals:
            p.peak_roe  = max(roe_vals)

        if p.roe is not None and p.avg_roe is not None:
            p.roe_vs_avg = p.roe - p.avg_roe
        if p.roic is not None and p.avg_roic is not None:
            p.roic_vs_avg = p.roic - p.avg_roic

        # Capital efficiency flags based on historical average
        if p.avg_roic is not None:
            p.is_high_return   = p.avg_roic > self._HIGH_RETURN_THRESHOLD
            p.is_value_creator = p.avg_roic > self._VALUE_CREATOR_THRESHOLD

        return p
