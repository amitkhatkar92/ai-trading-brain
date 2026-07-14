"""iios/investment/decision/risk/risk_quality.py
RiskQualityEvaluator — evaluates the quality of the risk assessment itself.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from iios.investment.decision.risk.risk_confidence import RiskConfidenceResult
from iios.investment.decision.risk.risk_constants import RiskQualityGrade
from iios.investment.decision.risk.scenario_risk import ScenarioRiskResult


@dataclass(frozen=True)
class RiskQualityReport:
    scenarios_covered:    int
    risk_confidence:      float    # 0–100
    scenario_coverage:    float    # 0–100 (9 scenarios = 100%)
    completeness_score:   float    # 0–100
    quality_score:        float    # 0–100
    grade:                RiskQualityGrade

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenarios_covered": self.scenarios_covered,
            "risk_confidence":   round(self.risk_confidence, 2),
            "scenario_coverage": round(self.scenario_coverage, 2),
            "completeness_score": round(self.completeness_score, 2),
            "quality_score":     round(self.quality_score, 2),
            "grade":             self.grade.value,
        }


_TOTAL_SCENARIOS = 9   # matches DEFAULT_SCENARIOS count


class RiskQualityEvaluator:
    """Evaluates quality of the risk assessment (not the investment decision)."""

    def evaluate(
        self,
        risk_confidence: RiskConfidenceResult,
        scenario_result: ScenarioRiskResult,
    ) -> RiskQualityReport:
        covered  = scenario_result.scenario_count
        sc_cov   = min(100.0, covered / _TOTAL_SCENARIOS * 100.0)
        rc       = risk_confidence.risk_confidence

        completeness = (sc_cov * 0.50 + rc * 0.50)
        quality_score = min(100.0, max(0.0, completeness))
        grade         = RiskQualityGrade.from_quality(quality_score)

        return RiskQualityReport(
            scenarios_covered=covered,
            risk_confidence=round(rc, 4),
            scenario_coverage=round(sc_cov, 4),
            completeness_score=round(completeness, 4),
            quality_score=round(quality_score, 4),
            grade=grade,
        )
