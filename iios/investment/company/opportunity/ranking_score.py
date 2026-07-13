"""iios/investment/company/opportunity/ranking_score.py
RankingScore and RankingResult dataclasses for the Ranking Engine.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

from iios.investment.company.opportunity.opportunity_profile import OpportunityStrength


@dataclass
class RankingScore:
    """Composite score used for ranking a company against peers."""
    ticker:         str
    overall:        float         # 0-100, primary sort key
    strength:       OpportunityStrength
    sector:         Optional[str] = None
    industry:       Optional[str] = None
    computed_at:    Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker":      self.ticker,
            "overall":     round(self.overall, 2),
            "strength":    self.strength.value,
            "sector":      self.sector,
            "industry":    self.industry,
            "computed_at": self.computed_at.isoformat() if self.computed_at else None,
        }


@dataclass
class RankingResult:
    """Ranking position of a single ticker within a population."""
    ticker:          str
    global_rank:     Optional[int] = None    # 1-based, None if not yet ranked
    sector_rank:     Optional[int] = None
    industry_rank:   Optional[int] = None
    score:           float = 0.0
    population_size: int   = 0              # total companies in global ranking

    @property
    def global_percentile(self) -> Optional[float]:
        """0-100 percentile; 100 = top-ranked."""
        if self.global_rank is None or self.population_size <= 0:
            return None
        return (1 - (self.global_rank - 1) / self.population_size) * 100

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker":           self.ticker,
            "global_rank":      self.global_rank,
            "sector_rank":      self.sector_rank,
            "industry_rank":    self.industry_rank,
            "score":            round(self.score, 2),
            "population_size":  self.population_size,
            "global_percentile": (
                round(self.global_percentile, 1) if self.global_percentile is not None else None
            ),
        }


@dataclass
class RankingChange:
    """Records a rank movement for a ticker."""
    ticker:       str
    from_rank:    Optional[int]
    to_rank:      Optional[int]
    score_change: float
    changed_at:   datetime

    @property
    def rank_delta(self) -> Optional[int]:
        if self.from_rank is None or self.to_rank is None:
            return None
        return self.from_rank - self.to_rank  # positive = moved up

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker":       self.ticker,
            "from_rank":    self.from_rank,
            "to_rank":      self.to_rank,
            "rank_delta":   self.rank_delta,
            "score_change": round(self.score_change, 2),
            "changed_at":   self.changed_at.isoformat(),
        }
