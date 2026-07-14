"""iios/investment/decision/confidence/confidence_snapshot.py
ConfidenceSnapshot — immutable, versioned, canonical confidence output.
Downstream Decision Intelligence engines consume ONLY this object.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from iios.investment.decision.confidence.confidence_constants import (
    CalibrationStatus,
    ConfidenceLevel,
    ConfidenceQualityGrade,
)
from iios.investment.decision.confidence.decision_confidence import DecisionConfidence


@dataclass(frozen=True)
class ConfidenceSnapshot:
    """
    Canonical, immutable, versioned confidence output for one decision.
    Produced once; never mutated.  All downstream engines read from this.
    Does NOT contain investment scores or recommendations.
    """
    snapshot_id:              str
    decision_id:              str
    subject_id:               str
    subject_type:             str
    version:                  int
    evidence_snapshot_id:     str
    reasoning_snapshot_id:    str
    scoring_snapshot_id:      Optional[str]     # None when scoring engine not available
    decision_confidence:      DecisionConfidence
    overall_confidence:       float             # 0–100 (fast-access copy)
    confidence_level:         ConfidenceLevel
    calibration_status:       CalibrationStatus
    quality_grade:            ConfidenceQualityGrade
    is_usable:                bool
    estimation_duration_ms:   float
    created_at:               datetime

    @property
    def is_high_confidence(self) -> bool:
        return self.overall_confidence >= 70.0

    @property
    def step_count(self) -> int:
        """Mirrors the reasoning chain step count for convenience."""
        return 0   # populated when chain is available through detail queries

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id":             self.snapshot_id,
            "decision_id":             self.decision_id,
            "subject_id":              self.subject_id,
            "subject_type":            self.subject_type,
            "version":                 self.version,
            "evidence_snapshot_id":    self.evidence_snapshot_id,
            "reasoning_snapshot_id":   self.reasoning_snapshot_id,
            "scoring_snapshot_id":     self.scoring_snapshot_id,
            "overall_confidence":      round(self.overall_confidence, 2),
            "confidence_level":        self.confidence_level.value,
            "calibration_status":      self.calibration_status.value,
            "quality_grade":           self.quality_grade.value,
            "is_usable":               self.is_usable,
            "estimation_duration_ms":  round(self.estimation_duration_ms, 2),
            "created_at":              self.created_at.isoformat(),
            "decision_confidence":     self.decision_confidence.to_dict(),
        }


def build_confidence_snapshot(
    decision_confidence:    DecisionConfidence,
    evidence_snapshot_id:   str,
    reasoning_snapshot_id:  str,
    scoring_snapshot_id:    Optional[str],
    calibration_status:     CalibrationStatus,
    quality_grade:          ConfidenceQualityGrade,
    estimation_start:       datetime,
    version:                int,
) -> ConfidenceSnapshot:
    now = datetime.now(timezone.utc)
    duration_ms = (now - estimation_start).total_seconds() * 1000.0

    is_usable = (
        decision_confidence.overall_confidence >= 30.0
        and calibration_status != CalibrationStatus.UNCALIBRATED
    )

    return ConfidenceSnapshot(
        snapshot_id=str(uuid.uuid4()),
        decision_id=decision_confidence.decision_id,
        subject_id=decision_confidence.subject_id,
        subject_type=decision_confidence.subject_type,
        version=version,
        evidence_snapshot_id=evidence_snapshot_id,
        reasoning_snapshot_id=reasoning_snapshot_id,
        scoring_snapshot_id=scoring_snapshot_id,
        decision_confidence=decision_confidence,
        overall_confidence=decision_confidence.overall_confidence,
        confidence_level=decision_confidence.confidence_level,
        calibration_status=calibration_status,
        quality_grade=quality_grade,
        is_usable=is_usable,
        estimation_duration_ms=round(duration_ms, 2),
        created_at=now,
    )
