"""iios/investment/portfolio/analytics/performance_analyzer.py"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from iios.investment.portfolio.core.portfolio import Portfolio


@dataclass
class PerformanceAnalysis:
    portfolio_id:       str   = ""
    total_nav:          float = 0.0
    unrealized_pnl:     float = 0.0
    unrealized_pnl_pct: float = 0.0
    cost_basis_total:   float = 0.0
    performance_score:  float = 50.0    # 0–100
    metadata:           dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "portfolio_id":       self.portfolio_id,
            "total_nav":          self.total_nav,
            "unrealized_pnl":     self.unrealized_pnl,
            "unrealized_pnl_pct": self.unrealized_pnl_pct,
            "cost_basis_total":   self.cost_basis_total,
            "performance_score":  self.performance_score,
            "metadata":           self.metadata,
        }


class PerformanceAnalyzer:
    """Computes P&L and performance score from open positions."""

    def analyze(self, portfolio: Portfolio) -> PerformanceAnalysis:
        nav         = portfolio.total_nav
        pnl         = portfolio.unrealized_pnl
        cost_total  = sum(p.cost_basis for p in portfolio.positions.values())
        pnl_pct     = portfolio.unrealized_pnl_pct

        # Performance score: 50 at breakeven, +25% pnl → 100, -25% → 0
        perf_score  = max(0.0, min(100.0, 50.0 + pnl_pct * 200.0))

        return PerformanceAnalysis(
            portfolio_id       = portfolio.portfolio_id,
            total_nav          = nav,
            unrealized_pnl     = round(pnl, 2),
            unrealized_pnl_pct = round(pnl_pct, 6),
            cost_basis_total   = round(cost_total, 2),
            performance_score  = round(perf_score, 2),
            metadata           = {"position_count": portfolio.position_count},
        )
