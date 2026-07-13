"""iios/investment/company/governance/management_quality.py
Management quality orchestrator — assembles ManagementQualityProfile.
"""
from __future__ import annotations

from typing import List, Optional

from iios.investment.company.governance.management_profile import (
    ManagementQualityProfile, LeadershipStability,
)
from iios.investment.company.governance.management_statistics import (
    clamp, score_leadership_stability, _label_score,
)
from iios.investment.company.governance.leadership_effectiveness import (
    score_execution_from_financials, score_strategic_consistency,
    score_long_term_orientation, score_management_credibility,
)
from iios.investment.company.governance.execution_quality import score_execution_quality
from iios.investment.company.governance.decision_quality import score_decision_quality


class ManagementQualityEngine:
    """Compute ManagementQualityProfile from available signals."""

    def compute(
        self,
        ceo_tenure_years:          Optional[float] = None,
        leadership_changes_3y:     int = 0,
        ceo_chairman_same:         bool = False,
        is_founder_led:            bool = False,
        earnings_stability_score:  Optional[float] = None,
        consistency_score:         Optional[float] = None,
        operational_quality_score: Optional[float] = None,
        avg_roic:                  Optional[float] = None,
        moat_score:                Optional[float] = None,
        growth_score:              Optional[float] = None,
        resilience_score:          Optional[float] = None,
        sustainability_score:      Optional[float] = None,
        earnings_quality_score:    Optional[float] = None,
        avg_ocf_to_ni:             Optional[float] = None,
        restatement_count:         int = 0,
        governance_incidents:      int = 0,
        eps_cagr:                  Optional[float] = None,
        debt_to_equity:            Optional[float] = None,
        payout_ratio:              Optional[float] = None,
    ) -> ManagementQualityProfile:
        explanation: List[str] = []

        # ── Leadership stability ───────────────────────────────────────────────
        stability_score = score_leadership_stability(
            ceo_tenure_years=ceo_tenure_years,
            leadership_changes_3y=leadership_changes_3y,
            ceo_chairman_same=ceo_chairman_same,
        )
        stability = self._classify_stability(stability_score, leadership_changes_3y)

        if ceo_tenure_years is not None:
            explanation.append(f"CEO tenure: {ceo_tenure_years:.1f}yr → stability {stability_score:.0f}/100")
        if leadership_changes_3y > 0:
            explanation.append(f"Leadership changes in 3y: {leadership_changes_3y}")

        # ── Execution quality ─────────────────────────────────────────────────
        exec_score = score_execution_quality(
            operational_quality_score=operational_quality_score,
            earnings_stability_score=earnings_stability_score,
            avg_roic=avg_roic,
            moat_score=moat_score,
            eps_cagr=eps_cagr,
        )
        if avg_roic is not None:
            explanation.append(f"Avg ROIC: {avg_roic:.1%} → execution quality {exec_score:.0f}/100")

        # ── Strategic consistency ─────────────────────────────────────────────
        strat_score = score_strategic_consistency(
            moat_score=moat_score,
            growth_score=growth_score,
            resilience_score=resilience_score,
        )

        # ── Long-term orientation ─────────────────────────────────────────────
        lt_score = score_long_term_orientation(
            avg_roic=avg_roic,
            earnings_stability=earnings_stability_score,
            sustainability_score=sustainability_score,
            is_founder_led=is_founder_led,
        )
        if is_founder_led:
            explanation.append("Founder-led: long-term orientation premium")

        # ── Management credibility ────────────────────────────────────────────
        cred_score = score_management_credibility(
            earnings_quality_score=earnings_quality_score,
            avg_ocf_to_ni=avg_ocf_to_ni,
            restatement_count=restatement_count,
            governance_incidents=governance_incidents,
        )
        if restatement_count > 0:
            explanation.append(f"Restatements: {restatement_count} → credibility penalty")
        if governance_incidents > 0:
            explanation.append(f"Governance incidents: {governance_incidents}")

        # ── Composite ─────────────────────────────────────────────────────────
        overall = clamp(
            stability_score * 0.20
            + exec_score    * 0.25
            + strat_score   * 0.20
            + lt_score      * 0.20
            + cred_score    * 0.15,
            0.0, 100.0,
        )
        label = _label_score(overall)
        explanation.append(f"Overall management quality: {overall:.1f}/100 ({label})")

        return ManagementQualityProfile(
            leadership_stability_score=round(stability_score, 1),
            execution_quality_score=round(exec_score, 1),
            strategic_consistency_score=round(strat_score, 1),
            long_term_orientation_score=round(lt_score, 1),
            management_credibility_score=round(cred_score, 1),
            overall_quality_score=round(overall, 1),
            stability=stability,
            quality_label=label,
            explanation=explanation,
        )

    @staticmethod
    def _classify_stability(
        score: float, changes_3y: int,
    ) -> LeadershipStability:
        if changes_3y >= 3:
            return LeadershipStability.UNSTABLE
        if changes_3y >= 2:
            return LeadershipStability.IN_TRANSITION
        if score >= 70:
            return LeadershipStability.STABLE
        if score >= 50:
            return LeadershipStability.MODERATELY_STABLE
        return LeadershipStability.UNSTABLE
