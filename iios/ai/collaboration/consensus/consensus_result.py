"""
consensus_result.py -- iios.ai.collaboration.consensus
========================================================
:class:`ConsensusOutcome` — result classification.
:class:`ConsensusResult`  — immutable output from a consensus strategy.

A6 Multi-Agent Collaboration Framework — Phase 3, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import FrozenSet, Optional, Tuple


class ConsensusOutcome(str, Enum):
    """High-level result of a consensus calculation."""

    REACHED             = "reached"
    MAJORITY_VOTE       = "majority_vote"
    TIE                 = "tie"
    INSUFFICIENT_VOTES  = "insufficient_votes"
    THRESHOLD_NOT_MET   = "threshold_not_met"
    FAILED              = "failed"

    def is_success(self) -> bool:
        return self in (ConsensusOutcome.REACHED, ConsensusOutcome.MAJORITY_VOTE)


@dataclass(frozen=True)
class ConsensusResult:
    """
    Immutable output produced by a :class:`ConsensusStrategy`.

    ``vote_counts`` is a frozenset of ``(position_type_value, count)`` tuples.
    ``weight_totals`` is a frozenset of ``(position_type_value, total_weight)`` tuples;
    empty for strategies that do not use weights.
    """

    result_id:          str
    session_id:         str
    outcome:            ConsensusOutcome
    winning_position:   Optional[str]   # position_type.value, or None
    vote_counts:        FrozenSet[Tuple[str, int]]
    weight_totals:      FrozenSet[Tuple[str, float]]
    total_votes:        int
    confidence:         float
    strategy_used:      str
    tiebreaker_applied: bool
    calculated_at:      float

    @classmethod
    def reached(
        cls,
        session_id:       str,
        winning_position: str,
        vote_counts:      FrozenSet[Tuple[str, int]],
        total_votes:      int,
        confidence:       float,
        strategy_used:    str,
        weight_totals:    FrozenSet[Tuple[str, float]] = frozenset(),
    ) -> "ConsensusResult":
        return cls(
            result_id          = str(uuid.uuid4()),
            session_id         = session_id,
            outcome            = ConsensusOutcome.REACHED,
            winning_position   = winning_position,
            vote_counts        = vote_counts,
            weight_totals      = weight_totals,
            total_votes        = total_votes,
            confidence         = confidence,
            strategy_used      = strategy_used,
            tiebreaker_applied = False,
            calculated_at      = time.time(),
        )

    @classmethod
    def majority(
        cls,
        session_id:         str,
        winning_position:   str,
        vote_counts:        FrozenSet[Tuple[str, int]],
        total_votes:        int,
        confidence:         float,
        strategy_used:      str,
        tiebreaker_applied: bool = False,
        weight_totals:      FrozenSet[Tuple[str, float]] = frozenset(),
    ) -> "ConsensusResult":
        return cls(
            result_id          = str(uuid.uuid4()),
            session_id         = session_id,
            outcome            = ConsensusOutcome.MAJORITY_VOTE,
            winning_position   = winning_position,
            vote_counts        = vote_counts,
            weight_totals      = weight_totals,
            total_votes        = total_votes,
            confidence         = confidence,
            strategy_used      = strategy_used,
            tiebreaker_applied = tiebreaker_applied,
            calculated_at      = time.time(),
        )

    @classmethod
    def failed(
        cls,
        session_id:    str,
        outcome:       ConsensusOutcome,
        vote_counts:   FrozenSet[Tuple[str, int]],
        total_votes:   int,
        strategy_used: str,
        weight_totals: FrozenSet[Tuple[str, float]] = frozenset(),
    ) -> "ConsensusResult":
        return cls(
            result_id          = str(uuid.uuid4()),
            session_id         = session_id,
            outcome            = outcome,
            winning_position   = None,
            vote_counts        = vote_counts,
            weight_totals      = weight_totals,
            total_votes        = total_votes,
            confidence         = 0.0,
            strategy_used      = strategy_used,
            tiebreaker_applied = False,
            calculated_at      = time.time(),
        )

    def is_decided(self) -> bool:
        return self.outcome.is_success() and self.winning_position is not None
