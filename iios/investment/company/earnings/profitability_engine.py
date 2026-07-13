"""iios/investment/company/earnings/profitability_engine.py
Orchestrates margin, return, and cost efficiency analysis.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.company.earnings.earnings_report import EarningsReport
from iios.investment.company.earnings.earnings_snapshot import ProfitabilityProfile
from iios.investment.company.earnings.margin_analysis import MarginAnalyzer, MarginProfile
from iios.investment.company.earnings.return_analysis import ReturnAnalyzer, ReturnProfile
from iios.investment.company.earnings.cost_efficiency import CostEfficiencyAnalyzer, CostEfficiencyProfile


@dataclass
class FullProfitabilityIntelligence:
    """Complete profitability intelligence for one company."""
    period_label: str
    margins:      MarginProfile         = field(default_factory=MarginProfile)
    returns:      ReturnProfile         = field(default_factory=ReturnProfile)
    costs:        CostEfficiencyProfile = field(default_factory=CostEfficiencyProfile)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "period_label": self.period_label,
            "margins":      self.margins.to_dict(),
            "returns":      self.returns.to_dict(),
            "costs":        self.costs.to_dict(),
        }

    def as_profitability_profile(self) -> ProfitabilityProfile:
        """Convert to the slim ProfitabilityProfile used in EarningsSnapshot."""
        p = ProfitabilityProfile(
            gross_margin=self.margins.gross_margin,
            ebitda_margin=self.margins.ebitda_margin,
            ebit_margin=self.margins.ebit_margin,
            net_margin=self.margins.net_margin,
            fcf_margin=self.margins.fcf_margin,
            roe=self.returns.roe,
            roa=self.returns.roa,
            roic=self.returns.roic,
            roce=self.returns.roce,
            avg_gross_margin=self.margins.avg_gross_margin,
            avg_ebitda_margin=self.margins.avg_ebitda_margin,
            avg_net_margin=self.margins.avg_net_margin,
            avg_roe=self.returns.avg_roe,
            avg_roic=self.returns.avg_roic,
            gross_margin_vs_avg=self.margins.gross_vs_avg,
            net_margin_vs_avg=self.margins.net_vs_avg,
            roe_vs_avg=self.returns.roe_vs_avg,
        )
        return p


class ProfitabilityEngine:
    """Orchestrates profitability analysis."""

    def __init__(self) -> None:
        self._margin  = MarginAnalyzer()
        self._return  = ReturnAnalyzer()
        self._cost    = CostEfficiencyAnalyzer()

    def analyze(
        self,
        history: List[EarningsReport],
        latest: Optional[EarningsReport] = None,
    ) -> FullProfitabilityIntelligence:
        latest = latest or (history[-1] if history else None)
        period_label = latest.period_label if latest else ""

        intel = FullProfitabilityIntelligence(period_label=period_label)
        intel.margins = self._margin.analyze(history, latest)
        intel.returns = self._return.analyze(history, latest)
        intel.costs   = self._cost.analyze(history, latest)
        return intel
