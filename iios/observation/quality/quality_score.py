"""
iios/observation/quality/quality_score.py
==========================================
QualityScore — comprehensive nine-dimension quality model.

Dimensions (with default weights)
----------------------------------
  completeness  0.20  — required fields present
  accuracy      0.15  — values within expected ranges
  consistency   0.15  — internal cross-field agreement
  timeliness    0.15  — lag from event time to ingestion
  reliability   0.10  — historical reliability of source
  source_trust  0.10  — static trust rating for source enum
  freshness     0.10  — time remaining vs TTL
  integrity     0.05  — checksum / hash validity
  ──────────────────
  OQI = weighted sum  (normalised to [0, 1])
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from ..observation_constants import ObservationQuality

__all__ = [
    "DimensionScore",
    "QualityScore",
    "quality_tier",
    "DEFAULT_WEIGHTS",
]

# Default dimension weights (must sum to ≤ 1.0)
DEFAULT_WEIGHTS: dict[str, float] = {
    "completeness": 0.20,
    "accuracy":     0.15,
    "consistency":  0.15,
    "timeliness":   0.15,
    "reliability":  0.10,
    "source_trust": 0.10,
    "freshness":    0.10,
    "integrity":    0.05,
}


def quality_tier(oqi: float) -> ObservationQuality:
    """Map OQI [0, 1] → :class:`ObservationQuality` tier."""
    if oqi >= 0.80: return ObservationQuality.EXCELLENT
    if oqi >= 0.60: return ObservationQuality.GOOD
    if oqi >= 0.40: return ObservationQuality.FAIR
    return ObservationQuality.POOR


@dataclass
class DimensionScore:
    """Score for a single quality dimension."""
    name:   str
    score:  float          # raw score in [0, 1]
    weight: float          # contribution weight
    reason: str  = ""      # human-readable explanation

    @property
    def weighted(self) -> float:
        return self.score * self.weight

    def to_dict(self) -> dict[str, Any]:
        return {
            "name":     self.name,
            "score":    round(self.score,   4),
            "weight":   round(self.weight,  4),
            "weighted": round(self.weighted, 4),
            "reason":   self.reason,
        }


@dataclass
class QualityScore:
    """Complete nine-dimension quality score for one observation."""

    obs_id:       str
    completeness: DimensionScore
    accuracy:     DimensionScore
    consistency:  DimensionScore
    timeliness:   DimensionScore
    reliability:  DimensionScore
    source_trust: DimensionScore
    freshness:    DimensionScore
    integrity:    DimensionScore
    oqi:          float              = 0.0
    tier:         ObservationQuality = ObservationQuality.POOR
    computed_at:  float              = field(default_factory=time.time)

    def passes(self, threshold: float = 0.50) -> bool:
        """Return True if OQI meets *threshold*."""
        return self.oqi >= threshold

    def dimensions(self) -> list[DimensionScore]:
        return [
            self.completeness, self.accuracy,   self.consistency,
            self.timeliness,   self.reliability, self.source_trust,
            self.freshness,    self.integrity,
        ]

    def lowest_dimension(self) -> DimensionScore:
        return min(self.dimensions(), key=lambda d: d.score)

    def highest_dimension(self) -> DimensionScore:
        return max(self.dimensions(), key=lambda d: d.score)

    def to_dict(self) -> dict[str, Any]:
        return {
            "obs_id":       self.obs_id,
            "oqi":          round(self.oqi, 4),
            "tier":         self.tier.value,
            "computed_at":  self.computed_at,
            "dimensions":   {d.name: d.to_dict() for d in self.dimensions()},
        }

    @classmethod
    def zero(cls, obs_id: str) -> "QualityScore":
        """Return a zero-score QualityScore (e.g. for failed computation)."""
        def _dim(name: str) -> DimensionScore:
            return DimensionScore(
                name   = name,
                score  = 0.0,
                weight = DEFAULT_WEIGHTS.get(name, 0.0),
                reason = "not computed",
            )
        return cls(
            obs_id       = obs_id,
            completeness = _dim("completeness"),
            accuracy     = _dim("accuracy"),
            consistency  = _dim("consistency"),
            timeliness   = _dim("timeliness"),
            reliability  = _dim("reliability"),
            source_trust = _dim("source_trust"),
            freshness    = _dim("freshness"),
            integrity    = _dim("integrity"),
            oqi          = 0.0,
            tier         = ObservationQuality.POOR,
        )
