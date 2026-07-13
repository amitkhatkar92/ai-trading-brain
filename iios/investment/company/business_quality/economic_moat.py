"""iios/investment/company/business_quality/economic_moat.py
Economic moat classification and profiling.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class MoatType(Enum):
    BRAND              = "brand"
    NETWORK_EFFECT     = "network_effect"
    COST_ADVANTAGE     = "cost_advantage"
    SWITCHING_COSTS    = "switching_costs"
    SCALE_ADVANTAGE    = "scale_advantage"
    INTELLECTUAL_PROPERTY = "intellectual_property"
    REGULATORY         = "regulatory"
    DISTRIBUTION       = "distribution"
    DATA_ADVANTAGE     = "data_advantage"
    NONE               = "none"


class MoatStrength(Enum):
    WIDE    = "wide"      # Durable 10+ year sustainable advantage
    NARROW  = "narrow"    # Defensible 5-10 year advantage
    NONE    = "none"      # No identifiable moat
    UNKNOWN = "unknown"   # Insufficient data


@dataclass
class MoatSignal:
    """A single financial signal supporting a moat type."""
    moat_type:  MoatType
    strength:   float         # 0-1 signal strength
    evidence:   List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "moat_type": self.moat_type.value,
            "strength":  round(self.strength, 3),
            "evidence":  self.evidence,
        }


@dataclass
class EconomicMoatProfile:
    """
    Economic moat analysis inferred from financial signal patterns.
    Wide moat = persistent ROIC >> cost of capital, durable margins.
    """

    moat_strength:       MoatStrength      = MoatStrength.UNKNOWN
    moat_score:          float             = 0.0    # 0-100
    detected_moat_types: List[MoatType]   = field(default_factory=list)
    signals:             List[MoatSignal] = field(default_factory=list)

    # Key financial evidence
    avg_roic:               Optional[float] = None
    roic_stability:         Optional[float] = None  # stdev(ROIC)
    avg_gross_margin:       Optional[float] = None
    gross_margin_stability: Optional[float] = None  # stdev(gross margin)
    fcf_conversion:         Optional[float] = None  # avg OCF/NI
    avg_roe:                Optional[float] = None

    # Component scores (0-100 each)
    brand_score:         float = 0.0
    network_score:       float = 0.0
    cost_advantage_score: float = 0.0
    switching_cost_score: float = 0.0
    scale_score:         float = 0.0
    ip_score:            float = 0.0
    regulatory_score:    float = 0.0
    distribution_score:  float = 0.0

    periods_analyzed: int = 0
    flags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "moat_strength":       self.moat_strength.value,
            "moat_score":          round(self.moat_score, 1),
            "detected_moat_types": [m.value for m in self.detected_moat_types],
            "avg_roic":            self.avg_roic,
            "roic_stability":      self.roic_stability,
            "avg_gross_margin":    self.avg_gross_margin,
            "fcf_conversion":      self.fcf_conversion,
            "brand_score":         round(self.brand_score, 1),
            "network_score":       round(self.network_score, 1),
            "cost_advantage_score": round(self.cost_advantage_score, 1),
            "switching_cost_score": round(self.switching_cost_score, 1),
            "scale_score":         round(self.scale_score, 1),
            "ip_score":            round(self.ip_score, 1),
            "periods_analyzed":    self.periods_analyzed,
            "flags":               self.flags,
        }
