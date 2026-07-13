"""iios/investment/company/earnings/cost_efficiency.py
Cost structure efficiency analysis.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.company.earnings.earnings_report import EarningsReport
from iios.investment.company.earnings.earnings_statistics import safe_mean, _clean


@dataclass
class CostEfficiencyProfile:
    """Cost structure analysis for current period and historical context."""
    # Current (% of revenue)
    cost_of_revenue_pct: Optional[float] = None
    sga_pct:             Optional[float] = None
    da_pct:              Optional[float] = None
    interest_pct:        Optional[float] = None
    effective_tax_rate:  Optional[float] = None

    # Historical averages
    avg_cogs_pct: Optional[float] = None
    avg_sga_pct:  Optional[float] = None
    avg_da_pct:   Optional[float] = None

    # vs average
    cogs_vs_avg: Optional[float] = None   # current - avg (negative = improving)
    sga_vs_avg:  Optional[float] = None

    # Operating leverage proxy
    # = EBIT margin slope vs revenue slope (positive = high operating leverage)
    operating_leverage_flag: Optional[bool] = None

    is_improving_cost_structure: bool = False   # cogs_vs_avg < -0.5 pp

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cost_of_revenue_pct": self.cost_of_revenue_pct,
            "sga_pct":             self.sga_pct,
            "da_pct":              self.da_pct,
            "interest_pct":        self.interest_pct,
            "effective_tax_rate":  self.effective_tax_rate,
            "avg_cogs_pct":        self.avg_cogs_pct,
            "avg_sga_pct":         self.avg_sga_pct,
            "avg_da_pct":          self.avg_da_pct,
            "cogs_vs_avg":         self.cogs_vs_avg,
            "sga_vs_avg":          self.sga_vs_avg,
            "is_improving_cost_structure": self.is_improving_cost_structure,
        }


class CostEfficiencyAnalyzer:
    def analyze(
        self,
        history: List[EarningsReport],
        latest: Optional[EarningsReport] = None,
    ) -> CostEfficiencyProfile:
        p = CostEfficiencyProfile()
        latest = latest or (history[-1] if history else None)

        if latest:
            p.cost_of_revenue_pct = latest.cost_of_revenue_pct
            p.sga_pct             = latest.sga_pct
            p.da_pct              = latest.da_pct
            p.interest_pct        = latest.interest_pct
            p.effective_tax_rate  = latest.effective_tax_rate

        if not history:
            return p

        p.avg_cogs_pct = safe_mean([r.cost_of_revenue_pct for r in history])
        p.avg_sga_pct  = safe_mean([r.sga_pct             for r in history])
        p.avg_da_pct   = safe_mean([r.da_pct              for r in history])

        if p.cost_of_revenue_pct is not None and p.avg_cogs_pct is not None:
            p.cogs_vs_avg = p.cost_of_revenue_pct - p.avg_cogs_pct
            p.is_improving_cost_structure = p.cogs_vs_avg < -0.5
        if p.sga_pct is not None and p.avg_sga_pct is not None:
            p.sga_vs_avg = p.sga_pct - p.avg_sga_pct

        return p
