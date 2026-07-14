"""tests/unit/investment/decision/committee/test_committee_session.py
End-to-end tests for CommitteeSession — full deliberation cycle.
"""
from __future__ import annotations

import pytest

from iios.investment.decision.committee.committee_constants import (
    CommitteePosition,
    SessionState,
)
from iios.investment.decision.committee.committee_report import CommitteeReport
from iios.investment.decision.committee.committee_session import CommitteeSession
from iios.investment.decision.committee.member_registry import MemberRegistry


class TestCommitteeSessionFullCycle:
    def test_rich_returns_committee_report(self, rich_context):
        session = CommitteeSession(rich_context.decision_id, rich_context)
        report  = session.run()
        assert isinstance(report, CommitteeReport)

    def test_session_state_concluded(self, rich_context):
        session = CommitteeSession(rich_context.decision_id, rich_context)
        session.run()
        assert session.state == SessionState.CONCLUDED

    def test_decision_id_preserved(self, rich_context):
        session = CommitteeSession(rich_context.decision_id, rich_context)
        report  = session.run()
        assert report.decision_id == rich_context.decision_id

    def test_subject_id_preserved(self, rich_context):
        session = CommitteeSession(rich_context.decision_id, rich_context)
        report  = session.run()
        assert report.subject_id == rich_context.subject_id

    def test_vote_summary_members_match_registry(self, rich_context):
        registry = MemberRegistry.default_committee()
        session  = CommitteeSession(
            rich_context.decision_id, rich_context, registry,
        )
        report = session.run()
        assert report.vote_summary.total_votes == registry.voting_member_count()

    def test_participating_members_non_empty(self, rich_context):
        session = CommitteeSession(rich_context.decision_id, rich_context)
        report  = session.run()
        assert len(report.participating_members) > 0

    def test_duration_ms_positive(self, rich_context):
        session = CommitteeSession(rich_context.decision_id, rich_context)
        report  = session.run()
        assert report.duration_ms >= 0.0

    def test_minority_reports_is_tuple(self, rich_context):
        session = CommitteeSession(rich_context.decision_id, rich_context)
        report  = session.run()
        assert isinstance(report.minority_reports, tuple)

    def test_opinions_tuple_non_empty(self, rich_context):
        session = CommitteeSession(rich_context.decision_id, rich_context)
        report  = session.run()
        assert len(report.opinions) > 0

    def test_committee_grade_assigned(self, rich_context):
        from iios.investment.decision.committee.committee_constants import CommitteeGrade
        session = CommitteeSession(rich_context.decision_id, rich_context)
        report  = session.run()
        assert report.committee_grade in list(CommitteeGrade)

    def test_is_high_quality_boolean(self, rich_context):
        session = CommitteeSession(rich_context.decision_id, rich_context)
        report  = session.run()
        assert isinstance(report.is_high_quality, bool)


class TestCommitteeSessionInsufficientEvidence:
    def test_minimal_evidence_insufficient(self, minimal_context):
        session = CommitteeSession(minimal_context.decision_id, minimal_context)
        report  = session.run()
        assert report.position == CommitteePosition.INSUFFICIENT_EVIDENCE

    def test_minimal_evidence_state_concluded(self, minimal_context):
        session = CommitteeSession(minimal_context.decision_id, minimal_context)
        session.run()
        # Fast-exit sessions also reach CONCLUDED
        assert session.state == SessionState.CONCLUDED

    def test_insufficient_report_has_no_rounds(self, minimal_context):
        session = CommitteeSession(minimal_context.decision_id, minimal_context)
        report  = session.run()
        # Fast-path = no deliberation rounds
        assert len(report.rounds) == 0

    def test_insufficient_report_to_dict(self, minimal_context):
        session = CommitteeSession(minimal_context.decision_id, minimal_context)
        report  = session.run()
        d       = report.to_dict()
        assert d["position"] == CommitteePosition.INSUFFICIENT_EVIDENCE.value


class TestCommitteeSessionNoQuorum:
    def test_small_registry_no_quorum(self, rich_context):
        registry = MemberRegistry()
        for _ in range(4):
            registry.add_member(
                __import__(
                    "iios.investment.decision.committee.committee_constants",
                    fromlist=["SpecialistType"],
                ).SpecialistType.MARKET_INTELLIGENCE,
            )
        session = CommitteeSession(rich_context.decision_id, rich_context, registry)
        report  = session.run()
        assert report.position == CommitteePosition.INSUFFICIENT_EVIDENCE

    def test_quorum_met_proceeds(self, rich_context):
        from iios.investment.decision.committee.committee_constants import SpecialistType
        registry = MemberRegistry()
        for t in [
            SpecialistType.RISK_INTELLIGENCE,
            SpecialistType.COMPLIANCE,
            SpecialistType.MARKET_INTELLIGENCE,
            SpecialistType.STRATEGY_INTELLIGENCE,
            SpecialistType.COMPANY_INTELLIGENCE,
        ]:
            registry.add_member(t)
        session = CommitteeSession(rich_context.decision_id, rich_context, registry)
        report  = session.run()
        # With quorum met and rich evidence the position should NOT be INSUFFICIENT
        assert report.position != CommitteePosition.INSUFFICIENT_EVIDENCE


class TestCommitteeSessionDeterminism:
    def test_same_context_same_position(self, rich_context):
        r1 = CommitteeSession(rich_context.decision_id, rich_context).run()
        r2 = CommitteeSession(rich_context.decision_id, rich_context).run()
        assert r1.position == r2.position

    def test_unique_session_ids(self, rich_context):
        r1 = CommitteeSession(rich_context.decision_id, rich_context).run()
        r2 = CommitteeSession(rich_context.decision_id, rich_context).run()
        assert r1.session_id != r2.session_id

    def test_unique_report_ids(self, rich_context):
        r1 = CommitteeSession(rich_context.decision_id, rich_context).run()
        r2 = CommitteeSession(rich_context.decision_id, rich_context).run()
        assert r1.report_id != r2.report_id
