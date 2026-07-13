"""iios/investment/company/financials/operating_cashflow.py
Analyzes operating cash flow from a CashFlowStatement.
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
class OperatingCFMetrics:
    operating_cash_flow:     Optional[float] = None
    da_added_back:           Optional[float] = None
    working_capital_changes: Optional[float] = None

    # Quality indicators
    ocf_to_net_income:  Optional[float] = None   # ratio; >1 is better
    ocf_to_revenue_pct: Optional[float] = None   # %

    # Is cash generation positive?
    is_cash_generative: bool = False

    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "operating_cash_flow":     self.operating_cash_flow,
            "da_added_back":           self.da_added_back,
            "working_capital_changes": self.working_capital_changes,
            "ocf_to_net_income":       self.ocf_to_net_income,
            "ocf_to_revenue_pct":      self.ocf_to_revenue_pct,
            "is_cash_generative":      self.is_cash_generative,
        }


class OperatingCashFlowAnalyzer:
    def analyze(
        self,
        cf:  CashFlowStatement,
        is_: Optional[IncomeStatement] = None,
    ) -> OperatingCFMetrics:
        m = OperatingCFMetrics(
            operating_cash_flow=cf.operating_cash_flow,
            da_added_back=cf.depreciation_amortization_cf,
            working_capital_changes=cf.changes_in_working_capital,
        )
        m.is_cash_generative = (cf.operating_cash_flow is not None and cf.operating_cash_flow > 0)

        if is_ is not None:
            ni  = is_.net_income_to_common or is_.net_income
            rev = is_.revenue
            m.ocf_to_net_income  = _pct(cf.operating_cash_flow, ni) if ni and ni != 0 else None
            if m.ocf_to_net_income is not None:
                m.ocf_to_net_income /= 100.0   # ratio, not %
            m.ocf_to_revenue_pct = _pct(cf.operating_cash_flow, rev)

        return m
