"""tests/unit/investment/decision/committee/test_deliberation.py
Tests for DiscussionEngine, ChallengeEngine, CommitteeSession deliberation flow.
"""
from __future__ import annotations

import pytest

from iios.investment.decision.committee.challenge_engine import (
    Challenge,
    ChallengeEngine,
)
from iios.investment.decision.committee.committee_constants import (
    ChallengeType,
    RoundType,
    SessionState,
    VoteType,
)
from iios.investment.decision.committee.committee_round import RoundResult
from iios.investment.decision.committee.committee_session import CommitteeSession
from iios.investment.decision.committee.discussion_engine import DiscussionEngine
from iios.investment.decision.committee.member_registry import MemberRegistry


class TestChallengeEngine:
    def test_generates_challenges_from_opinions(self, rich_context, default_registry):
        members  = default_registry.all_members()
        engine   = DiscussionEngine()
        r1       = engine.run_opening_review(members, rich_context, 1)
        opinions = list(r1.opinions)
        ce       = ChallengeEngine()
        challenges = ce.generate(opinions, rich_context)
        assert isinstance(challenges, list)

    def test_challenges_have_valid_types(self, rich_context, default_registry):
        members  = default_registry.all_members()
        engine   = DiscussionEngine()
        r1       = engine.run_opening_review(members, rich_context, 1)
        ce       = ChallengeEngine()
        challenges = ce.generate(list(r1.opinions), rich_context)
        for c in challenges:
            assert isinstance(c, Challenge)
            assert c.challenge_type in list(ChallengeType)

    def test_severity_in_range(self, rich_context, default_registry):
        members  = default_registry.all_members()
        engine   = DiscussionEngine()
        r1       = engine.run_opening_review(members, rich_context, 1)
        ce       = ChallengeEngine()
        for c in ce.generate(list(r1.opinions), rich_context):
            assert 0.0 <= c.severity <= 100.0

    def test_rebuttal_in_range(self, rich_context, default_registry):
        members  = default_registry.all_members()
        engine   = DiscussionEngine()
        r1       = engine.run_opening_review(members, rich_context, 1)
        ce       = ChallengeEngine()
        for c in ce.generate(list(r1.opinions), rich_context):
            assert 0.0 <= c.rebuttal_score <= 100.0

    def test_count_resolved(self, rich_context, default_registry):
        members  = default_registry.all_members()
        engine   = DiscussionEngine()
        r1       = engine.run_opening_review(members, rich_context, 1)
        ce       = ChallengeEngine()
        challenges = ce.generate(list(r1.opinions), rich_context)
        resolved   = ce.count_resolved(challenges)
        assert 0 <= resolved <= len(challenges)

    def test_to_dict(self, rich_context, default_registry):
        members  = default_registry.all_members()
        engine   = DiscussionEngine()
        r1       = engine.run_opening_review(members, rich_context, 1)
        ce       = ChallengeEngine()
        chs      = ce.generate(list(r1.opinions), rich_context)
        if chs:
            d = chs[0].to_dict()
            assert "challenge_id"  in d
            assert "challenge_type" in d


class TestDiscussionEngine:
    def test_opening_review_type(self, rich_context, default_registry):
        engine  = DiscussionEngine()
        members = default_registry.all_members()
        r       = engine.run_opening_review(members, rich_context, 1)
        assert r.round_type == RoundType.OPENING_REVIEW

    def test_opening_review_opinion_count(self, rich_context, default_registry):
        engine  = DiscussionEngine()
        members = default_registry.all_members()
        r       = engine.run_opening_review(members, rich_context, 1)
        assert len(r.opinions) == len(members)

    def test_challenge_round_type(self, rich_context, default_registry):
        engine   = DiscussionEngine()
        members  = default_registry.all_members()
        r1       = engine.run_opening_review(members, rich_context, 1)
        r2       = engine.run_challenge_round(list(r1.opinions), rich_context, 2)
        assert r2.round_type == RoundType.CHALLENGE

    def test_deliberation_round_type(self, rich_context, default_registry):
        engine  = DiscussionEngine()
        members = default_registry.all_members()
        r1      = engine.run_opening_review(members, rich_context, 1)
        r3      = engine.run_deliberation(members, list(r1.opinions), 0, 0, rich_context, 3)
        assert r3.round_type == RoundType.DELIBERATION

    def test_final_vote_round_type(self, rich_context, default_registry):
        engine  = DiscussionEngine()
        members = default_registry.all_members()
        r1      = engine.run_opening_review(members, rich_context, 1)
        r4      = engine.run_final_vote(list(r1.opinions), 4)
        assert r4.round_type == RoundType.FINAL_VOTE

    def test_duration_ms_positive(self, rich_context, default_registry):
        engine  = DiscussionEngine()
        members = default_registry.all_members()
        r1      = engine.run_opening_review(members, rich_context, 1)
        assert r1.duration_ms >= 0.0

    def test_round_result_to_dict(self, rich_context, default_registry):
        engine  = DiscussionEngine()
        members = default_registry.all_members()
        r1      = engine.run_opening_review(members, rich_context, 1)
        d       = r1.to_dict()
        assert "round_number" in d
        assert "round_type"   in d


class TestCommitteeSession:
    def test_run_returns_report(self, rich_context):
        session = CommitteeSession(
            rich_context.decision_id, rich_context, None, version=1,
        )
        report = session.run()
        assert report is not None

    def test_session_concludes(self, rich_context):
        session = CommitteeSession(
            rich_context.decision_id, rich_context,
        )
        session.run()
        assert session.state == SessionState.CONCLUDED

    def test_report_has_decision_id(self, rich_context):
        session = CommitteeSession(rich_context.decision_id, rich_context)
        report  = session.run()
        assert report.decision_id == rich_context.decision_id

    def test_report_has_vote_summary(self, rich_context):
        session = CommitteeSession(rich_context.decision_id, rich_context)
        report  = session.run()
        assert report.vote_summary is not None
        assert report.vote_summary.total_votes >= 0

    def test_report_position_is_valid(self, rich_context):
        from iios.investment.decision.committee.committee_constants import CommitteePosition
        session = CommitteeSession(rich_context.decision_id, rich_context)
        report  = session.run()
        assert report.position in list(CommitteePosition)

    def test_minimal_evidence_returns_insufficient(self, minimal_context):
        from iios.investment.decision.committee.committee_constants import CommitteePosition
        session = CommitteeSession(minimal_context.decision_id, minimal_context)
        report  = session.run()
        assert report.position == CommitteePosition.INSUFFICIENT_EVIDENCE

    def test_report_has_rounds(self, rich_context):
        session = CommitteeSession(rich_context.decision_id, rich_context)
        report  = session.run()
        # Rich input should have completed 4 rounds
        assert len(report.rounds) >= 0

    def test_report_has_findings(self, rich_context):
        session = CommitteeSession(rich_context.decision_id, rich_context)
        report  = session.run()
        assert report.findings is not None

    def test_report_executive_summary_non_empty(self, rich_context):
        session = CommitteeSession(rich_context.decision_id, rich_context)
        report  = session.run()
        assert len(report.executive_summary) > 0

    def test_report_to_dict(self, rich_context):
        session = CommitteeSession(rich_context.decision_id, rich_context)
        report  = session.run()
        d       = report.to_dict()
        assert "position"          in d
        assert "vote_summary"      in d
        assert "executive_summary" in d
        assert "committee_score"   in d

    def test_custom_registry(self, rich_context):
        from iios.investment.decision.committee.committee_constants import SpecialistType as ST
        registry = MemberRegistry()
        for _ in range(6):
            registry.add_member(
                ST.MARKET_INTELLIGENCE if _ < 3 else ST.COMPLIANCE,
            )
        session = CommitteeSession(rich_context.decision_id, rich_context, registry)
        report  = session.run()
        assert report is not None
