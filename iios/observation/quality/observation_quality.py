"""
iios/observation/quality/observation_quality.py
===============================================
ObservationQualityAssessor — standalone quality scorer for observations.

Scores observations on five dimensions and computes an overall OQI
(Observation Quality Index) in [0.0, 1.0].
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from ..observation_constants import (
    ObservationQuality,
    OBSERVATION_SCHEMA_VERSION,
)
from ..models.observation import Observation

__all__ = [
    "QualityDimension",
    "ObservationQualityScore",
    "ObservationQualityAssessor",
    "get_quality_assessor",
    "reset_quality_assessor",
]

_lock = threading.Lock()
_assessor: Optional["ObservationQualityAssessor"] = None

_WEIGHTS = {
    "completeness":  0.30,
    "freshness":     0.25,
    "confidence":    0.20,
    "consistency":   0.15,
    "provenance":    0.10,
}


@dataclass
class QualityDimension:
    name:   str
    score:  float   # 0.0 – 1.0
    weight: float

    @property
    def weighted(self) -> float:
        return self.score * self.weight

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "score": self.score, "weight": self.weight}


@dataclass
class ObservationQualityScore:
    obs_id:      str
    dimensions:  list[QualityDimension] = field(default_factory=list)
    oqi:         float                  = 0.0
    tier:        ObservationQuality     = ObservationQuality.POOR
    computed_at: float                  = field(default_factory=time.time)

    def passes(self, threshold: float = 0.50) -> bool:
        return self.oqi >= threshold

    def to_dict(self) -> dict[str, Any]:
        return {
            "obs_id":       self.obs_id,
            "oqi":          self.oqi,
            "tier":         self.tier.value,
            "dimensions":   [d.to_dict() for d in self.dimensions],
            "computed_at":  self.computed_at,
        }


def _tier(oqi: float) -> ObservationQuality:
    if oqi >= 0.80: return ObservationQuality.EXCELLENT
    if oqi >= 0.60: return ObservationQuality.GOOD
    if oqi >= 0.40: return ObservationQuality.FAIR
    return ObservationQuality.POOR


class ObservationQualityAssessor:
    """Scores observations on five quality dimensions."""

    def score(self, obs: Observation) -> ObservationQualityScore:
        dims = [
            QualityDimension("completeness", self._completeness(obs), _WEIGHTS["completeness"]),
            QualityDimension("freshness",    self._freshness(obs),    _WEIGHTS["freshness"]),
            QualityDimension("confidence",   obs.metadata.confidence, _WEIGHTS["confidence"]),
            QualityDimension("consistency",  self._consistency(obs),  _WEIGHTS["consistency"]),
            QualityDimension("provenance",   self._provenance(obs),   _WEIGHTS["provenance"]),
        ]
        oqi = sum(d.weighted for d in dims)
        oqi = max(0.0, min(1.0, oqi))
        return ObservationQualityScore(
            obs_id     = obs.id,
            dimensions = dims,
            oqi        = round(oqi, 4),
            tier       = _tier(oqi),
        )

    def _completeness(self, obs: Observation) -> float:
        score = 0.0
        if obs.content is not None: score += 0.50
        if obs.title:               score += 0.20
        if obs.metadata.tags:       score += 0.15
        if obs.source_info.instrument or obs.source_info.source_name: score += 0.15
        return score

    def _freshness(self, obs: Observation) -> float:
        if obs.metadata.is_expired:
            return 0.0
        age_s = obs.metadata.age_seconds
        ttl   = float(obs.metadata.ttl_seconds) if obs.metadata.ttl_seconds > 0 else 86_400.0
        ratio = 1.0 - (age_s / ttl)
        return max(0.0, min(1.0, ratio))

    def _consistency(self, obs: Observation) -> float:
        score = 1.0
        if obs.content is None:                      score -= 0.50
        if not obs.title and not obs.content:        score -= 0.30
        if obs.metadata.confidence <= 0.0:           score -= 0.20
        return max(0.0, score)

    def _provenance(self, obs: Observation) -> float:
        score = 0.0
        from ..observation_constants import ObservationSource
        if obs.source_info.source != ObservationSource.UNKNOWN:  score += 0.40
        if obs.source_info.source_name:                          score += 0.20
        if obs.source_info.instrument:                           score += 0.20
        if obs.source_info.exchange:                             score += 0.20
        return score


# ── Singleton helpers ─────────────────────────────────────────────────────────

def get_quality_assessor() -> ObservationQualityAssessor:
    global _assessor
    if _assessor is None:
        with _lock:
            if _assessor is None:
                _assessor = ObservationQualityAssessor()
    return _assessor


def reset_quality_assessor() -> None:
    global _assessor
    with _lock:
        _assessor = None
