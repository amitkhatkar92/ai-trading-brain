"""iios/investment/company/governance/governance_risk.py
Governance risk orchestrator — assembles GovernanceRiskProfile.
"""
from __future__ import annotations

from typing import List, Optional

from iios.investment.company.governance.management_profile import (
    GovernanceRiskProfile, RiskLabel,
)
from iios.investment.company.governance.management_statistics import clamp
from iios.investment.company.governance.governance_events import GovernanceEventLog
from iios.investment.company.governance.key_person_risk import score_key_person_risk
from iios.investment.company.governance.succession_analysis import score_succession_quality
from iios.investment.company.governance.governance_alerts import generate_alerts


def _risk_label(score: float) -> RiskLabel:
    if score <= 20:
        return RiskLabel.LOW
    if score <= 40:
        return RiskLabel.MODERATE
    if score <= 60:
        return RiskLabel.ELEVATED
    if score <= 80:
        return RiskLabel.HIGH
    return RiskLabel.CRITICAL


class GovernanceRiskEngine:
    """Compute GovernanceRiskProfile from available governance signals."""

    def compute(
        self,
        ceo_tenure_years:     Optional[float] = None,
        cfo_tenure_years:     Optional[float] = None,
        is_founder_led:       bool = False,
        executive_team_size:  int = 0,
        leadership_changes_3y: int = 0,
        has_nomination_committee: bool = False,
        avg_director_tenure:  Optional[float] = None,
        independence_ratio:   Optional[float] = None,
        ceo_chairman_same:    bool = False,
        is_family_controlled: bool = False,
        event_log:            Optional[GovernanceEventLog] = None,
        regulatory_actions:   Optional[List[str]] = None,
        restatement_count:    int = 0,
    ) -> GovernanceRiskProfile:
        explanation: List[str] = []
        event_log = event_log or GovernanceEventLog()
        risk_factors: List[str] = []

        # ── Key person risk ────────────────────────────────────────────────────
        kp_risk = score_key_person_risk(
            ceo_tenure_years=ceo_tenure_years,
            is_founder_led=is_founder_led,
            cfo_tenure_years=cfo_tenure_years,
            executive_team_size=executive_team_size,
            leadership_changes_3y=leadership_changes_3y,
        )
        if kp_risk >= 60:
            risk_factors.append("key_person_concentration")

        # ── Succession quality ────────────────────────────────────────────────
        succ_quality = score_succession_quality(
            ceo_tenure_years=ceo_tenure_years,
            avg_director_tenure=avg_director_tenure,
            has_nomination_committee=has_nomination_committee,
            is_founder_led=is_founder_led,
            executive_team_size=executive_team_size,
            leadership_changes_3y=leadership_changes_3y,
        )
        if succ_quality < 40:
            risk_factors.append("weak_succession_planning")

        # ── Board risk ─────────────────────────────────────────────────────────
        board_risk = 30.0
        if independence_ratio is not None and independence_ratio < 0.33:
            board_risk += 25.0
            risk_factors.append("low_board_independence")
        if ceo_chairman_same:
            board_risk += 15.0
            risk_factors.append("ceo_chairman_duality")
        if is_family_controlled:
            board_risk += 10.0
            risk_factors.append("family_controlled")
        board_risk = clamp(board_risk, 0, 100)

        # ── Regulatory risk ────────────────────────────────────────────────────
        reg_risk = 10.0
        reg_risk += event_log.high_severity_count   * 20.0
        reg_risk += event_log.medium_severity_count * 8.0
        reg_risk += restatement_count * 15.0
        if regulatory_actions:
            reg_risk += len(regulatory_actions) * 10.0
            risk_factors.append("regulatory_actions_on_record")
        reg_risk = clamp(reg_risk, 0, 100)
        if reg_risk >= 50:
            risk_factors.append("elevated_regulatory_risk")

        # ── Reputation risk ────────────────────────────────────────────────────
        rep_risk = clamp(event_log.reputation_penalty, 0, 100)
        if rep_risk >= 30:
            risk_factors.append("governance_incidents_on_record")

        # ── Composite ─────────────────────────────────────────────────────────
        # Succession quality inversely reduces overall risk
        succ_risk = 100.0 - succ_quality
        overall = clamp(
            kp_risk     * 0.25
            + succ_risk  * 0.20
            + board_risk * 0.25
            + reg_risk   * 0.20
            + rep_risk   * 0.10,
            0.0, 100.0,
        )
        label = _risk_label(overall)

        # ── Alerts ────────────────────────────────────────────────────────────
        alerts = generate_alerts(
            event_log=event_log,
            ceo_chairman_same=ceo_chairman_same,
            is_family_controlled=is_family_controlled,
            independence_ratio=independence_ratio,
            restatement_count=restatement_count,
            key_person_risk=kp_risk,
            regulatory_actions=regulatory_actions,
        )

        explanation.append(f"Key person risk: {kp_risk:.0f}/100")
        explanation.append(f"Succession quality: {succ_quality:.0f}/100")
        explanation.append(f"Board risk: {board_risk:.0f}/100")
        explanation.append(f"Regulatory risk: {reg_risk:.0f}/100")
        explanation.append(f"Overall governance risk: {overall:.0f}/100 ({label.value})")

        return GovernanceRiskProfile(
            key_person_risk_score=round(kp_risk, 1),
            succession_quality_score=round(succ_quality, 1),
            board_risk_score=round(board_risk, 1),
            regulatory_risk_score=round(reg_risk, 1),
            reputation_risk_score=round(rep_risk, 1),
            overall_risk_score=round(overall, 1),
            risk_label=label,
            risk_factors=risk_factors,
            alerts=alerts,
            explanation=explanation,
        )
