"""models/model_profile.py — Runtime performance snapshot for a deployed model."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ModelProfile:
    """
    Running statistics for a live model.

    Updated by the MonitoringEngine after each prediction batch.
    """
    model_id:             str
    model_version:        str
    total_predictions:    int
    predictions_per_sec:  float       # rolling average
    avg_latency_ms:       float
    p95_latency_ms:       float
    error_rate:           float       # fraction of calls that raised
    last_prediction_at:   Optional[float]
    uptime_sec:           float
    drift_score:          float       # 0.0 = no drift, 1.0 = max drift
    last_evaluated_at:    Optional[float]
    current_metrics:      dict[str, float]
    baseline_metrics:     dict[str, float]
    extra:                dict[str, Any]

    @classmethod
    def create(
        cls,
        model_id:        str,
        model_version:   str,
        baseline_metrics: Optional[dict] = None,
    ) -> "ModelProfile":
        return cls(
            model_id            = model_id,
            model_version       = model_version,
            total_predictions   = 0,
            predictions_per_sec = 0.0,
            avg_latency_ms      = 0.0,
            p95_latency_ms      = 0.0,
            error_rate          = 0.0,
            last_prediction_at  = None,
            uptime_sec          = 0.0,
            drift_score         = 0.0,
            last_evaluated_at   = None,
            current_metrics     = {},
            baseline_metrics    = baseline_metrics or {},
            extra               = {},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_id":             self.model_id,
            "model_version":        self.model_version,
            "total_predictions":    self.total_predictions,
            "predictions_per_sec":  self.predictions_per_sec,
            "avg_latency_ms":       self.avg_latency_ms,
            "p95_latency_ms":       self.p95_latency_ms,
            "error_rate":           self.error_rate,
            "last_prediction_at":   self.last_prediction_at,
            "uptime_sec":           self.uptime_sec,
            "drift_score":          self.drift_score,
            "last_evaluated_at":    self.last_evaluated_at,
            "current_metrics":      self.current_metrics,
            "baseline_metrics":     self.baseline_metrics,
        }
