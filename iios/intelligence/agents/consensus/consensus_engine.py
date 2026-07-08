"""
iios/intelligence/agents/consensus/consensus_engine.py
======================================================
ConsensusEngine — coordinates the full consensus-building pipeline:
  1. Collect agent decisions
  2. Detect/resolve conflicts
  3. Vote via selected algorithm
  4. Aggregate confidence
  5. Return ConsensusResult

Singleton: get_consensus_engine() / reset_consensus_engine()
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from ..agent_constants import ConsensusMethod, DEFAULT_CONSENSUS_TIMEOUT_S
from ..agent_exceptions import (
    ConsensusTimeoutError, NoConsensusError, InsufficientVotesError
)
from ..core.base_agent import AgentDecision
from .voting_engine         import VotingEngine, VoteResult
from .conflict_resolver     import ConflictResolver, ConflictReport
from .decision_merger       import DecisionMerger, MergedDecision
from .confidence_aggregator import ConfidenceAggregator, AggregatedConfidence

log = logging.getLogger(__name__)

__all__ = [
    "ConsensusResult",
    "ConsensusEngine",
    "get_consensus_engine",
    "reset_consensus_engine",
]


@dataclass
class ConsensusResult:
    """
    Final output of the consensus pipeline.
    """
    consensus_id:    str           = field(default_factory=lambda: str(uuid.uuid4()))
    method:          ConsensusMethod = ConsensusMethod.MAJORITY
    decision:        Any           = None
    confidence:      float         = 0.0
    agreement_rate:  float         = 0.0
    total_votes:     int           = 0
    vote_tally:      dict          = field(default_factory=dict)
    conflict_report: Optional[dict] = None
    merged:          Optional[dict] = None
    aggregated:      Optional[dict] = None
    explanation:     str           = ""
    reached:         bool          = False
    created_at:      float         = field(default_factory=time.time)
    metadata:        dict          = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "consensus_id":   self.consensus_id,
            "method":         self.method.value,
            "decision":       self.decision,
            "confidence":     round(self.confidence, 4),
            "agreement_rate": round(self.agreement_rate, 4),
            "total_votes":    self.total_votes,
            "vote_tally":     self.vote_tally,
            "explanation":    self.explanation,
            "reached":        self.reached,
            "created_at":     self.created_at,
        }


class ConsensusEngine:
    """
    Full consensus-building pipeline.

    Usage
    -----
    engine   = get_consensus_engine()
    decisions = [
        AgentDecision("agent_1", "BUY",  confidence=0.9, weight=1.0),
        AgentDecision("agent_2", "BUY",  confidence=0.7, weight=1.0),
        AgentDecision("agent_3", "HOLD", confidence=0.6, weight=0.5),
    ]
    result = engine.build(decisions, method=ConsensusMethod.CONFIDENCE_WEIGHTED)
    """

    def __init__(self) -> None:
        self._voter     = VotingEngine()
        self._resolver  = ConflictResolver()
        self._merger    = DecisionMerger()
        self._aggregator = ConfidenceAggregator()
        self._lock       = threading.RLock()
        self._call_count = 0

    def build(
        self,
        decisions:          list[AgentDecision],
        method:             ConsensusMethod       = ConsensusMethod.MAJORITY,
        threshold:          float                 = 0.5,
        min_votes:          int                   = 1,
        resolve_conflicts:  bool                  = True,
        merge_numeric:      bool                  = False,
    ) -> ConsensusResult:
        """
        Run the full consensus pipeline.

        Parameters
        ----------
        decisions         — list of agent decisions
        method            — voting algorithm to use
        threshold         — agreement threshold (0–1) for majority/weighted
        min_votes         — minimum decisions required
        resolve_conflicts — run conflict resolver before voting
        merge_numeric     — additionally merge numeric decisions
        """
        with self._lock:
            self._call_count += 1

        if len(decisions) < min_votes:
            raise InsufficientVotesError(min_votes, len(decisions))

        # 1. Conflict detection / resolution
        conflict_report: Optional[ConflictReport] = None
        if resolve_conflicts:
            conflict_report = self._resolver.resolve(decisions)
            # If resolver already determined the winner unambiguously, use it
            if (
                conflict_report.has_conflict
                and conflict_report.resolution is not None
                and method != ConsensusMethod.UNANIMOUS
            ):
                resolved_decision = conflict_report.resolution
            else:
                resolved_decision = None
        else:
            resolved_decision = None

        # 2. Vote
        vote_result = self._run_vote(decisions, method, threshold, min_votes)

        # 3. Confidence aggregation
        agg = self._aggregator.aggregate(decisions)

        # 4. Optional: merge numeric decisions
        merged_result: Optional[MergedDecision] = None
        if merge_numeric:
            merged_result = self._merger.confidence_weighted_average(decisions)

        # 5. Determine final decision
        final_decision = resolved_decision or vote_result.decision
        final_conf     = agg.weighted

        result = ConsensusResult(
            method          = method,
            decision        = final_decision,
            confidence      = final_conf,
            agreement_rate  = vote_result.agreement_rate,
            total_votes     = vote_result.total_votes,
            vote_tally      = vote_result.vote_tally,
            conflict_report = conflict_report.to_dict() if conflict_report else None,
            merged          = merged_result.to_dict() if merged_result else None,
            aggregated      = agg.to_dict(),
            explanation     = vote_result.explanation,
            reached         = vote_result.reached,
        )
        return result

    def build_with_timeout(
        self,
        get_decisions_fn,
        timeout_s:   float          = DEFAULT_CONSENSUS_TIMEOUT_S,
        min_votes:   int            = 1,
        method:      ConsensusMethod = ConsensusMethod.MAJORITY,
        **kwargs,
    ) -> ConsensusResult:
        """
        Call get_decisions_fn() to collect decisions, enforce timeout_s.

        get_decisions_fn: callable() → list[AgentDecision]
        """
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            decisions = get_decisions_fn()
            if len(decisions) >= min_votes:
                return self.build(decisions, method=method, min_votes=min_votes, **kwargs)
            time.sleep(0.05)

        decisions = get_decisions_fn()
        if len(decisions) < min_votes:
            raise ConsensusTimeoutError(timeout_s, len(decisions), min_votes)
        return self.build(decisions, method=method, min_votes=min_votes, **kwargs)

    def _run_vote(
        self,
        decisions: list[AgentDecision],
        method:    ConsensusMethod,
        threshold: float,
        min_votes: int,
    ) -> VoteResult:
        if method == ConsensusMethod.MAJORITY:
            return self._voter.majority_vote(decisions, threshold, min_votes)
        if method == ConsensusMethod.WEIGHTED_MAJORITY:
            return self._voter.weighted_vote(decisions, threshold, min_votes)
        if method == ConsensusMethod.CONFIDENCE_WEIGHTED:
            return self._voter.confidence_weighted_vote(decisions, threshold, min_votes)
        if method == ConsensusMethod.UNANIMOUS:
            return self._voter.unanimous_vote(decisions, min_votes)
        if method == ConsensusMethod.FIRST_PASS:
            return self._voter.first_pass_vote(decisions, threshold, min_votes)
        if method == ConsensusMethod.RANKED_CHOICE:
            return self._voter.ranked_choice_vote(decisions, min_votes)
        # Default
        return self._voter.majority_vote(decisions, threshold, min_votes)

    def stats(self) -> dict:
        return {"call_count": self._call_count}


# ── Singleton ─────────────────────────────────────────────────────────────────

_ce_lock = threading.Lock()
_ce_inst: Optional[ConsensusEngine] = None


def get_consensus_engine() -> ConsensusEngine:
    global _ce_inst
    if _ce_inst is None:
        with _ce_lock:
            if _ce_inst is None:
                _ce_inst = ConsensusEngine()
    return _ce_inst


def reset_consensus_engine() -> None:
    global _ce_inst
    with _ce_lock:
        _ce_inst = None
