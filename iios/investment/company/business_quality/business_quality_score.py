"""iios/investment/company/business_quality/business_quality_score.py
Scoring and labelling for BusinessQualitySnapshot.
"""
from __future__ import annotations

from iios.investment.company.business_quality.business_quality_snapshot import (
    BusinessQualityScore,
)
from iios.investment.company.business_quality.quality_statistics import clamp


class BusinessQualityScorer:
    """
    Combines dimension scores into BusinessQualityScore.

    Weights:
      Moat          25%
      Operational   25%
      Resilience    20%
      Competitive   15%
      Model         15%
    """

    def compute(
        self,
        moat_score:        float,
        operational_score: float,
        resilience_score:  float,
        competitive_score: float,
        model_score:       float,
        plugin_scores:     dict | None = None,
    ) -> BusinessQualityScore:
        bq = BusinessQualityScore(
            moat_score        = clamp(moat_score),
            operational_score = clamp(operational_score),
            resilience_score  = clamp(resilience_score),
            competitive_score = clamp(competitive_score),
            model_score       = clamp(model_score),
        )
        bq.recompute()

        # Apply plugin adjustments (blended at 10% total weight, max ±5 pts)
        if plugin_scores:
            if plugin_scores:
                values = list(plugin_scores.values())
                avg_plugin = sum(values) / len(values)
                # Treat 50 as neutral; adjust overall score by ±5 pts
                plugin_adjustment = clamp((avg_plugin - 50.0) / 10.0, -5, 5)
                bq.overall_score = clamp(bq.overall_score + plugin_adjustment)
                bq.label = self._label(bq.overall_score)

        # Explanatory notes
        bq.explanation = self._explain(bq)
        return bq

    @staticmethod
    def _label(score: float) -> str:
        if score >= 80:
            return "exceptional"
        if score >= 65:
            return "strong"
        if score >= 50:
            return "average"
        if score >= 35:
            return "weak"
        return "poor"

    @staticmethod
    def _explain(bq: BusinessQualityScore) -> list:
        notes = []
        if bq.moat_score >= 70:
            notes.append("Strong economic moat detected from financial signals")
        if bq.operational_score >= 70:
            notes.append("Operationally excellent — efficient capital deployment")
        if bq.resilience_score >= 70:
            notes.append("Resilient business model — low cyclicality and financial risk")
        if bq.moat_score < 35:
            notes.append("Limited moat signals — competitive advantage unclear")
        if bq.resilience_score < 35:
            notes.append("Resilience concern — high leverage or cyclicality")
        return notes
