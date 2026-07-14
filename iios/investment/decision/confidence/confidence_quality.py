"""iios/investment/decision/confidence/confidence_quality.py
ConfidenceQualityEvaluator — evaluates the quality of a confidence estimation.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from iios.investment.decision.confidence.confidence_constants import (
    ConfidenceQualityGrade,
)
from iios.investment.decision.confidence.confidence_snapshot import ConfidenceSnapshot
from iios.investment.decision.confidence.confidence_validator import (
    ConfidenceValidationResult,
    ConfidenceValidator,
)


@dataclass(frozen=True)
class ConfidenceQualityReport:
    snapshot_id:        str
    validation_result:  ConfidenceValidationResult
    completeness_score: float   # 0–100 how complete the estimation is
    explainability:     float   # 0–100 how traceable the confidence is
    reliability:        float   # 0–100 based on calibration
    overall_quality:    float   # 0–100
    grade:              ConfidenceQualityGrade
    computed_at:        datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id":        self.snapshot_id,
            "completeness_score": round(self.completeness_score, 2),
            "explainability":     round(self.explainability, 2),
            "reliability":        round(self.reliability, 2),
            "overall_quality":    round(self.overall_quality, 2),
            "grade":              self.grade.value,
            "validation":         self.validation_result.to_dict(),
            "computed_at":        self.computed_at.isoformat(),
        }


class ConfidenceQualityEvaluator:
    """Evaluates the quality of a completed confidence estimation."""

    def __init__(self, validator: ConfidenceValidator | None = None) -> None:
        self._validator = validator or ConfidenceValidator()

    def evaluate(self, snapshot: ConfidenceSnapshot) -> ConfidenceQualityReport:
        validation = self._validator.validate(snapshot)

        dc = snapshot.decision_confidence

        # Completeness: how many dimensions are non-trivial (>10)
        dims = [
            dc.evidence_confidence,
            dc.reasoning_confidence,
            dc.historical_confidence,
            dc.calibration_quality,
        ]
        if dc.scoring_available:
            dims.append(dc.scoring_confidence)

        non_trivial = sum(1 for d in dims if d > 10.0)
        completeness = min(100.0, (non_trivial / 5.0) * 100.0)

        # Explainability: presence of evidence_detail and reasoning_detail in snap
        # Both are always present in a real snapshot; reward high evidence count
        explainability = min(100.0, 60.0 + dc.evidence_confidence * 0.2 + dc.reasoning_confidence * 0.2)

        # Reliability: from calibration quality
        reliability = dc.calibration_quality

        overall_quality = (
            completeness * 0.35
            + explainability * 0.30
            + reliability    * 0.35
        )
        overall_quality = max(0.0, min(100.0, overall_quality))

        # Penalise for validation issues
        overall_quality -= len(validation.issues) * 10.0
        overall_quality  = max(0.0, overall_quality)

        return ConfidenceQualityReport(
            snapshot_id=snapshot.snapshot_id,
            validation_result=validation,
            completeness_score=round(completeness, 4),
            explainability=round(explainability, 4),
            reliability=round(reliability, 4),
            overall_quality=round(overall_quality, 4),
            grade=ConfidenceQualityGrade.from_score(overall_quality),
            computed_at=datetime.now(timezone.utc),
        )
