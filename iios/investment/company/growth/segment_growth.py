"""iios/investment/company/growth/segment_growth.py
Segment-level growth profile.
Without segment-level financial data from upstream snapshots, this module
models contribution estimates based on margin and quality signals.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class SegmentGrowthProfile:
    """Growth contribution estimates by business segment."""
    segments:               Dict[str, float] = field(default_factory=dict)
    has_segment_data:       bool = False
    dominant_segment:       Optional[str] = None
    diversification_score:  float = 0.0   # 0-100; higher = more diversified
    explanation:            List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "has_segment_data":      self.has_segment_data,
            "dominant_segment":      self.dominant_segment,
            "diversification_score": round(self.diversification_score, 1),
            "explanation":           self.explanation,
        }


class SegmentGrowthAnalyzer:
    """
    Estimates segment growth contribution.
    Without explicit segment data, returns a placeholder profile
    indicating single-segment or diversified based on industry signals.
    """

    def compute(
        self,
        sector:             Optional[str] = None,
        industry:           Optional[str] = None,
        operational_score:  Optional[float] = None,   # 0-100
    ) -> SegmentGrowthProfile:
        profile = SegmentGrowthProfile()
        explanation: List[str] = []

        # Without explicit segment data, estimate diversification from sector
        if sector:
            conglomerates = {"conglomerate", "holding", "diversified"}
            if any(c in (sector or "").lower() for c in conglomerates):
                profile.diversification_score = 70.0
                explanation.append("Sector suggests diversified business model")
            else:
                profile.diversification_score = 30.0
                explanation.append("Sector suggests focused business model")

        explanation.append("Segment-level data not available from upstream snapshots")
        profile.explanation = explanation
        return profile
