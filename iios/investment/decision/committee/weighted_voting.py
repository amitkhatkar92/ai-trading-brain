"""iios/investment/decision/committee/weighted_voting.py
WeightedVoting — aggregates vote weights into VoteSummary + ConsensusLevel.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from iios.investment.decision.committee.committee_constants import (
    ConsensusLevel,
    VoteType,
)
from iios.investment.decision.committee.vote_registry import CastVote


@dataclass(frozen=True)
class VoteSummary:
    total_votes:       int
    support_count:     int
    oppose_count:      int
    abstain_count:     int
    support_weight:    float
    oppose_weight:     float
    abstain_weight:    float
    total_weight:      float          # all weights (including abstain)
    decisive_weight:   float          # support + oppose only (abstains excluded)
    support_fraction:  float          # support / (support + oppose)
    consensus_level:   ConsensusLevel
    avg_support_confidence: float     # mean confidence of support voters
    avg_oppose_confidence:  float     # mean confidence of oppose voters

    @property
    def is_majority_support(self) -> bool:
        return self.support_fraction > 0.50

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_votes":           self.total_votes,
            "support_count":         self.support_count,
            "oppose_count":          self.oppose_count,
            "abstain_count":         self.abstain_count,
            "support_weight":        round(self.support_weight, 4),
            "oppose_weight":         round(self.oppose_weight, 4),
            "abstain_weight":        round(self.abstain_weight, 4),
            "decisive_weight":       round(self.decisive_weight, 4),
            "support_fraction":      round(self.support_fraction, 4),
            "consensus_level":       self.consensus_level.value,
            "avg_support_confidence":round(self.avg_support_confidence, 2),
            "avg_oppose_confidence": round(self.avg_oppose_confidence, 2),
        }


class WeightedVoting:
    """Stateless aggregator — converts a list of CastVotes into a VoteSummary."""

    def tally(self, votes: List[CastVote]) -> VoteSummary:
        support = [v for v in votes if v.vote == VoteType.SUPPORT]
        oppose  = [v for v in votes if v.vote == VoteType.OPPOSE]
        abstain = [v for v in votes if v.vote == VoteType.ABSTAIN]

        sw = sum(v.weight for v in support)
        ow = sum(v.weight for v in oppose)
        aw = sum(v.weight for v in abstain)
        dw = sw + ow  # decisive weight (excludes abstains)

        fraction = sw / dw if dw > 0.0 else 0.0

        avg_sc = (sum(v.confidence for v in support) / len(support)) if support else 0.0
        avg_oc = (sum(v.confidence for v in oppose) / len(oppose))   if oppose  else 0.0

        return VoteSummary(
            total_votes            = len(votes),
            support_count          = len(support),
            oppose_count           = len(oppose),
            abstain_count          = len(abstain),
            support_weight         = round(sw, 4),
            oppose_weight          = round(ow, 4),
            abstain_weight         = round(aw, 4),
            total_weight           = round(sw + ow + aw, 4),
            decisive_weight        = round(dw, 4),
            support_fraction       = round(fraction, 4),
            consensus_level        = ConsensusLevel.from_fraction(fraction),
            avg_support_confidence = round(avg_sc, 2),
            avg_oppose_confidence  = round(avg_oc, 2),
        )
