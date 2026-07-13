"""iios/investment/company/financials/cashflow_engine.py
Orchestrates all cash flow analysis.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from iios.investment.company.financials.cash_flow_statement import CashFlowStatement
from iios.investment.company.financials.income_statement import IncomeStatement
from iios.investment.company.financials.operating_cashflow import OperatingCashFlowAnalyzer, OperatingCFMetrics
from iios.investment.company.financials.investing_cashflow import InvestingCashFlowAnalyzer, InvestingCFMetrics
from iios.investment.company.financials.financing_cashflow import FinancingCashFlowAnalyzer, FinancingCFMetrics
from iios.investment.company.financials.free_cashflow import FreeCashFlowAnalyzer, FreeCashFlowMetrics


@dataclass
class CashFlowIntelligence:
    """Full cash flow intelligence for one period."""
    period_label: str
    operating:    OperatingCFMetrics  = field(default_factory=OperatingCFMetrics)
    investing:    InvestingCFMetrics  = field(default_factory=InvestingCFMetrics)
    financing:    FinancingCFMetrics  = field(default_factory=FinancingCFMetrics)
    free_cf:      FreeCashFlowMetrics = field(default_factory=FreeCashFlowMetrics)

    # Net cash movement
    net_change_in_cash: Optional[float] = None
    ending_cash:        Optional[float] = None

    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "period_label":       self.period_label,
            "operating":          self.operating.to_dict(),
            "investing":          self.investing.to_dict(),
            "financing":          self.financing.to_dict(),
            "free_cf":            self.free_cf.to_dict(),
            "net_change_in_cash": self.net_change_in_cash,
            "ending_cash":        self.ending_cash,
        }


class CashFlowEngine:
    def __init__(self) -> None:
        self._operating  = OperatingCashFlowAnalyzer()
        self._investing  = InvestingCashFlowAnalyzer()
        self._financing  = FinancingCashFlowAnalyzer()
        self._free_cf    = FreeCashFlowAnalyzer()

    def analyze(
        self,
        cf:  CashFlowStatement,
        is_: Optional[IncomeStatement] = None,
    ) -> CashFlowIntelligence:
        intel = CashFlowIntelligence(period_label=cf.period.label)
        intel.operating        = self._operating.analyze(cf, is_)
        intel.investing        = self._investing.analyze(cf, is_)
        intel.financing        = self._financing.analyze(cf)
        intel.free_cf          = self._free_cf.analyze(cf, is_)
        intel.net_change_in_cash = cf.net_change_in_cash
        intel.ending_cash        = cf.ending_cash
        return intel
