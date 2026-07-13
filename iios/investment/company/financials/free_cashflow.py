"""iios/investment/company/financials/free_cashflow.py
Analyzes free cash flow from a CashFlowStatement.
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
class FreeCashFlowMetrics:
    free_cash_flow:         Optional[float] = None   # OCF - |CapEx|
    operating_cash_flow:    Optional[float] = None
    capital_expenditure_abs: Optional[float] = None
    owner_earnings:         Optional[float] = None   # FCF proxy; same here

    # FCF as % of revenue
    fcf_margin:             Optional[float] = None   # %
    # FCF to net income conversion
    fcf_to_net_income:      Optional[float] = None   # ratio

    # Sustainability flag
    is_fcf_positive:        bool = False
    # Is capex fully covered by OCF?
    ocf_covers_capex:       bool = False

    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "free_cash_flow":          self.free_cash_flow,
            "operating_cash_flow":     self.operating_cash_flow,
            "capital_expenditure_abs": self.capital_expenditure_abs,
            "owner_earnings":          self.owner_earnings,
            "fcf_margin":              self.fcf_margin,
            "fcf_to_net_income":       self.fcf_to_net_income,
            "is_fcf_positive":         self.is_fcf_positive,
            "ocf_covers_capex":        self.ocf_covers_capex,
        }


class FreeCashFlowAnalyzer:
    def analyze(
        self,
        cf:  CashFlowStatement,
        is_: Optional[IncomeStatement] = None,
    ) -> FreeCashFlowMetrics:
        fcf  = cf.free_cash_flow
        ocf  = cf.operating_cash_flow
        capex = abs(cf.capital_expenditure) if cf.capital_expenditure is not None else None

        m = FreeCashFlowMetrics(
            free_cash_flow=fcf,
            operating_cash_flow=ocf,
            capital_expenditure_abs=capex,
            owner_earnings=fcf,   # Buffett-style owner earnings ≈ FCF here
        )

        m.is_fcf_positive  = (fcf is not None and fcf > 0)
        m.ocf_covers_capex = (ocf is not None and capex is not None and ocf >= capex)

        if is_ is not None:
            rev = is_.revenue
            ni  = is_.net_income_to_common or is_.net_income
            m.fcf_margin      = _pct(fcf, rev)
            if ni and ni != 0:
                m.fcf_to_net_income = (fcf / ni) if fcf is not None else None

        return m
