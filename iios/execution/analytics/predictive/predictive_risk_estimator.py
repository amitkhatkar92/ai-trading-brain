"""
iios/execution/analytics/predictive/predictive_risk_estimator.py
================================================================
PredictiveRiskEstimator — estimates operational risk for the forecast
horizon by aggregating signals from forecasts, anomaly detection,
capacity estimates, and trend analysis.

C8 Execution Analytics & Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import uuid
from typing import Dict, List, Optional, Tuple

from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import (
    FORECASTER_SYSTEM_ID,
    ForecastHorizon,
    PredictionDomain,
    PredictionType,
    RiskLevel,
    TrendType,
    risk_score_to_level,
)
from .exceptions import PredictiveEngineNotRunningError
from .predictive_anomaly_detector import AnomalyResult
from .predictive_capacity_estimator import CapacityForecast
from .predictive_response import Forecast, RiskForecast

_log = get_logger(__name__)

_RUNNING = frozenset({EngineState.RUNNING, "running"})


class PredictiveRiskEstimator(LifecycleAwareMixin):
    """
    Aggregates risk signals from forecasts and supplementary indicators
    to produce an operational RiskForecast.

    Thread-safe.  Must be started before use.
    """

    def _on_start(self) -> None:
        _log.info("PredictiveRiskEstimator started.", system_id=FORECASTER_SYSTEM_ID)

    def _on_stop(self) -> None:
        _log.info("PredictiveRiskEstimator stopped.", system_id=FORECASTER_SYSTEM_ID)

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in _RUNNING:
            raise PredictiveEngineNotRunningError()

    def estimate(
        self,
        domain:            PredictionDomain,
        horizon:           ForecastHorizon,
        forecasts:         List[Forecast],
        anomaly_result:    Optional[AnomalyResult]  = None,
        capacity_forecast: Optional[CapacityForecast] = None,
        trend_map:         Optional[Dict[PredictionType, TrendType]] = None,
    ) -> RiskForecast:
        """
        Estimate operational risk by aggregating multiple signals.
        """
        self._assert_running()
        factors:    List[str] = []
        mitigators: List[str] = []
        risk_signals: List[float] = []

        # ── Signal: forecast degrading predictions ────────────────────────
        degrading_preds = [
            f for f in forecasts
            if f.trend == TrendType.DEGRADING
        ]
        if degrading_preds:
            score = min(1.0, len(degrading_preds) / max(len(forecasts), 1))
            risk_signals.append(score * 0.35)
            factors.append(f"{len(degrading_preds)} degrading forecasts")
        else:
            mitigators.append("No degrading forecast trends")

        # ── Signal: low-confidence forecasts ──────────────────────────────
        low_conf = [f for f in forecasts if f.confidence < 0.4]
        if low_conf:
            score = min(1.0, len(low_conf) / max(len(forecasts), 1))
            risk_signals.append(score * 0.15)
            factors.append(f"{len(low_conf)} low-confidence forecasts")

        # ── Signal: anomaly probability ───────────────────────────────────
        if anomaly_result and anomaly_result.anomaly_probability > 0.1:
            prob = anomaly_result.anomaly_probability
            risk_signals.append(prob * 0.25)
            factors.append(f"Anomaly probability {prob:.1%}")
        elif anomaly_result and anomaly_result.anomaly_probability <= 0.05:
            mitigators.append("Low anomaly probability")

        # ── Signal: capacity bottleneck ───────────────────────────────────
        if capacity_forecast and capacity_forecast.bottleneck_risk > 0.6:
            risk_signals.append(capacity_forecast.bottleneck_risk * 0.25)
            factors.append(f"Capacity bottleneck risk {capacity_forecast.bottleneck_risk:.1%}")
        elif capacity_forecast and capacity_forecast.capacity_headroom > 0.4:
            mitigators.append(f"Adequate capacity headroom {capacity_forecast.capacity_headroom:.1%}")

        # ── Signal: failure/degradation predictions ───────────────────────
        failure_forecasts = [
            f for f in forecasts if f.prediction_type in (
                PredictionType.FAILURE_PROBABILITY,
                PredictionType.PERFORMANCE_DEGRADATION_RISK,
            )
        ]
        if failure_forecasts:
            max_val = max(f.terminal_forecast for f in failure_forecasts)
            if max_val > 0.5:
                risk_signals.append(min(1.0, max_val) * 0.20)
                factors.append(f"High failure/degradation forecast {max_val:.1%}")

        # ── Aggregate ─────────────────────────────────────────────────────
        if not risk_signals:
            risk_score = 0.0
            mitigators.append("No risk signals detected")
        else:
            risk_score = min(1.0, sum(risk_signals))

        risk_level  = risk_score_to_level(risk_score)
        avg_conf    = (sum(f.confidence for f in forecasts) / len(forecasts)) if forecasts else 0.0

        return RiskForecast(
            risk_id               = str(uuid.uuid4()),
            domain                = domain,
            horizon               = horizon,
            risk_level            = risk_level,
            risk_score            = risk_score,
            contributing_factors  = tuple(factors),
            mitigation_indicators = tuple(mitigators),
            confidence            = avg_conf,
        )
