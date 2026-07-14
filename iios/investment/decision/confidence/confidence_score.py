"""iios/investment/decision/confidence/confidence_score.py
ConfidenceScore dataclass and compute_confidence_score() factory function.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict

from iios.investment.decision.confidence.confidence_constants import (
    ConfidenceLevel,
    ConfidenceQualityGrade,
    EVIDENCE_DIM_WEIGHT,
    REASONING_DIM_WEIGHT,
    SCORING_DIM_WEIGHT,
    HISTORICAL_DIM_WEIGHT,
    CALIBRATION_DIM_WEIGHT,
)


@dataclass(frozen=True)
class ConfidenceScore:
    """
    Final scalar confidence score with dimensional breakdown.
    Immutable — produced once per estimation.
    """
    overall:           float    # 0–100
    evidence:          float    # 0–100
    reasoning:         float    # 0–100
    scoring:           float    # 0–100
    historical:        float    # 0–100
    calibration:       float    # 0–100
    level:             ConfidenceLevel
    grade:             ConfidenceQualityGrade
    computed_at:       datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall":     round(self.overall, 2),
            "evidence":    round(self.evidence, 2),
            "reasoning":   round(self.reasoning, 2),
            "scoring":     round(self.scoring, 2),
            "historical":  round(self.historical, 2),
            "calibration": round(self.calibration, 2),
            "level":       self.level.value,
            "grade":       self.grade.value,
            "computed_at": self.computed_at.isoformat(),
        }


def compute_confidence_score(
    evidence:    float,
    reasoning:   float,
    scoring:     float,
    historical:  float,
    calibration: float,
    *,
    ev_weight:  float = EVIDENCE_DIM_WEIGHT,
    re_weight:  float = REASONING_DIM_WEIGHT,
    sc_weight:  float = SCORING_DIM_WEIGHT,
    hi_weight:  float = HISTORICAL_DIM_WEIGHT,
    ca_weight:  float = CALIBRATION_DIM_WEIGHT,
) -> ConfidenceScore:
    """Factory: compute and return an immutable ConfidenceScore."""
    overall = (
        evidence    * ev_weight
        + reasoning * re_weight
        + scoring   * sc_weight
        + historical * hi_weight
        + calibration * ca_weight
    )
    overall = max(0.0, min(100.0, overall))

    return ConfidenceScore(
        overall=round(overall, 4),
        evidence=round(evidence, 4),
        reasoning=round(reasoning, 4),
        scoring=round(scoring, 4),
        historical=round(historical, 4),
        calibration=round(calibration, 4),
        level=ConfidenceLevel.from_score(overall),
        grade=ConfidenceQualityGrade.from_score(overall),
        computed_at=datetime.now(timezone.utc),
    )
