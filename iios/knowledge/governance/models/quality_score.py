"""
iios/knowledge/governance/models/quality_score.py
==================================================
DimensionScore — per-dimension quality score with supporting details.
QualityScore — aggregated multi-dimensional score for one knowledge record.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from ..quality_constants import (
    QualityDimension,
    QualityTier,
    DIMENSION_WEIGHTS,
    KQI_POOR_MAX,
    KQI_FAIR_MAX,
    KQI_GOOD_MAX,
    DEFAULT_MIN_KQI,
    GOVERNANCE_SCHEMA_VERSION,
)

__all__ = ["DimensionScore", "QualityScore"]


@dataclass
class DimensionScore:
    """Quality score for a single dimension."""

    dimension:  QualityDimension
    score:      float         # 0.0 to 1.0
    weight:     float         # contribution weight
    passed:     bool          = True
    violations: list[str]     = field(default_factory=list)
    details:    dict[str, Any]= field(default_factory=dict)

    @property
    def weighted_score(self) -> float:
        return self.score * self.weight

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension":  self.dimension.value,
            "score":      round(self.score, 4),
            "weight":     self.weight,
            "passed":     self.passed,
            "violations": list(self.violations),
            "details":    dict(self.details),
        }


@dataclass
class QualityScore:
    """Aggregated multi-dimensional quality score for a knowledge record.

    ``overall_kqi`` is the weighted sum of all dimension scores.
    ``tier`` maps the KQI to a human-readable quality level.
    """

    score_id:         str                   = field(default_factory=lambda: str(uuid.uuid4()))
    knowledge_id:     str                   = ""
    dimension_scores: list[DimensionScore]  = field(default_factory=list)
    overall_kqi:      float                 = 0.0
    tier:             QualityTier           = QualityTier.POOR
    computed_at:      float                 = field(default_factory=time.time)
    schema_version:   str                   = GOVERNANCE_SCHEMA_VERSION

    # ── Convenience properties ────────────────────────────────────────────────

    @property
    def is_poor(self) -> bool:
        return self.tier == QualityTier.POOR

    @property
    def is_excellent(self) -> bool:
        return self.tier == QualityTier.EXCELLENT

    def passes(self, threshold: float = DEFAULT_MIN_KQI) -> bool:
        return self.overall_kqi >= threshold

    def get_dimension(self, dim: QualityDimension) -> Optional[DimensionScore]:
        for ds in self.dimension_scores:
            if ds.dimension == dim:
                return ds
        return None

    def get_score(self, dim: QualityDimension) -> float:
        ds = self.get_dimension(dim)
        return ds.score if ds else 0.0

    def failing_dimensions(self) -> list[QualityDimension]:
        return [ds.dimension for ds in self.dimension_scores if not ds.passed]

    def all_violations(self) -> list[str]:
        out: list[str] = []
        for ds in self.dimension_scores:
            out.extend(ds.violations)
        return out

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "score_id":         self.score_id,
            "knowledge_id":     self.knowledge_id,
            "overall_kqi":      round(self.overall_kqi, 4),
            "tier":             self.tier.value,
            "computed_at":      self.computed_at,
            "dimension_scores": [ds.to_dict() for ds in self.dimension_scores],
            "schema_version":   self.schema_version,
        }


def compute_tier(kqi: float) -> QualityTier:
    if kqi < KQI_POOR_MAX:
        return QualityTier.POOR
    if kqi < KQI_FAIR_MAX:
        return QualityTier.FAIR
    if kqi < KQI_GOOD_MAX:
        return QualityTier.GOOD
    return QualityTier.EXCELLENT


def compute_kqi(dimension_scores: list[DimensionScore]) -> float:
    """Compute KQI as a weighted sum of dimension scores.

    If a dimension is missing from the list its weight contributes 0.0
    to the total (conservative — missing evaluation penalises the score).
    """
    total = 0.0
    weight_used = 0.0
    for ds in dimension_scores:
        total       += ds.score * ds.weight
        weight_used += ds.weight
    if weight_used <= 0:
        return 0.0
    # Normalise in case weights don't sum to exactly 1.0
    return min(1.0, total / weight_used)
