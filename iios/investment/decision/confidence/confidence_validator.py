"""iios/investment/decision/confidence/confidence_validator.py
ConfidenceValidator — validates a ConfidenceSnapshot for downstream consumption.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from iios.investment.decision.confidence.confidence_constants import (
    CalibrationStatus,
    ConfidenceLevel,
)
from iios.investment.decision.confidence.confidence_snapshot import ConfidenceSnapshot


@dataclass(frozen=True)
class ConfidenceValidationResult:
    is_valid:           bool
    is_usable:          bool
    issues:             Tuple[str, ...]
    warnings:           Tuple[str, ...]
    confidence_score:   float   # 0–100 (copy of overall)
    confidence_level:   ConfidenceLevel
    calibration_status: CalibrationStatus

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid":          self.is_valid,
            "is_usable":         self.is_usable,
            "issues":            list(self.issues),
            "warnings":          list(self.warnings),
            "confidence_score":  round(self.confidence_score, 2),
            "confidence_level":  self.confidence_level.value,
            "calibration_status": self.calibration_status.value,
        }


class ConfidenceValidator:
    """Validates a ConfidenceSnapshot before downstream consumption."""

    _MIN_VALID_CONFIDENCE = 10.0

    def validate(self, snapshot: ConfidenceSnapshot) -> ConfidenceValidationResult:
        issues: List[str]   = []
        warnings: List[str] = []

        conf = snapshot.overall_confidence

        if conf < self._MIN_VALID_CONFIDENCE:
            issues.append(
                f"Overall confidence {conf:.1f} is below minimum threshold "
                f"{self._MIN_VALID_CONFIDENCE}."
            )

        if snapshot.decision_confidence.evidence_confidence < 20.0:
            issues.append("Evidence confidence critically low (<20).")

        if snapshot.decision_confidence.reasoning_confidence < 20.0:
            issues.append("Reasoning confidence critically low (<20).")

        if snapshot.calibration_status == CalibrationStatus.UNCALIBRATED:
            issues.append("Confidence is uncalibrated — calibration data missing.")

        if snapshot.decision_confidence.uncertainty > 30.0:
            warnings.append(
                f"High uncertainty ({snapshot.decision_confidence.uncertainty:.1f}) "
                "across confidence dimensions."
            )

        if not snapshot.decision_confidence.scoring_available:
            warnings.append("Scoring engine output unavailable — scoring dimension is zero.")

        if snapshot.calibration_status == CalibrationStatus.INSUFFICIENT_DATA:
            warnings.append("Calibration has insufficient historical data.")

        is_valid = len(issues) == 0
        is_usable = is_valid and snapshot.is_usable

        return ConfidenceValidationResult(
            is_valid=is_valid,
            is_usable=is_usable,
            issues=tuple(issues),
            warnings=tuple(warnings),
            confidence_score=conf,
            confidence_level=snapshot.confidence_level,
            calibration_status=snapshot.calibration_status,
        )
