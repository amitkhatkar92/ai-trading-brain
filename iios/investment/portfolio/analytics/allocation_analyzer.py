"""iios/investment/portfolio/analytics/allocation_analyzer.py"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from iios.investment.portfolio.core.portfolio import Portfolio
from iios.investment.portfolio.allocation.allocation_report import AllocationReport


@dataclass
class AllocationAnalysis:
    portfolio_id:     str  = ""
    allocation_score: float = 50.0    # from AllocationReport
    by_asset_class:   dict[str, float] = field(default_factory=dict)
    rebalancing_needed: bool = False
    deviations:       dict[str, float] = field(default_factory=dict)
    metadata:         dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "portfolio_id":     self.portfolio_id,
            "allocation_score": self.allocation_score,
            "by_asset_class":   self.by_asset_class,
            "rebalancing_needed": self.rebalancing_needed,
            "deviations":       self.deviations,
            "metadata":         self.metadata,
        }


class AllocationAnalyzer:
    """
    Converts an AllocationReport into an AllocationAnalysis summary,
    and computes actual-weight breakdown by asset class from the portfolio.
    """

    def analyze(
        self,
        portfolio:      Portfolio,
        alloc_report:   AllocationReport,
    ) -> AllocationAnalysis:
        nav = portfolio.total_nav
        by_ac: dict[str, float] = {}
        if nav > 0:
            for p in portfolio.positions.values():
                ac = p.asset_class.value
                by_ac[ac] = by_ac.get(ac, 0.0) + p.market_value / nav

        return AllocationAnalysis(
            portfolio_id      = portfolio.portfolio_id,
            allocation_score  = alloc_report.allocation_score,
            by_asset_class    = {k: round(v, 6) for k, v in by_ac.items()},
            rebalancing_needed = alloc_report.rebalancing_needed,
            deviations        = alloc_report.deviations,
            metadata          = {"n_asset_classes": len(by_ac)},
        )
