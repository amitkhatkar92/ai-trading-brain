"""iios/investment/decision/committee/voting_engine.py
VotingEngine — orchestrates the full vote lifecycle for one session.
"""
from __future__ import annotations

from typing import List

from iios.investment.decision.committee.committee_member import CommitteeMember, MemberOpinion
from iios.investment.decision.committee.vote_registry import VoteRegistry
from iios.investment.decision.committee.weighted_voting import VoteSummary, WeightedVoting


class VotingEngine:
    """
    Collects final opinions from all voting members, registers their votes,
    and produces a VoteSummary.
    """

    def __init__(self) -> None:
        self._tally = WeightedVoting()

    def conduct_vote(
        self,
        members:  List[CommitteeMember],
        opinions: List[MemberOpinion],
    ) -> VoteSummary:
        registry   = VoteRegistry()
        member_map = {m.member_id: m for m in members}
        op_map     = {op.member_id: op for op in opinions}

        for member_id, member in member_map.items():
            if not member.role_policy.can_vote:
                continue
            opinion = op_map.get(member_id)
            if opinion is None:
                continue
            registry.cast_from_opinion(opinion, member.weight)

        all_votes = registry.all_votes()
        return self._tally.tally(all_votes)

    def tie_break(
        self,
        vote_summary: VoteSummary,
        members:       List[CommitteeMember],
        opinions:      List[MemberOpinion],
    ) -> VoteSummary:
        """
        If support_fraction == 0.50 exactly, the Chair breaks the tie.
        Returns an updated VoteSummary reflecting the chair's decision.
        """
        from iios.investment.decision.committee.committee_constants import VoteType
        from iios.investment.decision.committee.member_roles import MemberRole

        if abs(vote_summary.support_fraction - 0.50) > 0.001:
            return vote_summary  # no tie to break

        chair_members = [m for m in members if m.role == MemberRole.CHAIR]
        if not chair_members:
            return vote_summary

        chair = chair_members[0]
        op    = next((o for o in opinions if o.member_id == chair.member_id), None)
        if op is None:
            return vote_summary

        chair_vote = op.effective_vote
        # Re-create registry with chair's tiebreak weight doubled
        registry = VoteRegistry()
        member_map = {m.member_id: m for m in members}
        op_map     = {o.member_id: o for o in opinions}

        for mid, member in member_map.items():
            if not member.role_policy.can_vote:
                continue
            opinion = op_map.get(mid)
            if opinion is None:
                continue
            w = member.weight * 2.0 if mid == chair.member_id else member.weight
            registry.cast(mid, w, opinion.effective_vote, opinion.effective_confidence)

        return self._tally.tally(registry.all_votes())
