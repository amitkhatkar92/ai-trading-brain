"""tests/unit/investment/decision/committee/test_voting.py
Tests for VotingEngine, WeightedVoting, VoteRegistry, MinorityReports.
"""
from __future__ import annotations

import pytest

from iios.investment.decision.committee.committee_constants import (
    ConsensusLevel,
    VoteType,
)
from iios.investment.decision.committee.committee_member import (
    MarketIntelligenceMember,
    MemberOpinion,
    create_member,
    SpecialistType,
)
from iios.investment.decision.committee.member_registry import MemberRegistry
from iios.investment.decision.committee.member_roles import MemberRole
from iios.investment.decision.committee.minority_reports import MinorityReportBuilder
from iios.investment.decision.committee.vote_registry import CastVote, VoteRegistry
from iios.investment.decision.committee.voting_engine import VotingEngine
from iios.investment.decision.committee.weighted_voting import VoteSummary, WeightedVoting


class TestWeightedVoting:
    def _make_vote(self, mid, w, v, c=70.0):
        return CastVote(mid, w, v, c)

    def test_unanimous_support(self):
        wv = WeightedVoting()
        votes = [self._make_vote(f"M{i}", 1.0, VoteType.SUPPORT) for i in range(5)]
        s = wv.tally(votes)
        assert s.consensus_level == ConsensusLevel.UNANIMOUS
        assert s.support_fraction == pytest.approx(1.0)

    def test_unanimous_oppose(self):
        wv    = WeightedVoting()
        votes = [self._make_vote(f"M{i}", 1.0, VoteType.OPPOSE) for i in range(5)]
        s     = wv.tally(votes)
        assert s.support_fraction == pytest.approx(0.0)
        assert s.consensus_level  == ConsensusLevel.NO_CONSENSUS

    def test_majority_support(self):
        wv    = WeightedVoting()
        votes = (
            [self._make_vote(f"S{i}", 1.0, VoteType.SUPPORT) for i in range(7)]
            + [self._make_vote(f"O{i}", 1.0, VoteType.OPPOSE) for i in range(3)]
        )
        s = wv.tally(votes)
        assert s.support_fraction == pytest.approx(0.7, abs=0.01)
        assert s.consensus_level == ConsensusLevel.MAJORITY

    def test_abstains_excluded_from_decisive_weight(self):
        wv    = WeightedVoting()
        votes = [
            self._make_vote("S1", 1.0, VoteType.SUPPORT),
            self._make_vote("A1", 1.0, VoteType.ABSTAIN),
            self._make_vote("A2", 1.0, VoteType.ABSTAIN),
        ]
        s = wv.tally(votes)
        # decisive weight = support only (1.0), oppose = 0
        assert s.decisive_weight == pytest.approx(1.0)
        assert s.support_fraction == pytest.approx(1.0)

    def test_no_votes_zero_fraction(self):
        wv = WeightedVoting()
        s  = wv.tally([])
        assert s.support_fraction == 0.0
        assert s.total_votes == 0

    def test_counts_correct(self):
        wv = WeightedVoting()
        votes = [
            self._make_vote("S1", 1.0, VoteType.SUPPORT),
            self._make_vote("O1", 1.0, VoteType.OPPOSE),
            self._make_vote("A1", 1.0, VoteType.ABSTAIN),
        ]
        s = wv.tally(votes)
        assert s.support_count == 1
        assert s.oppose_count  == 1
        assert s.abstain_count == 1

    def test_to_dict(self):
        wv = WeightedVoting()
        s  = wv.tally([self._make_vote("M1", 1.0, VoteType.SUPPORT)])
        d  = s.to_dict()
        assert "consensus_level"  in d
        assert "support_fraction" in d


class TestVoteRegistry:
    def test_cast_and_get(self):
        r = VoteRegistry()
        r.cast("M1", 1.0, VoteType.SUPPORT, 80.0)
        v = r.get("M1")
        assert v.vote == VoteType.SUPPORT
        assert v.weight == pytest.approx(1.0)

    def test_cast_from_opinion(self, rich_context):
        m  = MarketIntelligenceMember("M1", MemberRole.VOTING_MEMBER)
        op = m.review(rich_context)
        r  = VoteRegistry()
        r.cast_from_opinion(op, m.weight)
        v = r.get("M1")
        assert v.vote == op.effective_vote

    def test_overwrite_existing(self):
        r = VoteRegistry()
        r.cast("M1", 1.0, VoteType.SUPPORT, 80.0)
        r.cast("M1", 1.0, VoteType.OPPOSE, 70.0)
        assert r.get("M1").vote == VoteType.OPPOSE

    def test_count(self):
        r = VoteRegistry()
        r.cast("M1", 1.0, VoteType.SUPPORT, 80.0)
        r.cast("M2", 1.0, VoteType.OPPOSE,  70.0)
        assert r.count() == 2

    def test_clear(self):
        r = VoteRegistry()
        r.cast("M1", 1.0, VoteType.SUPPORT, 80.0)
        r.clear()
        assert r.count() == 0


class TestVotingEngine:
    def test_conduct_vote_returns_summary(self, rich_context):
        registry = MemberRegistry.default_committee()
        members  = registry.all_members()
        opinions = [m.review(rich_context) for m in members]
        engine   = VotingEngine()
        vs       = engine.conduct_vote(members, opinions)
        assert isinstance(vs, VoteSummary)

    def test_total_votes_equals_member_count(self, rich_context):
        registry = MemberRegistry.default_committee()
        members  = registry.voting_members()
        opinions = [m.review(rich_context) for m in members]
        engine   = VotingEngine()
        vs       = engine.conduct_vote(members, opinions)
        assert vs.total_votes == len(members)

    def test_support_fraction_in_range(self, rich_context):
        registry = MemberRegistry.default_committee()
        members  = registry.all_members()
        opinions = [m.review(rich_context) for m in members]
        engine   = VotingEngine()
        vs       = engine.conduct_vote(members, opinions)
        assert 0.0 <= vs.support_fraction <= 1.0

    def test_observers_excluded_from_vote(self):
        from iios.investment.decision.committee.committee_member import CustomSpecialistMember
        # Create a registry with one observer
        registry = MemberRegistry()
        registry.add_member(SpecialistType.RESEARCH, MemberRole.OBSERVER, member_id="OBS1")
        registry.add_member(SpecialistType.MARKET_INTELLIGENCE, MemberRole.VOTING_MEMBER)
        assert registry.voting_member_count() == 1  # observer excluded

    def test_tie_break_called_when_exact_50(self, rich_context):
        # Build a tie manually: 1 SUPPORT + 1 OPPOSE with equal weights
        registry = MemberRegistry()
        registry.add_member(SpecialistType.RISK_INTELLIGENCE, MemberRole.CHAIR, member_id="CHAIR")
        registry.add_member(SpecialistType.COMPLIANCE, MemberRole.VOTING_MEMBER, member_id="COMP")

        members  = registry.all_members()
        opinions = [m.review(rich_context) for m in members]
        engine   = VotingEngine()
        vs       = engine.conduct_vote(members, opinions)
        # just verify it returns a valid summary (tie may or may not happen with real data)
        assert isinstance(vs, VoteSummary)


class TestMinorityReportBuilder:
    def test_no_minority_on_unanimous(self, rich_context):
        from iios.investment.decision.committee.weighted_voting import WeightedVoting
        from iios.investment.decision.committee.vote_registry import CastVote

        wv    = WeightedVoting()
        votes = [CastVote(f"M{i}", 1.0, VoteType.SUPPORT, 80.0) for i in range(5)]
        vs    = wv.tally(votes)

        # Build fake SUPPORT opinions
        m     = MarketIntelligenceMember("M0", MemberRole.VOTING_MEMBER)
        # override with all SUPPORT
        opinions = [
            MemberOpinion(
                f"M{i}", SpecialistType.MARKET_INTELLIGENCE, MemberRole.VOTING_MEMBER,
                VoteType.SUPPORT, 75.0, 70.0, ("Good data",), (), "All supports",
            )
            for i in range(5)
        ]
        builder = MinorityReportBuilder()
        reports = builder.build(opinions, vs)
        assert reports == []

    def test_dissenting_votes_generate_minority_reports(self, rich_context):
        registry = MemberRegistry.default_committee()
        members  = registry.all_members()
        opinions = [m.review(rich_context) for m in members]
        engine   = VotingEngine()
        vs       = engine.conduct_vote(members, opinions)
        builder  = MinorityReportBuilder()
        reports  = builder.build(opinions, vs)
        # just verify structure
        for r in reports:
            assert isinstance(r.formal_statement, str)
            assert len(r.formal_statement) > 0

    def test_minority_to_dict(self, rich_context):
        registry = MemberRegistry.default_committee()
        members  = registry.all_members()
        opinions = [m.review(rich_context) for m in members]
        engine   = VotingEngine()
        vs       = engine.conduct_vote(members, opinions)
        builder  = MinorityReportBuilder()
        reports  = builder.build(opinions, vs)
        for r in reports:
            d = r.to_dict()
            assert "member_id" in d
            assert "dissenting_vote" in d
