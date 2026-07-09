"""iios/investment/company/financials/financial_engine.py
Coordinates all financial sub-analyzers into a single FinancialAnalysis.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any

from iios.investment.company.company_constants import FinancialHealth, GrowthProfile
from iios.investment.company.financials.income_statement_analyzer import (
    IncomeStatementAnalysis,
    IncomeStatementAnalyzer,
)
from iios.investment.company.financials.balance_sheet_analyzer import (
    BalanceSheetAnalysis,
    BalanceSheetAnalyzer,
)
from iios.investment.company.financials.cashflow_analyzer import (
    CashflowAnalysis,
    CashflowAnalyzer,
)
from iios.investment.company.financials.financial_quality import (
    FinancialQualityAnalysis,
    FinancialQualityAnalyzer,
)


@dataclass
class FinancialAnalysis:
    """Composite financial analysis combining all four sub-analyses."""

    income:       IncomeStatementAnalysis = field(default_factory=IncomeStatementAnalysis)
    balance:      BalanceSheetAnalysis    = field(default_factory=BalanceSheetAnalysis)
    cashflow:     CashflowAnalysis        = field(default_factory=CashflowAnalysis)
    quality:      FinancialQualityAnalysis = field(default_factory=FinancialQualityAnalysis)
    health:       FinancialHealth         = FinancialHealth.UNKNOWN
    health_score: float                   = 50.0   # 0–100 composite
    growth_score: float                   = 50.0
    growth_profile: GrowthProfile         = GrowthProfile.UNKNOWN
    metadata:     dict[str, Any]          = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "income":         self.income.to_dict(),
            "balance":        self.balance.to_dict(),
            "cashflow":       self.cashflow.to_dict(),
            "quality":        self.quality.to_dict(),
            "health":         self.health.value,
            "health_score":   self.health_score,
            "growth_score":   self.growth_score,
            "growth_profile": self.growth_profile.value,
            "metadata":       self.metadata,
        }


class FinancialEngine:
    """
    Orchestrates income, balance sheet, cash flow, and quality analyzers.

    All data inputs are plain dicts — the engine is provider-agnostic.
    """

    def __init__(
        self,
        income_analyzer:  IncomeStatementAnalyzer  | None = None,
        balance_analyzer: BalanceSheetAnalyzer      | None = None,
        cashflow_analyzer: CashflowAnalyzer         | None = None,
        quality_analyzer:  FinancialQualityAnalyzer | None = None,
    ) -> None:
        self._lock     = threading.RLock()
        self._income   = income_analyzer   or IncomeStatementAnalyzer()
        self._balance  = balance_analyzer  or BalanceSheetAnalyzer()
        self._cashflow = cashflow_analyzer or CashflowAnalyzer()
        self._quality  = quality_analyzer  or FinancialQualityAnalyzer()

    def analyze(
        self,
        income_data:   dict[str, Any],
        balance_data:  dict[str, Any],
        cashflow_data: dict[str, Any],
    ) -> FinancialAnalysis:
        income   = self._income.analyze(income_data)
        balance  = self._balance.analyze(balance_data)
        cashflow = self._cashflow.analyze(
            cashflow_data,
            revenue = income.revenue,
            pat     = income.revenue * income.pat_margin if income.revenue > 0 else 0.0,
        )
        quality = self._quality.analyze(income, cashflow, balance)

        health_score = self._composite_health(income, balance, cashflow)
        health       = self._classify_health(health_score)
        growth_profile = self._classify_growth(income.revenue_growth_yoy)

        return FinancialAnalysis(
            income        = income,
            balance       = balance,
            cashflow      = cashflow,
            quality       = quality,
            health        = health,
            health_score  = round(health_score, 2),
            growth_score  = income.growth_score,
            growth_profile = growth_profile,
            metadata      = {"composite_inputs": 3},
        )

    @staticmethod
    def _composite_health(
        income:   IncomeStatementAnalysis,
        balance:  BalanceSheetAnalysis,
        cashflow: CashflowAnalysis,
    ) -> float:
        return (
            income.health_score   * 0.40
            + balance.health_score * 0.35
            + cashflow.health_score * 0.25
        )

    @staticmethod
    def _classify_health(score: float) -> FinancialHealth:
        if score >= 80:
            return FinancialHealth.VERY_STRONG
        elif score >= 65:
            return FinancialHealth.STRONG
        elif score >= 50:
            return FinancialHealth.MODERATE
        elif score >= 35:
            return FinancialHealth.WEAK
        elif score >= 20:
            return FinancialHealth.VERY_WEAK
        else:
            return FinancialHealth.DISTRESSED

    @staticmethod
    def _classify_growth(rev_growth: float) -> GrowthProfile:
        if rev_growth >= 0.25:
            return GrowthProfile.HIGH_GROWTH
        elif rev_growth >= 0.12:
            return GrowthProfile.GROWTH
        elif rev_growth >= 0.05:
            return GrowthProfile.MODERATE
        elif rev_growth >= 0:
            return GrowthProfile.LOW_GROWTH
        elif rev_growth >= -0.15:
            return GrowthProfile.DECLINING
        else:
            return GrowthProfile.TURNAROUND
