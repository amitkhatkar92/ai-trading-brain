"""iios/investment/portfolio/diversification/diversification_profile.py

The primary immutable output of one portfolio diversification evaluation.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from iios.investment.portfolio.diversification.diversification_types import (
    ConcentrationLevel,
    DiversificationGrade,
    DiversificationStatus,
    DIVERSIFICATION_PROFILE_SCHEMA_VERSION,
)


@dataclass(frozen=True)
class DiversificationProfile:
    """
    Immutable, version-stamped diversification profile for one portfolio snapshot.
    Produced by PortfolioDiversificationEngine.evaluate() and consumed by:
      • DiversificationHistory
      • Downstream monitoring layer
    """

    profile_id:       str                  = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:     str                  = ""
    plan_id:          str                  = ""
    allocation_plan_id:str                 = ""
    blueprint_id:     str                  = ""
    version:          int                  = 1
    schema_version:   str                  = DIVERSIFICATION_PROFILE_SCHEMA_VERSION

    # Capital context
    total_capital:    float                = 0.0
    currency:         str                  = "INR"

    # Position metrics
    n_positions:      int                  = 0
    effective_n:      float                = 0.0
    hhi:              float                = 0.0
    entropy:          float                = 0.0
    entropy_ratio:    float                = 0.0

    # Top-N weights
    top1_weight:      float                = 0.0
    top5_weight:      float                = 0.0
    top10_weight:     float                = 0.0
    top1_symbol:      str                  = ""

    # Sector metrics
    n_sectors:        int                  = 0
    top_sector_weight:float                = 0.0
    top_sector_name:  str                  = ""
    sector_hhi:       float                = 0.0
    sector_entropy_ratio: float            = 0.0

    # Correlation metrics
    avg_correlation:  float                = 0.0
    diversification_ratio: float           = 0.0
    portfolio_risk_proxy:  float           = 0.0
    n_high_corr_pairs:int                  = 0

    # Overlap metrics
    sector_overlap:   float                = 0.0
    thematic_overlap: float                = 0.0

    # Factor exposure
    quality_tilt:     float                = 0.5
    volatility_tilt:  float                = 0.5
    momentum_tilt:    float                = 0.5

    # Quality
    overall_score:    float                = 0.0
    position_score:   float                = 0.0
    sector_score:     float                = 0.0
    correlation_score:float                = 0.0
    concentration_score:float              = 0.0
    resilience_score: float                = 0.0
    grade:            DiversificationGrade = DiversificationGrade.F
    is_acceptable:    bool                 = False

    # Alerts
    has_concentration_risk:bool            = False
    has_correlation_risk:  bool            = False
    n_alerts:         int                  = 0
    n_critical_alerts:int                  = 0
    concentration_level: ConcentrationLevel = ConcentrationLevel.MODERATE

    created_at:       float                = field(default_factory=time.time)
    created_by:       str                  = "PortfolioDiversificationEngine"
    metadata:         Dict[str, Any]       = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id":             self.profile_id,
            "portfolio_id":           self.portfolio_id,
            "plan_id":                self.plan_id,
            "version":                self.version,
            "schema_version":         self.schema_version,
            "total_capital":          round(self.total_capital, 2),
            "currency":               self.currency,
            "n_positions":            self.n_positions,
            "effective_n":            round(self.effective_n, 2),
            "hhi":                    round(self.hhi, 6),
            "entropy":                round(self.entropy, 4),
            "entropy_ratio":          round(self.entropy_ratio, 4),
            "top1_weight":            round(self.top1_weight, 4),
            "top5_weight":            round(self.top5_weight, 4),
            "top10_weight":           round(self.top10_weight, 4),
            "top1_symbol":            self.top1_symbol,
            "n_sectors":              self.n_sectors,
            "top_sector_weight":      round(self.top_sector_weight, 4),
            "top_sector_name":        self.top_sector_name,
            "sector_hhi":             round(self.sector_hhi, 6),
            "sector_entropy_ratio":   round(self.sector_entropy_ratio, 4),
            "avg_correlation":        round(self.avg_correlation, 4),
            "diversification_ratio":  round(self.diversification_ratio, 4),
            "portfolio_risk_proxy":   round(self.portfolio_risk_proxy, 4),
            "n_high_corr_pairs":      self.n_high_corr_pairs,
            "sector_overlap":         round(self.sector_overlap, 4),
            "thematic_overlap":       round(self.thematic_overlap, 4),
            "quality_tilt":           round(self.quality_tilt, 4),
            "volatility_tilt":        round(self.volatility_tilt, 4),
            "momentum_tilt":          round(self.momentum_tilt, 4),
            "overall_score":          round(self.overall_score, 4),
            "grade":                  self.grade.value,
            "is_acceptable":          self.is_acceptable,
            "has_concentration_risk": self.has_concentration_risk,
            "has_correlation_risk":   self.has_correlation_risk,
            "n_alerts":               self.n_alerts,
            "n_critical_alerts":      self.n_critical_alerts,
            "concentration_level":    self.concentration_level.value,
            "created_at":             self.created_at,
        }
