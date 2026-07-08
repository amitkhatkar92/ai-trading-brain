"""
iios/intelligence/governance/quality/quality_score.py
======================================================
QualityScore dataclass + dimension-level scoring logic.
"""
from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from ..quality_constants import (
    EvaluationDimension,
    QualityLevel,
    IntelligenceType,
    DEFAULT_DIMENSION_WEIGHTS,
    QUALITY_SCORE_EXCELLENT,
    QUALITY_SCORE_GOOD,
    QUALITY_SCORE_ACCEPTABLE,
)


@dataclass
class DimensionScore:
    """Score on one quality dimension."""

    dimension:   EvaluationDimension
    score:       float              # [0, 1]
    weight:      float              # contribution weight
    evidence:    str                = ""

    def weighted(self) -> float:
        return self.score * self.weight

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension.value,
            "score":     round(self.score, 4),
            "weight":    round(self.weight, 4),
            "evidence":  self.evidence,
        }


@dataclass
class QualityScore:
    """
    Multi-dimensional quality assessment for one intelligence product.
    """

    score_id:    str                    = field(default_factory=lambda: str(uuid.uuid4()))
    product_id:  str                    = ""
    dimensions:  list[DimensionScore]   = field(default_factory=list)
    composite:   float                  = 0.0
    level:       QualityLevel           = QualityLevel.REJECTED
    warnings:    list[str]              = field(default_factory=list)
    computed_at: float                  = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "score_id":   self.score_id,
            "product_id": self.product_id,
            "dimensions": [d.to_dict() for d in self.dimensions],
            "composite":  round(self.composite, 4),
            "level":      self.level.value,
            "warnings":   list(self.warnings),
            "computed_at": self.computed_at,
        }


def level_from_score(score: float) -> QualityLevel:
    if score >= QUALITY_SCORE_EXCELLENT:
        return QualityLevel.EXCELLENT
    if score >= QUALITY_SCORE_GOOD:
        return QualityLevel.GOOD
    if score >= QUALITY_SCORE_ACCEPTABLE:
        return QualityLevel.ACCEPTABLE
    if score >= 0.40:
        return QualityLevel.POOR
    return QualityLevel.REJECTED


def compute_composite(dimensions: list[DimensionScore]) -> float:
    if not dimensions:
        return 0.0
    total_w = sum(d.weight for d in dimensions) or 1.0
    return sum(d.score * d.weight for d in dimensions) / total_w


def build_dimension_scores(
    raw_scores: dict[str, float],
    weights:    dict[str, float] | None = None,
) -> list[DimensionScore]:
    """
    Build a list of DimensionScore from a raw score dict.

    raw_scores  : dimension name → score in [0, 1]
    weights     : override default weights (optional)
    """
    w = weights or DEFAULT_DIMENSION_WEIGHTS
    dims: list[DimensionScore] = []
    for dim in EvaluationDimension:
        score  = max(0.0, min(1.0, raw_scores.get(dim.value, 0.0)))
        weight = w.get(dim.value, 0.0)
        dims.append(DimensionScore(
            dimension = dim,
            score     = score,
            weight    = weight,
        ))
    return dims


def score_product(
    product_id:  str,
    raw_scores:  dict[str, float],
    weights:     dict[str, float] | None = None,
) -> QualityScore:
    """
    Produce a complete QualityScore from raw per-dimension scores.
    """
    dims      = build_dimension_scores(raw_scores, weights)
    composite = compute_composite(dims)
    level     = level_from_score(composite)

    warnings: list[str] = []
    if raw_scores.get("accuracy", 1.0) < 0.4:
        warnings.append("Low accuracy score — product reliability questionable")
    if raw_scores.get("completeness", 1.0) < 0.4:
        warnings.append("Low completeness — mandatory fields may be missing")

    return QualityScore(
        product_id  = product_id,
        dimensions  = dims,
        composite   = composite,
        level       = level,
        warnings    = warnings,
    )
