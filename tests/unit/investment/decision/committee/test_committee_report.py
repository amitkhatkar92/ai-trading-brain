"""tests/unit/investment/decision/committee/test_committee_report.py
Tests for CommitteeReport, CommitteeFindings, CommitteeStance, MinorityReports.
"""
from __future__ import annotations

import pytest

from iios.investment.decision.committee.committee_constants import (
    CommitteeGrade,
    CommitteePosition,
    ConsensusLevel,
)
from iios.investment.decision.committee.committee_findings import (
    CommitteeFindingsBuilder,
)
from iios.investment.decision.committee.committee_recommendations import build_committee_stance
from iios.investment.decision.committee.committee_report import build_committee_report
from iios.investment.decision.committee.committee_session import CommitteeSession
from iios.investment.decision.committee.minority_reports import MinorityReport
from iios.investment.decision.committee.weighted_voting import VoteSummary, WeightedVoting
from iios.investment.decision.committee.vote_registry import CastVote
from iios.investment.decision.committee.committee_constants import VoteType


class TestCommitteeFindings:
    def test_build_returns_findings(self, rich_context, default_registry):
        from iios.investment.decision.committee.discussion_engine import DiscussionEngine
        engine   = DiscussionEngine()
        members  = default_registry.all_members()
        r1       = engine.run_opening_review(members, rich_context, 1)
        opinions = list(r1.opinions)
        builder  = CommitteeFindingsBuilder()
        f        = builder.build(opinions, rich_context)
        assert f is not None

    def test_findings_have_assessments(self, rich_context, default_registry):
        from iios.investment.decision.committee.discussion_engine import DiscussionEngine
        engine   = DiscussionEngine()
        members  = default_registry.all_members()
        r1       = engine.run_opening_review(members, rich_context, 1)
        builder  = CommitteeFindingsBuilder()
        f        = builder.build(list(r1.opinions), rich_context)
        assert len(f.evidence_assessment)   > 0
        assert len(f.risk_assessment)       > 0
        assert len(f.confidence_assessment) > 0
        assert len(f.reasoning_assessment)  > 0

    def test_findings_to_dict(self, rich_context, default_registry):
        from iios.investment.decision.committee.discussion_engine import DiscussionEngine
        engine   = DiscussionEngine()
        members  = default_registry.all_members()
        r1       = engine.run_opening_review(members, rich_context, 1)
        builder  = CommitteeFindingsBuilder()
        f        = builder.build(list(r1.opinions), rich_context)
        d        = f.to_dict()
        assert "supporting_observations" in d
        assert "key_risks"               in d


class TestCommitteeStance:
    def test_build_proceed_stance(self):
        stance = build_committee_stance(
            position         = CommitteePosition.PROCEED_TO_RECOMMENDATION,
            support_fraction = 0.80,
            consensus_level  = ConsensusLevel.STRONG,
            risk_concerns    = (),
            open_questions   = (),
        )
        assert stance.forwarding_approved
        assert stance.position == CommitteePosition.PROCEED_TO_RECOMMENDATION

    def test_build_blocked_stance(self):
        stance = build_committee_stance(
            position         = CommitteePosition.BLOCKED,
            support_fraction = 0.30,
            consensus_level  = ConsensusLevel.NO_CONSENSUS,
            risk_concerns    = ("Critical risk",),
            open_questions   = (),
        )
        assert not stance.forwarding_approved
        assert len(stance.required_conditions) > 0

    def test_defer_has_required_conditions(self):
        stance = build_committee_stance(
            position         = CommitteePosition.DEFER_PENDING_EVIDENCE,
            support_fraction = 0.55,
            consensus_level  = ConsensusLevel.SLIM_MAJORITY,
            risk_concerns    = (),
            open_questions   = ("Question A", "Question B"),
        )
        assert not stance.forwarding_approved
        assert len(stance.required_conditions) >= 1

    def test_stance_to_dict(self):
        stance = build_committee_stance(
            CommitteePosition.PROCEED_TO_RECOMMENDATION,
            0.80, ConsensusLevel.STRONG, (), (),
        )
        d = stance.to_dict()
        assert "position" in d
        assert "forwarding_approved" in d

    def test_stance_is_not_actionable_when_blocked(self):
        stance = build_committee_stance(
            CommitteePosition.BLOCKED, 0.30, ConsensusLevel.NO_CONSENSUS, (), (),
        )
        assert not stance.is_actionable


class TestCommitteeReport:
    def _run(self, ctx):
        session = CommitteeSession(ctx.decision_id, ctx)
        return session.run()

    def test_report_fields(self, rich_context):
        r = self._run(rich_context)
        assert r.report_id    is not None
        assert r.session_id   is not None
        assert r.decision_id  is not None
        assert r.created_at   is not None

    def test_grade_is_valid(self, rich_context):
        r = self._run(rich_context)
        assert r.committee_grade in list(CommitteeGrade)

    def test_score_in_range(self, rich_context):
        r = self._run(rich_context)
        assert 0.0 <= r.committee_score <= 100.0

    def test_committee_confidence_in_range(self, rich_context):
        r = self._run(rich_context)
        assert 0.0 <= r.committee_confidence <= 100.0

    def test_is_approved_matches_position(self, rich_context):
        r = self._run(rich_context)
        expected = r.position == CommitteePosition.PROCEED_TO_RECOMMENDATION
        assert r.is_approved == expected

    def test_snapshot_ids_present(self, rich_context):
        r = self._run(rich_context)
        assert r.evidence_snapshot_id    is not None
        assert r.reasoning_snapshot_id   is not None
        assert r.confidence_snapshot_id  is not None
        assert r.risk_snapshot_id        is not None
        assert r.explanation_snapshot_id is not None

    def test_minority_count_non_negative(self, rich_context):
        r = self._run(rich_context)
        assert r.minority_count >= 0

    def test_to_dict_structure(self, rich_context):
        r = self._run(rich_context)
        d = r.to_dict()
        required_keys = [
            "report_id", "session_id", "decision_id", "position",
            "committee_score", "vote_summary", "findings",
            "executive_summary", "is_approved",
        ]
        for k in required_keys:
            assert k in d, f"Missing key: {k}"

    def test_frozen(self, rich_context):
        r = self._run(rich_context)
        with pytest.raises((AttributeError, TypeError)):
            r.committee_score = 999.0  # type: ignore


class TestCommitteeGrade:
    def test_from_score_A(self):
        assert CommitteeGrade.from_score(90) == CommitteeGrade.A

    def test_from_score_B(self):
        assert CommitteeGrade.from_score(72) == CommitteeGrade.B

    def test_from_score_F(self):
        assert CommitteeGrade.from_score(20) == CommitteeGrade.F
