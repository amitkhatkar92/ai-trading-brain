"""iios/investment/decision/risk/risk_confidence.py
RiskConfidenceEstimator — estimates how confident we are IN the risk assessment
(not confidence in the investment decision).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from iios.investment.decision.confidence.confidence_snapshot import ConfidenceSnapshot
from iios.investment.decision.evidence.evidence_snapshot import EvidenceSnapshot
from iios.investment.decision.reasoning.reasoning_snapshot import ReasoningSnapshot
from iios.investment.decision.risk.risk_constants import MIN_EVIDENCE_ITEMS_LOW_RISK


@dataclass(frozen=True)
class RiskConfidenceResult:
    evidence_quality:      float   # 0–100 from EvidenceSnapshot
    reasoning_completeness: float  # 0–100 proxy
    confidence_availability: float # 0–100 (100 if confidence engine ran)
    risk_confidence:       float   # 0–100 overall confidence in risk assessment

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_quality":       round(self.evidence_quality, 2),
            "reasoning_completeness": round(self.reasoning_completeness, 2),
            "confidence_availability": round(self.confidence_availability, 2),
            "risk_confidence":         round(self.risk_confidence, 2),
        }


class RiskConfidenceEstimator:
    """
    Estimates how reliable the current risk assessment is.
    Higher = more trustworthy risk scores.
    """

    def estimate(
        self,
        evidence_snapshot:   EvidenceSnapshot,
        reasoning_snapshot:  ReasoningSnapshot,
        confidence_snapshot: ConfidenceSnapshot,
    ) -> RiskConfidenceResult:
        ev_quality = evidence_snapshot.quality_score   # 0–100

        # Reasoning completeness: step count as proxy
        steps      = reasoning_snapshot.reasoning_chain.step_count
        r_complete = min(100.0, steps * 10.0)

        # Confidence availability: is scoring data present?
        dc = confidence_snapshot.decision_confidence
        c_avail = 100.0 if dc.scoring_available else 70.0

        # Item count adequacy
        items_ok = 1.0 if evidence_snapshot.item_count >= MIN_EVIDENCE_ITEMS_LOW_RISK else 0.5
        ev_quality_adjusted = ev_quality * items_ok

        risk_confidence = (
            ev_quality_adjusted * 0.40
            + r_complete * 0.35
            + c_avail    * 0.25
        )
        risk_confidence = max(0.0, min(100.0, risk_confidence))

        return RiskConfidenceResult(
            evidence_quality=round(ev_quality, 4),
            reasoning_completeness=round(r_complete, 4),
            confidence_availability=round(c_avail, 4),
            risk_confidence=round(risk_confidence, 4),
        )
