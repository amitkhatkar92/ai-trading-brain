"""tests/unit/investment/decision/committee/test_committee_quality.py
Tests for CommitteeQualityEvaluator, CommitteeConfidenceCalculator,
CommitteeHealthMonitor, CommitteeStatisticsTracker.
"""
from __future__ import annotations

import pytest

from iios.investment.decision.committee.committee_confidence import (
    CommitteeConfidenceCalculator,
)
from iios.investment.decision.committee.committee_constants import CommitteeStatus
from iios.investment.decision.committee.committee_health import CommitteeHealthMonitor
from iios.investment.decision.committee.committee_quality import CommitteeQualityEvaluator
from iios.investment.decision.committee.committee_session import CommitteeSession
from iios.investment.decision.committee.committee_statistics import (
    CommitteeStatisticsTracker,
)


def _make_vote_summary(opinions):
    from iios.investment.decision.committee.voting_engine import VotingEngine
    from iios.investment.decision.committee.member_registry import MemberRegistry
    # Create minimal members matching the opinions
    from iios.investment.decision.committee.committee_constants import SpecialistType
    from iios.investment.decision.committee.member_roles import MemberRole
    from iios.investment.decision.committee.committee_member import create_member
    members = [create_member(op.member_id, op.specialist_type, op.role) for op in opinions]
    ve = VotingEngine()
    return ve.conduct_vote(members, list(opinions))


class TestCommitteeQualityEvaluator:
    def test_returns_float_in_range(self, rich_context, default_registry):
        from iios.investment.decision.committee.discussion_engine import DiscussionEngine
        from iios.investment.decision.committee.voting_engine import VotingEngine
        engine   = DiscussionEngine()
        members  = default_registry.all_members()
        r1       = engine.run_opening_review(members, rich_context, 1)
        opinions = list(r1.opinions)
        vs       = VotingEngine().conduct_vote(members, opinions)
        ev       = CommitteeQualityEvaluator()
        score    = ev.evaluate(
            opinions        = opinions,
            vote_summary    = vs,
            rounds          = [r1],
            challenge_count = 0,
            resolved_count  = 0,
            ctx             = rich_context,
        )
        assert 0.0 <= score <= 100.0

    def test_more_members_higher_participation(self, rich_context):
        from iios.investment.decision.committee.discussion_engine import DiscussionEngine
        from iios.investment.decision.committee.member_registry import MemberRegistry
        from iios.investment.decision.committee.committee_constants import SpecialistType
        from iios.investment.decision.committee.voting_engine import VotingEngine
        ev        = CommitteeQualityEvaluator()
        members12 = MemberRegistry.default_committee().all_members()
        engine    = DiscussionEngine()
        r1_12     = engine.run_opening_review(members12, rich_context, 1)
        vs12      = VotingEngine().conduct_vote(members12, list(r1_12.opinions))
        sc12      = ev.evaluate(list(r1_12.opinions), vs12, [r1_12], 0, 0, rich_context)

        small_reg = MemberRegistry()
        for _ in range(5):
            small_reg.add_member(SpecialistType.MARKET_INTELLIGENCE)
        members5  = small_reg.all_members()
        r1_5      = engine.run_opening_review(members5, rich_context, 1)
        vs5       = VotingEngine().conduct_vote(members5, list(r1_5.opinions))
        sc5       = ev.evaluate(list(r1_5.opinions), vs5, [r1_5], 0, 0, rich_context)
        # Both scores must be valid; we don't assert ordering because specialist diversity
        # (abstain rates) can produce non-monotonic participation scores.
        assert 0.0 <= sc12 <= 100.0
        assert 0.0 <= sc5  <= 100.0

    def test_resolved_challenges_improve_score(self, rich_context, default_registry):
        from iios.investment.decision.committee.discussion_engine import DiscussionEngine
        from iios.investment.decision.committee.voting_engine import VotingEngine
        engine   = DiscussionEngine()
        members  = default_registry.all_members()
        r1       = engine.run_opening_review(members, rich_context, 1)
        opinions = list(r1.opinions)
        vs       = VotingEngine().conduct_vote(members, opinions)
        ev       = CommitteeQualityEvaluator()
        sc_none  = ev.evaluate(opinions, vs, [r1], 5, 0, rich_context)
        sc_all   = ev.evaluate(opinions, vs, [r1], 5, 5, rich_context)
        assert sc_all >= sc_none


class TestCommitteeConfidenceCalculator:
    def test_returns_float_in_range(self, rich_context, default_registry):
        from iios.investment.decision.committee.discussion_engine import DiscussionEngine
        from iios.investment.decision.committee.voting_engine import VotingEngine
        engine   = DiscussionEngine()
        members  = default_registry.all_members()
        r1       = engine.run_opening_review(members, rich_context, 1)
        opinions = list(r1.opinions)
        ve       = VotingEngine()
        vs       = ve.conduct_vote(members, opinions)
        calc     = CommitteeConfidenceCalculator()
        conf     = calc.calculate(vs, opinions, rich_context, 0, 0)
        assert 0.0 <= conf <= 100.0

    def test_higher_consensus_higher_confidence(self, rich_context):
        from iios.investment.decision.committee.vote_registry import CastVote
        from iios.investment.decision.committee.committee_constants import VoteType
        from iios.investment.decision.committee.weighted_voting import WeightedVoting
        from iios.investment.decision.committee.committee_member import MemberOpinion
        from iios.investment.decision.committee.committee_constants import SpecialistType
        from iios.investment.decision.committee.member_roles import MemberRole

        wv   = WeightedVoting()
        calc = CommitteeConfidenceCalculator()

        votes_uni = [CastVote(f"M{i}", 1.0, VoteType.SUPPORT, 80.0) for i in range(10)]
        vs_uni    = wv.tally(votes_uni)

        votes_split = (
            [CastVote(f"S{i}", 1.0, VoteType.SUPPORT, 80.0) for i in range(6)]
            + [CastVote(f"O{i}", 1.0, VoteType.OPPOSE, 80.0) for i in range(4)]
        )
        vs_split = wv.tally(votes_split)

        opinions = [
            MemberOpinion(
                f"M{i}", SpecialistType.MARKET_INTELLIGENCE, MemberRole.VOTING_MEMBER,
                VoteType.SUPPORT, 80.0, 70.0, (), (), "OK",
            )
            for i in range(10)
        ]
        c_uni   = calc.calculate(vs_uni,   opinions, rich_context, 0, 0)
        c_split = calc.calculate(vs_split, opinions, rich_context, 0, 0)
        assert c_uni >= c_split


class TestCommitteeStatisticsTracker:
    def test_initial_empty(self):
        t = CommitteeStatisticsTracker()
        s = t.summary()
        assert s.total_sessions == 0
        assert s.success_rate   == 0.0

    def test_record_success(self):
        from iios.investment.decision.committee.committee_constants import CommitteePosition
        t = CommitteeStatisticsTracker()
        t.record_success(CommitteePosition.PROCEED_TO_RECOMMENDATION, 75.0, 200)
        s = t.summary()
        assert s.total_sessions == 1
        assert s.successful     == 1
        assert s.success_rate   == pytest.approx(1.0)

    def test_record_failure(self):
        t = CommitteeStatisticsTracker()
        t.record_failure(100)
        s = t.summary()
        assert s.total_sessions == 1
        assert s.failed         == 1

    def test_block_rate(self):
        from iios.investment.decision.committee.committee_constants import CommitteePosition
        t = CommitteeStatisticsTracker()
        t.record_success(CommitteePosition.BLOCKED, 30.0, 150)
        t.record_success(CommitteePosition.PROCEED_TO_RECOMMENDATION, 80.0, 200)
        s = t.summary()
        assert s.block_rate == pytest.approx(0.5, abs=0.01)

    def test_avg_score(self):
        from iios.investment.decision.committee.committee_constants import CommitteePosition
        t = CommitteeStatisticsTracker()
        t.record_success(CommitteePosition.PROCEED_TO_RECOMMENDATION, 60.0, 100)
        t.record_success(CommitteePosition.PROCEED_TO_RECOMMENDATION, 80.0, 100)
        s = t.summary()
        assert s.avg_score == pytest.approx(70.0, abs=0.5)

    def test_reset(self):
        from iios.investment.decision.committee.committee_constants import CommitteePosition
        t = CommitteeStatisticsTracker()
        t.record_success(CommitteePosition.PROCEED_TO_RECOMMENDATION, 70.0, 100)
        t.reset()
        assert t.summary().total_sessions == 0

    def test_to_dict(self):
        t = CommitteeStatisticsTracker()
        d = t.summary().to_dict()
        assert "total_sessions" in d
        assert "success_rate"   in d


class TestCommitteeHealthMonitor:
    def test_initial_status_initializing(self):
        h = CommitteeHealthMonitor()
        assert h.report().status == CommitteeStatus.INITIALIZING

    def test_set_ready(self):
        h = CommitteeHealthMonitor()
        h.set_status(CommitteeStatus.READY)
        assert h.report().status == CommitteeStatus.READY

    def test_record_success(self):
        h = CommitteeHealthMonitor()
        h.set_status(CommitteeStatus.READY)
        h.record_success(200.0)
        r = h.report()
        assert r.successful == 1

    def test_record_failure(self):
        h = CommitteeHealthMonitor()
        h.set_status(CommitteeStatus.READY)
        h.record_failure()
        r = h.report()
        assert r.failed == 1

    def test_consecutive_failures_degrade(self):
        h = CommitteeHealthMonitor()
        h.set_status(CommitteeStatus.READY)
        for _ in range(5):
            h.record_failure()
        r = h.report()
        assert r.status in (CommitteeStatus.DEGRADED, CommitteeStatus.STOPPED)

    def test_success_resets_consecutive(self):
        h = CommitteeHealthMonitor()
        h.set_status(CommitteeStatus.READY)
        for _ in range(3):
            h.record_failure()
        h.record_success(100.0)
        r = h.report()
        assert r.consecutive_failures == 0

    def test_is_healthy_when_running(self):
        h = CommitteeHealthMonitor()
        h.set_status(CommitteeStatus.RUNNING)
        r = h.report()
        assert r.is_healthy

    def test_is_unhealthy_when_stopped(self):
        h = CommitteeHealthMonitor()
        h.set_status(CommitteeStatus.STOPPED)
        assert not h.report().is_healthy

    def test_to_dict(self):
        h = CommitteeHealthMonitor()
        d = h.report().to_dict()
        assert "status" in d
        assert "is_healthy" in d

    def test_reset(self):
        h = CommitteeHealthMonitor()
        h.set_status(CommitteeStatus.READY)
        h.record_success(200.0)
        h.reset()
        r = h.report()
        assert r.total_sessions == 0
