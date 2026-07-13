"""iios/investment/company/financials/income_statement_engine.py
Orchestrates income statement analysis.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from iios.investment.company.financials.income_statement import IncomeStatement
from iios.investment.company.financials.revenue_analyzer import RevenueAnalyzer, RevenueMetrics
from iios.investment.company.financials.expense_analyzer import ExpenseAnalyzer, ExpenseMetrics
from iios.investment.company.financials.profit_analyzer import ProfitAnalyzer, ProfitMetrics


@dataclass
class IncomeStatementIntelligence:
    """Full income statement intelligence for one period."""
    period_label: str
    revenue:      RevenueMetrics = field(default_factory=RevenueMetrics)
    expenses:     ExpenseMetrics = field(default_factory=ExpenseMetrics)
    profit:       ProfitMetrics  = field(default_factory=ProfitMetrics)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "period_label": self.period_label,
            "revenue":      self.revenue.to_dict(),
            "expenses":     self.expenses.to_dict(),
            "profit":       self.profit.to_dict(),
        }


class IncomeStatementEngine:
    def __init__(self) -> None:
        self._revenue  = RevenueAnalyzer()
        self._expense  = ExpenseAnalyzer()
        self._profit   = ProfitAnalyzer()

    def analyze(self, is_: IncomeStatement) -> IncomeStatementIntelligence:
        return IncomeStatementIntelligence(
            period_label=is_.period.label,
            revenue=self._revenue.analyze(is_),
            expenses=self._expense.analyze(is_),
            profit=self._profit.analyze(is_),
        )
