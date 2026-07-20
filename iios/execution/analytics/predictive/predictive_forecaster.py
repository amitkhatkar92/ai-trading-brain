"""
iios/execution/analytics/predictive/predictive_forecaster.py
============================================================
PredictiveForecaster — generates operational Forecasts from historical
time-series data using pure-Python algorithms.

Supported algorithms:
  - LINEAR:       Ordinary least-squares extrapolation
  - EXPONENTIAL:  Holt's double exponential smoothing
  - HYBRID:       OLS trend direction + EWM level

All math is pure Python.  No external numeric libraries.
NO predictive trading signals.  NO trade execution.

C8 Execution Analytics & Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import math
import uuid
from typing import Dict, List, Optional

from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import (
    DEFAULT_CONFIDENCE,
    DEFAULT_FORECAST_POINTS,
    FORECASTER_SYSTEM_ID,
    HORIZON_SECONDS,
    ConfidenceLevel,
    ForecastAlgorithm,
    ForecastHorizon,
    PredictionDomain,
    PredictionType,
    TrendType,
    confidence_to_level,
)
from .exceptions import PredictiveEngineNotRunningError
from .predictive_model_registry import ForecastModel, PredictiveModelRegistry
from .predictive_response import Forecast, ForecastPoint

_log = get_logger(__name__)

_RUNNING = frozenset({EngineState.RUNNING, "running"})

# Z-score for 95% prediction interval
_Z95 = 1.960
# Slope threshold ratio (1% of mean) to distinguish FLAT from trending
_SLOPE_THRESHOLD_RATIO = 0.01
# CV threshold for VOLATILE classification
_CV_VOLATILE = 0.5


# ── Pure-Python math ──────────────────────────────────────────────────────────

def _mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _std_dev(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / (len(values) - 1))


def _ols_slope_intercept(values: List[float]):
    """Return (slope, intercept) from OLS fit to y=a+b*x, x=0..n-1."""
    n = len(values)
    if n < 2:
        return 0.0, values[0] if values else 0.0
    x_mean = (n - 1) / 2.0
    y_mean = _mean(values)
    num   = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    denom = sum((i - x_mean) ** 2 for i in range(n))
    slope = num / denom if denom else 0.0
    return slope, y_mean - slope * x_mean


def _linear_extrapolate(values: List[float], steps: int) -> float:
    """Project `steps` periods ahead using OLS."""
    slope, intercept = _ols_slope_intercept(values)
    return intercept + slope * (len(values) - 1 + steps)


def _holt_extrapolate(values: List[float], steps: int, alpha: float = 0.4, beta: float = 0.3) -> float:
    """
    Holt's double exponential smoothing.

    Level:  L_t = alpha * y_t + (1 - alpha) * (L_{t-1} + T_{t-1})
    Trend:  T_t = beta  * (L_t - L_{t-1}) + (1 - beta) * T_{t-1}
    Forecast: L_n + steps * T_n
    """
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    level = values[0]
    trend = values[1] - values[0]
    for v in values[1:]:
        prev_level = level
        level = alpha * v + (1 - alpha) * (level + trend)
        trend = beta  * (level - prev_level) + (1 - beta) * trend
    return level + steps * trend


def _hybrid_extrapolate(values: List[float], steps: int) -> float:
    """
    Hybrid: OLS trend direction weights exponential smoothing result.
    """
    if not values:
        return 0.0
    exp_val  = _holt_extrapolate(values, steps)
    lin_val  = _linear_extrapolate(values, steps)
    # Blend 60% exponential + 40% linear
    return 0.6 * exp_val + 0.4 * lin_val


def _compute_confidence(values: List[float], forecast_value: float, data_points: int) -> float:
    """
    Compute forecast confidence based on:
    - Sample size (more data → higher confidence)
    - Coefficient of variation (lower CV → higher confidence)
    - Forecast deviation from recent average
    """
    if data_points < 3:
        return max(0.1, min(0.45, 0.2 * data_points))
    mean_val = _mean(values)
    std      = _std_dev(values)
    cv       = (std / abs(mean_val)) if mean_val != 0 else 1.0
    # Base confidence from CV
    base = max(0.1, 1.0 - min(cv, 1.0))
    # Slight boost for larger samples (max +0.1 at 30+ samples)
    sample_boost = min(0.1, (data_points - 3) * 0.005)
    # Penalise extreme forecasts
    if std > 0:
        deviation_penalty = min(0.3, abs(forecast_value - mean_val) / std * 0.05)
    else:
        deviation_penalty = 0.0
    return max(0.1, min(0.95, base + sample_boost - deviation_penalty))


# Prediction types where LOWER values are BETTER (rising = degrading, falling = improving)
_LOWER_IS_BETTER_FC: frozenset = frozenset({
    PredictionType.EXPECTED_LATENCY,
    PredictionType.GATEWAY_SATURATION,
    PredictionType.FAILURE_PROBABILITY,
    PredictionType.QUEUE_GROWTH_FORECAST,
    PredictionType.PERFORMANCE_DEGRADATION_RISK,
    PredictionType.INFRASTRUCTURE_UTILIZATION_FORECAST,
})


def _classify_trend(
    values:          List[float],
    slope:           float,
    prediction_type: Optional["PredictionType"] = None,
) -> TrendType:
    """Classify the trend direction, respecting metric polarity."""
    if len(values) < 2:
        return TrendType.UNKNOWN
    mean_val = _mean(values)
    std      = _std_dev(values)
    cv = (std / abs(mean_val)) if mean_val != 0 else 0.0
    if cv > _CV_VOLATILE:
        return TrendType.VOLATILE
    threshold = abs(mean_val * _SLOPE_THRESHOLD_RATIO) if mean_val != 0 else 1e-9
    lower_is_better = prediction_type in _LOWER_IS_BETTER_FC
    if slope > threshold:
        return TrendType.DEGRADING if lower_is_better else TrendType.IMPROVING
    if slope < -threshold:
        return TrendType.IMPROVING if lower_is_better else TrendType.DEGRADING
    return TrendType.STABLE


def _build_points(
    values:          List[float],
    algorithm:       ForecastAlgorithm,
    horizon_seconds: float,
    n_points:        int = DEFAULT_FORECAST_POINTS,
) -> List[ForecastPoint]:
    """Build N evenly-spaced ForecastPoint objects across the horizon."""
    if not values:
        return []
    step_s    = horizon_seconds / n_points
    slope, _  = _ols_slope_intercept(values) if len(values) >= 2 else (0.0, values[0])
    std       = _std_dev(values)
    margin    = _Z95 * max(std, 1e-9)
    points: List[ForecastPoint] = []
    for i in range(1, n_points + 1):
        steps     = i * (len(values) / n_points)  # evenly spaced
        if algorithm == ForecastAlgorithm.LINEAR:
            val = _linear_extrapolate(values, steps)
        elif algorithm == ForecastAlgorithm.EXPONENTIAL:
            val = _holt_extrapolate(values, int(steps) or 1)
        else:  # HYBRID
            val = _hybrid_extrapolate(values, int(steps) or 1)
        base_conf = _compute_confidence(values, val, len(values))
        # Confidence decays slightly further out
        point_conf = max(0.05, base_conf - 0.02 * (i - 1))
        points.append(ForecastPoint(
            step           = i,
            offset_seconds = step_s * i,
            value          = val,
            lower_bound    = val - margin,
            upper_bound    = val + margin,
            confidence     = min(0.95, point_conf),
        ))
    return points


# ── Forecaster ────────────────────────────────────────────────────────────────

class PredictiveForecaster(LifecycleAwareMixin):
    """
    Generates operational Forecast objects from historical time-series data.

    Uses a PredictiveModelRegistry to select the appropriate algorithm for
    each (PredictionType, ForecastHorizon) combination.

    Thread-safe.  Must be started before use.
    NO trading signals.  NO execution logic.
    """

    def __init__(self, model_registry: Optional[PredictiveModelRegistry] = None) -> None:
        super().__init__()
        self._registry = model_registry or PredictiveModelRegistry()

    def _on_start(self) -> None:
        if self._registry.lifecycle_state() not in _RUNNING:
            self._registry.start()
        _log.info("PredictiveForecaster started.", system_id=FORECASTER_SYSTEM_ID)

    def _on_stop(self) -> None:
        try:
            self._registry.stop()
        except Exception:
            pass
        _log.info("PredictiveForecaster stopped.", system_id=FORECASTER_SYSTEM_ID)

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in _RUNNING:
            raise PredictiveEngineNotRunningError()

    # ── Public API ────────────────────────────────────────────────────────────

    def forecast(
        self,
        prediction_type:   PredictionType,
        domain:            PredictionDomain,
        horizon:           ForecastHorizon,
        historical_values: List[float],
        custom_horizon_s:  float = 0.0,
    ) -> Forecast:
        """
        Generate a Forecast from historical values.

        Parameters
        ----------
        prediction_type:   Type of prediction.
        domain:            Prediction domain.
        horizon:           Forecast time horizon.
        historical_values: Ordered list of past values (oldest first).
        custom_horizon_s:  Override horizon for CUSTOM horizon type.
        """
        self._assert_running()
        h_seconds = (
            custom_horizon_s if horizon == ForecastHorizon.CUSTOM and custom_horizon_s > 0
            else HORIZON_SECONDS.get(horizon, 3600.0)
        )
        n         = len(historical_values)
        model     = self._registry.get_best(prediction_type, domain, n)
        algorithm = model.algorithm

        if n == 0:
            return self._empty_forecast(prediction_type, domain, horizon, h_seconds)

        if n < model.min_data_points:
            model     = self._registry.get_fallback()
            algorithm = model.algorithm

        slope, _ = _ols_slope_intercept(historical_values) if n >= 2 else (0.0, historical_values[0])
        trend    = _classify_trend(historical_values, slope, prediction_type)
        points   = _build_points(historical_values, algorithm, h_seconds)
        terminal = _linear_extrapolate(historical_values, n) if algorithm == ForecastAlgorithm.LINEAR else \
                   _holt_extrapolate(historical_values, n) if algorithm == ForecastAlgorithm.EXPONENTIAL else \
                   _hybrid_extrapolate(historical_values, n)
        confidence = _compute_confidence(historical_values, terminal, n)

        return Forecast(
            forecast_id      = str(uuid.uuid4()),
            prediction_type  = prediction_type,
            domain           = domain,
            horizon          = horizon,
            forecast_points  = tuple(points),
            trend            = trend,
            confidence       = confidence,
            horizon_seconds  = h_seconds,
            data_points_used = n,
            algorithm        = algorithm.value,
        )

    def forecast_all(
        self,
        historical_analytics: Dict[str, List[float]],
        domain:               PredictionDomain,
        horizon:              ForecastHorizon,
        prediction_types:     Optional[List[PredictionType]] = None,
        custom_horizon_s:     float = 0.0,
    ) -> List[Forecast]:
        """
        Generate forecasts for all available prediction types.

        Only types that have data in historical_analytics are forecast.
        If prediction_types is None, all 11 types are attempted.
        """
        self._assert_running()
        targets = prediction_types or list(PredictionType)
        results: List[Forecast] = []
        for pt in targets:
            values = historical_analytics.get(pt.value, [])
            try:
                f = self.forecast(pt, domain, horizon, values, custom_horizon_s)
                results.append(f)
            except Exception as exc:
                _log.warning(
                    "Forecast failed; skipping.",
                    prediction_type = pt.value,
                    error           = str(exc),
                )
        return results

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _empty_forecast(
        self,
        prediction_type: PredictionType,
        domain:          PredictionDomain,
        horizon:         ForecastHorizon,
        h_seconds:       float,
    ) -> Forecast:
        return Forecast(
            forecast_id      = str(uuid.uuid4()),
            prediction_type  = prediction_type,
            domain           = domain,
            horizon          = horizon,
            forecast_points  = (),
            trend            = TrendType.UNKNOWN,
            confidence       = 0.0,
            horizon_seconds  = h_seconds,
            data_points_used = 0,
            algorithm        = "none",
        )
