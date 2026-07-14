"""iios/investment/portfolio/diversification/diversification_metrics.py

Computes a comprehensive DiversificationMetrics record from a
DiversificationAnalysis and DiversificationScore.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from iios.investment.portfolio.diversification.diversification_engine import (
    DiversificationAnalysis,
)
from iios.investment.portfolio.diversification.diversification_score import (
    DiversificationScore,
)


@dataclass(frozen=True)
class DiversificationMetrics:
    """All diversification metrics in one flat structure for reporting."""

    metrics_id:          str   = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:        str   = ""
    analysis_id:         str   = ""

    # Position-level
    n_positions:         int   = 0
    effective_n:         float = 0.0
    hhi:                 float = 0.0
    entropy:             float = 0.0
    entropy_ratio:       float = 0.0
    top1_weight:         float = 0.0
    top5_weight:         float = 0.0
    top10_weight:        float = 0.0

    # Sector-level
    n_sectors:           int   = 0
    sector_hhi:          float = 0.0
    sector_entropy_ratio:float = 0.0
    top_sector_weight:   float = 0.0

    # Correlation
    avg_correlation:     float = 0.0
    diversification_ratio:float = 0.0
    n_high_corr_pairs:   int   = 0
    portfolio_risk_proxy:float = 0.0

    # Overlap
    sector_overlap:      float = 0.0
    industry_overlap:    float = 0.0

    # Factor
    quality_tilt:        float = 0.5
    volatility_tilt:     float = 0.5
    momentum_tilt:       float = 0.5

    # Quality
    overall_score:       float = 0.0
    grade:               str   = "F"
    is_acceptable:       bool  = False

    computed_at:         float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metrics_id":          self.metrics_id,
            "portfolio_id":        self.portfolio_id,
            "analysis_id":         self.analysis_id,
            "n_positions":         self.n_positions,
            "effective_n":         round(self.effective_n, 2),
            "hhi":                 round(self.hhi, 6),
            "entropy":             round(self.entropy, 4),
            "entropy_ratio":       round(self.entropy_ratio, 4),
            "top1_weight":         round(self.top1_weight, 4),
            "top5_weight":         round(self.top5_weight, 4),
            "top10_weight":        round(self.top10_weight, 4),
            "n_sectors":           self.n_sectors,
            "sector_hhi":          round(self.sector_hhi, 6),
            "sector_entropy_ratio":round(self.sector_entropy_ratio, 4),
            "top_sector_weight":   round(self.top_sector_weight, 4),
            "avg_correlation":     round(self.avg_correlation, 4),
            "diversification_ratio":round(self.diversification_ratio, 4),
            "n_high_corr_pairs":   self.n_high_corr_pairs,
            "portfolio_risk_proxy":round(self.portfolio_risk_proxy, 4),
            "sector_overlap":      round(self.sector_overlap, 4),
            "industry_overlap":    round(self.industry_overlap, 4),
            "quality_tilt":        round(self.quality_tilt, 4),
            "volatility_tilt":     round(self.volatility_tilt, 4),
            "momentum_tilt":       round(self.momentum_tilt, 4),
            "overall_score":       round(self.overall_score, 4),
            "grade":               self.grade,
            "is_acceptable":       self.is_acceptable,
            "computed_at":         self.computed_at,
        }


def compute_diversification_metrics(
    analysis: DiversificationAnalysis,
    score:    Optional[DiversificationScore] = None,
) -> DiversificationMetrics:
    pos_c    = analysis.concentration.position
    sec_c    = analysis.concentration.sector.sector
    fac      = analysis.concentration.factor
    corr_a   = analysis.correlation.analysis
    overlap  = analysis.correlation.overlap

    return DiversificationMetrics(
        portfolio_id         = analysis.portfolio_id,
        analysis_id          = analysis.analysis_id,
        n_positions          = analysis.n_positions,
        effective_n          = analysis.effective_n,
        hhi                  = analysis.hhi,
        entropy              = analysis.entropy,
        entropy_ratio        = analysis.entropy_ratio,
        top1_weight          = pos_c.top1_weight,
        top5_weight          = pos_c.top5_weight,
        top10_weight         = pos_c.top10_weight,
        n_sectors            = analysis.n_sectors,
        sector_hhi           = analysis.sector_hhi,
        sector_entropy_ratio = analysis.sector_entropy_ratio,
        top_sector_weight    = analysis.top_sector_weight,
        avg_correlation      = corr_a.avg_correlation,
        diversification_ratio= analysis.diversification_ratio,
        n_high_corr_pairs    = corr_a.n_high_pairs,
        portfolio_risk_proxy = corr_a.portfolio_risk,
        sector_overlap       = overlap.sector_overlap,
        industry_overlap     = overlap.industry_overlap,
        quality_tilt         = fac.quality_tilt,
        volatility_tilt      = fac.volatility_tilt,
        momentum_tilt        = fac.momentum_tilt,
        overall_score        = score.overall if score else 0.0,
        grade                = score.grade.value if score else "F",
        is_acceptable        = score.is_acceptable if score else False,
    )
