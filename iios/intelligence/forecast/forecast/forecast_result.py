"""
iios/intelligence/forecast/forecast/forecast_result.py
=======================================================
ForecastResult — the canonical output of a forecast run.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from ..hypothesis_constants import ForecastHorizon, ForecastType


@dataclass
class ForecastResult:
    """
    Canonical output record produced by the forecast engine.

    Attributes
    ----------
    forecast_id    : Unique identifier.
    hypothesis_id  : Parent hypothesis.
    model_id       : Model that generated this forecast.
    horizon        : Temporal scope.
    forecast_type  : Point / Range / Distribution / …
    value          : Central (point) estimate.
    range_low      : Lower bound of forecast range.
    range_high     : Upper bound of forecast range.
    probability    : Probability the central estimate is correct [0, 1].
    confidence     : Model confidence in the entire forecast [0, 1].
    confidence_interval : CI level (e.g. 0.90 for 90 % CI).
    is_evaluated   : Whether an actual outcome has been recorded.
    actual_value   : Observed outcome (populated post-hoc).
    notes          : Human-readable annotations.
    ttl_s          : Time-to-live in seconds (0 = never expires).
    metadata       : Caller-supplied extras.
    created_at     : Unix timestamp.
    """

    forecast_id:         str              = field(default_factory=lambda: str(uuid.uuid4()))
    hypothesis_id:       str              = ""
    model_id:            str              = ""
    horizon:             ForecastHorizon  = ForecastHorizon.SHORT_TERM
    forecast_type:       ForecastType     = ForecastType.POINT
    value:               float            = 0.0
    range_low:           float            = 0.0
    range_high:          float            = 0.0
    probability:         float            = 0.5
    confidence:          float            = 0.5
    confidence_interval: float            = 0.90
    is_evaluated:        bool             = False
    actual_value:        float | None     = None
    notes:               list[str]        = field(default_factory=list)
    ttl_s:               float            = 3_600.0
    metadata:            dict[str, Any]   = field(default_factory=dict)
    created_at:          float            = field(default_factory=time.time)

    # -- Derived ───────────────────────────────────────────────────────────────

    @property
    def is_expired(self) -> bool:
        if self.ttl_s <= 0:
            return False
        return time.time() - self.created_at > self.ttl_s

    @property
    def range_width(self) -> float:
        return self.range_high - self.range_low

    # -- Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "forecast_id":         self.forecast_id,
            "hypothesis_id":       self.hypothesis_id,
            "model_id":            self.model_id,
            "horizon":             self.horizon.value,
            "forecast_type":       self.forecast_type.value,
            "value":               round(self.value, 6),
            "range_low":           round(self.range_low, 6),
            "range_high":          round(self.range_high, 6),
            "probability":         round(self.probability, 4),
            "confidence":          round(self.confidence, 4),
            "confidence_interval": self.confidence_interval,
            "is_evaluated":        self.is_evaluated,
            "actual_value":        self.actual_value,
            "notes":               list(self.notes),
            "ttl_s":               self.ttl_s,
            "is_expired":          self.is_expired,
            "metadata":            self.metadata,
            "created_at":          self.created_at,
        }
