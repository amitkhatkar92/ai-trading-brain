"""iios/investment/company/financials/cashflow_analyzer.py"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from iios.investment.company.company_constants import FinancialHealth


@dataclass
class CashflowAnalysis:
    operating_cf:       float          = 0.0
    investing_cf:       float          = 0.0
    financing_cf:       float          = 0.0
    free_cf:            float          = 0.0    # OCF + capex (capex usually negative)
    fcf_margin:         float          = 0.0    # FCF / revenue
    cf_quality:         float          = 0.0    # OCF / PAT (ideally > 1)
    cf_health:          FinancialHealth = FinancialHealth.UNKNOWN
    health_score:       float          = 50.0
    is_cash_generative: bool           = False
    metadata:           dict[str, Any]  = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "operating_cf":       self.operating_cf,
            "investing_cf":       self.investing_cf,
            "financing_cf":       self.financing_cf,
            "free_cf":            self.free_cf,
            "fcf_margin":         self.fcf_margin,
            "cf_quality":         self.cf_quality,
            "cf_health":          self.cf_health.value,
            "health_score":       self.health_score,
            "is_cash_generative": self.is_cash_generative,
            "metadata":           self.metadata,
        }


class CashflowAnalyzer:
    """
    Derives cash flow quality metrics.

    Expected keys:
      operating_cf, investing_cf, financing_cf, capex
    Optional context: revenue, pat
    """

    def analyze(
        self,
        data:    dict[str, Any],
        revenue: float = 0.0,
        pat:     float = 0.0,
    ) -> CashflowAnalysis:
        if not data:
            return CashflowAnalysis()

        ocf  = float(data.get("operating_cf",  0) or 0)
        icf  = float(data.get("investing_cf",  0) or 0)
        fcf_fin = float(data.get("financing_cf", 0) or 0)
        capex = float(data.get("capex", 0) or 0)

        # Capex may be stored as positive (outflow) or negative — normalise
        if capex > 0 and icf < 0:
            capex = -capex   # make capex negative

        free_cf    = ocf + capex   # both in same sign convention
        fcf_margin = free_cf / revenue if revenue > 0 else 0.0
        cf_quality = ocf / pat if pat > 0 else 0.0

        cf_health, health_score = self._classify(ocf, free_cf, cf_quality)

        return CashflowAnalysis(
            operating_cf       = ocf,
            investing_cf       = icf,
            financing_cf       = fcf_fin,
            free_cf            = round(free_cf, 2),
            fcf_margin         = round(fcf_margin, 6),
            cf_quality         = round(cf_quality, 4),
            cf_health          = cf_health,
            health_score       = round(health_score, 2),
            is_cash_generative = free_cf > 0,
            metadata           = {"n_items": len(data)},
        )

    @staticmethod
    def _classify(
        ocf:        float,
        free_cf:    float,
        cf_quality: float,
    ) -> tuple[FinancialHealth, float]:
        if free_cf > 0 and cf_quality >= 1.0:
            return FinancialHealth.VERY_STRONG, 90.0
        elif free_cf > 0 and cf_quality >= 0.75:
            return FinancialHealth.STRONG, 75.0
        elif free_cf > 0:
            return FinancialHealth.MODERATE, 60.0
        elif ocf > 0:
            return FinancialHealth.WEAK, 40.0
        else:
            return FinancialHealth.DISTRESSED, 15.0
