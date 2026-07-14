"""iios/investment/decision/risk/confidence_risk.py
ConfidenceRiskEvaluator — derives confidence dimension risk directly from
the ConfidenceSnapshot produced by the Decision Confidence Engine.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from iios.investment.decision.confidence.confidence_constants import CalibrationStatus
from iios.investment.decision.confidence.confidence_snapshot import ConfidenceSnapshot


@dataclass(frozen=True)
class ConfidenceRiskResult:
    overall_confidence:    float   # 0–100 from confidence engine
    confidence_gap:        float   # 0–100 (100 - overall_confidence)
    calibration_risk:      float   # 0–100 from calibration status
    evidence_conf_risk:    float   # 0–100 inverse of evidence confidence dim
    reasoning_conf_risk:   float   # 0–100 inverse of reasoning confidence dim
    uncertainty_risk:      float   # 0–100 from uncertainty field
    confidence_risk:       float   # 0–100 composite

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_confidence":  round(self.overall_confidence, 2),
            "confidence_gap":      round(self.confidence_gap, 2),
            "calibration_risk":    round(self.calibration_risk, 2),
            "evidence_conf_risk":  round(self.evidence_conf_risk, 2),
            "reasoning_conf_risk": round(self.reasoning_conf_risk, 2),
            "uncertainty_risk":    round(self.uncertainty_risk, 2),
            "confidence_risk":     round(self.confidence_risk, 2),
        }


_CALIBRATION_RISK: Dict[str, float] = {
    "well_calibrated":      5.0,
    "partially_calibrated": 20.0,
    "poorly_calibrated":    50.0,
    "uncalibrated":         70.0,
}


class ConfidenceRiskEvaluator:
    """Derives confidence dimension risk from ConfidenceSnapshot."""

    def evaluate(self, confidence_snapshot: ConfidenceSnapshot) -> ConfidenceRiskResult:
        dc   = confidence_snapshot.decision_confidence
        conf = confidence_snapshot.overall_confidence

        confidence_gap      = max(0.0, 100.0 - conf)
        calibration_risk    = _CALIBRATION_RISK.get(
            confidence_snapshot.calibration_status.value, 30.0
        )
        evidence_conf_risk  = max(0.0, 100.0 - dc.evidence_confidence)
        reasoning_conf_risk = max(0.0, 100.0 - dc.reasoning_confidence)
        uncertainty_risk    = min(100.0, dc.uncertainty * 2.0)

        confidence_risk = (
            confidence_gap      * 0.35
            + calibration_risk  * 0.20
            + evidence_conf_risk * 0.20
            + reasoning_conf_risk * 0.15
            + uncertainty_risk  * 0.10
        )
        confidence_risk = max(0.0, min(100.0, confidence_risk))

        return ConfidenceRiskResult(
            overall_confidence=round(conf, 4),
            confidence_gap=round(confidence_gap, 4),
            calibration_risk=round(calibration_risk, 4),
            evidence_conf_risk=round(evidence_conf_risk, 4),
            reasoning_conf_risk=round(reasoning_conf_risk, 4),
            uncertainty_risk=round(uncertainty_risk, 4),
            confidence_risk=round(confidence_risk, 4),
        )
