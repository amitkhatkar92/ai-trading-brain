"""iios/investment/company/opportunity/classification_engine.py
ClassificationEngine — orchestrates company classification from upstream snapshots.
"""
from __future__ import annotations

from typing import Any, Optional

from iios.investment.company.opportunity.company_classifier import (
    classify_company, extract_classification_inputs,
)
from iios.investment.company.opportunity.opportunity_category import ClassificationResult
from iios.investment.company.opportunity.opportunity_profile import OpportunityCategory
from iios.investment.company.opportunity.opportunity_statistics import safe_float


class ClassificationEngine:
    """
    Stateless engine that wraps the pure classification functions.
    One instance can be shared across threads (no mutable state).
    """

    def classify(
        self,
        overall_score:      float,
        bq_score:           float,
        val_score:          float,
        grw_score:          float,
        mgmt_score:         float,
        fin_score:          float,
        ear_score:          float,
        own_score:          float,
        earnings_snapshot:  Any = None,
        business_quality:   Any = None,
        valuation_snapshot: Any = None,
        growth_snapshot:    Any = None,
        dividend_yield:     Optional[float] = None,
        payout_ratio:       Optional[float] = None,
        has_alerts:         bool = False,
    ) -> ClassificationResult:
        """
        Classify a company based on pre-computed component scores and upstream snapshots.

        *overall_score* is the composite 0-100 opportunity score.
        Component scores (bq, val, grw, mgmt, fin, ear, own) are all 0-100.
        """
        # Extract additional classification signals from snapshots
        extra = extract_classification_inputs(
            earnings_snapshot=earnings_snapshot,
            business_quality=business_quality,
            valuation_snapshot=valuation_snapshot,
            growth_snapshot=growth_snapshot,
        )

        primary, secondary, rationale = classify_company(
            bq_score=bq_score,
            val_score=val_score,
            grw_score=grw_score,
            mgmt_score=mgmt_score,
            fin_score=fin_score,
            ear_score=ear_score,
            own_score=own_score,
            moat_score=extra.get("moat_score", 50.0),
            overall_score=overall_score,
            eps_cagr=extra.get("eps_cagr"),
            rev_cagr=extra.get("rev_cagr"),
            avg_roic=extra.get("avg_roic"),
            is_undervalued=extra.get("is_undervalued"),
            is_overvalued=extra.get("is_overvalued"),
            is_cyclical=extra.get("is_cyclical", False),
            dividend_yield=dividend_yield,
            payout_ratio=payout_ratio,
            fcf_margin=extra.get("fcf_margin"),
            has_alerts=has_alerts,
        )

        # Confidence: higher when more evidence aligns with category
        confidence = self._estimate_classification_confidence(
            primary=primary,
            overall_score=overall_score,
            bq_score=bq_score,
            fin_score=fin_score,
        )

        return ClassificationResult(
            primary=primary,
            secondary=secondary,
            confidence=confidence,
            rationale=rationale,
        )

    @staticmethod
    def _estimate_classification_confidence(
        primary: OpportunityCategory,
        overall_score: float,
        bq_score: float,
        fin_score: float,
    ) -> float:
        """Heuristic classification confidence — higher when signals are decisive."""
        base = overall_score / 100.0
        if primary in (OpportunityCategory.OBSERVATION_ONLY, OpportunityCategory.UNCLASSIFIED):
            return min(base, 0.40)
        if primary == OpportunityCategory.WATCHLIST:
            return min(base, 0.55)
        # Strong financial + quality alignment → higher confidence
        if bq_score >= 65 and fin_score >= 60:
            return min(base + 0.10, 0.90)
        return min(base + 0.05, 0.85)
