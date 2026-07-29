"""
consensus_strategy.py -- iios.ai.collaboration.consensus
==========================================================
Abstract :class:`ConsensusStrategy` plus four built-in implementations.

Strategies
----------
MajorityVoteStrategy       — >50% wins; tie-breaks to the first-occurring
WeightedVoteStrategy       — uses ``Participant.weight``; >50% weight wins
UnanimousStrategy          — all decisive votes must agree
ConfidenceThresholdStrategy — winner's mean confidence must meet threshold

A6 Multi-Agent Collaboration Framework — Phase 3, Module 6
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections import Counter
from typing import Dict, FrozenSet, List, Tuple

from ..debate.debate_position import DebatePosition, PositionType
from .consensus_result        import ConsensusOutcome, ConsensusResult


# ── Abstract base ──────────────────────────────────────────────────────────────

class ConsensusStrategy(ABC):
    """Abstract base for consensus algorithms."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def calculate(
        self,
        session_id:  str,
        positions:   List[DebatePosition],
        weights:     Dict[str, float],     # agent_id -> weight
    ) -> ConsensusResult: ...


# ── Helpers ────────────────────────────────────────────────────────────────────

def _vote_counts(positions: List[DebatePosition]) -> FrozenSet[Tuple[str, int]]:
    return frozenset(Counter(p.position_type.value for p in positions).items())


def _decisive(positions: List[DebatePosition]) -> List[DebatePosition]:
    return [p for p in positions if p.position_type.is_decisive()]


# ── MajorityVote ──────────────────────────────────────────────────────────────

class MajorityVoteStrategy(ConsensusStrategy):
    """Simple majority: the position with > 50% of decisive votes wins."""

    name = "majority"

    def calculate(
        self,
        session_id: str,
        positions:  List[DebatePosition],
        weights:    Dict[str, float],
    ) -> ConsensusResult:
        decisive = _decisive(positions)
        counts   = Counter(p.position_type.value for p in decisive)
        vc       = _vote_counts(positions)

        if not decisive:
            return ConsensusResult.failed(
                session_id    = session_id,
                outcome       = ConsensusOutcome.INSUFFICIENT_VOTES,
                vote_counts   = vc,
                total_votes   = 0,
                strategy_used = self.name,
            )

        total   = len(decisive)
        top_val, top_count = max(counts.items(), key=lambda x: x[1])

        # Check for a tie between top positions
        top_vals = [v for v, c in counts.items() if c == top_count]
        tiebreak = len(top_vals) > 1

        if top_count / total > 0.5:
            conf = sum(p.confidence for p in decisive if p.position_type.value == top_val) / top_count
            return ConsensusResult.majority(
                session_id         = session_id,
                winning_position   = top_val,
                vote_counts        = vc,
                total_votes        = total,
                confidence         = conf,
                strategy_used      = self.name,
                tiebreaker_applied = tiebreak,
            )
        return ConsensusResult.failed(
            session_id    = session_id,
            outcome       = ConsensusOutcome.TIE if tiebreak else ConsensusOutcome.FAILED,
            vote_counts   = vc,
            total_votes   = total,
            strategy_used = self.name,
        )


# ── WeightedVote ──────────────────────────────────────────────────────────────

class WeightedVoteStrategy(ConsensusStrategy):
    """Weighted majority: sum of agent weights > 50% decides."""

    name = "weighted"

    def calculate(
        self,
        session_id: str,
        positions:  List[DebatePosition],
        weights:    Dict[str, float],
    ) -> ConsensusResult:
        decisive = _decisive(positions)
        vc       = _vote_counts(positions)

        if not decisive:
            return ConsensusResult.failed(
                session_id    = session_id,
                outcome       = ConsensusOutcome.INSUFFICIENT_VOTES,
                vote_counts   = vc,
                total_votes   = 0,
                strategy_used = self.name,
            )

        wt: Dict[str, float] = {}
        for p in decisive:
            w = weights.get(p.agent_id, 1.0)
            wt[p.position_type.value] = wt.get(p.position_type.value, 0.0) + w

        total_w = sum(wt.values())
        top_val, top_w = max(wt.items(), key=lambda x: x[1])
        wt_fset = frozenset((k, round(v, 6)) for k, v in wt.items())

        if total_w and top_w / total_w > 0.5:
            dom  = [p for p in decisive if p.position_type.value == top_val]
            conf = sum(p.confidence for p in dom) / len(dom)
            return ConsensusResult.majority(
                session_id       = session_id,
                winning_position = top_val,
                vote_counts      = vc,
                total_votes      = len(decisive),
                confidence       = conf,
                strategy_used    = self.name,
                weight_totals    = wt_fset,
            )
        return ConsensusResult.failed(
            session_id    = session_id,
            outcome       = ConsensusOutcome.TIE,
            vote_counts   = vc,
            total_votes   = len(decisive),
            strategy_used = self.name,
            weight_totals = wt_fset,
        )


# ── Unanimous ─────────────────────────────────────────────────────────────────

class UnanimousStrategy(ConsensusStrategy):
    """All decisive votes must agree for consensus to be reached."""

    name = "unanimous"

    def calculate(
        self,
        session_id: str,
        positions:  List[DebatePosition],
        weights:    Dict[str, float],
    ) -> ConsensusResult:
        decisive = _decisive(positions)
        vc       = _vote_counts(positions)

        if not decisive:
            return ConsensusResult.failed(
                session_id    = session_id,
                outcome       = ConsensusOutcome.INSUFFICIENT_VOTES,
                vote_counts   = vc,
                total_votes   = 0,
                strategy_used = self.name,
            )

        types = {p.position_type.value for p in decisive}
        if len(types) == 1:
            winner = types.pop()
            conf   = sum(p.confidence for p in decisive) / len(decisive)
            return ConsensusResult.reached(
                session_id       = session_id,
                winning_position = winner,
                vote_counts      = vc,
                total_votes      = len(decisive),
                confidence       = conf,
                strategy_used    = self.name,
            )
        return ConsensusResult.failed(
            session_id    = session_id,
            outcome       = ConsensusOutcome.FAILED,
            vote_counts   = vc,
            total_votes   = len(decisive),
            strategy_used = self.name,
        )


# ── ConfidenceThreshold ────────────────────────────────────────────────────────

class ConfidenceThresholdStrategy(ConsensusStrategy):
    """
    Majority vote where the winner's mean confidence must reach *threshold*.

    Default threshold is 0.7.
    """

    def __init__(self, threshold: float = 0.7) -> None:
        self._threshold = max(0.0, min(1.0, threshold))

    @property
    def name(self) -> str:
        return f"confidence_threshold_{self._threshold:.2f}"

    def calculate(
        self,
        session_id: str,
        positions:  List[DebatePosition],
        weights:    Dict[str, float],
    ) -> ConsensusResult:
        decisive = _decisive(positions)
        vc       = _vote_counts(positions)

        if not decisive:
            return ConsensusResult.failed(
                session_id    = session_id,
                outcome       = ConsensusOutcome.INSUFFICIENT_VOTES,
                vote_counts   = vc,
                total_votes   = 0,
                strategy_used = self.name,
            )

        total   = len(decisive)
        counts  = Counter(p.position_type.value for p in decisive)
        top_val, top_count = max(counts.items(), key=lambda x: x[1])

        if top_count / total <= 0.5:
            return ConsensusResult.failed(
                session_id    = session_id,
                outcome       = ConsensusOutcome.TIE,
                vote_counts   = vc,
                total_votes   = total,
                strategy_used = self.name,
            )

        dom  = [p for p in decisive if p.position_type.value == top_val]
        conf = sum(p.confidence for p in dom) / len(dom)

        if conf >= self._threshold:
            return ConsensusResult.majority(
                session_id       = session_id,
                winning_position = top_val,
                vote_counts      = vc,
                total_votes      = total,
                confidence       = conf,
                strategy_used    = self.name,
            )
        return ConsensusResult.failed(
            session_id    = session_id,
            outcome       = ConsensusOutcome.THRESHOLD_NOT_MET,
            vote_counts   = vc,
            total_votes   = total,
            strategy_used = self.name,
        )
