"""iios/investment/decision/committee/vote_registry.py
VoteRegistry — records all votes cast in one session.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from iios.investment.decision.committee.committee_constants import VoteType
from iios.investment.decision.committee.committee_member import MemberOpinion


@dataclass(frozen=True)
class CastVote:
    member_id:       str
    weight:          float
    vote:            VoteType
    confidence:      float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "member_id":  self.member_id,
            "weight":     round(self.weight, 4),
            "vote":       self.vote.value,
            "confidence": round(self.confidence, 2),
        }


class VoteRegistry:
    """Thread-safe store of all votes for one session."""

    def __init__(self) -> None:
        self._lock  = threading.RLock()
        self._votes: Dict[str, CastVote] = {}

    def cast(self, member_id: str, weight: float, vote: VoteType, confidence: float) -> None:
        with self._lock:
            self._votes[member_id] = CastVote(member_id, weight, vote, confidence)

    def cast_from_opinion(self, opinion: MemberOpinion, weight: float) -> None:
        self.cast(opinion.member_id, weight, opinion.effective_vote, opinion.effective_confidence)

    def get(self, member_id: str) -> Optional[CastVote]:
        with self._lock:
            return self._votes.get(member_id)

    def all_votes(self) -> List[CastVote]:
        with self._lock:
            return list(self._votes.values())

    def count(self) -> int:
        with self._lock:
            return len(self._votes)

    def clear(self) -> None:
        with self._lock:
            self._votes.clear()
