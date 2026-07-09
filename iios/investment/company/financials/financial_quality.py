"""iios/investment/company/financials/financial_quality.py
Earnings quality assessment based on accruals and CF/earnings ratio.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from iios.investment.company.financials.income_statement_analyzer import IncomeStatementAnalysis
from iios.investment.company.financials.balance_sheet_analyzer import BalanceSheetAnalysis
from iios.investment.company.financials.cashflow_analyzer import CashflowAnalysis


@dataclass
class FinancialQualityAnalysis:
    """
    Composite earnings quality assessment.

    High-quality earnings = mostly cash-backed, low accruals, consistent.
    """

    earnings_quality_score: float         = 50.0   # 0–100
    accrual_ratio:          float         = 0.0    # (NI − OCF) / avg_assets
    cf_to_earnings:         float         = 0.0    # OCF / PAT
    quality_level:          str           = "moderate"   # high / moderate / low / poor
    metadata:               dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "earnings_quality_score": self.earnings_quality_score,
            "accrual_ratio":          self.accrual_ratio,
            "cf_to_earnings":         self.cf_to_earnings,
            "quality_level":          self.quality_level,
            "metadata":               self.metadata,
        }


class FinancialQualityAnalyzer:
    """
    Derives earnings quality from income, balance sheet, and cash flow.
    """

    def analyze(
        self,
        income:   IncomeStatementAnalysis,
        cashflow: CashflowAnalysis,
        balance:  BalanceSheetAnalysis,
    ) -> FinancialQualityAnalysis:
        pat    = income.revenue * income.pat_margin if income.revenue > 0 else 0.0
        ocf    = cashflow.operating_cf
        assets = balance.total_assets

        # Accrual ratio: (PAT − OCF) / total_assets
        accrual_ratio = (pat - ocf) / assets if assets > 0 else 0.0

        # CF/Earnings ratio (>1 = high quality)
        cf_to_earnings = cashflow.cf_quality  # already computed in cashflow analyzer

        # Score: based on cf_to_earnings and accrual_ratio
        quality_score = self._score(cf_to_earnings, accrual_ratio)

        if quality_score >= 75:
            quality_level = "high"
        elif quality_score >= 55:
            quality_level = "moderate"
        elif quality_score >= 35:
            quality_level = "low"
        else:
            quality_level = "poor"

        return FinancialQualityAnalysis(
            earnings_quality_score = round(quality_score, 2),
            accrual_ratio          = round(accrual_ratio, 6),
            cf_to_earnings         = round(cf_to_earnings, 4),
            quality_level          = quality_level,
            metadata               = {
                "pat_estimate": round(pat, 2),
                "ocf":          round(ocf, 2),
            },
        )

    @staticmethod
    def _score(cf_to_earnings: float, accrual_ratio: float) -> float:
        # CF/Earnings component (70%)
        if cf_to_earnings >= 1.5:
            cfe_score = 100.0
        elif cf_to_earnings >= 1.0:
            cfe_score = 80.0
        elif cf_to_earnings >= 0.75:
            cfe_score = 60.0
        elif cf_to_earnings >= 0.50:
            cfe_score = 40.0
        elif cf_to_earnings >= 0:
            cfe_score = 20.0
        else:
            cfe_score = 0.0

        # Accrual ratio component (30%): lower abs value = better
        abs_acc = abs(accrual_ratio)
        if abs_acc < 0.01:
            acc_score = 100.0
        elif abs_acc < 0.03:
            acc_score = 75.0
        elif abs_acc < 0.06:
            acc_score = 50.0
        elif abs_acc < 0.10:
            acc_score = 25.0
        else:
            acc_score = 0.0

        return cfe_score * 0.70 + acc_score * 0.30
