"""iios/investment/company/financials/investing_cashflow.py
Analyzes investing cash flow from a CashFlowStatement.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from iios.investment.company.financials.cash_flow_statement import CashFlowStatement
from iios.investment.company.financials.income_statement import IncomeStatement


def _pct(n: Optional[float], d: Optional[float]) -> Optional[float]:
    if n is None or d is None or d == 0:
        return None
    return 100.0 * n / d


@dataclass
class InvestingCFMetrics:
    investing_cash_flow:   Optional[float] = None
    capital_expenditure:   Optional[float] = None   # as stored (negative = outflow)
    capex_abs:             Optional[float] = None   # absolute value for display
    acquisitions:          Optional[float] = None
    net_investment_inflow: Optional[float] = None   # proceeds - purchases

    # CapEx intensity
    capex_to_revenue_pct:  Optional[float] = None   # %

    # Growth vs maintenance
    is_net_investor: bool = False   # net outflow → investing for growth

    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "investing_cash_flow":   self.investing_cash_flow,
            "capital_expenditure":   self.capital_expenditure,
            "capex_abs":             self.capex_abs,
            "acquisitions":          self.acquisitions,
            "net_investment_inflow": self.net_investment_inflow,
            "capex_to_revenue_pct":  self.capex_to_revenue_pct,
            "is_net_investor":       self.is_net_investor,
        }


class InvestingCashFlowAnalyzer:
    def analyze(
        self,
        cf:  CashFlowStatement,
        is_: Optional[IncomeStatement] = None,
    ) -> InvestingCFMetrics:
        capex = cf.capital_expenditure
        m = InvestingCFMetrics(
            investing_cash_flow=cf.investing_cash_flow,
            capital_expenditure=capex,
            capex_abs=abs(capex) if capex is not None else None,
            acquisitions=cf.acquisitions,
        )

        inflow  = (cf.proceeds_from_investments or 0) + (cf.proceeds_from_disposals or 0)
        outflow = (cf.purchases_of_investments or 0)
        if inflow or outflow:
            m.net_investment_inflow = inflow - abs(outflow)

        m.is_net_investor = (cf.investing_cash_flow is not None and cf.investing_cash_flow < 0)

        if is_ and is_.revenue and capex is not None:
            m.capex_to_revenue_pct = _pct(abs(capex), is_.revenue)

        return m
