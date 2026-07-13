"""iios/investment/company/financials/balance_sheet_engine.py
Orchestrates BalanceSheet analysis using AssetAnalyzer, LiabilityAnalyzer, EquityAnalyzer.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from iios.investment.company.financials.balance_sheet import BalanceSheet
from iios.investment.company.financials.asset_analyzer import AssetAnalyzer, AssetMetrics
from iios.investment.company.financials.liability_analyzer import LiabilityAnalyzer, LiabilityMetrics
from iios.investment.company.financials.equity_analyzer import EquityAnalyzer, EquityMetrics


@dataclass
class BalanceSheetIntelligence:
    """Full balance sheet intelligence for one period."""
    period_label: str
    assets:       AssetMetrics     = field(default_factory=AssetMetrics)
    liabilities:  LiabilityMetrics = field(default_factory=LiabilityMetrics)
    equity:       EquityMetrics    = field(default_factory=EquityMetrics)

    # Quick-access computed fields
    working_capital:      Optional[float] = None
    current_ratio:        Optional[float] = None
    debt_to_equity:       Optional[float] = None
    net_cash:             Optional[float] = None
    is_net_cash_positive: bool = False

    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "period_label":       self.period_label,
            "assets":             self.assets.to_dict(),
            "liabilities":        self.liabilities.to_dict(),
            "equity":             self.equity.to_dict(),
            "working_capital":    self.working_capital,
            "current_ratio":      self.current_ratio,
            "debt_to_equity":     self.debt_to_equity,
            "net_cash":           self.net_cash,
            "is_net_cash_positive": self.is_net_cash_positive,
        }


class BalanceSheetEngine:
    """Produces BalanceSheetIntelligence from a BalanceSheet."""

    def __init__(self) -> None:
        self._asset_analyzer     = AssetAnalyzer()
        self._liability_analyzer = LiabilityAnalyzer()
        self._equity_analyzer    = EquityAnalyzer()

    def analyze(self, bs: BalanceSheet) -> BalanceSheetIntelligence:
        intel = BalanceSheetIntelligence(period_label=bs.period.label)
        intel.assets      = self._asset_analyzer.analyze(bs)
        intel.liabilities = self._liability_analyzer.analyze(bs)
        intel.equity      = self._equity_analyzer.analyze(bs)

        intel.working_capital = bs.working_capital
        intel.net_cash        = bs.net_cash
        intel.is_net_cash_positive = (bs.net_cash is not None and bs.net_cash > 0)

        # Current ratio
        ca = bs.total_current_assets
        cl = bs.total_current_liabilities
        if ca is not None and cl is not None and cl > 0:
            intel.current_ratio = ca / cl

        # Debt to equity
        td = bs.total_debt
        eq = bs.total_equity
        if td is not None and eq is not None and eq != 0:
            intel.debt_to_equity = td / eq

        return intel
