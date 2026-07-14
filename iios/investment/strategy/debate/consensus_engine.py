"""iios/investment/strategy/debate/consensus_engine.py
Consensus computation orchestrating voting, agreement, and policy.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.strategy.debate.debate_constants import (
    ConsensusLevel,
    VoteOutcome,
    VotingMechanism,
)
from iios.investment.strategy.debate.participant_profile import ParticipantProfile
from iios.investment.strategy.debate.voting_engine import Vote, VotingEngine, VotingResult
from iios.investment.strategy.debate.agreement_analysis import AgreementAnalysis, AgreementMetrics


@dataclass
class ConsensusPolicy:
    """Configurable policy for consensus computation."""
    mechanism:          VotingMechanism = VotingMechanism.WEIGHTED_MAJORITY
    threshold:          float           = 0.6     # required agreement fraction
    require_quorum:     bool            = True
    min_quorum:         int             = 3       # minimum active votes
    allow_abstention:   bool            = True
    minority_threshold: float           = 0.3     # fraction to trigger minority report


@dataclass(frozen=True)
class ConsensusResult:
    """Immutable consensus outcome for one debate session."""
    session_id:         str
    consensus_level:    ConsensusLevel
    voting_result:      VotingResult
    agreement_metrics:  AgreementMetrics
    winning_outcome:    VoteOutcome
    minority_outcomes:  Tuple[VoteOutcome, ...]
    minority_agent_ids: Tuple[str, ...]
    confidence_score:   float             # 0–100
    consensus_reached:  bool
    policy_used:        ConsensusPolicy
    computed_at:        datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id":         self.session_id,
            "consensus_level":    self.consensus_level.value,
            "winning_outcome":    self.winning_outcome.value,
            "minority_outcomes":  [o.value for o in self.minority_outcomes],
            "minority_agent_ids": list(self.minority_agent_ids),
            "confidence_score":   round(self.confidence_score, 2),
            "consensus_reached":  self.consensus_reached,
            "voting_result":      self.voting_result.to_dict(),
            "agreement_metrics":  self.agreement_metrics.to_dict(),
            "computed_at":        self.computed_at.isoformat(),
        }


class ConsensusEngine:
    """
    Computes consensus from votes using a ConsensusPolicy.
    Pure computation — no state.
    """

    def __init__(self) -> None:
        self._voting    = VotingEngine()
        self._agreement = AgreementAnalysis()

    def compute(
        self,
        votes:      List[Vote],
        profiles:   List[ParticipantProfile],
        session_id: str             = "",
        policy:     Optional[ConsensusPolicy] = None,
    ) -> ConsensusResult:
        p = policy or ConsensusPolicy()

        v_result = self._voting.compute(
            votes       = votes,
            profiles    = profiles,
            mechanism   = p.mechanism,
            session_id  = session_id,
            min_quorum  = p.min_quorum,
        )

        a_metrics = self._agreement.analyse(votes, session_id=session_id)
        level     = self._determine_level(a_metrics.agreement_fraction)

        consensus_reached = (
            v_result.quorum_met
            and a_metrics.agreement_fraction >= p.threshold
        )

        minority_agents = self._minority_agents(
            votes          = votes,
            winner         = v_result.winning_outcome,
            threshold_frac = p.minority_threshold,
        )

        confidence = self._confidence_score(
            agree_frac = a_metrics.agreement_fraction,
            n_votes    = v_result.total_votes - v_result.abstentions,
            quorum_met = v_result.quorum_met,
            min_quorum = p.min_quorum,
        )

        minority_outcomes = tuple({v.outcome for v in votes
                                   if v.participant_id in minority_agents and not v.outcome.is_abstain})

        return ConsensusResult(
            session_id         = session_id,
            consensus_level    = level,
            voting_result      = v_result,
            agreement_metrics  = a_metrics,
            winning_outcome    = v_result.winning_outcome,
            minority_outcomes  = minority_outcomes,
            minority_agent_ids = tuple(minority_agents),
            confidence_score   = confidence,
            consensus_reached  = consensus_reached,
            policy_used        = p,
            computed_at        = datetime.now(timezone.utc),
        )

    # ── Internal helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _determine_level(agree_frac: float) -> ConsensusLevel:
        if agree_frac >= 1.0:
            return ConsensusLevel.UNANIMOUS
        if agree_frac >= 0.75:
            return ConsensusLevel.STRONG
        if agree_frac >= 0.60:
            return ConsensusLevel.MODERATE
        if agree_frac >= 0.50:
            return ConsensusLevel.WEAK
        return ConsensusLevel.SPLIT

    @staticmethod
    def _minority_agents(
        votes:          List[Vote],
        winner:         VoteOutcome,
        threshold_frac: float,
    ) -> List[str]:
        """Return participant_ids that disagreed with the majority."""
        dissenters = [
            v.participant_id for v in votes
            if not v.outcome.is_abstain and v.outcome != winner
        ]
        n_active   = sum(1 for v in votes if not v.outcome.is_abstain)
        if n_active == 0:
            return []
        if len(dissenters) / n_active >= threshold_frac:
            return dissenters
        return []

    @staticmethod
    def _confidence_score(
        agree_frac: float,
        n_votes:    int,
        quorum_met: bool,
        min_quorum: int,
    ) -> float:
        if not quorum_met or n_votes == 0:
            return 0.0
        # Scale: 0–100 based on agreement and vote count
        volume_bonus = min(n_votes / max(min_quorum * 2, 1), 1.0) * 20
        conf         = agree_frac * 80 + volume_bonus
        return round(min(conf, 100.0), 2)
