"""iios/investment/strategy/opportunity/strategy_ranking.py
StrategyRanking — the output of the ranking step:
a snapshot of ordered strategy recommendations for an opportunity.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.strategy.opportunity.ranking_score import RankingScore
from iios.investment.strategy.opportunity.strategy_opportunity import StrategyOpportunity


@dataclass(frozen=True)
class RankedOpportunity:
    """A strategy opportunity with its RankingScore, ready for downstream consumption."""
    opportunity:   StrategyOpportunity
    ranking_score: RankingScore

    @property
    def rank(self) -> int:
        return self.ranking_score.rank

    @property
    def strategy_id(self) -> str:
        return self.opportunity.strategy_id

    @property
    def overall_score(self) -> float:
        return self.ranking_score.overall_score

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rank":            self.rank,
            "opportunity":     self.opportunity.to_dict(),
            "ranking_score":   self.ranking_score.to_dict(),
        }


@dataclass(frozen=True)
class StrategyRanking:
    """
    Ordered list of the best strategy opportunities for a single incoming
    market or company opportunity, produced by the RankingEngine.
    """
    source_opportunity_id: str
    ranked_at:             datetime
    total_candidates:      int
    total_matched:         int
    total_suitable:        int
    entries:               List[RankedOpportunity] = field(default_factory=list)
    metadata:              Dict[str, Any] = field(default_factory=dict)

    @property
    def top(self) -> Optional[RankedOpportunity]:
        return self.entries[0] if self.entries else None

    def top_n(self, n: int) -> List[RankedOpportunity]:
        return self.entries[:n]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_opportunity_id": self.source_opportunity_id,
            "ranked_at":             self.ranked_at.isoformat(),
            "total_candidates":      self.total_candidates,
            "total_matched":         self.total_matched,
            "total_suitable":        self.total_suitable,
            "entries":               [e.to_dict() for e in self.entries],
        }
