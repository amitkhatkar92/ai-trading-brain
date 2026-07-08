"""
iios/intelligence/agents/consensus/voting_engine.py
====================================================
VotingEngine — implements multiple voting algorithms for
consensus building across agent decisions.

Algorithms
----------
majority_vote            — simple majority of decision labels
weighted_vote            — agent-weight-scaled majority
confidence_weighted_vote — decision × confidence × weight
unanimous_vote           — all must agree
first_pass_vote          — first agent with confidence > threshold wins
ranked_choice_vote       — instant-runoff voting
"""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Optional

from ..agent_constants import ConsensusMethod
from ..agent_exceptions import InsufficientVotesError, NoConsensusError
from ..core.base_agent import AgentDecision

log = logging.getLogger(__name__)

__all__ = ["VoteResult", "VotingEngine"]


@dataclass
class VoteResult:
    """Raw result from a single voting pass."""
    method:         ConsensusMethod
    decision:       Any
    confidence:     float
    agreement_rate: float
    total_votes:    int
    vote_tally:     dict
    explanation:    str
    reached:        bool = True

    def to_dict(self) -> dict:
        return {
            "method":         self.method.value,
            "decision":       self.decision,
            "confidence":     round(self.confidence, 4),
            "agreement_rate": round(self.agreement_rate, 4),
            "total_votes":    self.total_votes,
            "vote_tally":     self.vote_tally,
            "explanation":    self.explanation,
            "reached":        self.reached,
        }


class VotingEngine:
    """
    Stateless voting algorithms.

    All methods accept a list[AgentDecision] and return a VoteResult.
    """

    MIN_VOTES: int   = 1
    THRESHOLD: float = 0.5   # majority threshold

    def majority_vote(
        self,
        decisions:  list[AgentDecision],
        threshold:  float = 0.5,
        min_votes:  int   = 1,
    ) -> VoteResult:
        """Simple majority: each agent has one equal vote."""
        self._check_min(decisions, min_votes)
        tally:  Counter = Counter()
        for d in decisions:
            tally[self._key(d.decision)] += 1

        winner, top_count = tally.most_common(1)[0]
        agreement_rate = top_count / len(decisions)
        # find original decision value for the winner key
        winner_value = next(
            (d.decision for d in decisions if self._key(d.decision) == winner), winner
        )
        reached = agreement_rate >= threshold

        return VoteResult(
            method         = ConsensusMethod.MAJORITY,
            decision       = winner_value,
            confidence     = agreement_rate,
            agreement_rate = agreement_rate,
            total_votes    = len(decisions),
            vote_tally     = dict(tally),
            explanation    = (
                f"Majority vote: {winner!r} won {top_count}/{len(decisions)} "
                f"({agreement_rate:.1%})"
            ),
            reached        = reached,
        )

    def weighted_vote(
        self,
        decisions: list[AgentDecision],
        threshold: float = 0.5,
        min_votes: int   = 1,
    ) -> VoteResult:
        """Weighted majority: each agent vote is scaled by decision.weight."""
        self._check_min(decisions, min_votes)
        tally:    dict[str, float] = defaultdict(float)
        total_wt: float = 0.0
        for d in decisions:
            key       = self._key(d.decision)
            tally[key] += d.weight
            total_wt   += d.weight

        if total_wt == 0:
            raise InsufficientVotesError(min_votes, 0)

        winner     = max(tally, key=tally.__getitem__)
        top_weight = tally[winner]
        agreement  = top_weight / total_wt
        reached    = agreement >= threshold
        winner_val = next(
            (d.decision for d in decisions if self._key(d.decision) == winner), winner
        )
        return VoteResult(
            method         = ConsensusMethod.WEIGHTED_MAJORITY,
            decision       = winner_val,
            confidence     = agreement,
            agreement_rate = agreement,
            total_votes    = len(decisions),
            vote_tally     = {k: round(v, 4) for k, v in tally.items()},
            explanation    = (
                f"Weighted vote: {winner!r} scored {top_weight:.2f}/{total_wt:.2f} "
                f"({agreement:.1%})"
            ),
            reached        = reached,
        )

    def confidence_weighted_vote(
        self,
        decisions: list[AgentDecision],
        threshold: float = 0.5,
        min_votes: int   = 1,
    ) -> VoteResult:
        """
        Confidence-weighted vote:
        each vote = decision.confidence × decision.weight
        """
        self._check_min(decisions, min_votes)
        tally:    dict[str, float] = defaultdict(float)
        total_wt: float = 0.0
        for d in decisions:
            key       = self._key(d.decision)
            score     = d.confidence * d.weight
            tally[key] += score
            total_wt   += score

        if total_wt == 0:
            raise InsufficientVotesError(min_votes, 0)

        winner     = max(tally, key=tally.__getitem__)
        top_score  = tally[winner]
        agreement  = top_score / total_wt
        reached    = agreement >= threshold
        winner_val = next(
            (d.decision for d in decisions if self._key(d.decision) == winner), winner
        )
        avg_conf = sum(d.confidence for d in decisions) / len(decisions)
        return VoteResult(
            method         = ConsensusMethod.CONFIDENCE_WEIGHTED,
            decision       = winner_val,
            confidence     = avg_conf,
            agreement_rate = agreement,
            total_votes    = len(decisions),
            vote_tally     = {k: round(v, 4) for k, v in tally.items()},
            explanation    = (
                f"Confidence-weighted: {winner!r} scored {top_score:.2f}/{total_wt:.2f} "
                f"(avg confidence {avg_conf:.1%})"
            ),
            reached        = reached,
        )

    def unanimous_vote(
        self,
        decisions: list[AgentDecision],
        min_votes: int = 2,
    ) -> VoteResult:
        """All agents must agree on the same decision."""
        self._check_min(decisions, min_votes)
        keys = {self._key(d.decision) for d in decisions}
        if len(keys) == 1:
            winner_val = decisions[0].decision
            avg_conf   = sum(d.confidence for d in decisions) / len(decisions)
            return VoteResult(
                method         = ConsensusMethod.UNANIMOUS,
                decision       = winner_val,
                confidence     = avg_conf,
                agreement_rate = 1.0,
                total_votes    = len(decisions),
                vote_tally     = {self._key(winner_val): len(decisions)},
                explanation    = f"Unanimous agreement on {winner_val!r}",
                reached        = True,
            )
        # No unanimity
        tally: Counter = Counter(self._key(d.decision) for d in decisions)
        return VoteResult(
            method         = ConsensusMethod.UNANIMOUS,
            decision       = None,
            confidence     = 0.0,
            agreement_rate = 1.0 / len(decisions),
            total_votes    = len(decisions),
            vote_tally     = dict(tally),
            explanation    = f"No unanimous agreement — {len(keys)} distinct decisions",
            reached        = False,
        )

    def first_pass_vote(
        self,
        decisions:  list[AgentDecision],
        threshold:  float = 0.8,
        min_votes:  int   = 1,
    ) -> VoteResult:
        """Return the first decision with confidence ≥ threshold."""
        self._check_min(decisions, min_votes)
        for d in decisions:
            if d.confidence >= threshold:
                return VoteResult(
                    method         = ConsensusMethod.FIRST_PASS,
                    decision       = d.decision,
                    confidence     = d.confidence,
                    agreement_rate = 1.0,
                    total_votes    = len(decisions),
                    vote_tally     = {self._key(d.decision): 1},
                    explanation    = (
                        f"First-pass: agent {d.agent_id!r} confidence "
                        f"{d.confidence:.1%} ≥ threshold {threshold:.1%}"
                    ),
                    reached        = True,
                )
        # Fallback to highest confidence
        best = max(decisions, key=lambda x: x.confidence)
        return VoteResult(
            method         = ConsensusMethod.FIRST_PASS,
            decision       = best.decision,
            confidence     = best.confidence,
            agreement_rate = best.confidence,
            total_votes    = len(decisions),
            vote_tally     = {self._key(best.decision): 1},
            explanation    = (
                f"First-pass fallback: best confidence {best.confidence:.1%} "
                f"from agent {best.agent_id!r}"
            ),
            reached        = best.confidence >= threshold / 2,
        )

    def ranked_choice_vote(
        self,
        decisions: list[AgentDecision],
        min_votes: int = 1,
    ) -> VoteResult:
        """
        Instant-runoff: eliminate lowest-scoring candidate until
        one reaches >50% of remaining votes.
        """
        self._check_min(decisions, min_votes)
        tally: Counter = Counter(self._key(d.decision) for d in decisions)
        total = len(decisions)
        original_tally = dict(tally)

        while tally:
            leader, top_count = tally.most_common(1)[0]
            # Win if majority or only candidate remaining
            if top_count / total > 0.5 or len(tally) == 1:
                winner_val = next(
                    (d.decision for d in decisions if self._key(d.decision) == leader),
                    leader,
                )
                return VoteResult(
                    method         = ConsensusMethod.RANKED_CHOICE,
                    decision       = winner_val,
                    confidence     = top_count / total,
                    agreement_rate = top_count / total,
                    total_votes    = total,
                    vote_tally     = original_tally,
                    explanation    = (
                        f"Ranked-choice: {leader!r} won with "
                        f"{top_count}/{total} votes"
                    ),
                    reached        = True,
                )
            # Eliminate the last-place candidate
            loser = tally.most_common()[-1][0]
            del tally[loser]

        raise InsufficientVotesError(min_votes, 0)

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _key(decision: Any) -> str:
        """Stable string key for a decision value."""
        if isinstance(decision, str):
            return decision
        if isinstance(decision, (int, float, bool)):
            return str(decision)
        try:
            import json
            return json.dumps(decision, sort_keys=True, default=str)
        except Exception:
            return repr(decision)

    @staticmethod
    def _check_min(decisions: list[AgentDecision], min_votes: int) -> None:
        if len(decisions) < min_votes:
            raise InsufficientVotesError(min_votes, len(decisions))
