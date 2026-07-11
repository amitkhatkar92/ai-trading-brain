"""iios/investment/market/opportunity/opportunity_profile.py
Extended per-opportunity profile with rolling history of key metrics.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from iios.investment.market.opportunity.models import (
    Opportunity,
    OpportunityCategory,
    OpportunityLifecycleStage,
)


@dataclass
class OpportunityProfile:
    """Historical view of a single opportunity — stored per opportunity_id."""
    opportunity_id:  str
    symbol:          str
    sector:          str
    industry:        str
    primary_category: OpportunityCategory
    score_history:   deque = field(default_factory=lambda: deque(maxlen=60))
    conf_history:    deque = field(default_factory=lambda: deque(maxlen=60))
    stage_history:   deque = field(default_factory=lambda: deque(maxlen=60))

    def record(self, opp: Opportunity) -> None:
        self.score_history.append(opp.composite_score)
        self.conf_history.append(opp.confidence)
        self.stage_history.append(opp.lifecycle_stage.value)

    def avg_score(self, n: int = 5) -> float:
        tail = list(self.score_history)[-n:]
        return sum(tail) / len(tail) if tail else 0.0

    def score_trend(self, n: int = 5) -> float:
        """Positive = score improving; negative = declining."""
        tail = list(self.score_history)[-n:]
        if len(tail) < 2:
            return 0.0
        return (tail[-1] - tail[0]) / len(tail)

    def peak_score(self) -> float:
        return max(self.score_history) if self.score_history else 0.0

    def to_dict(self) -> Dict:
        return {
            "opportunity_id":  self.opportunity_id,
            "symbol":          self.symbol,
            "primary_category": self.primary_category.value,
            "avg_score_5bar":  round(self.avg_score(5), 2),
            "score_trend":     round(self.score_trend(5), 3),
            "peak_score":      round(self.peak_score(), 2),
        }


class ProfileStore:
    """Maintains :class:`OpportunityProfile` per opportunity."""

    def __init__(self) -> None:
        self._profiles: Dict[str, OpportunityProfile] = {}  # opp_id → profile

    def record(self, opp: Opportunity) -> None:
        if opp.opportunity_id not in self._profiles:
            self._profiles[opp.opportunity_id] = OpportunityProfile(
                opportunity_id=opp.opportunity_id,
                symbol=opp.symbol,
                sector=opp.sector,
                industry=opp.industry,
                primary_category=opp.primary_category,
            )
        self._profiles[opp.opportunity_id].record(opp)

    def get(self, opportunity_id: str) -> Optional[OpportunityProfile]:
        return self._profiles.get(opportunity_id)

    def record_batch(self, opportunities: List[Opportunity]) -> None:
        for opp in opportunities:
            self.record(opp)

    def count(self) -> int:
        return len(self._profiles)
