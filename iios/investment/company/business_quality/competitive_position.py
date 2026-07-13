"""iios/investment/company/business_quality/competitive_position.py
Competitive position, market position, and peer comparison profiles.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class MarketLeadershipLabel(Enum):
    LEADER      = "leader"       # Top 3 in market by financial metrics
    CHALLENGER  = "challenger"   # Strong #2-5 position
    FOLLOWER    = "follower"     # Below average in peer group
    NICHE       = "niche"        # Specialised segment leader
    UNKNOWN     = "unknown"


class CompetitivePressureLabel(Enum):
    LOW      = "low"      # Protected, high barriers
    MODERATE = "moderate" # Normal competitive dynamics
    HIGH     = "high"     # Intense competition, commoditised
    UNKNOWN  = "unknown"


@dataclass
class PeerMetric:
    """Relative standing of one metric vs peer group."""
    field_name:     str
    own_value:      Optional[float]
    peer_median:    Optional[float]
    percentile:     Optional[float]   # 0-100; where own sits in peer distribution
    vs_median_pct:  Optional[float]   # (own - peer_median) / |peer_median|

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field":        self.field_name,
            "own":          self.own_value,
            "peer_median":  self.peer_median,
            "percentile":   self.percentile,
            "vs_median_pct": self.vs_median_pct,
        }


@dataclass
class PeerComparisonProfile:
    """
    Comparison of this company against a peer group.
    Populated when peer snapshots are provided to the engine.
    """
    peer_count:         int = 0
    peer_tickers:       List[str] = field(default_factory=list)

    # Metric comparisons
    metrics:            List[PeerMetric] = field(default_factory=list)

    # Summary rankings (percentile within peer group)
    profitability_rank: Optional[float] = None  # 0-100 percentile
    efficiency_rank:    Optional[float] = None
    growth_rank:        Optional[float] = None
    quality_rank:       Optional[float] = None

    # Overall competitive score vs peers (0-100)
    competitive_score_vs_peers: float = 50.0

    flags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "peer_count":                   self.peer_count,
            "peer_tickers":                 self.peer_tickers,
            "profitability_rank":           self.profitability_rank,
            "efficiency_rank":              self.efficiency_rank,
            "growth_rank":                  self.growth_rank,
            "quality_rank":                 self.quality_rank,
            "competitive_score_vs_peers":   round(self.competitive_score_vs_peers, 1),
            "metrics":                      [m.to_dict() for m in self.metrics],
            "flags":                        self.flags,
        }


@dataclass
class MarketPositionProfile:
    """
    Absolute market position inferred from financial signals.
    (No real-time market share data; all from financial ratios.)
    """
    leadership:         MarketLeadershipLabel = MarketLeadershipLabel.UNKNOWN
    competitive_pressure: CompetitivePressureLabel = CompetitivePressureLabel.UNKNOWN

    # Absolute quality signals
    is_premium_margins:     bool = False   # Gross margin > 50%
    is_high_roic:           bool = False   # ROIC > 15%
    is_market_share_gainer: bool = False   # Revenue growing faster than industry proxy

    market_position_score: float = 50.0    # 0-100

    flags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "leadership":              self.leadership.value,
            "competitive_pressure":    self.competitive_pressure.value,
            "is_premium_margins":      self.is_premium_margins,
            "is_high_roic":            self.is_high_roic,
            "is_market_share_gainer":  self.is_market_share_gainer,
            "market_position_score":   round(self.market_position_score, 1),
            "flags":                   self.flags,
        }


@dataclass
class CompetitiveIntelligenceProfile:
    """Composite competitive intelligence."""

    market_position: MarketPositionProfile = field(default_factory=MarketPositionProfile)
    peer_comparison: PeerComparisonProfile = field(default_factory=PeerComparisonProfile)

    # Consolidated competitive score
    competitive_intelligence_score: float = 0.0   # 0-100

    flags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "market_position":              self.market_position.to_dict(),
            "peer_comparison":              self.peer_comparison.to_dict(),
            "competitive_intelligence_score": round(self.competitive_intelligence_score, 1),
            "flags":                        self.flags,
        }
