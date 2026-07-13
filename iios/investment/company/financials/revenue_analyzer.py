"""iios/investment/company/financials/revenue_analyzer.py
Analyzes revenue composition and structure from an IncomeStatement.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from iios.investment.company.financials.income_statement import IncomeStatement


@dataclass
class RevenueMetrics:
    revenue:               Optional[float] = None
    other_income:          Optional[float] = None
    total_income:          Optional[float] = None
    other_income_pct:      Optional[float] = None   # other income as % of total
    revenue_per_share:     Optional[float] = None   # if shares available
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "revenue":           self.revenue,
            "other_income":      self.other_income,
            "total_income":      self.total_income,
            "other_income_pct":  self.other_income_pct,
            "revenue_per_share": self.revenue_per_share,
        }


class RevenueAnalyzer:
    def analyze(self, is_: IncomeStatement) -> RevenueMetrics:
        m = RevenueMetrics(
            revenue=is_.revenue,
            other_income=is_.other_income,
            total_income=is_.total_income,
        )
        if is_.other_income is not None and is_.total_income and is_.total_income > 0:
            m.other_income_pct = 100.0 * is_.other_income / is_.total_income

        if is_.revenue is not None and is_.shares_outstanding_basic and is_.shares_outstanding_basic > 0:
            m.revenue_per_share = is_.revenue / is_.shares_outstanding_basic

        return m
