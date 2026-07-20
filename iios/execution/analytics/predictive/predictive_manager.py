"""
iios/execution/analytics/predictive/predictive_manager.py
=========================================================
PredictiveManager — orchestrates the full prediction intelligence cycle.

Workflow per request:
  1.  Validate request
  2.  Register in registry
  3.  Build context if not provided
  4.  Generate forecasts  (PredictiveForecaster)
  5.  Analyse trends      (PredictiveTrendEngine)       if include_trends
  6.  Detect anomalies   (PredictiveAnomalyDetector)   if include_anomalies
  7.  Estimate capacity  (PredictiveCapacityEstimator)  if include_capacity
  8.  Estimate risk      (PredictiveRiskEstimator)      if include_risks
  9.  Estimate probabilities (PredictiveProbabilityEstimator)
 10.  Score all forecasts (PredictiveScorer)
 11.  Build OperationalForecast
 12.  Build ForecastSummary
 13.  Build PredictiveSnapshot
 14.  Build PredictionReport
 15.  Record stats + history + events
 16.  Return PredictionReport

NO predictive trading signals.  NO order generation.  NO broker calls.

C8 Execution Analytics & Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import time
import uuid
from typing import Dict, List, Optional

from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import (
    HORIZON_SECONDS,
    MANAGER_SYSTEM_ID,
    ForecastHorizon,
    PredictionDomain,
    PredictionType,
    TrendType,
)
from .exceptions import PredictiveEngineNotRunningError
from .predictive_anomaly_detector import AnomalyResult, PredictiveAnomalyDetector
from .predictive_capacity_estimator import PredictiveCapacityEstimator
from .predictive_context import PredictiveContext, make_predictive_context
from .predictive_events import (
    make_capacity_forecast_completed_event,
    make_forecast_generated_event,
    make_prediction_failed_event,
    make_prediction_published_event,
    make_prediction_started_event,
    make_risk_forecast_completed_event,
    make_trend_forecast_completed_event,
)
from .predictive_forecaster import PredictiveForecaster
from .predictive_history import PredictiveIntelligenceHistory
from .predictive_probability import PredictiveProbabilityEstimator
from .predictive_registry import PredictiveIntelligenceRegistry
from .predictive_request import PredictionRequest
from .predictive_response import (
    CapacityForecast,
    Forecast,
    ForecastSummary,
    OperationalForecast,
    PredictionReport,
    ProbabilityReport,
    RiskForecast,
    make_predictive_snapshot,
)
from .predictive_risk_estimator import PredictiveRiskEstimator
from .predictive_scorer import PredictiveScorer
from .predictive_statistics import PredictiveIntelligenceStatistics
from .predictive_trend_engine import PredictiveTrendEngine
from .predictive_validation import PredictiveValidator

_log = get_logger(__name__)

_RUNNING = frozenset({EngineState.RUNNING, "running"})


class PredictiveManager(LifecycleAwareMixin):
    """
    Orchestrates the full prediction intelligence cycle.

    Thread-safe.  Must be started before use.
    """

    def __init__(self) -> None:
        super().__init__()
        self._validator    = PredictiveValidator()
        self._registry     = PredictiveIntelligenceRegistry()
        self._forecaster   = PredictiveForecaster()
        self._trend_engine = PredictiveTrendEngine()
        self._anomaly      = PredictiveAnomalyDetector()
        self._capacity     = PredictiveCapacityEstimator()
        self._risk         = PredictiveRiskEstimator()
        self._probability  = PredictiveProbabilityEstimator()
        self._scorer       = PredictiveScorer()
        self._stats        = PredictiveIntelligenceStatistics()
        self._history      = PredictiveIntelligenceHistory()

    def _on_start(self) -> None:
        for component in (
            self._registry, self._forecaster,
            self._trend_engine, self._anomaly,
            self._capacity, self._risk,
            self._probability, self._scorer,
        ):
            component.start()
        _log.info("PredictiveManager started.", system_id=MANAGER_SYSTEM_ID)

    def _on_stop(self) -> None:
        for component in (
            self._registry, self._forecaster,
            self._trend_engine, self._anomaly,
            self._capacity, self._risk,
            self._probability, self._scorer,
        ):
            try:
                component.stop()
            except Exception:
                pass
        _log.info("PredictiveManager stopped.", system_id=MANAGER_SYSTEM_ID)

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in _RUNNING:
            raise PredictiveEngineNotRunningError()

    # ── Public API ────────────────────────────────────────────────────────────

    def process(
        self,
        request: PredictionRequest,
        context: Optional[PredictiveContext] = None,
    ) -> PredictionReport:
        """Execute the full prediction cycle for the given request."""
        self._assert_running()
        t0 = time.perf_counter()
        start_event = make_prediction_started_event(request.request_id)
        self._history.add_event(start_event)

        try:
            # 1. Validate
            self._validator.validate_and_raise(request, context)

            # 2. Register
            self._registry.register(request)

            # 3. Build context if not provided
            if context is None:
                context = make_predictive_context(
                    request_id = request.request_id,
                    domain     = request.domain,
                    horizon    = request.horizon,
                )

            hist = context.historical_analytics
            h_seconds = context.horizon_seconds()

            # 4. Generate forecasts
            t_fc = time.perf_counter()
            ptypes = list(request.prediction_types) if request.prediction_types else None
            forecasts = self._forecaster.forecast_all(
                hist, request.domain, request.horizon, ptypes, h_seconds
            )
            fc_ms = (time.perf_counter() - t_fc) * 1_000.0

            fc_event = make_forecast_generated_event(
                request.request_id, len(forecasts), request.domain.value
            )
            self._history.add_event(fc_event)
            for f in forecasts:
                self._history.add_forecast(f)

            # 5. Trend analysis
            trend_map: Dict[PredictionType, TrendType] = {}
            if request.include_trends and hist:
                trend_map = self._trend_engine.analyze_all(hist, request.domain)
                trend_event = make_trend_forecast_completed_event(
                    request.request_id, len(trend_map)
                )
                self._history.add_event(trend_event)

            # 6. Anomaly detection
            anomaly_result: Optional[AnomalyResult] = None
            if request.include_anomalies:
                # Use the first available metric series for anomaly detection
                all_values: List[float] = []
                for v in hist.values():
                    if v:
                        all_values = v
                        break
                if all_values:
                    anomaly_result = self._anomaly.detect(all_values)

            # 7. Capacity estimation
            capacity_forecast: Optional[CapacityForecast] = None
            if request.include_capacity:
                util_series = (
                    hist.get(PredictionType.INFRASTRUCTURE_UTILIZATION_FORECAST.value) or
                    hist.get(PredictionType.CAPACITY_FORECAST.value) or
                    []
                )
                capacity_forecast = self._capacity.estimate(
                    request.domain, request.horizon, util_series, h_seconds
                )
                self._history.add_capacity_forecast(capacity_forecast)
                cf_event = make_capacity_forecast_completed_event(
                    request.request_id,
                    capacity_forecast.forecasted_utilization,
                    capacity_forecast.bottleneck_risk,
                )
                self._history.add_event(cf_event)

            # 8. Risk estimation
            risk_forecast: Optional[RiskForecast] = None
            if request.include_risks:
                risk_forecast = self._risk.estimate(
                    request.domain, request.horizon,
                    forecasts, anomaly_result, capacity_forecast, trend_map,
                )
                self._history.add_risk_forecast(risk_forecast)
                rf_event = make_risk_forecast_completed_event(
                    request.request_id,
                    risk_forecast.risk_level.value,
                    risk_forecast.risk_score,
                )
                self._history.add_event(rf_event)

            # 9. Probability estimation
            probability_report: Optional[ProbabilityReport] = None
            if forecasts:
                probability_report = self._probability.estimate(
                    request.domain, request.horizon, forecasts, hist
                )
                self._history.add_probability_report(probability_report)

            # 10. Score forecasts
            avg_conf    = self._scorer.average_confidence(forecasts)
            hi_conf     = self._scorer.high_confidence_count(forecasts)
            low_conf    = self._scorer.low_confidence_count(forecasts)

            # 11. Build OperationalForecast
            dominant_trend = self._trend_engine.dominant_trend(trend_map) if trend_map else TrendType.UNKNOWN
            op_health  = avg_conf
            op_avail   = 1.0 - (risk_forecast.risk_score if risk_forecast else 0.0)
            operational_forecast = OperationalForecast(
                operational_id       = str(uuid.uuid4()),
                domain               = request.domain,
                horizon              = request.horizon,
                health_score         = op_health,
                availability_forecast= max(0.0, min(1.0, op_avail)),
                performance_outlook  = dominant_trend,
                overall_confidence   = avg_conf,
            )
            self._history.add_operational_forecast(operational_forecast)

            # 12. Build ForecastSummary
            forecast_summary = ForecastSummary(
                summary_id            = str(uuid.uuid4()),
                domain                = request.domain,
                horizon               = request.horizon,
                total_forecasts       = len(forecasts),
                avg_confidence        = avg_conf,
                dominant_trend        = dominant_trend,
                high_confidence_count = hi_conf,
                low_confidence_count  = low_conf,
            )

            # 13. Build PredictiveSnapshot
            snapshot = make_predictive_snapshot(
                request.domain, request.horizon, forecasts
            )

            # 14. Build PredictionReport
            processing_ms = (time.perf_counter() - t0) * 1_000.0
            report = PredictionReport(
                report_id            = str(uuid.uuid4()),
                request_id           = request.request_id,
                domain               = request.domain,
                horizon              = request.horizon,
                forecasts            = tuple(forecasts),
                snapshot             = snapshot,
                probability_report   = probability_report,
                capacity_forecast    = capacity_forecast,
                risk_forecast        = risk_forecast,
                operational_forecast = operational_forecast,
                forecast_summary     = forecast_summary,
                processing_ms        = processing_ms,
            )

            # 15. Stats, history, events
            self._stats.record_cycle(
                forecast_count    = len(forecasts),
                processing_ms     = processing_ms,
                forecast_ms       = fc_ms,
                had_trends        = bool(trend_map),
                had_anomalies     = anomaly_result is not None,
                had_risk          = risk_forecast is not None,
                had_capacity      = capacity_forecast is not None,
                had_probabilities = probability_report is not None,
            )
            self._history.add_report(report)

            pub_event = make_prediction_published_event(
                request.request_id, report.report_id
            )
            self._history.add_event(pub_event)

            self._registry.complete(request.request_id)
            return report

        except Exception as exc:
            self._stats.record_failure()
            fail_event = make_prediction_failed_event(request.request_id, str(exc))
            self._history.add_event(fail_event)
            self._registry.complete(request.request_id)
            processing_ms = (time.perf_counter() - t0) * 1_000.0
            _log.error(
                "Prediction cycle failed.",
                request_id = request.request_id,
                error      = str(exc),
            )
            empty_snapshot = make_predictive_snapshot(
                request.domain, request.horizon, []
            )
            return PredictionReport(
                report_id     = str(uuid.uuid4()),
                request_id    = request.request_id,
                domain        = request.domain,
                horizon       = request.horizon,
                forecasts     = (),
                snapshot      = empty_snapshot,
                error_message = str(exc),
                processing_ms = processing_ms,
            )

    @property
    def statistics(self) -> PredictiveIntelligenceStatistics:
        return self._stats

    @property
    def history(self) -> PredictiveIntelligenceHistory:
        return self._history

    @property
    def registry(self) -> PredictiveIntelligenceRegistry:
        return self._registry
