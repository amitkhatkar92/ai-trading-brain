"""iios/investment/decision/risk/company_risk.py
CompanyRiskEvaluator — derives company-specific risk from EvidenceSnapshot.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Any, Dict, List

from iios.investment.decision.evidence.evidence_constants import EvidenceSourceType
from iios.investment.decision.evidence.evidence_snapshot import EvidenceSnapshot


@dataclass(frozen=True)
class CompanyRiskResult:
    item_count:        int
    avg_confidence:    float   # 0–100
    coverage_risk:     float   # 0–100 (missing company evidence)
    freshness_risk:    float   # 0–100
    fundamental_risk:  float   # 0–100 from pe_ratio, roe, etc.
    company_risk:      float   # 0–100

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_count":       self.item_count,
            "avg_confidence":   round(self.avg_confidence, 2),
            "coverage_risk":    round(self.coverage_risk, 2),
            "freshness_risk":   round(self.freshness_risk, 2),
            "fundamental_risk": round(self.fundamental_risk, 2),
            "company_risk":     round(self.company_risk, 2),
        }


# Warning thresholds for company fundamentals
_PE_RATIO_HIGH  = 40.0    # high P/E = risk
_ROE_LOW        = 10.0    # low ROE = risk
_REVENUE_GROWTH_LOW = 0.0  # negative = risk


class CompanyRiskEvaluator:
    """Derives company dimension risk from EvidenceSnapshot."""

    def evaluate(self, snapshot: EvidenceSnapshot) -> CompanyRiskResult:
        items = [i for i in snapshot.items if i.source_type == EvidenceSourceType.COMPANY]

        if not items:
            return CompanyRiskResult(
                item_count=0, avg_confidence=0.0,
                coverage_risk=80.0, freshness_risk=60.0,
                fundamental_risk=50.0, company_risk=65.0,
            )

        avg_conf      = statistics.mean(i.confidence for i in items)
        avg_freshness = statistics.mean(i.freshness_score for i in items)
        coverage_risk = max(0.0, 60.0 - len(items) * 5.0)   # more items = lower gap risk
        freshness_risk = (1.0 - avg_freshness) * 100.0

        # Fundamental risk from known keys
        fundamental_risk = 0.0
        for item in items:
            if item.key == "pe_ratio":
                try:
                    if float(item.value) > _PE_RATIO_HIGH:
                        fundamental_risk += 15.0
                except (TypeError, ValueError):
                    pass
            elif item.key == "roe":
                try:
                    if float(item.value) < _ROE_LOW:
                        fundamental_risk += 10.0
                except (TypeError, ValueError):
                    pass
            elif item.key == "revenue_growth":
                try:
                    if float(item.value) < _REVENUE_GROWTH_LOW:
                        fundamental_risk += 10.0
                except (TypeError, ValueError):
                    pass
        fundamental_risk = min(100.0, fundamental_risk)

        company_risk = (
            coverage_risk    * 0.30
            + freshness_risk * 0.30
            + fundamental_risk * 0.20
            + max(0.0, 100.0 - avg_conf) * 0.20
        )
        company_risk = max(0.0, min(100.0, company_risk))

        return CompanyRiskResult(
            item_count=len(items),
            avg_confidence=round(avg_conf, 4),
            coverage_risk=round(coverage_risk, 4),
            freshness_risk=round(freshness_risk, 4),
            fundamental_risk=round(fundamental_risk, 4),
            company_risk=round(company_risk, 4),
        )
