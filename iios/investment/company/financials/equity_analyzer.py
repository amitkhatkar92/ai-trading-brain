"""iios/investment/company/financials/equity_analyzer.py
Analyzes shareholder equity from a BalanceSheet.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from iios.investment.company.financials.balance_sheet import BalanceSheet


def _pct(n: Optional[float], d: Optional[float]) -> Optional[float]:
    if n is None or d is None or d == 0:
        return None
    return 100.0 * n / d


@dataclass
class EquityMetrics:
    # Components as % of total equity
    retained_earnings_ratio: Optional[float] = None   # %
    paid_in_capital_ratio:   Optional[float] = None   # %

    # Absolute
    total_equity:            Optional[float] = None
    retained_earnings:       Optional[float] = None
    common_stock:            Optional[float] = None
    additional_paid_in_capital: Optional[float] = None
    minority_interest:       Optional[float] = None

    # Equity to assets
    equity_to_assets:        Optional[float] = None   # %

    # Is equity negative?
    is_negative_equity: bool = False

    # Net cash position
    net_cash: Optional[float] = None

    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_equity":              self.total_equity,
            "retained_earnings":         self.retained_earnings,
            "common_stock":              self.common_stock,
            "additional_paid_in_capital": self.additional_paid_in_capital,
            "minority_interest":         self.minority_interest,
            "retained_earnings_ratio":   self.retained_earnings_ratio,
            "paid_in_capital_ratio":     self.paid_in_capital_ratio,
            "equity_to_assets":          self.equity_to_assets,
            "is_negative_equity":        self.is_negative_equity,
            "net_cash":                  self.net_cash,
        }


class EquityAnalyzer:
    """Extracts equity structure metrics from a BalanceSheet."""

    def analyze(self, bs: BalanceSheet) -> EquityMetrics:
        eq = bs.total_equity
        ta = bs.total_assets

        m = EquityMetrics(
            total_equity=eq,
            retained_earnings=bs.retained_earnings,
            common_stock=bs.common_stock,
            additional_paid_in_capital=bs.additional_paid_in_capital,
            minority_interest=bs.minority_interest,
            net_cash=bs.net_cash,
        )

        m.retained_earnings_ratio  = _pct(bs.retained_earnings, eq)
        m.paid_in_capital_ratio    = _pct(bs.additional_paid_in_capital, eq)
        m.equity_to_assets         = _pct(eq, ta)
        m.is_negative_equity       = (eq is not None and eq < 0)

        return m
