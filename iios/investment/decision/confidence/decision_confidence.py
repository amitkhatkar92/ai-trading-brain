"""iios/investment/decision/confidence/decision_confidence.py
DecisionConfidence — the core output dataclass from one confidence estimation pass.
Immutable after construction.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from iios.investment.decision.confidence.confidence_constants import (
    ConfidenceDimension,
    ConfidenceLevel,
    EVIDENCE_DIM_WEIGHT,
    REASONING_DIM_WEIGHT,
    SCORING_DIM_WEIGHT,
    HISTORICAL_DIM_WEIGHT,
    CALIBRATION_DIM_WEIGHT,
)


@dataclass(frozen=True)
class DecisionConfidence:
    """
    Complete confidence estimation for one investment decision.
    Produced by the pipeline; consumed by ConfidenceSnapshot and downstream engines.
    Never contains investment recommendations or scores.
    """
    confidence_id:         str
    decision_id:           str
    subject_id:            str
    subject_type:          str
    # ── dimension scores ──────────────────────────────────────────────────
    evidence_confidence:   float    # 0–100
    reasoning_confidence:  float    # 0–100
    scoring_confidence:    float    # 0–100  (0 when no scoring snapshot)
    historical_confidence: float    # 0–100
    calibration_quality:   float    # 0–100
    # ── aggregate ─────────────────────────────────────────────────────────
    overall_confidence:    float    # 0–100 weighted
    confidence_level:      ConfidenceLevel
    # ── metadata ──────────────────────────────────────────────────────────
    dimension_weights:     Tuple[Tuple[str, float], ...]  # (dim_name, weight)
    scoring_available:     bool
    uncertainty:           float    # 0–100  higher = more uncertain
    version:               int
    computed_at:           datetime

    @property
    def is_high_confidence(self) -> bool:
        return self.confidence_level.is_actionable and self.overall_confidence >= 70.0

    def dimension_score(self, dim: ConfidenceDimension) -> float:
        mapping = {
            ConfidenceDimension.EVIDENCE:    self.evidence_confidence,
            ConfidenceDimension.REASONING:   self.reasoning_confidence,
            ConfidenceDimension.SCORING:     self.scoring_confidence,
            ConfidenceDimension.HISTORICAL:  self.historical_confidence,
            ConfidenceDimension.CALIBRATION: self.calibration_quality,
        }
        return mapping[dim]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "confidence_id":         self.confidence_id,
            "decision_id":           self.decision_id,
            "subject_id":            self.subject_id,
            "subject_type":          self.subject_type,
            "evidence_confidence":   round(self.evidence_confidence, 2),
            "reasoning_confidence":  round(self.reasoning_confidence, 2),
            "scoring_confidence":    round(self.scoring_confidence, 2),
            "historical_confidence": round(self.historical_confidence, 2),
            "calibration_quality":   round(self.calibration_quality, 2),
            "overall_confidence":    round(self.overall_confidence, 2),
            "confidence_level":      self.confidence_level.value,
            "uncertainty":           round(self.uncertainty, 2),
            "scoring_available":     self.scoring_available,
            "version":               self.version,
            "computed_at":           self.computed_at.isoformat(),
        }


def build_decision_confidence(
    decision_id:           str,
    subject_id:            str,
    subject_type:          str,
    evidence_confidence:   float,
    reasoning_confidence:  float,
    scoring_confidence:    float,
    historical_confidence: float,
    calibration_quality:   float,
    scoring_available:     bool,
    version:               int,
    *,
    ev_weight:   float = EVIDENCE_DIM_WEIGHT,
    re_weight:   float = REASONING_DIM_WEIGHT,
    sc_weight:   float = SCORING_DIM_WEIGHT,
    hi_weight:   float = HISTORICAL_DIM_WEIGHT,
    ca_weight:   float = CALIBRATION_DIM_WEIGHT,
) -> DecisionConfidence:
    """
    Factory that builds and returns a frozen DecisionConfidence.
    Re-distributes scoring weight to evidence+reasoning when scoring is unavailable.
    """
    if not scoring_available:
        freed = sc_weight
        ev_weight = round(ev_weight + freed / 2, 6)
        re_weight = round(re_weight + freed / 2, 6)
        sc_weight = 0.0

    overall = (
        evidence_confidence   * ev_weight
        + reasoning_confidence  * re_weight
        + scoring_confidence    * sc_weight
        + historical_confidence * hi_weight
        + calibration_quality   * ca_weight
    )
    overall = max(0.0, min(100.0, overall))

    # Uncertainty: spread across dimensions
    scores = [
        evidence_confidence,
        reasoning_confidence,
        *([] if not scoring_available else [scoring_confidence]),
        historical_confidence,
        calibration_quality,
    ]
    mean = sum(scores) / len(scores)
    variance = sum((s - mean) ** 2 for s in scores) / len(scores)
    import math
    uncertainty = min(100.0, math.sqrt(variance))

    weights_tuple: Tuple[Tuple[str, float], ...] = (
        (ConfidenceDimension.EVIDENCE.value,    ev_weight),
        (ConfidenceDimension.REASONING.value,   re_weight),
        (ConfidenceDimension.SCORING.value,     sc_weight),
        (ConfidenceDimension.HISTORICAL.value,  hi_weight),
        (ConfidenceDimension.CALIBRATION.value, ca_weight),
    )

    return DecisionConfidence(
        confidence_id=str(uuid.uuid4()),
        decision_id=decision_id,
        subject_id=subject_id,
        subject_type=subject_type,
        evidence_confidence=round(evidence_confidence, 4),
        reasoning_confidence=round(reasoning_confidence, 4),
        scoring_confidence=round(scoring_confidence, 4),
        historical_confidence=round(historical_confidence, 4),
        calibration_quality=round(calibration_quality, 4),
        overall_confidence=round(overall, 4),
        confidence_level=ConfidenceLevel.from_score(overall),
        dimension_weights=weights_tuple,
        scoring_available=scoring_available,
        uncertainty=round(uncertainty, 4),
        version=version,
        computed_at=datetime.now(timezone.utc),
    )
