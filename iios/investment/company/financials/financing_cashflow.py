"""iios/investment/company/financials/financing_cashflow.py
Analyzes financing cash flow from a CashFlowStatement.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from iios.investment.company.financials.cash_flow_statement import CashFlowStatement


@dataclass
class FinancingCFMetrics:
    financing_cash_flow: Optional[float] = None
    debt_issued:         Optional[float] = None
    debt_repaid:         Optional[float] = None
    net_debt_change:     Optional[float] = None   # debt_issued - |debt_repaid|
    equity_issued:       Optional[float] = None
    equity_repurchased:  Optional[float] = None   # buybacks (stored as negative)
    dividends_paid:      Optional[float] = None

    # Is the company borrowing net?
    is_net_borrower:     bool = False
    # Is the company returning capital (buybacks + dividends)?
    is_returning_capital: bool = False

    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "financing_cash_flow":  self.financing_cash_flow,
            "debt_issued":          self.debt_issued,
            "debt_repaid":          self.debt_repaid,
            "net_debt_change":      self.net_debt_change,
            "equity_issued":        self.equity_issued,
            "equity_repurchased":   self.equity_repurchased,
            "dividends_paid":       self.dividends_paid,
            "is_net_borrower":      self.is_net_borrower,
            "is_returning_capital": self.is_returning_capital,
        }


class FinancingCashFlowAnalyzer:
    def analyze(self, cf: CashFlowStatement) -> FinancingCFMetrics:
        m = FinancingCFMetrics(
            financing_cash_flow=cf.financing_cash_flow,
            debt_issued=cf.debt_issued,
            debt_repaid=cf.debt_repaid,
            equity_issued=cf.equity_issued,
            equity_repurchased=cf.equity_repurchased,
            dividends_paid=cf.dividends_paid,
        )

        issued  = cf.debt_issued or 0.0
        repaid  = abs(cf.debt_repaid or 0.0)
        m.net_debt_change = issued - repaid
        m.is_net_borrower = m.net_debt_change > 0

        buybacks  = abs(cf.equity_repurchased or 0.0)
        dividends = abs(cf.dividends_paid or 0.0)
        m.is_returning_capital = (buybacks + dividends) > 0

        return m
