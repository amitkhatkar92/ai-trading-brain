"""iios/investment/portfolio/diversification/dependency_analysis.py

Systemic dependency and hidden-exposure analysis using sector/industry
clustering.  Pure-Python proxy analysis — no market data required.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from iios.investment.portfolio.diversification.diversification_types import (
    PositionData,
    compute_hhi,
)


@dataclass(frozen=True)
class DependencyCluster:
    """A group of correlated positions sharing sector/industry exposure."""

    cluster_id:    str                 = ""
    dimension:     str                 = "sector"   # "sector" or "industry"
    bucket_name:   str                 = ""
    symbols:       Tuple[str, ...]     = field(default_factory=tuple)
    total_weight:  float               = 0.0
    n_positions:   int                 = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cluster_id":   self.cluster_id,
            "dimension":    self.dimension,
            "bucket_name":  self.bucket_name,
            "symbols":      list(self.symbols),
            "total_weight": round(self.total_weight, 4),
            "n_positions":  self.n_positions,
        }


@dataclass(frozen=True)
class DependencyAnalysisResult:
    """Systemic exposure and dependency summary."""

    sector_clusters:       Tuple[DependencyCluster, ...] = field(default_factory=tuple)
    industry_clusters:     Tuple[DependencyCluster, ...] = field(default_factory=tuple)
    max_sector_cluster_weight:   float = 0.0
    max_industry_cluster_weight: float = 0.0
    n_sector_clusters:     int   = 0
    n_industry_clusters:   int   = 0
    systemic_exposure_score: float = 0.0  # 0 = independent, 1 = fully systemic
    hidden_dependency_count: int  = 0     # cross-sector pairs sharing same industry

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_sector_cluster_weight":   round(self.max_sector_cluster_weight, 4),
            "max_industry_cluster_weight": round(self.max_industry_cluster_weight, 4),
            "n_sector_clusters":           self.n_sector_clusters,
            "n_industry_clusters":         self.n_industry_clusters,
            "systemic_exposure_score":     round(self.systemic_exposure_score, 4),
            "hidden_dependency_count":     self.hidden_dependency_count,
            "sector_clusters":             [c.to_dict() for c in self.sector_clusters],
            "industry_clusters":           [c.to_dict() for c in self.industry_clusters[:10]],
        }


def _build_clusters(
    positions: List[PositionData],
    key: str,
) -> List[DependencyCluster]:
    buckets: Dict[str, List[PositionData]] = {}
    for p in positions:
        k = getattr(p, key, "unknown")
        buckets.setdefault(k, []).append(p)
    clusters = []
    for i, (name, members) in enumerate(
        sorted(buckets.items(), key=lambda kv: -sum(p.weight for p in kv[1]))
    ):
        clusters.append(DependencyCluster(
            cluster_id  = f"{key}_{i}",
            dimension   = key,
            bucket_name = name,
            symbols     = tuple(m.symbol for m in members),
            total_weight= round(sum(m.weight for m in members), 4),
            n_positions = len(members),
        ))
    return clusters


def analyze_dependencies(positions: List[PositionData]) -> DependencyAnalysisResult:
    if not positions:
        return DependencyAnalysisResult()

    sec_clusters = _build_clusters(positions, "sector")
    ind_clusters = _build_clusters(positions, "industry")

    max_sec = sec_clusters[0].total_weight if sec_clusters else 0.0
    max_ind = ind_clusters[0].total_weight if ind_clusters else 0.0

    # Systemic exposure: HHI of sector weights as proxy
    sec_weights = [c.total_weight for c in sec_clusters]
    systemic_score = compute_hhi(sec_weights) * len(sec_clusters)
    systemic_score = min(1.0, systemic_score)

    # Hidden dependencies: positions that differ in sector but share an industry
    hidden = 0
    pos_list = list(positions)
    for i, a in enumerate(pos_list):
        for b in pos_list[i+1:]:
            if (a.sector != b.sector and
                a.industry == b.industry and
                a.industry not in ("unknown", "")):
                hidden += 1

    return DependencyAnalysisResult(
        sector_clusters             = tuple(sec_clusters),
        industry_clusters           = tuple(ind_clusters),
        max_sector_cluster_weight   = max_sec,
        max_industry_cluster_weight = max_ind,
        n_sector_clusters           = len(sec_clusters),
        n_industry_clusters         = len(ind_clusters),
        systemic_exposure_score     = round(systemic_score, 4),
        hidden_dependency_count     = hidden,
    )
