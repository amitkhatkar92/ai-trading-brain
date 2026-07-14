"""iios/investment/decision/committee/executive_summary.py
ExecutiveSummaryBuilder — generates the committee's executive summary text.
"""
from __future__ import annotations

from iios.investment.decision.committee.committee_constants import (
    CommitteePosition,
    ConsensusLevel,
)
from iios.investment.decision.committee.committee_context import CommitteeContext
from iios.investment.decision.committee.weighted_voting import VoteSummary


class ExecutiveSummaryBuilder:
    """Generates a plain-English executive summary of the committee's deliberation."""

    def build(
        self,
        position:     CommitteePosition,
        vote_summary: VoteSummary,
        ctx:          CommitteeContext,
        minority_count: int,
        challenge_count: int,
    ) -> str:
        subject = f"{ctx.subject_id} ({ctx.subject_type})"
        cons    = vote_summary.consensus_level.value.upper().replace("_", " ")
        frac    = vote_summary.support_fraction * 100.0
        conf    = ctx.confidence.overall_confidence
        risk    = ctx.risk.overall_risk
        ev_cnt  = ctx.evidence.item_count
        expl    = ctx.explanation.explainability_score

        pos_line = {
            CommitteePosition.PROCEED_TO_RECOMMENDATION:
                "The committee has approved this decision package for forwarding to the Recommendation Engine.",
            CommitteePosition.DEFER_PENDING_EVIDENCE:
                "The committee has deferred this decision pending additional evidence.",
            CommitteePosition.INSUFFICIENT_EVIDENCE:
                "The committee found insufficient evidence to deliberate and has suspended review.",
            CommitteePosition.BLOCKED:
                "The committee has blocked this decision due to risk or compliance concerns.",
        }[position]

        summary = (
            f"COMMITTEE REVIEW: {subject}\n\n"
            f"{pos_line}\n\n"
            f"Committee Position : {position.value.upper().replace('_', ' ')}\n"
            f"Consensus          : {cons} ({frac:.1f}% weighted support)\n"
            f"Vote               : {vote_summary.support_count} SUPPORT | "
            f"{vote_summary.oppose_count} OPPOSE | "
            f"{vote_summary.abstain_count} ABSTAIN\n"
            f"Total Members      : {vote_summary.total_votes}\n"
            f"Minority Opinions  : {minority_count}\n"
            f"Challenges Raised  : {challenge_count}\n\n"
            f"Evidence: {ev_cnt} items | Quality: {ctx.evidence.quality_score:.1f}/100 | "
            f"Coverage: {ctx.evidence.coverage_fraction:.0%}\n"
            f"Confidence : {conf:.1f}/100 ({ctx.confidence.confidence_level.value})\n"
            f"Risk       : {risk:.1f}/100 ({ctx.risk.risk_level.value})\n"
            f"Explainability: {expl:.1f}/100 ({ctx.explanation.explainability_grade.value})\n"
        )
        return summary
