"""
iios/execution/analytics/predictive/predictive_anomaly_detector.py
==================================================================
PredictiveAnomalyDetector — detects anomalies in historical data and
predicts anomaly probability for the forecast horizon.

Detection method: Z-score (> 3σ = anomaly).
Prediction: If the current trend extrapolates toward the anomaly zone,
return a non-zero anomaly probability.

C8 Execution Analytics & Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional

from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import FORECASTER_SYSTEM_ID, ForecastHorizon, PredictionDomain, PredictionType
from .exceptions import PredictiveEngineNotRunningError
from .predictive_forecaster import _linear_extrapolate, _mean, _std_dev

_log = get_logger(__name__)

_RUNNING = frozenset({EngineState.RUNNING, "running"})

_Z_ANOMALY   = 3.0   # Z-score threshold for anomaly
_Z_WARNING   = 2.0   # Z-score threshold for warning


@dataclass(frozen=True)
class AnomalyResult:
    """Result of an anomaly detection pass."""

    anomalies_detected:   int     = 0
    anomaly_probability:  float   = 0.0  # probability a future point is anomalous
    warning_count:        int     = 0
    mean_value:           float   = 0.0
    std_dev:              float   = 0.0
    forecast_z_score:     float   = 0.0  # Z-score of the terminal forecast
    data_points:          int     = 0


class PredictiveAnomalyDetector(LifecycleAwareMixin):
    """
    Detects historical anomalies and estimates future anomaly probability.

    Thread-safe.  Must be started before use.
    """

    def _on_start(self) -> None:
        _log.info("PredictiveAnomalyDetector started.", system_id=FORECASTER_SYSTEM_ID)

    def _on_stop(self) -> None:
        _log.info("PredictiveAnomalyDetector stopped.", system_id=FORECASTER_SYSTEM_ID)

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in _RUNNING:
            raise PredictiveEngineNotRunningError()

    def detect(
        self,
        values:          List[float],
        horizon_steps:   int = 5,
    ) -> AnomalyResult:
        """
        Detect historical anomalies and estimate future anomaly probability.

        Parameters
        ----------
        values:        Historical time-series (oldest first).
        horizon_steps: Number of steps ahead to consider for anomaly probability.
        """
        self._assert_running()
        n = len(values)
        if n < 3:
            return AnomalyResult(data_points=n)

        mean_val = _mean(values)
        std      = _std_dev(values)

        if std == 0.0:
            return AnomalyResult(mean_value=mean_val, data_points=n)

        anomaly_count = sum(1 for v in values if abs(v - mean_val) / std > _Z_ANOMALY)
        warning_count = sum(1 for v in values if _Z_WARNING < abs(v - mean_val) / std <= _Z_ANOMALY)

        # Estimate anomaly probability for forecast window using trend extrapolation
        # If the terminal forecast is within the anomaly zone, probability rises
        terminal = _linear_extrapolate(values, horizon_steps)
        forecast_z = abs(terminal - mean_val) / std
        # Probability sigmoid: 0 at z=0, 0.5 at z=2, ~1 at z=5
        anomaly_prob = min(1.0, max(0.0, (forecast_z - _Z_WARNING) / (_Z_ANOMALY - _Z_WARNING)))
        # Also factor in historical anomaly rate
        hist_rate = anomaly_count / n
        combined  = min(1.0, (anomaly_prob + hist_rate) / 2.0)

        return AnomalyResult(
            anomalies_detected  = anomaly_count,
            anomaly_probability = combined,
            warning_count       = warning_count,
            mean_value          = mean_val,
            std_dev             = std,
            forecast_z_score    = forecast_z,
            data_points         = n,
        )
