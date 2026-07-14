"""iios/investment/decision/confidence/calibration_engine.py
CalibrationEngine — orchestrates calibration for an overall confidence score.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from iios.investment.decision.confidence.confidence_calibrator import (
    CalibrationBucket,
    ConfidenceCalibrator,
)
from iios.investment.decision.confidence.confidence_constants import (
    CalibrationStatus,
)


@dataclass(frozen=True)
class CalibrationResult:
    raw_confidence:     float
    calibrated_conf:    float
    adjustment:         float   # calibrated - raw (signed)
    status:             CalibrationStatus
    bucket_count:       int
    record_count:       int
    computed_at:        datetime

    @property
    def quality_score(self) -> float:
        return self.status.quality_score

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw_confidence":  round(self.raw_confidence, 2),
            "calibrated_conf": round(self.calibrated_conf, 2),
            "adjustment":      round(self.adjustment, 2),
            "status":          self.status.value,
            "quality_score":   round(self.quality_score, 2),
            "bucket_count":    self.bucket_count,
            "record_count":    self.record_count,
            "computed_at":     self.computed_at.isoformat(),
        }


class CalibrationEngine:
    """
    Wraps ConfidenceCalibrator and produces a CalibrationResult.
    Provides a clean API for the confidence pipeline.
    """

    def __init__(self, calibrator: Optional[ConfidenceCalibrator] = None) -> None:
        self._cal = calibrator or ConfidenceCalibrator()

    def calibrate(self, raw_confidence: float) -> CalibrationResult:
        calibrated, status = self._cal.calibrate(raw_confidence)
        return CalibrationResult(
            raw_confidence=raw_confidence,
            calibrated_conf=calibrated,
            adjustment=round(calibrated - raw_confidence, 4),
            status=status,
            bucket_count=len(self._cal.buckets()),
            record_count=self._cal.record_count(),
            computed_at=datetime.now(timezone.utc),
        )

    def record_outcome(
        self,
        decision_id:    str,
        raw_confidence: float,
        was_correct:    bool,
    ) -> None:
        self._cal.record_outcome(decision_id, raw_confidence, was_correct)

    @property
    def calibrator(self) -> ConfidenceCalibrator:
        return self._cal
