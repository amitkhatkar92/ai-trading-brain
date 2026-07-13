"""iios/investment/company/financials/expense_analyzer.py
Analyzes cost structure from an IncomeStatement.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from iios.investment.company.financials.income_statement import IncomeStatement


def _pct(n: Optional[float], d: Optional[float]) -> Optional[float]:
    if n is None or d is None or d == 0:
        return None
    return 100.0 * n / d


@dataclass
class ExpenseMetrics:
    # % of revenue
    cogs_pct:        Optional[float] = None   # cost of revenue / revenue
    sga_pct:         Optional[float] = None   # SG&A / revenue
    rd_pct:          Optional[float] = None   # R&D / revenue
    da_pct:          Optional[float] = None   # D&A / revenue
    interest_pct:    Optional[float] = None   # interest / revenue
    tax_rate:        Optional[float] = None   # effective tax rate %

    # Absolute
    cost_of_revenue:          Optional[float] = None
    selling_general_admin:    Optional[float] = None
    research_and_development: Optional[float] = None
    depreciation_amortization: Optional[float] = None
    interest_expense:         Optional[float] = None
    tax_expense:              Optional[float] = None

    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cogs_pct":        self.cogs_pct,
            "sga_pct":         self.sga_pct,
            "rd_pct":          self.rd_pct,
            "da_pct":          self.da_pct,
            "interest_pct":    self.interest_pct,
            "tax_rate":        self.tax_rate,
            "cost_of_revenue": self.cost_of_revenue,
            "selling_general_admin":    self.selling_general_admin,
            "research_and_development": self.research_and_development,
            "depreciation_amortization": self.depreciation_amortization,
            "interest_expense": self.interest_expense,
            "tax_expense":      self.tax_expense,
        }


class ExpenseAnalyzer:
    def analyze(self, is_: IncomeStatement) -> ExpenseMetrics:
        rev = is_.revenue
        m = ExpenseMetrics(
            cost_of_revenue=is_.cost_of_revenue,
            selling_general_admin=is_.selling_general_admin,
            research_and_development=is_.research_and_development,
            depreciation_amortization=is_.depreciation_amortization,
            interest_expense=is_.interest_expense,
            tax_expense=is_.tax_expense,
        )
        m.cogs_pct     = _pct(is_.cost_of_revenue, rev)
        m.sga_pct      = _pct(is_.selling_general_admin, rev)
        m.rd_pct       = _pct(is_.research_and_development, rev)
        m.da_pct       = _pct(is_.depreciation_amortization, rev)
        m.interest_pct = _pct(is_.interest_expense, rev)
        m.tax_rate     = is_.effective_tax_rate if is_.effective_tax_rate is not None else (
            _pct(is_.tax_expense, is_.ebt) if is_.ebt and is_.ebt > 0 else None
        )
        return m
