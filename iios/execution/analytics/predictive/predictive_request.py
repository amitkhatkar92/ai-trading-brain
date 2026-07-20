"""
iios/execution/analytics/predictive/predictive_request.py
=========================================================
PredictionRequest — immutable request for the Predictive Intelligence Framework.

C8 Execution Analytics & Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from .constants import ACTOR_SYSTEM, VERSION, ForecastHorizon, PredictionDomain, PredictionType


@dataclass(frozen=True)
class PredictionRequest:
    """
    Immutable request submitted to the Predictive Intelligence Engine.

    Fields
    ------
    request_id:          Unique request identifier.
    domain:              Prediction domain.
    prediction_types:    Predictions to compute (empty = all applicable).
    horizon:             Forecast horizon.
    include_trends:      Whether to run trend forecasting.
    include_anomalies:   Whether to run anomaly prediction.
    include_risks:       Whether to produce a risk forecast.
    include_capacity:    Whether to produce a capacity forecast.
    requester:           Actor submitting the request.
    priority:            Dispatch priority (1 = highest).
    reason:              Human-readable reason.
    tags:                Classification tags.
    metadata:            Supplementary data.
    submitted_at:        Wall-time of submission.
    framework_version:   Framework version.
    """

    request_id:         str
    domain:             PredictionDomain
    prediction_types:   Tuple[PredictionType, ...]   = field(default_factory=tuple)
    horizon:            ForecastHorizon              = ForecastHorizon.NEXT_HOUR
    include_trends:     bool                         = True
    include_anomalies:  bool                         = True
    include_risks:      bool                         = True
    include_capacity:   bool                         = True
    requester:          str                          = ACTOR_SYSTEM
    priority:           int                          = 5
    reason:             str                          = ""
    tags:               Tuple[str, ...]               = field(default_factory=tuple)
    metadata:           Dict[str, Any]               = field(default_factory=dict)
    submitted_at:       float                        = field(default_factory=time.time)
    framework_version:  str                          = VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":        self.request_id,
            "domain":            self.domain.value,
            "prediction_types":  [p.value for p in self.prediction_types],
            "horizon":           self.horizon.value,
            "include_trends":    self.include_trends,
            "include_anomalies": self.include_anomalies,
            "include_risks":     self.include_risks,
            "include_capacity":  self.include_capacity,
            "requester":         self.requester,
            "priority":          self.priority,
            "reason":            self.reason,
            "submitted_at":      self.submitted_at,
            "framework_version": self.framework_version,
        }


def make_prediction_request(
    domain:             PredictionDomain,
    *,
    request_id:         Optional[str]                  = None,
    prediction_types:   Tuple[PredictionType, ...]      = (),
    horizon:            ForecastHorizon                = ForecastHorizon.NEXT_HOUR,
    include_trends:     bool                           = True,
    include_anomalies:  bool                           = True,
    include_risks:      bool                           = True,
    include_capacity:   bool                           = True,
    requester:          str                            = ACTOR_SYSTEM,
    priority:           int                            = 5,
    reason:             str                            = "",
    tags:               Tuple[str, ...]                 = (),
    metadata:           Optional[Dict[str, Any]]       = None,
) -> PredictionRequest:
    """Create a new PredictionRequest."""
    return PredictionRequest(
        request_id        = request_id or str(uuid.uuid4()),
        domain            = domain,
        prediction_types  = prediction_types,
        horizon           = horizon,
        include_trends    = include_trends,
        include_anomalies = include_anomalies,
        include_risks     = include_risks,
        include_capacity  = include_capacity,
        requester         = requester,
        priority          = priority,
        reason            = reason,
        tags              = tags,
        metadata          = metadata or {},
    )
