"""iios/investment/decision/committee/committee_quality.py
CommitteeQualityEvaluator — scores the overall quality of the committee process.
"""
from __future__ import annotations

from typing import List

from iios.investment.decision.committee.committee_context import CommitteeContext
from iios.investment.decision.committee.committee_member import MemberOpinion
from iios.investment.decision.committee.committee_round import RoundResult
from iios.investment.decision.committee.weighted_voting import VoteSummary


class CommitteeQualityEvaluator:
    """
    Produces a 0–100 quality score reflecting how thoroughly and rigorously
    the committee deliberated.
    """

    def evaluate(
        self,
        opinions:        List[MemberOpinion],
        vote_summary:    VoteSummary,
        rounds:          List[RoundResult],
        challenge_count: int,
        resolved_count:  int,
        ctx:             CommitteeContext,
    ) -> float:
        # 1. Participation quality — all members voted? (25 pts)
        total = max(1, vote_summary.total_votes)
        abstain_rate = vote_summary.abstain_count / total
        participation_score = max(0.0, 100.0 - abstain_rate * 100.0)

        # 2. Evidence coverage — how well evidence covers needed domains (20 pts)
        evidence_score = ctx.evidence.quality_score * ctx.evidence.coverage_fraction

        # 3. Consensus strength — clear outcome (20 pts)
        consensus_score = vote_summary.support_fraction * 100.0
        # penalise razor-thin margins
        if 0.48 < vote_summary.support_fraction < 0.52:
            consensus_score *= 0.70

        # 4. Debate quality — challenges raised and resolved (20 pts)
        if challenge_count == 0:
            debate_score = 50.0  # no challenges = no real debate
        else:
            resolution_rate = resolved_count / max(1, challenge_count)
            depth_bonus     = min(20.0, challenge_count * 2.0)
            debate_score    = resolution_rate * 80.0 + depth_bonus

        # 5. Decision readiness — explanation + reasoning quality (15 pts)
        readiness_score = (
            ctx.explanation.explainability_score * 0.50
            + ctx.confidence.overall_confidence  * 0.30
            + (100.0 - ctx.risk.overall_risk)    * 0.20
        )

        score = (
            participation_score * 0.25
            + evidence_score    * 0.20
            + consensus_score   * 0.20
            + debate_score      * 0.20
            + readiness_score   * 0.15
        )
        return round(min(100.0, max(0.0, score)), 4)
