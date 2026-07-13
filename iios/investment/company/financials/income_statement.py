"""iios/investment/company/financials/income_statement.py
Raw income statement data model — no analysis, no scoring.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from iios.investment.company.financials.financial_period import FinancialPeriod, FinancialUnit


@dataclass
class IncomeStatement:
    """Raw income statement for one financial period."""
    period:   FinancialPeriod
    currency: str           = "INR"
    unit:     FinancialUnit = FinancialUnit.CRORES
    restated: bool          = False

    # ── Revenue ────────────────────────────────────────────────────────────────
    revenue:          Optional[float] = None   # net revenue / net sales
    other_income:     Optional[float] = None
    total_income:     Optional[float] = None

    # ── Cost structure ─────────────────────────────────────────────────────────
    cost_of_revenue:           Optional[float] = None   # COGS / cost of goods sold
    gross_profit:              Optional[float] = None
    selling_general_admin:     Optional[float] = None   # SG&A
    research_and_development:  Optional[float] = None
    other_operating_expenses:  Optional[float] = None
    total_operating_expenses:  Optional[float] = None

    # ── Earnings levels ────────────────────────────────────────────────────────
    ebitda:                    Optional[float] = None
    depreciation_amortization: Optional[float] = None
    ebit:                      Optional[float] = None   # operating profit
    interest_expense:          Optional[float] = None
    interest_income:           Optional[float] = None
    ebt:                       Optional[float] = None   # earnings before tax
    tax_expense:               Optional[float] = None
    effective_tax_rate:        Optional[float] = None   # %
    net_income:                Optional[float] = None
    minority_interest_pnl:     Optional[float] = None
    net_income_to_common:      Optional[float] = None   # after minority interest

    # ── Per-share ──────────────────────────────────────────────────────────────
    basic_eps:                 Optional[float] = None
    diluted_eps:               Optional[float] = None
    shares_outstanding_basic:  Optional[float] = None   # in millions
    shares_outstanding_diluted: Optional[float] = None

    # ── Margins (%) ───────────────────────────────────────────────────────────
    # computed properties; raw values stored above

    metadata: Dict[str, Any] = field(default_factory=dict)

    # ── Computed properties ───────────────────────────────────────────────────

    @property
    def gross_margin(self) -> Optional[float]:
        if self.gross_profit is not None and self.revenue and self.revenue > 0:
            return 100.0 * self.gross_profit / self.revenue
        return None

    @property
    def ebitda_margin(self) -> Optional[float]:
        if self.ebitda is not None and self.revenue and self.revenue > 0:
            return 100.0 * self.ebitda / self.revenue
        return None

    @property
    def ebit_margin(self) -> Optional[float]:
        if self.ebit is not None and self.revenue and self.revenue > 0:
            return 100.0 * self.ebit / self.revenue
        return None

    @property
    def net_margin(self) -> Optional[float]:
        ni  = self.net_income_to_common if self.net_income_to_common is not None else self.net_income
        if ni is not None and self.revenue and self.revenue > 0:
            return 100.0 * ni / self.revenue
        return None

    def completeness_pct(self) -> float:
        key_fields = [
            self.revenue, self.cost_of_revenue, self.gross_profit,
            self.ebitda, self.ebit, self.interest_expense,
            self.ebt, self.tax_expense, self.net_income, self.basic_eps,
        ]
        filled = sum(1 for f in key_fields if f is not None)
        return 100.0 * filled / len(key_fields)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "period":   self.period.to_dict(),
            "currency": self.currency,
            "unit":     self.unit.value,
            "restated": self.restated,
            "revenue":                      self.revenue,
            "other_income":                 self.other_income,
            "total_income":                 self.total_income,
            "cost_of_revenue":              self.cost_of_revenue,
            "gross_profit":                 self.gross_profit,
            "selling_general_admin":        self.selling_general_admin,
            "research_and_development":     self.research_and_development,
            "total_operating_expenses":     self.total_operating_expenses,
            "ebitda":                       self.ebitda,
            "depreciation_amortization":    self.depreciation_amortization,
            "ebit":                         self.ebit,
            "interest_expense":             self.interest_expense,
            "interest_income":              self.interest_income,
            "ebt":                          self.ebt,
            "tax_expense":                  self.tax_expense,
            "effective_tax_rate":           self.effective_tax_rate,
            "net_income":                   self.net_income,
            "net_income_to_common":         self.net_income_to_common,
            "basic_eps":                    self.basic_eps,
            "diluted_eps":                  self.diluted_eps,
            "shares_outstanding_basic":     self.shares_outstanding_basic,
            "shares_outstanding_diluted":   self.shares_outstanding_diluted,
            # computed margins
            "gross_margin":   self.gross_margin,
            "ebitda_margin":  self.ebitda_margin,
            "ebit_margin":    self.ebit_margin,
            "net_margin":     self.net_margin,
            "completeness_pct": round(self.completeness_pct(), 1),
        }

    @staticmethod
    def from_dict(data: Dict[str, Any], period: FinancialPeriod) -> "IncomeStatement":
        is_ = IncomeStatement(period=period)
        for field_name in (
            "revenue", "other_income", "total_income", "cost_of_revenue",
            "gross_profit", "selling_general_admin", "research_and_development",
            "other_operating_expenses", "total_operating_expenses", "ebitda",
            "depreciation_amortization", "ebit", "interest_expense", "interest_income",
            "ebt", "tax_expense", "effective_tax_rate", "net_income",
            "minority_interest_pnl", "net_income_to_common", "basic_eps",
            "diluted_eps", "shares_outstanding_basic", "shares_outstanding_diluted",
        ):
            val = data.get(field_name)
            if val is not None:
                try:
                    setattr(is_, field_name, float(val))
                except (TypeError, ValueError):
                    pass
        is_.currency = str(data.get("currency", "INR"))
        is_.restated  = bool(data.get("restated", False))
        return is_
