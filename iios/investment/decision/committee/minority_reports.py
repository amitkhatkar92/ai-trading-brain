"""iios/investment/decision/committee/minority_reports.py
MinorityReport — captures dissenting specialist opinions.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from iios.investment.decision.committee.committee_constants import VoteType
from iios.investment.decision.committee.committee_member import MemberOpinion
from iios.investment.decision.committee.weighted_voting import VoteSummary


@dataclass(frozen=True)
class MinorityReport:
    """Formal record of a dissenting specialist's position."""
    member_id:        str
    specialist_type:  str
    dissenting_vote:  str          # VoteType.value
    majority_vote:    str          # what the majority voted
    confidence:       float
    domain_score:     float
    key_concerns:     Tuple[str, ...]
    formal_statement: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "member_id":        self.member_id,
            "specialist_type":  self.specialist_type,
            "dissenting_vote":  self.dissenting_vote,
            "majority_vote":    self.majority_vote,
            "confidence":       round(self.confidence, 2),
            "domain_score":     round(self.domain_score, 2),
            "key_concerns":     list(self.key_concerns),
            "formal_statement": self.formal_statement,
        }


class MinorityReportBuilder:
    """Extracts minority opinions from the final vote."""

    def build(
        self,
        opinions:     List[MemberOpinion],
        vote_summary: VoteSummary,
    ) -> List[MinorityReport]:
        if vote_summary.total_votes == 0:
            return []

        majority_vote = (
            VoteType.SUPPORT if vote_summary.support_fraction > 0.50 else VoteType.OPPOSE
        )

        reports: List[MinorityReport] = []
        for op in opinions:
            ev = op.effective_vote
            if ev == majority_vote:
                continue
            # This member dissents
            concerns = list(op.challenges)
            if not concerns:
                concerns = op.observations[:2]

            formal = (
                f"{op.specialist_type.value.upper()} dissents. "
                f"Vote: {ev.value.upper()} (majority: {majority_vote.value.upper()}). "
                f"Confidence: {op.effective_confidence:.1f}/100. "
                f"Primary concern: {concerns[0] if concerns else 'No specific concern recorded'}."
            )
            reports.append(MinorityReport(
                member_id        = op.member_id,
                specialist_type  = op.specialist_type.value,
                dissenting_vote  = ev.value,
                majority_vote    = majority_vote.value,
                confidence       = op.effective_confidence,
                domain_score     = op.domain_score,
                key_concerns     = tuple(concerns),
                formal_statement = formal,
            ))
        return reports
