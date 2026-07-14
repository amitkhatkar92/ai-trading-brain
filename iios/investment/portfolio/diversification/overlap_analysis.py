"""iios/investment/portfolio/diversification/overlap_analysis.py

Measures how much positions overlap in their sector/industry/asset-class
exposure — an indicator of hidden concentration.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from iios.investment.portfolio.diversification.diversification_types import PositionData


@dataclass(frozen=True)
class OverlapResult:
    """Overlap scores across exposure dimensions."""

    sector_overlap:      float = 0.0   # fraction of weight pairs sharing same sector
    industry_overlap:    float = 0.0   # fraction of weight pairs sharing same industry
    asset_class_overlap: float = 0.0   # fraction of weight pairs sharing same asset class
    country_overlap:     float = 0.0   # fraction of weight pairs sharing same country
    thematic_overlap:    float = 0.0   # average of sector + industry overlap
    overlap_risk:        str   = "low"  # "low" | "moderate" | "high"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sector_overlap":      round(self.sector_overlap, 4),
            "industry_overlap":    round(self.industry_overlap, 4),
            "asset_class_overlap": round(self.asset_class_overlap, 4),
            "country_overlap":     round(self.country_overlap, 4),
            "thematic_overlap":    round(self.thematic_overlap, 4),
            "overlap_risk":        self.overlap_risk,
        }


def _pairwise_overlap(positions: List[PositionData], key: str) -> float:
    """
    Weight-adjusted fraction of position pairs sharing the same value for `key`.
    = Σ_i Σ_{j≠i} w_i w_j * 1[key_i == key_j]
    = Σ_bucket (Σ_i_in_bucket w_i)² - Σ_i w_i²
    = HHI_bucket - HHI_position
    """
    if not positions or len(positions) < 2:
        return 0.0
    buckets: Dict[str, float] = {}
    for p in positions:
        k = getattr(p, key, "unknown")
        buckets[k] = buckets.get(k, 0.0) + p.weight
    hhi_bucket   = sum(v * v for v in buckets.values())
    hhi_position = sum(p.weight * p.weight for p in positions)
    # normalised into [0, 1]: 0 = no overlap, 1 = total overlap
    overlap = max(0.0, hhi_bucket - hhi_position) / max(1.0 - hhi_position, 1e-10)
    return min(1.0, overlap)


def analyze_overlap(positions: List[PositionData]) -> OverlapResult:
    if not positions:
        return OverlapResult()

    sec_ov  = _pairwise_overlap(positions, "sector")
    ind_ov  = _pairwise_overlap(positions, "industry")
    ac_ov   = _pairwise_overlap(positions, "asset_class")
    cty_ov  = _pairwise_overlap(positions, "country")
    them_ov = (sec_ov + ind_ov) / 2.0

    if them_ov >= 0.60:
        risk = "high"
    elif them_ov >= 0.35:
        risk = "moderate"
    else:
        risk = "low"

    return OverlapResult(
        sector_overlap      = round(sec_ov, 4),
        industry_overlap    = round(ind_ov, 4),
        asset_class_overlap = round(ac_ov, 4),
        country_overlap     = round(cty_ov, 4),
        thematic_overlap    = round(them_ov, 4),
        overlap_risk        = risk,
    )
