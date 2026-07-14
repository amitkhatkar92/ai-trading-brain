"""iios/investment/decision/committee/discussion_engine.py
DiscussionEngine — coordinates specialist reviews across deliberation rounds.
"""
from __future__ import annotations

from typing import List

from iios.investment.decision.committee.challenge_engine import ChallengeEngine
from iios.investment.decision.committee.committee_constants import RoundType
from iios.investment.decision.committee.committee_context import CommitteeContext
from iios.investment.decision.committee.committee_member import CommitteeMember, MemberOpinion
from iios.investment.decision.committee.committee_round import RoundResult


class DiscussionEngine:
    """
    Manages sequential discussion rounds:
      Round 1 — OPENING_REVIEW: every specialist produces an initial opinion
      Round 2 — CHALLENGE: challenges generated from round-1 opinions
      Round 3 — DELIBERATION: specialists revise positions after challenges
      Round 4 — FINAL_VOTE: locked-in opinions for voting
    """

    def __init__(self) -> None:
        self._challenge_engine = ChallengeEngine()

    def run_opening_review(
        self, members: List[CommitteeMember], ctx: CommitteeContext, round_num: int,
    ) -> RoundResult:
        import time
        t0 = time.perf_counter()
        opinions = [m.review(ctx) for m in members]
        return RoundResult(
            round_number    = round_num,
            round_type      = RoundType.OPENING_REVIEW,
            opinions        = tuple(opinions),
            challenge_count = 0,
            resolved_count  = 0,
            duration_ms     = (time.perf_counter() - t0) * 1000.0,
        )

    def run_challenge_round(
        self,
        initial_opinions: List[MemberOpinion],
        ctx:              CommitteeContext,
        round_num:        int,
    ) -> RoundResult:
        import time
        t0 = time.perf_counter()
        challenges = self._challenge_engine.generate(initial_opinions, ctx)
        resolved   = self._challenge_engine.count_resolved(challenges)
        # Opinions don't change in the challenge round — they respond in deliberation
        return RoundResult(
            round_number    = round_num,
            round_type      = RoundType.CHALLENGE,
            opinions        = tuple(initial_opinions),
            challenge_count = len(challenges),
            resolved_count  = resolved,
            duration_ms     = (time.perf_counter() - t0) * 1000.0,
        )

    def run_deliberation(
        self,
        members:     List[CommitteeMember],
        opinions:    List[MemberOpinion],
        challenges:  int,
        resolved:    int,
        ctx:         CommitteeContext,
        round_num:   int,
    ) -> RoundResult:
        import time
        t0 = time.perf_counter()
        # Build a member map for fast lookup
        member_map = {m.member_id: m for m in members}
        updated: List[MemberOpinion] = []
        for op in opinions:
            member = member_map.get(op.member_id)
            if member is not None:
                updated.append(member.deliberate(op, challenges, resolved))
            else:
                updated.append(op)
        return RoundResult(
            round_number    = round_num,
            round_type      = RoundType.DELIBERATION,
            opinions        = tuple(updated),
            challenge_count = challenges,
            resolved_count  = resolved,
            duration_ms     = (time.perf_counter() - t0) * 1000.0,
        )

    def run_final_vote(
        self, opinions: List[MemberOpinion], round_num: int,
    ) -> RoundResult:
        import time
        t0 = time.perf_counter()
        return RoundResult(
            round_number    = round_num,
            round_type      = RoundType.FINAL_VOTE,
            opinions        = tuple(opinions),
            challenge_count = 0,
            resolved_count  = 0,
            duration_ms     = (time.perf_counter() - t0) * 1000.0,
        )
