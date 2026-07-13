"""iios/investment/company/financials/ratio_calculator.py
Computes all registered ratios from a set of financial statements.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from iios.investment.company.financials.balance_sheet import BalanceSheet
from iios.investment.company.financials.income_statement import IncomeStatement
from iios.investment.company.financials.cash_flow_statement import CashFlowStatement
from iios.investment.company.financials.financial_ratios import RatioCategory, RatioResult
from iios.investment.company.financials.ratio_registry import RatioRegistry


class RatioCalculator:
    """Computes all ratios from statement inputs."""

    def __init__(self, registry: Optional[RatioRegistry] = None) -> None:
        self._registry = registry or RatioRegistry.get_instance()

    def compute_all(
        self,
        bs:  Optional[BalanceSheet],
        is_: Optional[IncomeStatement],
        cf:  Optional[CashFlowStatement],
        period_label: str = "",
    ) -> Dict[str, Optional[float]]:
        """Return dict {ratio_name: value} for all registered ratios."""
        results: Dict[str, Optional[float]] = {}
        for defn in self._registry.list_all():
            results[defn.name] = defn.compute(bs, is_, cf)
        return results

    def compute_by_category(
        self,
        category: RatioCategory,
        bs:  Optional[BalanceSheet],
        is_: Optional[IncomeStatement],
        cf:  Optional[CashFlowStatement],
    ) -> List[RatioResult]:
        """Compute only ratios in the given category, return RatioResult list."""
        results: List[RatioResult] = []
        for defn in self._registry.list_by_category(category):
            val = defn.compute(bs, is_, cf)
            results.append(RatioResult(
                name=defn.name,
                value=val,
                category=defn.category,
                unit=defn.unit,
            ))
        return results

    def compute_single(
        self,
        name: str,
        bs:  Optional[BalanceSheet],
        is_: Optional[IncomeStatement],
        cf:  Optional[CashFlowStatement],
    ) -> Optional[float]:
        defn = self._registry.get(name)
        return defn.compute(bs, is_, cf) if defn else None

    def known_ratio_names(self) -> List[str]:
        return self._registry.names()
