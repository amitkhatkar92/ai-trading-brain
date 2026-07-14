"""tests/unit/investment/strategy/debate/test_debate_report.py"""
import pytest
from iios.investment.strategy.debate.debate_constants import (
    ArgumentType, DebatePhase, ParticipantRole, VoteOutcome,
)
from iios.investment.strategy.debate.debate_session import DebateSession
from iios.investment.strategy.debate.argument_manager import make_argument
from iios.investment.strategy.debate.evidence_registry import make_evidence
from iios.investment.strategy.debate.debate_constants import EvidenceSource
from iios.investment.strategy.debate.voting_engine import make_vote
from iios.investment.strategy.debate.consensus_engine import ConsensusEngine, ConsensusPolicy
from iios.investment.strategy.debate.participant_profile import build_profile
from iios.investment.strategy.debate.recommendation_summary import (
    RecommendationSummary, build_recommendation_summary,
)
from iios.investment.strategy.debate.debate_explanation import (
    DebateExplainer, DebateExplanation,
)
from iios.investment.strategy.debate.executive_summary import (
    ExecutiveSummaryBuilder, ExecutiveSummary,
)
from iios.investment.strategy.debate.debate_report import DebateReport, build_report


def _populated_session(debate_context):
    """Create a partially-completed session with data for report building."""
    session = DebateSession(debate_context)
    session.start()
    session.add_participant("p1")
    session.add_participant("p2")

    sid = session.session_id
    session.evidence_registry.add(make_evidence(
        sid, EvidenceSource.TECHNICAL_ANALYSIS, "tech", "RSI", "RSI signal", 70.0,
    ))
    session.add_argument(make_argument(
        sid, "p1", ParticipantRole.TECHNICAL_ANALYST,
        ArgumentType.SUPPORTING, "Price bullish", "RSI", 75.0,
    ))
    session.add_argument(make_argument(
        sid, "p2", ParticipantRole.RISK_ANALYST,
        ArgumentType.OPPOSING, "Risk high", "VaR", 65.0,
    ))

    votes = [
        make_vote(sid, "p1", ParticipantRole.TECHNICAL_ANALYST,
                  VoteOutcome.SUPPORT, 80.0, "r", 1.5),
        make_vote(sid, "p2", ParticipantRole.RISK_ANALYST,
                  VoteOutcome.SUPPORT, 70.0, "r", 2.0),
    ]
    for v in votes:
        session.add_vote(v)

    profiles = [build_profile(ParticipantRole.TECHNICAL_ANALYST, participant_id="p1"),
                build_profile(ParticipantRole.RISK_ANALYST,         participant_id="p2")]
    policy   = ConsensusPolicy(min_quorum=2)
    consensus = ConsensusEngine().compute(votes, profiles, session_id=sid, policy=policy)
    session.set_consensus(consensus)
    session.add_final_opinion("p1", "Technical: bullish setup.")
    session.add_final_opinion("p2", "Risk: acceptable risk.")

    # Advance to closed
    for phase in [
        DebatePhase.OPENING_STATEMENTS,
        DebatePhase.EVIDENCE_COLLECTION,
        DebatePhase.ARGUMENTS,
        DebatePhase.REBUTTALS,
        DebatePhase.COUNTER_ARGUMENTS,
        DebatePhase.CONSENSUS_BUILDING,
        DebatePhase.FINAL_OPINIONS,
        DebatePhase.CLOSED,
    ]:
        session.advance_phase(phase)

    return session


class TestRecommendationSummary:
    def test_not_a_decision(self, debate_context):
        session  = _populated_session(debate_context)
        rec = build_recommendation_summary(
            "debate-001", "strat-001", session, session.consensus,
        )
        assert rec.not_a_decision is True

    def test_to_dict_has_guard(self, debate_context):
        session = _populated_session(debate_context)
        rec     = build_recommendation_summary(
            "debate-001", "strat-001", session, session.consensus,
        )
        d = rec.to_dict()
        assert d["NOT_A_TRADING_DECISION"] is True
        assert "consensus_direction" in d

    def test_is_frozen(self, debate_context):
        session = _populated_session(debate_context)
        rec     = build_recommendation_summary(
            "debate-001", "strat-001", session, session.consensus,
        )
        with pytest.raises((AttributeError, TypeError)):
            rec.not_a_decision = False  # type: ignore


class TestDebateExplanation:
    def test_explain_returns_explanation(self, debate_context):
        session  = _populated_session(debate_context)
        explainer = DebateExplainer()
        exp       = explainer.explain(session)
        assert isinstance(exp, DebateExplanation)

    def test_to_dict(self, debate_context):
        session = _populated_session(debate_context)
        exp     = DebateExplainer().explain(session)
        d       = exp.to_dict()
        assert "session_id" in d
        assert "consensus_narrative" in d
        assert "vote_breakdown" in d

    def test_vote_breakdown_populated(self, debate_context):
        session = _populated_session(debate_context)
        exp     = DebateExplainer().explain(session)
        assert len(exp.vote_breakdown) == 2


class TestExecutiveSummary:
    def test_build_returns_summary(self, debate_context):
        session = _populated_session(debate_context)
        builder = ExecutiveSummaryBuilder()
        summary = builder.build(session)
        assert isinstance(summary, ExecutiveSummary)

    def test_one_liner_contains_symbol(self, debate_context):
        session = _populated_session(debate_context)
        summary = ExecutiveSummaryBuilder().build(session)
        assert debate_context.symbol in summary.one_liner

    def test_agent_counts(self, debate_context):
        session = _populated_session(debate_context)
        summary = ExecutiveSummaryBuilder().build(session)
        assert summary.participating_agents == 2
        assert summary.total_arguments == 2

    def test_to_dict(self, debate_context):
        session = _populated_session(debate_context)
        d       = ExecutiveSummaryBuilder().build(session).to_dict()
        assert "consensus_level" in d
        assert "confidence" in d


class TestDebateReport:
    def test_build_report(self, debate_context):
        session = _populated_session(debate_context)
        report  = build_report(session)
        assert isinstance(report, DebateReport)

    def test_report_not_a_decision(self, debate_context):
        session = _populated_session(debate_context)
        report  = build_report(session)
        assert report.not_a_decision is True

    def test_report_to_dict_has_guard(self, debate_context):
        session = _populated_session(debate_context)
        d       = build_report(session).to_dict()
        assert d["NOT_A_TRADING_DECISION"] is True

    def test_report_arguments(self, debate_context):
        session = _populated_session(debate_context)
        report  = build_report(session)
        assert len(report.arguments_for) == 1
        assert len(report.arguments_against) == 1

    def test_report_evidence_summary(self, debate_context):
        session = _populated_session(debate_context)
        report  = build_report(session)
        assert report.evidence_summary["total"] == 1

    def test_report_is_frozen(self, debate_context):
        session = _populated_session(debate_context)
        report  = build_report(session)
        with pytest.raises((AttributeError, TypeError)):
            report.not_a_decision = False  # type: ignore
