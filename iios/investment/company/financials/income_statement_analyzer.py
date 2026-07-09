"""iios/investment/company/financials/income_statement_analyzer.py"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from iios.investment.company.company_constants import FinancialHealth


@dataclass
class IncomeStatementAnalysis:
    revenue:            float         = 0.0
    revenue_prev:       float         = 0.0
    revenue_growth_yoy: float         = 0.0   # fraction, e.g. 0.15 = 15%
    gross_margin:       float         = 0.0
    ebitda_margin:      float         = 0.0
    pat_margin:         float         = 0.0
    interest_coverage:  float         = 0.0
    revenue_trend:      str           = "stable"   # growing / declining / stable
    profitability:      FinancialHealth = FinancialHealth.UNKNOWN
    health_score:       float         = 50.0    # 0–100
    growth_score:       float         = 50.0    # 0–100
    metadata:           dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "revenue":            self.revenue,
            "revenue_prev":       self.revenue_prev,
            "revenue_growth_yoy": self.revenue_growth_yoy,
            "gross_margin":       self.gross_margin,
            "ebitda_margin":      self.ebitda_margin,
            "pat_margin":         self.pat_margin,
            "interest_coverage":  self.interest_coverage,
            "revenue_trend":      self.revenue_trend,
            "profitability":      self.profitability.value,
            "health_score":       self.health_score,
            "growth_score":       self.growth_score,
            "metadata":           self.metadata,
        }


class IncomeStatementAnalyzer:
    """
    Derives profitability and growth metrics from an income statement dict.

    Expected keys (all optional, default 0):
      revenue, revenue_prev, gross_profit, ebitda, pat, interest, depreciation
    """

    def analyze(self, data: dict[str, Any]) -> IncomeStatementAnalysis:
        if not data:
            return IncomeStatementAnalysis()

        revenue      = float(data.get("revenue", 0) or 0)
        revenue_prev = float(data.get("revenue_prev", 0) or 0)
        gross        = float(data.get("gross_profit", 0) or 0)
        ebitda       = float(data.get("ebitda", 0) or 0)
        pat          = float(data.get("pat", 0) or 0)
        interest     = float(data.get("interest", 0) or 0)

        # Growth
        rev_growth = (
            (revenue - revenue_prev) / revenue_prev
            if revenue_prev > 0 else 0.0
        )

        # Margins
        gross_margin  = gross  / revenue if revenue > 0 else 0.0
        ebitda_margin = ebitda / revenue if revenue > 0 else 0.0
        pat_margin    = pat    / revenue if revenue > 0 else 0.0

        # Interest coverage
        interest_cov = (
            ebitda / interest if interest > 0
            else (float("inf") if ebitda > 0 else 0.0)
        )

        # Revenue trend
        if rev_growth > 0.05:
            revenue_trend = "growing"
        elif rev_growth < -0.05:
            revenue_trend = "declining"
        else:
            revenue_trend = "stable"

        # Profitability health from PAT margin
        if pat_margin >= 0.20:
            profitability = FinancialHealth.VERY_STRONG
        elif pat_margin >= 0.15:
            profitability = FinancialHealth.STRONG
        elif pat_margin >= 0.10:
            profitability = FinancialHealth.MODERATE
        elif pat_margin >= 0.05:
            profitability = FinancialHealth.WEAK
        elif pat_margin >= 0:
            profitability = FinancialHealth.VERY_WEAK
        else:
            profitability = FinancialHealth.DISTRESSED

        # Scores
        health_score = self._health_score(pat_margin, ebitda_margin, interest_cov)
        growth_score = self._growth_score(rev_growth)

        return IncomeStatementAnalysis(
            revenue            = revenue,
            revenue_prev       = revenue_prev,
            revenue_growth_yoy = round(rev_growth, 6),
            gross_margin       = round(gross_margin, 6),
            ebitda_margin      = round(ebitda_margin, 6),
            pat_margin         = round(pat_margin, 6),
            interest_coverage  = round(min(interest_cov, 999.0), 4),
            revenue_trend      = revenue_trend,
            profitability      = profitability,
            health_score       = round(health_score, 2),
            growth_score       = round(growth_score, 2),
            metadata           = {"n_items": len(data)},
        )

    @staticmethod
    def _health_score(pat_margin: float, ebitda_margin: float, ic: float) -> float:
        # PAT margin component (60%)
        pm_score = min(100.0, max(0.0, pat_margin * 500))
        # EBITDA margin component (20%)
        em_score = min(100.0, max(0.0, ebitda_margin * 333))
        # Interest coverage component (20%)
        if ic == float("inf") or ic >= 5:
            ic_score = 100.0
        elif ic >= 3:
            ic_score = 75.0
        elif ic >= 1.5:
            ic_score = 50.0
        elif ic >= 1:
            ic_score = 25.0
        else:
            ic_score = 0.0
        return pm_score * 0.60 + em_score * 0.20 + ic_score * 0.20

    @staticmethod
    def _growth_score(rev_growth: float) -> float:
        if rev_growth >= 0.30:
            return 100.0
        elif rev_growth >= 0.20:
            return 85.0
        elif rev_growth >= 0.10:
            return 70.0
        elif rev_growth >= 0.05:
            return 55.0
        elif rev_growth >= 0:
            return 40.0
        elif rev_growth >= -0.10:
            return 25.0
        else:
            return 10.0
