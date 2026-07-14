"""iios/investment/strategy/debate/voting_engine.py
Vote, VotingResult, and VotingEngine.
"""
from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.strategy.debate.debate_constants import (
    ParticipantRole,
    VotingMechanism,
    VoteOutcome,
)
from iios.investment.strategy.debate.participant_profile import ParticipantProfile


@dataclass(frozen=True)
class Vote:
    vote_id:        str
    session_id:     str
    participant_id: str
    role:           ParticipantRole
    outcome:        VoteOutcome
    confidence:     float          # 0–100
    rationale:      str
    weight:         float
    submitted_at:   datetime
    evidence_ids:   Tuple[str, ...] = ()
    metadata:       Dict[str, Any]  = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "vote_id":        self.vote_id,
            "session_id":     self.session_id,
            "participant_id": self.participant_id,
            "role":           self.role.value,
            "outcome":        self.outcome.value,
            "confidence":     round(self.confidence, 2),
            "rationale":      self.rationale,
            "weight":         round(self.weight, 4),
            "submitted_at":   self.submitted_at.isoformat(),
        }


def make_vote(
    session_id:     str,
    participant_id: str,
    role:           ParticipantRole,
    outcome:        VoteOutcome,
    confidence:     float,
    rationale:      str,
    weight:         float = 1.0,
    evidence_ids:   Optional[List[str]] = None,
) -> Vote:
    return Vote(
        vote_id=str(uuid.uuid4()),
        session_id=session_id,
        participant_id=participant_id,
        role=role,
        outcome=outcome,
        confidence=min(max(confidence, 0.0), 100.0),
        rationale=rationale,
        weight=max(weight, 0.0),
        submitted_at=datetime.now(timezone.utc),
        evidence_ids=tuple(evidence_ids or []),
    )


@dataclass(frozen=True)
class VotingResult:
    session_id:      str
    mechanism:       VotingMechanism
    total_votes:     int
    abstentions:     int
    weighted_score:  float          # sum of weight × numeric_value
    normalised_score: float         # -1.0 to +1.0
    winning_outcome: VoteOutcome
    vote_counts:     Dict[str, int] # outcome.value → count
    quorum_met:      bool
    computed_at:     datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id":       self.session_id,
            "mechanism":        self.mechanism.value,
            "total_votes":      self.total_votes,
            "abstentions":      self.abstentions,
            "weighted_score":   round(self.weighted_score, 4),
            "normalised_score": round(self.normalised_score, 4),
            "winning_outcome":  self.winning_outcome.value,
            "vote_counts":      self.vote_counts,
            "quorum_met":       self.quorum_met,
            "computed_at":      self.computed_at.isoformat(),
        }


class VotingEngine:
    """
    Computes a VotingResult from a list of Votes using the specified mechanism.
    Pure functional — no internal state.
    """

    def compute(
        self,
        votes:       List[Vote],
        profiles:    List[ParticipantProfile],
        mechanism:   VotingMechanism = VotingMechanism.WEIGHTED_MAJORITY,
        session_id:  str             = "",
        min_quorum:  int             = 3,
    ) -> VotingResult:
        if not votes:
            return self._empty_result(session_id, mechanism, min_quorum)

        profile_map = {p.participant_id: p for p in profiles}
        active      = [v for v in votes if not v.outcome.is_abstain]
        abstentions = len(votes) - len(active)
        quorum_met  = len(active) >= min_quorum

        # Vote counts (including abstentions)
        counts: Dict[str, int] = {}
        for v in votes:
            counts[v.outcome.value] = counts.get(v.outcome.value, 0) + 1

        if not active:
            return self._empty_result(session_id, mechanism, min_quorum)

        if mechanism == VotingMechanism.SIMPLE_MAJORITY:
            winner, w_score, norm = self._simple_majority(active)
        elif mechanism == VotingMechanism.SUPERMAJORITY:
            winner, w_score, norm = self._supermajority(active)
        elif mechanism == VotingMechanism.UNANIMOUS:
            winner, w_score, norm = self._unanimous(active)
        elif mechanism == VotingMechanism.RANKED_CHOICE:
            winner, w_score, norm = self._ranked_choice(active)
        else:  # WEIGHTED_MAJORITY (default)
            winner, w_score, norm = self._weighted_majority(active, profile_map)

        return VotingResult(
            session_id=session_id,
            mechanism=mechanism,
            total_votes=len(votes),
            abstentions=abstentions,
            weighted_score=round(w_score, 4),
            normalised_score=round(norm, 4),
            winning_outcome=winner,
            vote_counts=counts,
            quorum_met=quorum_met,
            computed_at=datetime.now(timezone.utc),
        )

    # ── Mechanisms ─────────────────────────────────────────────────────────────

    @staticmethod
    def _weighted_majority(
        active:      List[Vote],
        profile_map: Dict[str, ParticipantProfile],
    ) -> Tuple[VoteOutcome, float, float]:
        total_weight = sum(
            profile_map[v.participant_id].weight
            if v.participant_id in profile_map else v.weight
            for v in active
        )
        if total_weight == 0:
            return VoteOutcome.NEUTRAL, 0.0, 0.0
        weighted_sum = sum(
            v.outcome.numeric_value * (
                profile_map[v.participant_id].weight
                if v.participant_id in profile_map else v.weight
            )
            for v in active
        )
        norm = weighted_sum / (total_weight * 2.0)  # -1 to +1
        return _outcome_from_norm(norm), round(weighted_sum, 4), round(norm, 4)

    @staticmethod
    def _simple_majority(active: List[Vote]) -> Tuple[VoteOutcome, float, float]:
        total   = len(active)
        raw_sum = sum(v.outcome.numeric_value for v in active)
        norm    = raw_sum / (total * 2.0)
        return _outcome_from_norm(norm), round(raw_sum, 4), round(norm, 4)

    @staticmethod
    def _supermajority(active: List[Vote]) -> Tuple[VoteOutcome, float, float]:
        pos = sum(1 for v in active if v.outcome.is_positive)
        neg = sum(1 for v in active if not v.outcome.is_positive)
        total = len(active)
        if pos / total >= 2 / 3:
            return VoteOutcome.SUPPORT, float(pos), pos / total
        if neg / total >= 2 / 3:
            return VoteOutcome.OPPOSE, float(-neg), -(neg / total)
        return VoteOutcome.NEUTRAL, 0.0, 0.0

    @staticmethod
    def _unanimous(active: List[Vote]) -> Tuple[VoteOutcome, float, float]:
        outcomes = {v.outcome for v in active}
        if len(outcomes) == 1:
            o = next(iter(outcomes))
            return o, float(len(active)) * o.numeric_value, o.numeric_value / 2.0
        return VoteOutcome.NEUTRAL, 0.0, 0.0

    @staticmethod
    def _ranked_choice(active: List[Vote]) -> Tuple[VoteOutcome, float, float]:
        # Simple version: count first preferences
        tally: Dict[VoteOutcome, int] = {}
        for v in active:
            tally[v.outcome] = tally.get(v.outcome, 0) + 1
        winner = max(tally, key=lambda o: tally[o])
        raw_sum = sum(v.outcome.numeric_value for v in active)
        norm    = raw_sum / (len(active) * 2.0)
        return winner, round(raw_sum, 4), round(norm, 4)

    @staticmethod
    def _empty_result(
        session_id: str,
        mechanism:  VotingMechanism,
        min_quorum: int,
    ) -> VotingResult:
        return VotingResult(
            session_id=session_id,
            mechanism=mechanism,
            total_votes=0,
            abstentions=0,
            weighted_score=0.0,
            normalised_score=0.0,
            winning_outcome=VoteOutcome.NEUTRAL,
            vote_counts={},
            quorum_met=False,
            computed_at=datetime.now(timezone.utc),
        )


def _outcome_from_norm(norm: float) -> VoteOutcome:
    if norm >= 0.6:
        return VoteOutcome.STRONG_SUPPORT
    if norm >= 0.2:
        return VoteOutcome.SUPPORT
    if norm <= -0.6:
        return VoteOutcome.STRONG_OPPOSE
    if norm <= -0.2:
        return VoteOutcome.OPPOSE
    return VoteOutcome.NEUTRAL
