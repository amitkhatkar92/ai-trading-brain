"""iios/investment/company/financials/liability_analyzer.py
Analyzes liability structure from a BalanceSheet.
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
class LiabilityMetrics:
    # Structure (% of total liabilities)
    current_liabilities_ratio:     Optional[float] = None   # %
    non_current_liabilities_ratio: Optional[float] = None   # %
    short_term_debt_ratio:         Optional[float] = None   # % of total liabilities
    long_term_debt_ratio:          Optional[float] = None   # % of total liabilities

    # % of total assets
    total_liabilities_to_assets:   Optional[float] = None   # %

    # Absolute
    total_liabilities:             Optional[float] = None
    total_current_liabilities:     Optional[float] = None
    total_debt:                    Optional[float] = None
    short_term_debt:               Optional[float] = None
    long_term_debt:                Optional[float] = None
    accounts_payable:              Optional[float] = None

    # Leverage flags
    is_over_leveraged: bool = False    # total_debt > total_equity × 2

    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_liabilities_ratio":     self.current_liabilities_ratio,
            "non_current_liabilities_ratio": self.non_current_liabilities_ratio,
            "short_term_debt_ratio":         self.short_term_debt_ratio,
            "long_term_debt_ratio":          self.long_term_debt_ratio,
            "total_liabilities_to_assets":   self.total_liabilities_to_assets,
            "total_liabilities":             self.total_liabilities,
            "total_current_liabilities":     self.total_current_liabilities,
            "total_debt":                    self.total_debt,
            "short_term_debt":               self.short_term_debt,
            "long_term_debt":                self.long_term_debt,
            "accounts_payable":              self.accounts_payable,
            "is_over_leveraged":             self.is_over_leveraged,
        }


class LiabilityAnalyzer:
    """Extracts liability structure metrics from a BalanceSheet."""

    _OVER_LEVERAGE_THRESHOLD = 2.0   # debt/equity

    def analyze(self, bs: BalanceSheet) -> LiabilityMetrics:
        tl   = bs.total_liabilities
        ta   = bs.total_assets
        td   = bs.total_debt
        eq   = bs.total_equity

        m = LiabilityMetrics(
            total_liabilities=tl,
            total_current_liabilities=bs.total_current_liabilities,
            total_debt=td,
            short_term_debt=bs.short_term_debt,
            long_term_debt=bs.long_term_debt,
            accounts_payable=bs.accounts_payable,
        )

        m.current_liabilities_ratio     = _pct(bs.total_current_liabilities, tl)
        m.non_current_liabilities_ratio = _pct(bs.total_non_current_liabilities, tl)
        m.short_term_debt_ratio         = _pct(bs.short_term_debt, tl)
        m.long_term_debt_ratio          = _pct(bs.long_term_debt, tl)
        m.total_liabilities_to_assets   = _pct(tl, ta)

        if td is not None and eq is not None and eq > 0:
            m.is_over_leveraged = (td / eq) > self._OVER_LEVERAGE_THRESHOLD

        return m
