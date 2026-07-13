"""iios/investment/company/governance/transparency_engine.py
Transparency and ethics analysis orchestrator.
"""
from __future__ import annotations

from typing import List, Optional

from iios.investment.company.governance.management_profile import (
    TransparencyProfile, TransparencyLabel,
)
from iios.investment.company.governance.management_statistics import clamp
from iios.investment.company.governance.governance_events import GovernanceEventLog
from iios.investment.company.governance.disclosure_quality import (
    score_disclosure_quality, score_reporting_transparency,
)
from iios.investment.company.governance.compliance_tracker import score_compliance
from iios.investment.company.governance.ethics_profile import score_accounting_integrity


def _label_transparency(score: float) -> TransparencyLabel:
    if score >= 85:
        return TransparencyLabel.EXEMPLARY
    if score >= 70:
        return TransparencyLabel.TRANSPARENT
    if score >= 50:
        return TransparencyLabel.ADEQUATE
    if score >= 30:
        return TransparencyLabel.OPAQUE
    return TransparencyLabel.CONCERNING


class TransparencyEngine:
    """Produce TransparencyProfile from earnings quality and governance event data."""

    def compute(
        self,
        earnings_quality_score: Optional[float] = None,   # 0-100
        consistency_score:      Optional[float] = None,   # 0-100
        avg_accruals_ratio:     Optional[float] = None,
        avg_ocf_to_ni:          Optional[float] = None,
        restatement_count:      int = 0,
        event_log:              Optional[GovernanceEventLog] = None,
        regulatory_actions:     Optional[List[str]] = None,
        governance_standard:    str = "generic",
    ) -> TransparencyProfile:
        explanation: List[str] = []
        event_log = event_log or GovernanceEventLog()

        # ── Disclosure quality ─────────────────────────────────────────────────
        disc_score = score_disclosure_quality(
            earnings_quality_score=earnings_quality_score,
            consistency_score=consistency_score,
            restatement_count=restatement_count,
        )
        if restatement_count > 0:
            explanation.append(f"Financial restatements: {restatement_count} → penalty")

        # ── Reporting transparency ─────────────────────────────────────────────
        report_score = score_reporting_transparency(
            avg_accruals_ratio=avg_accruals_ratio,
            avg_ocf_to_ni=avg_ocf_to_ni,
        )
        if avg_accruals_ratio is not None:
            explanation.append(f"Avg accruals ratio: {avg_accruals_ratio:.3f}")
        if avg_ocf_to_ni is not None:
            explanation.append(f"Avg OCF/NI: {avg_ocf_to_ni:.2f}")

        # ── Compliance ─────────────────────────────────────────────────────────
        comp_score = score_compliance(
            event_log=event_log,
            regulatory_actions=regulatory_actions,
            governance_standard=governance_standard,
        )

        # ── Accounting integrity ───────────────────────────────────────────────
        integrity_score = score_accounting_integrity(
            avg_accruals_ratio=avg_accruals_ratio,
            avg_ocf_to_ni=avg_ocf_to_ni,
            restatement_count=restatement_count,
            event_log=event_log,
        )

        # ── Composite ─────────────────────────────────────────────────────────
        overall = clamp(
            disc_score      * 0.30
            + report_score  * 0.30
            + comp_score    * 0.20
            + integrity_score * 0.20,
            0.0, 100.0,
        )
        label = _label_transparency(overall)
        explanation.append(f"Transparency: {overall:.1f}/100 ({label.value})")

        has_incidents = event_log.has_critical_events or restatement_count > 0

        return TransparencyProfile(
            disclosure_quality_score=round(disc_score, 1),
            reporting_transparency_score=round(report_score, 1),
            compliance_score=round(comp_score, 1),
            accounting_integrity_score=round(integrity_score, 1),
            overall_transparency_score=round(overall, 1),
            transparency_label=label,
            has_governance_incidents=has_incidents,
            incident_count=event_log.total_count,
            restatement_count=restatement_count,
            explanation=explanation,
        )
