"""iios/investment/decision/committee/committee_confidence.py
CommitteeConfidenceCalculator — produces a committee-level confidence score.
"""
from __future__ import annotations

from iios.investment.decision.committee.committee_context import CommitteeContext
from iios.investment.decision.committee.committee_member import MemberOpinion
from iios.investment.decision.committee.weighted_voting import VoteSummary
from typing import List


class CommitteeConfidenceCalculator:
    """
    Aggregates multiple confidence signals into one committee confidence score
    on a 0–100 scale (higher = more confident the package is decision-ready).
    """

    def calculate(
        self,
        vote_summary:    VoteSummary,
        opinions:        List[MemberOpinion],
        ctx:             CommitteeContext,
        challenge_count: int,
        resolved_count:  int,
    ) -> float:
        # 1. Vote consensus strength (35%)
        consensus_score = vote_summary.support_fraction * 100.0

        # 2. Average specialist confidence of support voters (25%)
        specialist_conf = vote_summary.avg_support_confidence

        # 3. Upstream confidence score (20%)
        upstream_conf = ctx.confidence.overall_confidence

        # 4. Evidence quality (10%)
        ev_quality = ctx.evidence.quality_score

        # 5. Challenge resolution rate (10%)
        total_ch = max(1, challenge_count)
        ch_score = min(100.0, resolved_count / total_ch * 100.0)

        score = (
            consensus_score  * 0.35
            + specialist_conf  * 0.25
            + upstream_conf    * 0.20
            + ev_quality       * 0.10
            + ch_score         * 0.10
        )
        return round(min(100.0, max(0.0, score)), 4)
