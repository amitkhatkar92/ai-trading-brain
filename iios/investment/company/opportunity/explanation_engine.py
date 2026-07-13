"""iios/investment/company/opportunity/explanation_engine.py
ExplanationEngine — assembles InvestmentThesis from evidence and reason generators.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, List, Optional

from iios.investment.company.opportunity.evidence_collector import collect_all_evidence
from iios.investment.company.opportunity.investment_thesis import InvestmentThesis
from iios.investment.company.opportunity.opportunity_profile import (
    ConfidenceLevel, OpportunityCategory, OpportunityLifecycle, OpportunityStrength,
)
from iios.investment.company.opportunity.opportunity_statistics import (
    confidence_to_level, safe_float,
)
from iios.investment.company.opportunity.reason_generator import (
    build_headline, build_narrative,
    generate_catalysts, generate_key_risks,
    generate_monitoring_points, generate_strengths, generate_weaknesses,
)


def _g(obj: Any, *attrs: str) -> Optional[float]:
    cur = obj
    for attr in attrs:
        if cur is None:
            return None
        cur = getattr(cur, attr, None)
    try:
        return float(cur) if cur is not None else None
    except (TypeError, ValueError):
        return None


class ExplanationEngine:
    """
    Stateless engine that composes an InvestmentThesis from all available signals.
    NOT a buy/sell/hold recommendation — describes WHY a company is interesting.
    """

    def generate(
        self,
        ticker:             str,
        category:           OpportunityCategory,
        lifecycle:          OpportunityLifecycle,
        strength:           OpportunityStrength,
        overall_score:      float,
        bq_score:           float,
        val_score:          float,
        grw_score:          float,
        mgmt_score:         float,
        fin_score:          float,
        own_score:          float,
        confidence:         float,
        alerts:             List[str],
        financial_snapshot: Any = None,
        earnings_snapshot:  Any = None,
        business_quality:   Any = None,
        valuation_snapshot: Any = None,
        growth_snapshot:    Any = None,
        management_snapshot: Any = None,
        ownership_snapshot:  Any = None,
    ) -> InvestmentThesis:
        """Generate a complete InvestmentThesis for the given ticker."""

        # ── Collect raw evidence from snapshots ───────────────────────────────
        evidence = collect_all_evidence(
            financial_snapshot=financial_snapshot,
            earnings_snapshot=earnings_snapshot,
            business_quality=business_quality,
            valuation_snapshot=valuation_snapshot,
            growth_snapshot=growth_snapshot,
            management_snapshot=management_snapshot,
            ownership_snapshot=ownership_snapshot,
        )

        # ── Pull auxiliary signals ────────────────────────────────────────────
        prof = getattr(earnings_snapshot, "profitability", None) if earnings_snapshot else None
        trend = getattr(earnings_snapshot, "trend", None) if earnings_snapshot else None
        risk_e = getattr(earnings_snapshot, "risk", None) if earnings_snapshot else None

        avg_roic   = _g(prof, "avg_roic") if prof else None
        eps_cagr   = _g(trend, "cagr_eps") if trend else None
        moat       = getattr(business_quality, "moat", None) if business_quality else None
        moat_score = safe_float(_g(moat, "moat_score"), 50.0)
        is_cyclical = bool(getattr(risk_e, "is_cyclical", False)) if risk_e else False

        # ── Generate components ───────────────────────────────────────────────
        strengths = generate_strengths(
            evidence=evidence, bq_score=bq_score, fin_score=fin_score,
            grw_score=grw_score, moat_score=moat_score,
            avg_roic=avg_roic, eps_cagr=eps_cagr,
        )
        weaknesses = generate_weaknesses(
            evidence=evidence, val_score=val_score, fin_score=fin_score,
            mgmt_score=mgmt_score, own_score=own_score,
        )
        key_risks = generate_key_risks(
            alerts=alerts, is_cyclical=is_cyclical,
            fin_score=fin_score, val_score=val_score, category=category,
        )
        catalysts = generate_catalysts(
            category=category, grw_score=grw_score, val_score=val_score,
            moat_score=moat_score, eps_cagr=eps_cagr,
        )
        monitoring = generate_monitoring_points(
            category=category, lifecycle=lifecycle,
            is_cyclical=is_cyclical, fin_score=fin_score,
        )
        headline  = build_headline(ticker, category, strength, bq_score, val_score)
        narrative = build_narrative(ticker, category, strengths, key_risks, lifecycle, overall_score)

        conf_level = confidence_to_level(confidence)
        conf_explanation = self._explain_confidence(confidence, conf_level, evidence)

        # ── Partition evidence ────────────────────────────────────────────────
        positive_ev = [e for e in evidence if e.signal == "positive"]
        risk_ev     = [e for e in evidence if e.signal == "negative"]

        return InvestmentThesis(
            ticker=ticker,
            category=category,
            lifecycle=lifecycle,
            headline=headline,
            narrative=narrative,
            strengths=strengths,
            weaknesses=weaknesses,
            key_risks=key_risks,
            key_catalysts=catalysts,
            monitoring_points=monitoring,
            supporting_evidence=positive_ev,
            risk_evidence=risk_ev,
            confidence_explanation=conf_explanation,
            confidence_level=conf_level,
            generated_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def _explain_confidence(
        confidence: float,
        level: ConfidenceLevel,
        evidence: List,
    ) -> str:
        n_pos  = sum(1 for e in evidence if e.signal == "positive")
        n_neg  = sum(1 for e in evidence if e.signal == "negative")
        n_total = len(evidence)
        if level == ConfidenceLevel.VERY_HIGH:
            return (
                f"Very high confidence ({confidence:.0%}): {n_total} evidence points "
                f"with {n_pos} positive and {n_neg} risk signals from multiple sources."
            )
        if level == ConfidenceLevel.HIGH:
            return (
                f"High confidence ({confidence:.0%}): sufficient data from primary "
                f"intelligence sources with {n_pos} supporting signals."
            )
        if level == ConfidenceLevel.MODERATE:
            return (
                f"Moderate confidence ({confidence:.0%}): core intelligence available "
                f"but some supplementary sources are missing."
            )
        if level == ConfidenceLevel.LOW:
            return (
                f"Low confidence ({confidence:.0%}): limited data coverage; "
                f"conclusions should be treated with caution."
            )
        return (
            f"Very low confidence ({confidence:.0%}): insufficient intelligence "
            f"coverage for reliable evaluation."
        )
