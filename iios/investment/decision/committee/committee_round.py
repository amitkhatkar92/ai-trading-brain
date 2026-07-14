"""iios/investment/decision/committee/committee_round.py
CommitteeRound — tracks the inputs/outputs of one deliberation round.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from iios.investment.decision.committee.committee_constants import RoundType
from iios.investment.decision.committee.committee_member import MemberOpinion


@dataclass(frozen=True)
class RoundResult:
    """Immutable summary of one round of deliberation."""
    round_number:   int
    round_type:     RoundType
    opinions:       Tuple[MemberOpinion, ...]
    challenge_count: int
    resolved_count: int
    duration_ms:    float

    @property
    def support_count(self) -> int:
        from iios.investment.decision.committee.committee_constants import VoteType
        return sum(1 for o in self.opinions if o.effective_vote == VoteType.SUPPORT)

    @property
    def oppose_count(self) -> int:
        from iios.investment.decision.committee.committee_constants import VoteType
        return sum(1 for o in self.opinions if o.effective_vote == VoteType.OPPOSE)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "round_number":   self.round_number,
            "round_type":     self.round_type.value,
            "opinions_count": len(self.opinions),
            "support_count":  self.support_count,
            "oppose_count":   self.oppose_count,
            "challenge_count":self.challenge_count,
            "resolved_count": self.resolved_count,
            "duration_ms":    round(self.duration_ms, 2),
        }
