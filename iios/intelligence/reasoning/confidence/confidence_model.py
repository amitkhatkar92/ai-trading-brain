"""
iios/intelligence/reasoning/confidence/confidence_model.py
==========================================================
Multi-dimensional confidence model and component dataclass.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from ..reasoning_constants import (
    ConfidenceLevel,
    CONFIDENCE_WEIGHT_CONSENSUS,
    CONFIDENCE_WEIGHT_EVIDENCE,
    CONFIDENCE_WEIGHT_HISTORICAL,
    CONFIDENCE_WEIGHT_REASONING,
    CONFIDENCE_WEIGHT_SOURCE,
    CONFIDENCE_THRESHOLD_VERY_LOW,
    CONFIDENCE_THRESHOLD_LOW,
    CONFIDENCE_THRESHOLD_MODERATE,
    CONFIDENCE_THRESHOLD_HIGH,
    CONFIDENCE_THRESHOLD_VERY_HIGH,
    CONFIDENCE_THRESHOLD_CERTAIN,
)


@dataclass
class ConfidenceComponent:
    """One dimension of the multi-dimensional confidence model."""
    name:        str
    value:       float          # Raw score [0, 1]
    weight:      float          # Contribution weight
    explanation: str            = ""

    @property
    def weighted_value(self) -> float:
        return max(0.0, min(1.0, self.value)) * self.weight

    def to_dict(self) -> dict[str, Any]:
        return {
            "name":           self.name,
            "value":          round(self.value, 4),
            "weight":         round(self.weight, 4),
            "weighted_value": round(self.weighted_value, 4),
            "explanation":    self.explanation,
        }


@dataclass
class ConfidenceModel:
    """
    Full multi-dimensional confidence model for one reasoning session.

    Dimensions
    ----------
    evidence_confidence    : Quality & consistency of supporting evidence.
    source_confidence      : Reliability of the evidence sources.
    reasoning_confidence   : Quality of the reasoning process itself.
    consensus_confidence   : Degree of agreement among debate participants.
    historical_reliability : Track record of similar past conclusions.
    risk_adjustment        : Multiplicative penalty for high-risk conclusions [0,1].
    """

    model_id:               str                       = field(
        default_factory=lambda: str(uuid.uuid4())
    )
    evidence_confidence:    float                     = 0.0
    source_confidence:      float                     = 0.0
    reasoning_confidence:   float                     = 0.0
    consensus_confidence:   float                     = 0.0
    historical_reliability: float                     = 0.5    # neutral default
    risk_adjustment:        float                     = 1.0    # no risk penalty by default
    final_score:            float                     = 0.0
    components:             list[ConfidenceComponent] = field(default_factory=list)
    explanation:            str                       = ""
    computed_at:            float | None              = None

    # -- Computation ───────────────────────────────────────────────────────────

    def compute(self) -> float:
        """
        Compute the final confidence score from all dimensions.
        Stores the result in ``final_score`` and returns it.
        """
        weighted_sum = (
            CONFIDENCE_WEIGHT_EVIDENCE   * max(0.0, min(1.0, self.evidence_confidence))
            + CONFIDENCE_WEIGHT_SOURCE   * max(0.0, min(1.0, self.source_confidence))
            + CONFIDENCE_WEIGHT_REASONING * max(0.0, min(1.0, self.reasoning_confidence))
            + CONFIDENCE_WEIGHT_CONSENSUS * max(0.0, min(1.0, self.consensus_confidence))
            + CONFIDENCE_WEIGHT_HISTORICAL * max(0.0, min(1.0, self.historical_reliability))
        )
        total_weight = (
            CONFIDENCE_WEIGHT_EVIDENCE
            + CONFIDENCE_WEIGHT_SOURCE
            + CONFIDENCE_WEIGHT_REASONING
            + CONFIDENCE_WEIGHT_CONSENSUS
            + CONFIDENCE_WEIGHT_HISTORICAL
        )
        base_score = weighted_sum / total_weight if total_weight > 0 else 0.0
        self.final_score = base_score * max(0.0, min(1.0, self.risk_adjustment))
        self.computed_at = time.time()
        return self.final_score

    # -- Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def score_to_level(score: float) -> ConfidenceLevel:
        if score >= CONFIDENCE_THRESHOLD_CERTAIN:
            return ConfidenceLevel.CERTAIN
        if score >= CONFIDENCE_THRESHOLD_VERY_HIGH:
            return ConfidenceLevel.VERY_HIGH
        if score >= CONFIDENCE_THRESHOLD_HIGH:
            return ConfidenceLevel.HIGH
        if score >= CONFIDENCE_THRESHOLD_MODERATE:
            return ConfidenceLevel.MODERATE
        if score >= CONFIDENCE_THRESHOLD_LOW:
            return ConfidenceLevel.LOW
        return ConfidenceLevel.VERY_LOW

    # -- Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_id":               self.model_id,
            "evidence_confidence":    round(self.evidence_confidence, 4),
            "source_confidence":      round(self.source_confidence, 4),
            "reasoning_confidence":   round(self.reasoning_confidence, 4),
            "consensus_confidence":   round(self.consensus_confidence, 4),
            "historical_reliability": round(self.historical_reliability, 4),
            "risk_adjustment":        round(self.risk_adjustment, 4),
            "final_score":            round(self.final_score, 4),
            "confidence_level":       self.score_to_level(self.final_score).value,
            "components":             [c.to_dict() for c in self.components],
            "explanation":            self.explanation,
            "computed_at":            self.computed_at,
        }
