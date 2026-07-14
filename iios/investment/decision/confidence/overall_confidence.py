"""iios/investment/decision/confidence/overall_confidence.py
OverallConfidenceEstimator — combines all dimensions into the final DecisionConfidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from iios.investment.decision.confidence.calibration_engine import CalibrationResult
from iios.investment.decision.confidence.confidence_constants import CalibrationStatus
from iios.investment.decision.confidence.decision_confidence import (
    DecisionConfidence,
    build_decision_confidence,
)
from iios.investment.decision.confidence.evidence_confidence import EvidenceConfidenceResult
from iios.investment.decision.confidence.historical_confidence import (
    HistoricalConfidenceResult,
)
from iios.investment.decision.confidence.reasoning_confidence import (
    ReasoningConfidenceResult,
)


@dataclass(frozen=True)
class OverallConfidenceResult:
    decision_confidence:    DecisionConfidence
    calibration_result:     CalibrationResult
    evidence_detail:        EvidenceConfidenceResult
    reasoning_detail:       ReasoningConfidenceResult
    historical_detail:      HistoricalConfidenceResult
    scoring_confidence_raw: float   # raw scoring engine confidence (0 if unavailable)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_confidence": self.decision_confidence.to_dict(),
            "calibration":         self.calibration_result.to_dict(),
            "evidence_detail":     self.evidence_detail.to_dict(),
            "reasoning_detail":    self.reasoning_detail.to_dict(),
            "historical_detail":   self.historical_detail.to_dict(),
        }


class OverallConfidenceEstimator:
    """Combines all dimension estimates into one DecisionConfidence."""

    def estimate(
        self,
        decision_id:        str,
        subject_id:         str,
        subject_type:       str,
        version:            int,
        evidence_result:    EvidenceConfidenceResult,
        reasoning_result:   ReasoningConfidenceResult,
        historical_result:  HistoricalConfidenceResult,
        calibration_result: CalibrationResult,
        scoring_confidence: float,
        scoring_available:  bool,
    ) -> OverallConfidenceResult:
        dc = build_decision_confidence(
            decision_id=decision_id,
            subject_id=subject_id,
            subject_type=subject_type,
            evidence_confidence=evidence_result.overall,
            reasoning_confidence=reasoning_result.overall,
            scoring_confidence=scoring_confidence,
            historical_confidence=historical_result.historical_conf,
            calibration_quality=calibration_result.quality_score,
            scoring_available=scoring_available,
            version=version,
        )
        return OverallConfidenceResult(
            decision_confidence=dc,
            calibration_result=calibration_result,
            evidence_detail=evidence_result,
            reasoning_detail=reasoning_result,
            historical_detail=historical_result,
            scoring_confidence_raw=scoring_confidence,
        )
