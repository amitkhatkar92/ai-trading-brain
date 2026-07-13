"""iios/investment/company/financials/profit_analyzer.py
Analyzes profitability from an IncomeStatement.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from iios.investment.company.financials.income_statement import IncomeStatement


@dataclass
class ProfitMetrics:
    # Absolute earnings levels
    gross_profit:         Optional[float] = None
    ebitda:               Optional[float] = None
    ebit:                 Optional[float] = None
    ebt:                  Optional[float] = None
    net_income:           Optional[float] = None
    net_income_to_common: Optional[float] = None

    # Margins (%)
    gross_margin:  Optional[float] = None
    ebitda_margin: Optional[float] = None
    ebit_margin:   Optional[float] = None
    net_margin:    Optional[float] = None

    # Per share
    basic_eps:   Optional[float] = None
    diluted_eps: Optional[float] = None

    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gross_profit":         self.gross_profit,
            "ebitda":               self.ebitda,
            "ebit":                 self.ebit,
            "ebt":                  self.ebt,
            "net_income":           self.net_income,
            "net_income_to_common": self.net_income_to_common,
            "gross_margin":         self.gross_margin,
            "ebitda_margin":        self.ebitda_margin,
            "ebit_margin":          self.ebit_margin,
            "net_margin":           self.net_margin,
            "basic_eps":            self.basic_eps,
            "diluted_eps":          self.diluted_eps,
        }


class ProfitAnalyzer:
    def analyze(self, is_: IncomeStatement) -> ProfitMetrics:
        return ProfitMetrics(
            gross_profit=is_.gross_profit,
            ebitda=is_.ebitda,
            ebit=is_.ebit,
            ebt=is_.ebt,
            net_income=is_.net_income,
            net_income_to_common=is_.net_income_to_common,
            gross_margin=is_.gross_margin,
            ebitda_margin=is_.ebitda_margin,
            ebit_margin=is_.ebit_margin,
            net_margin=is_.net_margin,
            basic_eps=is_.basic_eps,
            diluted_eps=is_.diluted_eps,
        )
