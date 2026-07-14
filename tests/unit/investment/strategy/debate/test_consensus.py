"""tests/unit/investment/strategy/debate/test_consensus.py"""
import pytest
from iios.investment.strategy.debate.debate_constants import (
    ConsensusLevel, VoteOutcome, VotingMechanism,
)
from iios.investment.strategy.debate.voting_engine import (
    Vote, VotingEngine, VotingResult, make_vote,
)
from iios.investment.strategy.debate.agreement_analysis import (
    AgreementAnalysis, AgreementMetrics,
)
from iios.investment.strategy.debate.consensus_engine import (
    ConsensusEngine, ConsensusPolicy, ConsensusResult,
)
from iios.investment.strategy.debate.consensus_statistics import (
    ConsensusStatistics, ConsensusStatisticsTracker,
)
from iios.investment.strategy.debate.participant_profile import (
    build_profile,
)
from iios.investment.strategy.debate.debate_constants import ParticipantRole


class TestVotingEngine:
    def test_weighted_majority_support(self, sample_votes, session_id):
        engine   = VotingEngine()
        profiles = [build_profile(v.role, participant_id=v.participant_id)
                    for v in sample_votes]
        result   = engine.compute(sample_votes, profiles, VotingMechanism.WEIGHTED_MAJORITY, session_id)
        assert isinstance(result, VotingResult)
        assert result.total_votes == 5

    def test_simple_majority(self, sample_votes, session_id):
        engine   = VotingEngine()
        profiles = [build_profile(v.role, participant_id=v.participant_id)
                    for v in sample_votes]
        result   = engine.compute(sample_votes, profiles, VotingMechanism.SIMPLE_MAJORITY, session_id)
        assert result.mechanism == VotingMechanism.SIMPLE_MAJORITY

    def test_unanimous_consensus(self, session_id):
        votes = [
            make_vote(session_id, f"a{i}", ParticipantRole.TECHNICAL_ANALYST,
                      VoteOutcome.SUPPORT, 80.0, "reason", 1.0)
            for i in range(5)
        ]
        engine   = VotingEngine()
        profiles = [build_profile(ParticipantRole.TECHNICAL_ANALYST, participant_id=f"a{i}")
                    for i in range(5)]
        result   = engine.compute(votes, profiles, VotingMechanism.UNANIMOUS, session_id)
        assert result.winning_outcome == VoteOutcome.SUPPORT

    def test_abstain_excluded(self, session_id):
        votes = [
            make_vote(session_id, "a1", ParticipantRole.TECHNICAL_ANALYST,
                      VoteOutcome.SUPPORT, 80.0, "r", 1.0),
            make_vote(session_id, "a2", ParticipantRole.RISK_ANALYST,
                      VoteOutcome.ABSTAIN, 50.0, "r", 1.0),
        ]
        engine   = VotingEngine()
        profiles = [
            build_profile(ParticipantRole.TECHNICAL_ANALYST, participant_id="a1"),
            build_profile(ParticipantRole.RISK_ANALYST, participant_id="a2"),
        ]
        result   = engine.compute(votes, profiles, session_id=session_id)
        assert result.abstentions == 1

    def test_empty_votes_returns_neutral(self, session_id):
        engine = VotingEngine()
        result = engine.compute([], [], session_id=session_id)
        assert result.winning_outcome == VoteOutcome.NEUTRAL
        assert not result.quorum_met

    def test_quorum_not_met(self, session_id):
        votes = [
            make_vote(session_id, "a1", ParticipantRole.TECHNICAL_ANALYST,
                      VoteOutcome.SUPPORT, 80.0, "r", 1.0),
        ]
        engine   = VotingEngine()
        profiles = [build_profile(ParticipantRole.TECHNICAL_ANALYST, participant_id="a1")]
        result   = engine.compute(votes, profiles, min_quorum=5, session_id=session_id)
        assert not result.quorum_met

    def test_vote_to_dict(self, sample_votes):
        d = sample_votes[0].to_dict()
        assert "vote_id" in d
        assert "outcome" in d


class TestAgreementAnalysis:
    def test_unanimous_agreement(self, session_id):
        votes = [
            make_vote(session_id, f"a{i}", ParticipantRole.TECHNICAL_ANALYST,
                      VoteOutcome.SUPPORT, 80.0, "r", 1.0)
            for i in range(5)
        ]
        analysis = AgreementAnalysis()
        metrics  = analysis.analyse(votes, session_id)
        assert metrics.agreement_fraction == 1.0

    def test_split_vote(self, session_id):
        votes = [
            make_vote(session_id, "a1", ParticipantRole.TECHNICAL_ANALYST,
                      VoteOutcome.SUPPORT, 80.0, "r", 1.0),
            make_vote(session_id, "a2", ParticipantRole.RISK_ANALYST,
                      VoteOutcome.OPPOSE, 80.0, "r", 1.0),
        ]
        analysis = AgreementAnalysis()
        metrics  = analysis.analyse(votes, session_id)
        assert metrics.agreement_fraction < 1.0

    def test_empty_votes(self, session_id):
        analysis = AgreementAnalysis()
        metrics  = analysis.analyse([], session_id)
        assert metrics.total_active_votes == 0

    def test_metrics_to_dict(self, session_id):
        votes    = [make_vote(session_id, "a", ParticipantRole.MACRO_ANALYST,
                              VoteOutcome.NEUTRAL, 60.0, "r", 1.0)]
        analysis = AgreementAnalysis()
        metrics  = analysis.analyse(votes, session_id)
        d        = metrics.to_dict()
        assert "agreement_fraction" in d

    def test_detect_clusters(self, session_id):
        votes = [
            make_vote(session_id, "a1", ParticipantRole.TECHNICAL_ANALYST,
                      VoteOutcome.SUPPORT, 80.0, "r", 1.0),
            make_vote(session_id, "a2", ParticipantRole.FUNDAMENTAL_ANALYST,
                      VoteOutcome.STRONG_SUPPORT, 90.0, "r", 1.0),
            make_vote(session_id, "a3", ParticipantRole.RISK_ANALYST,
                      VoteOutcome.STRONG_OPPOSE, 85.0, "r", 1.0),
        ]
        clusters = AgreementAnalysis().detect_clusters(votes)
        assert len(clusters) >= 1


class TestConsensusEngine:
    def test_basic_consensus(self, sample_votes, session_id):
        profiles = [build_profile(v.role, participant_id=v.participant_id)
                    for v in sample_votes]
        engine = ConsensusEngine()
        result = engine.compute(sample_votes, profiles, session_id=session_id)
        assert isinstance(result, ConsensusResult)
        assert result.consensus_level in ConsensusLevel

    def test_unanimous_level(self, session_id):
        votes = [
            make_vote(session_id, f"a{i}", ParticipantRole.TECHNICAL_ANALYST,
                      VoteOutcome.SUPPORT, 80.0, "r", 1.0)
            for i in range(5)
        ]
        profiles = [build_profile(ParticipantRole.TECHNICAL_ANALYST, participant_id=f"a{i}")
                    for i in range(5)]
        result   = ConsensusEngine().compute(votes, profiles, session_id=session_id)
        assert result.consensus_level == ConsensusLevel.UNANIMOUS

    def test_split_level(self, session_id):
        votes = [
            make_vote(session_id, "a1", ParticipantRole.TECHNICAL_ANALYST,
                      VoteOutcome.SUPPORT, 80.0, "r", 1.0),
            make_vote(session_id, "a2", ParticipantRole.RISK_ANALYST,
                      VoteOutcome.STRONG_OPPOSE, 80.0, "r", 1.0),
            make_vote(session_id, "a3", ParticipantRole.MACRO_ANALYST,
                      VoteOutcome.OPPOSE, 80.0, "r", 1.0),
        ]
        profiles = [build_profile(v.role, participant_id=v.participant_id) for v in votes]
        result   = ConsensusEngine().compute(votes, profiles, session_id=session_id)
        assert result.consensus_level in (ConsensusLevel.SPLIT, ConsensusLevel.WEAK,
                                          ConsensusLevel.MODERATE, ConsensusLevel.NO_CONSENSUS)

    def test_consensus_to_dict(self, sample_votes, session_id):
        profiles = [build_profile(v.role, participant_id=v.participant_id)
                    for v in sample_votes]
        result   = ConsensusEngine().compute(sample_votes, profiles, session_id=session_id)
        d        = result.to_dict()
        assert "consensus_level" in d
        assert "confidence_score" in d
        assert "winning_outcome" in d

    def test_custom_policy(self, sample_votes, session_id):
        policy   = ConsensusPolicy(
            mechanism=VotingMechanism.SIMPLE_MAJORITY,
            threshold=0.5,
            min_quorum=3,
        )
        profiles = [build_profile(v.role, participant_id=v.participant_id)
                    for v in sample_votes]
        result   = ConsensusEngine().compute(sample_votes, profiles,
                                              session_id=session_id, policy=policy)
        assert result.policy_used.mechanism == VotingMechanism.SIMPLE_MAJORITY

    def test_minority_agents_identified(self, session_id):
        votes = [
            make_vote(session_id, f"a{i}", ParticipantRole.TECHNICAL_ANALYST,
                      VoteOutcome.SUPPORT, 80.0, "r", 1.0)
            for i in range(7)
        ]
        # Add one strong dissenter
        votes.append(make_vote(session_id, "dissenter", ParticipantRole.RISK_ANALYST,
                               VoteOutcome.STRONG_OPPOSE, 90.0, "r", 1.0))
        profiles = [build_profile(v.role, participant_id=v.participant_id) for v in votes]
        result   = ConsensusEngine().compute(votes, profiles, session_id=session_id)
        assert isinstance(result.minority_agent_ids, tuple)


class TestConsensusStatistics:
    def test_record_and_summary(self, sample_votes, session_id):
        votes    = sample_votes
        profiles = [build_profile(v.role, participant_id=v.participant_id) for v in votes]
        result   = ConsensusEngine().compute(votes, profiles, session_id=session_id)

        tracker = ConsensusStatisticsTracker()
        tracker.record(result)
        summary = tracker.summary()
        assert summary.total_debates == 1

    def test_reset(self, sample_votes, session_id):
        votes    = sample_votes
        profiles = [build_profile(v.role, participant_id=v.participant_id) for v in votes]
        result   = ConsensusEngine().compute(votes, profiles, session_id=session_id)

        tracker = ConsensusStatisticsTracker()
        tracker.record(result)
        tracker.reset()
        summary = tracker.summary()
        assert summary.total_debates == 0

    def test_statistics_to_dict(self, sample_votes, session_id):
        votes    = sample_votes
        profiles = [build_profile(v.role, participant_id=v.participant_id) for v in votes]
        result   = ConsensusEngine().compute(votes, profiles, session_id=session_id)

        tracker = ConsensusStatisticsTracker()
        tracker.record(result)
        d = tracker.summary().to_dict()
        assert "total_debates" in d
        assert "consensus_rate" in d
