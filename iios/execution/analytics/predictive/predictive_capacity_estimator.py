"""
iios/execution/analytics/predictive/predictive_capacity_estimator.py
====================================================================
PredictiveCapacityEstimator — estimates future capacity utilization
and identifies bottleneck risks.

Uses linear extrapolation of utilization history to project forward.
Maps projected utilization to a RiskLevel.

C8 Execution Analytics & Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import uuid
from typing import List, Optional

from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import (
    FORECASTER_SYSTEM_ID,
    HORIZON_SECONDS,
    ForecastHorizon,
    PredictionDomain,
    RiskLevel,
    risk_score_to_level,
)
from .exceptions import PredictiveEngineNotRunningError
from .predictive_forecaster import _compute_confidence, _linear_extrapolate, _mean
from .predictive_response import CapacityForecast

_log = get_logger(__name__)

_RUNNING = frozenset({EngineState.RUNNING, "running"})

# Utilization risk thresholds
_UTIL_CRITICAL = 0.90
_UTIL_HIGH     = 0.80
_UTIL_MEDIUM   = 0.65
_UTIL_LOW      = 0.50


def _utilization_to_risk_score(utilization: float) -> float:
    """Map utilization to a risk score [0, 1]."""
    # Risk grows non-linearly as utilization increases
    clamped = min(1.0, max(0.0, utilization))
    return clamped ** 2


class PredictiveCapacityEstimator(LifecycleAwareMixin):
    """
    Estimates future capacity utilization and bottleneck risks.

    Thread-safe.  Must be started before use.
    """

    def _on_start(self) -> None:
        _log.info("PredictiveCapacityEstimator started.", system_id=FORECASTER_SYSTEM_ID)

    def _on_stop(self) -> None:
        _log.info("PredictiveCapacityEstimator stopped.", system_id=FORECASTER_SYSTEM_ID)

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in _RUNNING:
            raise PredictiveEngineNotRunningError()

    def estimate(
        self,
        domain:               PredictionDomain,
        horizon:              ForecastHorizon,
        utilization_history:  List[float],
        custom_horizon_s:     float = 0.0,
    ) -> CapacityForecast:
        """
        Estimate capacity utilization for the given horizon.

        Parameters
        ----------
        domain:               Prediction domain.
        horizon:              Forecast horizon.
        utilization_history:  Historical utilization values [0, 1] (oldest first).
        custom_horizon_s:     Override for CUSTOM horizon.
        """
        self._assert_running()
        h_seconds   = (
            custom_horizon_s if horizon == ForecastHorizon.CUSTOM and custom_horizon_s > 0
            else HORIZON_SECONDS.get(horizon, 3600.0)
        )
        n           = len(utilization_history)
        current     = utilization_history[-1] if utilization_history else 0.0

        if n < 2:
            forecasted  = current
            confidence  = 0.2
        else:
            steps       = max(1, int(h_seconds / 60))  # steps in ~1-min units
            forecasted  = _linear_extrapolate(utilization_history, steps)
            forecasted  = min(1.0, max(0.0, forecasted))
            confidence  = _compute_confidence(utilization_history, forecasted, n)

        headroom      = max(0.0, 1.0 - forecasted)
        risk_score    = _utilization_to_risk_score(forecasted)
        risk_level    = risk_score_to_level(risk_score)

        return CapacityForecast(
            capacity_id           = str(uuid.uuid4()),
            domain                = domain,
            horizon               = horizon,
            current_utilization   = min(1.0, max(0.0, current)),
            forecasted_utilization= forecasted,
            capacity_headroom     = headroom,
            bottleneck_risk       = risk_score,
            risk_level            = risk_level,
            confidence            = confidence,
        )
