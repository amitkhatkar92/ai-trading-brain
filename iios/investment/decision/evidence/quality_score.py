"""iios/investment/decision/evidence/quality_score.py
QualityScore — immutable score object and single-item scorer.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict

from iios.investment.decision.evidence.evidence_constants import (
    EvidenceQualityDimension,
)


@dataclass(frozen=True)
class QualityScore:
    overall:     float             # 0–100 weighted composite
    coverage:    float             # 0–100
    freshness:   float             # 0–100
    consistency: float             # 0–100
    reliability: float             # 0–100
    completeness: float            # 0–100
    computed_at: datetime

    @property
    def grade(self) -> str:
        if self.overall >= 85:
            return "A"
        if self.overall >= 70:
            return "B"
        if self.overall >= 55:
            return "C"
        if self.overall >= 40:
            return "D"
        return "F"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall":     round(self.overall, 2),
            "grade":       self.grade,
            "coverage":    round(self.coverage, 2),
            "freshness":   round(self.freshness, 2),
            "consistency": round(self.consistency, 2),
            "reliability": round(self.reliability, 2),
            "completeness": round(self.completeness, 2),
            "computed_at": self.computed_at.isoformat(),
        }


def compute_quality_score(
    coverage:    float,
    freshness:   float,
    consistency: float,
    reliability: float,
    completeness: float,
) -> QualityScore:
    """Compute weighted composite quality score from 5 dimensions."""
    weighted = sum([
        coverage    * EvidenceQualityDimension.COVERAGE.default_weight,
        freshness   * EvidenceQualityDimension.FRESHNESS.default_weight,
        consistency * EvidenceQualityDimension.CONSISTENCY.default_weight,
        reliability * EvidenceQualityDimension.RELIABILITY.default_weight,
        completeness * EvidenceQualityDimension.COMPLETENESS.default_weight,
    ])
    return QualityScore(
        overall=round(min(100.0, max(0.0, weighted)), 2),
        coverage=round(min(100.0, max(0.0, coverage)), 2),
        freshness=round(min(100.0, max(0.0, freshness)), 2),
        consistency=round(min(100.0, max(0.0, consistency)), 2),
        reliability=round(min(100.0, max(0.0, reliability)), 2),
        completeness=round(min(100.0, max(0.0, completeness)), 2),
        computed_at=datetime.now(timezone.utc),
    )
