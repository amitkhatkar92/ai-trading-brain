"""iios/investment/company/ownership/ownership_risk.py
Ownership risk aggregation engine.
"""
from __future__ import annotations

from typing import Any, Optional

from iios.investment.company.ownership.ownership_profile import (
    OwnershipRiskProfile, OwnershipRiskLabel,
)
from iios.investment.company.ownership.shareholder_registry import ShareholderRegistry
from iios.investment.company.ownership.ownership_statistics import (
    clamp, score_pledge_risk, pct_to_100,
)
from iios.investment.company.ownership.ownership_concentration import score_concentration_risk
from iios.investment.company.ownership.control_risk import (
    score_control_risk,
    score_hostile_takeover_exposure,
)
from iios.investment.company.ownership.dilution_analysis import score_total_dilution_risk
from iios.investment.company.ownership.ownership_alerts import generate_ownership_alerts


def _classify_risk(score: float) -> OwnershipRiskLabel:
    if score >= 75:
        return OwnershipRiskLabel.CRITICAL
    if score >= 60:
        return OwnershipRiskLabel.HIGH
    if score >= 45:
        return OwnershipRiskLabel.ELEVATED
    if score >= 25:
        return OwnershipRiskLabel.MODERATE
    return OwnershipRiskLabel.LOW


class OwnershipRiskEngine:
    """Computes comprehensive ownership risk profile."""

    def compute(
        self,
        registry:          ShareholderRegistry,
        insider_activity:  Any = None,   # InsiderActivityProfile
        management_snapshot: Any = None, # Optional[ManagementSnapshot]
        is_family_controlled: bool = False,
        ceo_chairman_same:    bool = False,
        board_independence_ratio: Optional[float] = None,
        esop_outstanding_pct: Optional[float] = None,
    ) -> OwnershipRiskProfile:

        reg = registry
        profile = OwnershipRiskProfile()

        # ── Pledge risk ───────────────────────────────────────────────────────
        profile.pledge_risk_score = score_pledge_risk(reg.promoter_pledge_pct)

        # ── Concentration risk ─────────────────────────────────────────────────
        profile.concentration_risk_score = score_concentration_risk(
            reg.top10_pct, reg.promoter_pct, reg.computed_free_float
        )

        # ── Dilution risk ──────────────────────────────────────────────────────
        profile.dilution_risk_score = score_total_dilution_risk(
            esop_outstanding_pct=esop_outstanding_pct,
            promoter_pct_change=reg.promoter_change_1y,
            free_float_pct=reg.computed_free_float,
        )

        # ── Control risk ───────────────────────────────────────────────────────
        profile.control_risk_score = score_control_risk(
            promoter_pct=reg.promoter_pct,
            is_family_controlled=is_family_controlled,
            ceo_chairman_same=ceo_chairman_same,
            govt_holding_pct=reg.government_pct,
        )

        # ── Liquidity / free-float risk ────────────────────────────────────────
        ff = reg.computed_free_float
        if ff is not None:
            ffp = pct_to_100(ff) if ff <= 1.0 else ff
            if ffp is not None:
                if ffp < 10:
                    profile.liquidity_risk_score = 80.0
                elif ffp < 20:
                    profile.liquidity_risk_score = 60.0
                elif ffp < 30:
                    profile.liquidity_risk_score = 35.0
                else:
                    profile.liquidity_risk_score = 15.0
        else:
            profile.liquidity_risk_score = 25.0

        # ── Cross-engine risk adjustments ──────────────────────────────────────
        if management_snapshot is not None:
            gov_risk = getattr(management_snapshot, "governance_risk", None)
            gov_risk_score = getattr(gov_risk, "overall_risk_score", None)
            if gov_risk_score is not None and gov_risk_score >= 65:
                profile.control_risk_score = clamp(
                    profile.control_risk_score + 10.0
                )

        # ── Overall risk ───────────────────────────────────────────────────────
        profile.overall_risk_score = clamp(
            profile.pledge_risk_score        * 0.30
            + profile.concentration_risk_score * 0.20
            + profile.control_risk_score       * 0.20
            + profile.dilution_risk_score      * 0.15
            + profile.liquidity_risk_score     * 0.15
        )

        profile.risk_label = _classify_risk(profile.overall_risk_score)

        # ── Alerts ─────────────────────────────────────────────────────────────
        insider_label = None
        if insider_activity is not None:
            lbl = getattr(insider_activity, "insider_activity_label", None)
            if lbl is not None:
                insider_label = lbl.value

        profile.alerts = generate_ownership_alerts(
            promoter_pledge_pct=reg.promoter_pledge_pct,
            promoter_change_3m=reg.promoter_change_3m,
            promoter_change_1y=reg.promoter_change_1y,
            control_risk_score=profile.control_risk_score,
            concentration_risk_score=profile.concentration_risk_score,
            dilution_risk_score=profile.dilution_risk_score,
            pledge_risk_score=profile.pledge_risk_score,
            free_float_pct=reg.computed_free_float,
            esop_outstanding_pct=esop_outstanding_pct,
            insider_activity_label=insider_label,
            institutional_pct=reg.institutional_pct,
            promoter_pct=reg.promoter_pct,
        )

        return profile
