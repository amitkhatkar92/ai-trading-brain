"""iios/investment/company/ownership/shareholder_analysis.py
Shareholder composition analysis engine.
"""
from __future__ import annotations

from typing import Any, Optional

from iios.investment.company.ownership.ownership_profile import (
    OwnershipStructureProfile,
    InstitutionalParticipationLabel,
)
from iios.investment.company.ownership.shareholder_registry import ShareholderRegistry
from iios.investment.company.ownership.ownership_statistics import (
    clamp, safe_mean,
    score_promoter_holding,
    score_institutional_holding,
    score_free_float,
)
from iios.investment.company.ownership.ownership_concentration import (
    classify_concentration_level,
    score_herfindahl_proxy,
    score_control_concentration,
)
from iios.investment.company.ownership.ownership_stability import (
    classify_promoter_stability,
    score_ownership_stability,
    score_promoter_conviction,
)
from iios.investment.company.ownership.ownership_distribution import score_distribution_quality


class ShareholderAnalysisEngine:
    """Evaluates the complete shareholder composition for a ticker."""

    def compute(
        self,
        registry:           ShareholderRegistry,
        management_snapshot: Any = None,   # Optional[ManagementSnapshot]
    ) -> OwnershipStructureProfile:

        reg = registry
        profile = OwnershipStructureProfile()
        expl: list[str] = []

        # ── Copy raw fields ───────────────────────────────────────────────────
        profile.promoter_holding_pct      = reg.promoter_pct
        profile.institutional_holding_pct = reg.institutional_pct
        profile.retail_holding_pct        = reg.retail_pct
        profile.government_holding_pct    = reg.government_pct
        profile.foreign_holding_pct       = reg.foreign_pct
        profile.employee_holding_pct      = reg.employee_pct
        profile.treasury_pct              = reg.treasury_pct
        profile.free_float_pct            = reg.computed_free_float
        profile.fii_holding_pct           = reg.fii_pct
        profile.dii_holding_pct           = reg.dii_pct
        profile.mutual_fund_holding_pct   = reg.mutual_fund_pct
        profile.promoter_pledge_pct       = reg.promoter_pledge_pct
        profile.top10_holder_pct          = reg.top10_pct

        # ── Concentration ─────────────────────────────────────────────────────
        profile.concentration_level = classify_concentration_level(reg.top10_pct)

        # ── Promoter stability ────────────────────────────────────────────────
        profile.promoter_stability = classify_promoter_stability(
            promoter_pct=reg.promoter_pct,
            change_3m=reg.promoter_change_3m,
            change_1y=reg.promoter_change_1y,
            pledge_pct=reg.promoter_pledge_pct,
        )

        # ── Institutional participation label ─────────────────────────────────
        profile.institutional_participation = _classify_institutional_participation(
            reg.institutional_pct
        )

        # ── Promoter stability score (0-100) ──────────────────────────────────
        conviction_score  = score_promoter_conviction(
            reg.promoter_pct, reg.promoter_pledge_pct, reg.promoter_change_1y
        )
        stability_score   = score_ownership_stability(
            reg.promoter_pct, reg.promoter_change_3m, reg.promoter_change_1y,
            reg.inst_change_3m, reg.promoter_pledge_pct,
        )
        profile.promoter_stability_score = clamp((conviction_score + stability_score) / 2)

        # ── Institutional quality score ────────────────────────────────────────
        profile.institutional_quality_score = clamp(
            score_institutional_holding(reg.institutional_pct) * 0.55
            + (score_institutional_holding(reg.fii_pct) * 0.25 if reg.fii_pct else 0)
            + (score_institutional_holding(reg.dii_pct) * 0.20 if reg.dii_pct else 0)
        )

        # Governance crosscheck: if management_snapshot has good governance → boost
        if management_snapshot is not None:
            gov = getattr(management_snapshot, "governance", None)
            gov_score = getattr(gov, "overall_governance_score", None)
            if gov_score is not None and gov_score >= 65:
                profile.institutional_quality_score = clamp(
                    profile.institutional_quality_score + 5.0
                )
                expl.append("Institutional quality boosted by strong governance score.")

        # ── Free float score ───────────────────────────────────────────────────
        profile.free_float_score = score_free_float(profile.free_float_pct)

        # ── Distribution quality ───────────────────────────────────────────────
        profile.distribution_quality_score = score_distribution_quality(
            reg.promoter_pct, reg.institutional_pct, reg.retail_pct,
            reg.government_pct, reg.fii_pct, reg.dii_pct, profile.free_float_pct,
        )

        # ── Overall structure score ────────────────────────────────────────────
        profile.overall_structure_score = clamp(
            profile.promoter_stability_score   * 0.35
            + profile.institutional_quality_score * 0.30
            + profile.free_float_score            * 0.15
            + profile.distribution_quality_score  * 0.20
        )

        profile.explanation = expl
        return profile


def _classify_institutional_participation(pct: Optional[float]) -> InstitutionalParticipationLabel:
    from iios.investment.company.ownership.ownership_statistics import pct_to_100
    if pct is None:
        return InstitutionalParticipationLabel.UNKNOWN
    p = pct_to_100(pct) or 0.0
    if p >= 40:
        return InstitutionalParticipationLabel.EXCEPTIONAL
    if p >= 25:
        return InstitutionalParticipationLabel.HIGH
    if p >= 15:
        return InstitutionalParticipationLabel.MODERATE
    if p >= 5:
        return InstitutionalParticipationLabel.LOW
    return InstitutionalParticipationLabel.NEGLIGIBLE
