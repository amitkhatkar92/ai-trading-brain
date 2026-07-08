"""
iios/intelligence/forecast/evaluation/prediction_accuracy.py
=============================================================
Stateless functions that compute forecast accuracy metrics.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from ..hypothesis_constants import EvaluationMetric
from ..hypothesis_exceptions import EvaluationMetricError
from ..forecast.forecast_statistics import mae, rmse, mape, directional_accuracy


@dataclass
class AccuracyScore:
    """Single metric result."""

    metric:    EvaluationMetric
    value:     float
    label:     str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric": self.metric.value,
            "value":  round(self.value, 6),
            "label":  self.label,
        }


@dataclass
class AccuracyReport:
    """Aggregated accuracy across metrics."""

    forecast_id:  str                   = ""
    actual_value: float                 = 0.0
    predicted:    float                 = 0.0
    scores:       list[AccuracyScore]   = field(default_factory=list)
    composite:    float                 = 0.0   # [0, 1], higher = better
    metadata:     dict[str, Any]        = field(default_factory=dict)

    def score_for(self, metric: EvaluationMetric) -> float | None:
        for s in self.scores:
            if s.metric == metric:
                return s.value
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "forecast_id":  self.forecast_id,
            "actual_value": self.actual_value,
            "predicted":    self.predicted,
            "scores":       [s.to_dict() for s in self.scores],
            "composite":    round(self.composite, 4),
            "metadata":     self.metadata,
        }


def compute_accuracy(
    forecast_id:  str,
    predicted:    float,
    actual:       float,
    range_low:    float | None = None,
    range_high:   float | None = None,
) -> AccuracyReport:
    """
    Compute all available accuracy metrics for a single (predicted, actual) pair.
    Calibration and sharpness require range bounds.
    """
    scores: list[AccuracyScore] = []

    # MAE
    try:
        v = abs(predicted - actual)
        scores.append(AccuracyScore(EvaluationMetric.MAE, v, "Mean Absolute Error"))
    except Exception as exc:
        raise EvaluationMetricError("MAE", str(exc)) from exc

    # RMSE (single-sample ≡ abs error)
    try:
        scores.append(AccuracyScore(EvaluationMetric.RMSE, abs(predicted - actual), "RMSE"))
    except Exception as exc:
        raise EvaluationMetricError("RMSE", str(exc)) from exc

    # MAPE
    try:
        mape_v = abs((predicted - actual) / actual) if actual != 0 else 0.0
        scores.append(AccuracyScore(EvaluationMetric.MAPE, mape_v, "MAPE"))
    except Exception as exc:
        raise EvaluationMetricError("MAPE", str(exc)) from exc

    # Directional accuracy (1 if correct sign, 0 if not)
    try:
        dir_acc = 1.0 if (predicted >= 0) == (actual >= 0) else 0.0
        scores.append(AccuracyScore(EvaluationMetric.ACCURACY, dir_acc, "Directional Accuracy"))
    except Exception as exc:
        raise EvaluationMetricError("ACCURACY", str(exc)) from exc

    # Calibration (actual within CI range?)
    if range_low is not None and range_high is not None:
        try:
            calibrated = 1.0 if range_low <= actual <= range_high else 0.0
            scores.append(AccuracyScore(EvaluationMetric.CALIBRATION, calibrated, "Calibration"))
        except Exception as exc:
            raise EvaluationMetricError("CALIBRATION", str(exc)) from exc

        # Sharpness (1 - relative CI width; lower CI width = sharper)
        try:
            width    = range_high - range_low
            scale    = abs(actual) if actual != 0 else 1.0
            sharpness = max(0.0, 1.0 - width / scale)
            scores.append(AccuracyScore(EvaluationMetric.SHARPNESS, sharpness, "Sharpness"))
        except Exception as exc:
            raise EvaluationMetricError("SHARPNESS", str(exc)) from exc

    # Composite: mean of accuracy scores where higher = better
    # MAE, RMSE, MAPE are error metrics → normalise to 1/(1+err)
    accuracy_vals = []
    for s in scores:
        if s.metric in (EvaluationMetric.MAE, EvaluationMetric.RMSE, EvaluationMetric.MAPE):
            accuracy_vals.append(1.0 / (1.0 + s.value))
        else:
            accuracy_vals.append(s.value)
    composite = sum(accuracy_vals) / len(accuracy_vals) if accuracy_vals else 0.0

    return AccuracyReport(
        forecast_id  = forecast_id,
        actual_value = actual,
        predicted    = predicted,
        scores       = scores,
        composite    = composite,
    )
