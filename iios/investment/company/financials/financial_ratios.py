"""iios/investment/company/financials/financial_ratios.py
Ratio category enums and the RatioResult value object.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional

from iios.investment.company.financials.balance_sheet import BalanceSheet
from iios.investment.company.financials.income_statement import IncomeStatement
from iios.investment.company.financials.cash_flow_statement import CashFlowStatement


class RatioCategory(str, Enum):
    LIQUIDITY        = "liquidity"
    PROFITABILITY    = "profitability"
    LEVERAGE         = "leverage"
    EFFICIENCY       = "efficiency"
    CASHFLOW         = "cashflow"
    CAPITAL_STRUCTURE = "capital_structure"
    RETURNS          = "returns"
    COVERAGE         = "coverage"
    PER_SHARE        = "per_share"


# Type alias for a ratio calculator function
RatioFn = Callable[
    [Optional[BalanceSheet], Optional[IncomeStatement], Optional[CashFlowStatement]],
    Optional[float],
]


@dataclass(frozen=True)
class RatioDefinition:
    """Static definition of a financial ratio."""
    name:                str
    category:            RatioCategory
    formula_description: str
    unit:                str           # "x", "%", "", "days"
    higher_is_better:    Optional[bool] = None  # None = context-dependent
    calculator:          Optional[RatioFn] = None  # callable; set at registration

    def compute(
        self,
        bs: Optional[BalanceSheet],
        is_: Optional[IncomeStatement],
        cf: Optional[CashFlowStatement],
    ) -> Optional[float]:
        if self.calculator is None:
            return None
        try:
            return self.calculator(bs, is_, cf)
        except Exception:
            return None

    def to_dict(self) -> dict:
        return {
            "name":                self.name,
            "category":            self.category.value,
            "formula_description": self.formula_description,
            "unit":                self.unit,
            "higher_is_better":    self.higher_is_better,
        }


@dataclass
class RatioResult:
    """Computed value of a single ratio for one period."""
    name:     str
    value:    Optional[float]
    category: RatioCategory
    unit:     str
    period_label: str = ""
    note:     str     = ""

    def to_dict(self) -> dict:
        return {
            "name":         self.name,
            "value":        self.value,
            "category":     self.category.value,
            "unit":         self.unit,
            "period_label": self.period_label,
            "note":         self.note,
        }
