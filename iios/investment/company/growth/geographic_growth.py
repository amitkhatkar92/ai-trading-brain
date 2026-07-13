"""iios/investment/company/growth/geographic_growth.py
Geographic growth profile.
Without explicit geographic segment data, models contribution estimates
from available signals.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class GeographicGrowthProfile:
    """Geographic revenue growth contribution estimates."""
    has_geo_data:         bool = False
    international_pct:    Optional[float] = None   # 0-1; fraction of revenue from outside home market
    geo_diversification:  float = 0.0              # 0-100
    dominant_region:      Optional[str] = None
    explanation:          List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "has_geo_data":        self.has_geo_data,
            "international_pct":   self.international_pct,
            "geo_diversification": round(self.geo_diversification, 1),
            "dominant_region":     self.dominant_region,
            "explanation":         self.explanation,
        }


class GeographicGrowthAnalyzer:
    """
    Estimates geographic growth contribution.
    Without explicit geo-segment data from upstream snapshots, returns
    a profile with best available approximations from sector/industry context.
    """

    def compute(
        self,
        sector:   Optional[str] = None,
        industry: Optional[str] = None,
    ) -> GeographicGrowthProfile:
        profile = GeographicGrowthProfile()
        explanation: List[str] = []

        # Heuristic: some sectors are inherently domestic vs global
        global_sectors = {"technology", "pharmaceutical", "energy", "materials", "financials"}
        domestic_sectors = {"real estate", "utilities", "retail"}

        sl = (sector or "").lower()
        if any(s in sl for s in global_sectors):
            profile.geo_diversification = 60.0
            profile.dominant_region     = "global"
            explanation.append("Sector typically has significant international exposure")
        elif any(s in sl for s in domestic_sectors):
            profile.geo_diversification = 20.0
            profile.dominant_region     = "domestic"
            explanation.append("Sector typically has limited international exposure")
        else:
            profile.geo_diversification = 40.0
            explanation.append("Geographic diversification unknown; using neutral estimate")

        explanation.append("Geographic segment data not available from upstream snapshots")
        profile.explanation = explanation
        return profile
