"""
iios/execution/analytics/predictive/predictive_probability.py
=============================================================
PredictiveProbabilityEstimator — estimates operational event
probabilities for the forecast horizon.

Probabilities produced:
  - Recovery probability
  - Failure probability
  - Gateway saturation probability
  - Broker availability probability
  - Performance degradation probability
  - Operational health probability

All estimates are derived from historical rates and trend direction.
NO trading signal generation.

C8 Execution Analytics & Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import uuid
from typing import Dict, List, Optional

from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import FORECASTER_SYSTEM_ID, ForecastHorizon, PredictionDomain, PredictionType
from .exceptions import PredictiveEngineNotRunningError
from .predictive_forecaster import _linear_extrapolate, _mean
from .predictive_response import Forecast, ProbabilityReport

_log = get_logger(__name__)

_RUNNING = frozenset({EngineState.RUNNING, "running"})


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


class PredictiveProbabilityEstimator(LifecycleAwareMixin):
    """
    Estimates operational event probabilities from forecasts and
    historical data.

    Thread-safe.  Must be started before use.
    """

    def _on_start(self) -> None:
        _log.info("PredictiveProbabilityEstimator started.", system_id=FORECASTER_SYSTEM_ID)

    def _on_stop(self) -> None:
        _log.info("PredictiveProbabilityEstimator stopped.", system_id=FORECASTER_SYSTEM_ID)

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in _RUNNING:
            raise PredictiveEngineNotRunningError()

    def estimate(
        self,
        domain:               PredictionDomain,
        horizon:              ForecastHorizon,
        forecasts:            List[Forecast],
        historical_analytics: Optional[Dict[str, List[float]]] = None,
    ) -> ProbabilityReport:
        """
        Estimate probabilities for key operational events.

        Uses terminal forecast values and historical averages.
        """
        self._assert_running()
        hist  = historical_analytics or {}
        probs: Dict[str, float] = {}
        confs: Dict[str, float] = {}

        # Build a fast lookup of forecasts by PredictionType
        forecast_map: Dict[PredictionType, Forecast] = {
            f.prediction_type: f for f in forecasts
        }

        for pt in PredictionType:
            p, c = self._estimate_for_type(pt, forecast_map, hist)
            probs[pt.value] = p
            confs[pt.value] = c

        return ProbabilityReport(
            report_id        = str(uuid.uuid4()),
            domain           = domain,
            horizon          = horizon,
            probabilities    = probs,
            confidence_scores= confs,
        )

    # ── Per-type estimation ───────────────────────────────────────────────────

    def _estimate_for_type(
        self,
        pt:           PredictionType,
        forecast_map: Dict[PredictionType, Forecast],
        hist:         Dict[str, List[float]],
    ):
        """Return (probability, confidence) for a single PredictionType."""
        f   = forecast_map.get(pt)
        h   = hist.get(pt.value, [])

        if f and f.forecast_points:
            # Use terminal forecast value
            terminal = f.terminal_forecast
            conf     = f.confidence
        elif h:
            # Fall back to historical linear extrapolation
            terminal = _linear_extrapolate(h, max(1, len(h) // 5))
            conf     = 0.3
        else:
            return 0.5, 0.1  # no data — neutral probability

        # Map to [0,1] probability based on prediction type semantics
        p = self._value_to_probability(pt, terminal)
        return _clamp(p), _clamp(conf)

    def _value_to_probability(self, pt: PredictionType, value: float) -> float:
        """
        Convert a forecast value to a probability [0, 1].

        - Probability-type predictions (already [0, 1]): returned as-is.
        - Ratio-type predictions: clamped to [0, 1].
        - Volume/latency predictions: normalised by a reference scale.
        """
        # Already probability or ratio
        if pt in (
            PredictionType.RECOVERY_PROBABILITY,
            PredictionType.FAILURE_PROBABILITY,
            PredictionType.GATEWAY_SATURATION,
            PredictionType.BROKER_AVAILABILITY_FORECAST,
            PredictionType.PERFORMANCE_DEGRADATION_RISK,
            PredictionType.INFRASTRUCTURE_UTILIZATION_FORECAST,
            PredictionType.OPERATIONAL_HEALTH_SCORE,
        ):
            return _clamp(value)

        # Capacity forecast: already a utilization ratio
        if pt == PredictionType.CAPACITY_FORECAST:
            return _clamp(value)

        # Volume / latency: use a soft normalisation
        if pt == PredictionType.EXPECTED_LATENCY:
            # Probability that latency stays under threshold (e.g. 200ms)
            ref = 200.0
            return _clamp(1.0 - value / ref if ref > 0 else 0.5)

        if pt == PredictionType.EXECUTION_VOLUME_FORECAST:
            # Probability of exceeding baseline volume (normalised to 0..1)
            return _clamp(value)

        if pt == PredictionType.QUEUE_GROWTH_FORECAST:
            # Higher queue growth = higher probability of congestion
            return _clamp(value)

        return _clamp(value)
