"""iios/investment/company/business_quality/business_quality_snapshot.py
Primary output object of the Business Quality Intelligence Engine.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.company.business_quality.business_model import BusinessModelProfile
from iios.investment.company.business_quality.economic_moat import EconomicMoatProfile
from iios.investment.company.business_quality.operational_quality import OperationalQualityProfile
from iios.investment.company.business_quality.business_resilience import ResilienceProfile
from iios.investment.company.business_quality.competitive_position import (
    CompetitiveIntelligenceProfile,
)


@dataclass
class BusinessQualityScore:
    """Composite business quality score across all dimensions."""

    moat_score:          float = 0.0   # Economic moat strength (25%)
    operational_score:   float = 0.0   # Operational excellence (25%)
    resilience_score:    float = 0.0   # Business resilience (20%)
    competitive_score:   float = 0.0   # Competitive position (15%)
    model_score:         float = 0.0   # Business model quality (15%)

    overall_score:       float = 0.0   # Weighted composite

    # Bands
    label: str = "unknown"   # "exceptional" | "strong" | "average" | "weak" | "poor"

    explanation: List[str] = field(default_factory=list)

    _W_MOAT        = 0.25
    _W_OPERATIONAL = 0.25
    _W_RESILIENCE  = 0.20
    _W_COMPETITIVE = 0.15
    _W_MODEL       = 0.15

    def recompute(self) -> None:
        self.overall_score = (
            self.moat_score        * self._W_MOAT
            + self.operational_score * self._W_OPERATIONAL
            + self.resilience_score  * self._W_RESILIENCE
            + self.competitive_score * self._W_COMPETITIVE
            + self.model_score       * self._W_MODEL
        )
        self.label = _score_to_label(self.overall_score)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_score":     round(self.overall_score, 1),
            "label":             self.label,
            "moat_score":        round(self.moat_score, 1),
            "operational_score": round(self.operational_score, 1),
            "resilience_score":  round(self.resilience_score, 1),
            "competitive_score": round(self.competitive_score, 1),
            "model_score":       round(self.model_score, 1),
            "explanation":       self.explanation,
        }


def _score_to_label(score: float) -> str:
    if score >= 80:
        return "exceptional"
    if score >= 65:
        return "strong"
    if score >= 50:
        return "average"
    if score >= 35:
        return "weak"
    return "poor"


@dataclass
class QualityConfidenceScore:
    """Confidence in the business quality assessment."""

    score:   float = 0.0    # 0-100
    label:   str   = "insufficient"  # "high" | "medium" | "low" | "insufficient"

    data_sufficiency:      float = 0.0   # Historical depth
    signal_quality:        float = 0.0   # Consistency of signals
    coverage_pct:          float = 0.0   # Fraction of fields populated

    factors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score":             round(self.score, 1),
            "label":             self.label,
            "data_sufficiency":  round(self.data_sufficiency, 1),
            "signal_quality":    round(self.signal_quality, 1),
            "coverage_pct":      round(self.coverage_pct, 2),
            "factors":           self.factors,
        }


@dataclass
class BusinessQualitySnapshot:
    """
    Primary output of the Business Quality Intelligence Engine.

    This is the single source of truth for business quality assessment
    across IIOS. All downstream engines must consume this object.
    """
    ticker:       str
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    sector:       Optional[str] = None
    industry:     Optional[str] = None

    # Core dimensions
    business_model:  BusinessModelProfile          = field(default_factory=BusinessModelProfile)
    moat:            EconomicMoatProfile            = field(default_factory=EconomicMoatProfile)
    operational:     OperationalQualityProfile      = field(default_factory=OperationalQualityProfile)
    resilience:      ResilienceProfile              = field(default_factory=ResilienceProfile)
    competitive:     CompetitiveIntelligenceProfile = field(default_factory=CompetitiveIntelligenceProfile)

    # Scoring
    quality_score: BusinessQualityScore    = field(default_factory=BusinessQualityScore)
    confidence:    QualityConfidenceScore  = field(default_factory=QualityConfidenceScore)

    # Plugin contributions (extensible)
    plugin_scores: Dict[str, float] = field(default_factory=dict)

    @property
    def overall_score(self) -> float:
        return self.quality_score.overall_score

    @property
    def moat_score(self) -> float:
        return self.moat.moat_score

    @property
    def is_wide_moat(self) -> bool:
        from iios.investment.company.business_quality.economic_moat import MoatStrength
        return self.moat.moat_strength == MoatStrength.WIDE

    @property
    def is_resilient(self) -> bool:
        return self.resilience.is_resilient

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker":         self.ticker,
            "generated_at":   self.generated_at.isoformat(),
            "sector":         self.sector,
            "industry":       self.industry,
            "business_model": self.business_model.to_dict(),
            "moat":           self.moat.to_dict(),
            "operational":    self.operational.to_dict(),
            "resilience":     self.resilience.to_dict(),
            "competitive":    self.competitive.to_dict(),
            "quality_score":  self.quality_score.to_dict(),
            "confidence":     self.confidence.to_dict(),
            "plugin_scores":  self.plugin_scores,
        }
