"""
iios/intelligence/forecast/hypothesis_result.py
===============================================
Output models for the Hypothesis & Forecast Engine.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from .hypothesis_constants import (
    HypothesisStatus,
    ForecastHorizon,
    ForecastType,
    EvaluationMetric,
)


@dataclass
class HypothesisResult:
    """
    Terminal output of a hypothesis evaluation cycle.

    Attributes
    ----------
    result_id        : Unique identifier for this result.
    hypothesis_id    : Source hypothesis.
    status           : CONFIRMED / REJECTED / SUSPENDED.
    probability      : Updated posterior probability [0, 1].
    confidence       : Confidence in the status assessment [0, 1].
    evidence_ids     : Evidence that influenced this result.
    forecast_ids     : Forecasts generated under this hypothesis.
    supporting_count : Number of supporting evidence/forecast items.
    opposing_count   : Number of opposing items.
    summary          : Human-readable conclusion.
    duration_ms      : Time to reach this result.
    metadata         : Caller-supplied extras.
    created_at       : Unix timestamp.
    """

    result_id:        str                = field(default_factory=lambda: str(uuid.uuid4()))
    hypothesis_id:    str                = ""
    status:           HypothesisStatus   = HypothesisStatus.ACTIVE
    probability:      float              = 0.5
    confidence:       float              = 0.0
    evidence_ids:     list[str]          = field(default_factory=list)
    forecast_ids:     list[str]          = field(default_factory=list)
    supporting_count: int                = 0
    opposing_count:   int                = 0
    summary:          str                = ""
    duration_ms:      float              = 0.0
    metadata:         dict[str, Any]     = field(default_factory=dict)
    created_at:       float              = field(default_factory=time.time)

    @property
    def is_confirmed(self) -> bool:
        return self.status == HypothesisStatus.CONFIRMED

    @property
    def is_rejected(self) -> bool:
        return self.status == HypothesisStatus.REJECTED

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_id":        self.result_id,
            "hypothesis_id":    self.hypothesis_id,
            "status":           self.status.value,
            "probability":      round(self.probability, 4),
            "confidence":       round(self.confidence, 4),
            "evidence_ids":     self.evidence_ids,
            "forecast_ids":     self.forecast_ids,
            "supporting_count": self.supporting_count,
            "opposing_count":   self.opposing_count,
            "summary":          self.summary,
            "duration_ms":      round(self.duration_ms, 2),
            "metadata":         self.metadata,
            "created_at":       self.created_at,
        }


@dataclass
class ForecastOutput:
    """
    Lightweight output from a single forecast step.
    Suitable for pipeline composition.
    """

    output_id:     str            = field(default_factory=lambda: str(uuid.uuid4()))
    forecaster_id: str            = ""
    hypothesis_id: str            = ""
    horizon:       ForecastHorizon = ForecastHorizon.SHORT_TERM
    forecast_type: ForecastType   = ForecastType.POINT
    value:         float          = 0.0
    range_low:     float          = 0.0
    range_high:    float          = 0.0
    probability:   float          = 0.5
    confidence:    float          = 0.5
    explanation:   str            = ""
    duration_ms:   float          = 0.0
    metadata:      dict[str, Any] = field(default_factory=dict)
    created_at:    float          = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "output_id":     self.output_id,
            "forecaster_id": self.forecaster_id,
            "hypothesis_id": self.hypothesis_id,
            "horizon":       self.horizon.value,
            "forecast_type": self.forecast_type.value,
            "value":         round(self.value, 6),
            "range_low":     round(self.range_low, 6),
            "range_high":    round(self.range_high, 6),
            "probability":   round(self.probability, 4),
            "confidence":    round(self.confidence, 4),
            "explanation":   self.explanation,
            "duration_ms":   round(self.duration_ms, 2),
            "metadata":      self.metadata,
            "created_at":    self.created_at,
        }
