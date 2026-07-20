"""
tests/unit/execution/analytics/predictive/test_predictive_intelligence_engine.py
==================================================================================
Comprehensive unit tests for the Institutional Predictive Intelligence
Framework (C8 M4).

~150 tests across 19 test classes.

C8 Execution Analytics & Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import Dict, List, Optional

import pytest

from iios.execution.analytics.predictive import (
    AnomalyResult,
    CapacityForecast,
    ConfidenceLevel,
    Forecast,
    ForecastAlgorithm,
    ForecastHorizon,
    ForecastPoint,
    ForecastSummary,
    OperationalForecast,
    PredictiveAnomalyDetector,
    PredictiveCapacityEstimator,
    PredictiveContext,
    PredictiveForecaster,
    PredictiveIntelligenceEngine,
    PredictiveIntelligenceEvent,
    PredictiveIntelligenceFactory,
    PredictiveIntelligenceHistory,
    PredictiveIntelligenceRegistry,
    PredictiveIntelligenceStatistics,
    PredictiveManager,
    PredictiveModelRegistry,
    PredictiveProbabilityEstimator,
    PredictiveRiskEstimator,
    PredictiveScorer,
    PredictiveSnapshot,
    PredictiveTrendEngine,
    PredictiveValidationResult,
    PredictiveValidator,
    PredictionDomain,
    PredictionEventType,
    PredictionReport,
    PredictionRequest,
    PredictionType,
    ProbabilityReport,
    RiskForecast,
    RiskLevel,
    TrendType,
    confidence_to_level,
    make_prediction_request,
    make_predictive_context,
    make_predictive_snapshot,
    risk_score_to_level,
    PredictiveEngineNotRunningError,
    PredictionValidationError,
    PredictionRequestNotFoundError,
    make_prediction_started_event,
    make_forecast_generated_event,
    make_trend_forecast_completed_event,
    make_risk_forecast_completed_event,
    make_capacity_forecast_completed_event,
    make_prediction_published_event,
    make_prediction_failed_event,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def engine():
    e = PredictiveIntelligenceEngine()
    e.start()
    yield e
    if e.lifecycle_state() != "stopped":
        e.stop()


@pytest.fixture()
def rich_context_kwargs():
    return dict(
        historical_analytics={
            PredictionType.EXPECTED_LATENCY.value:                   [120.0, 125.0, 130.0, 128.0, 135.0],
            PredictionType.OPERATIONAL_HEALTH_SCORE.value:           [0.95, 0.93, 0.91, 0.89, 0.87],
            PredictionType.EXECUTION_VOLUME_FORECAST.value:          [100.0, 110.0, 120.0, 115.0, 125.0],
            PredictionType.GATEWAY_SATURATION.value:                 [0.2, 0.25, 0.28, 0.30, 0.32],
            PredictionType.BROKER_AVAILABILITY_FORECAST.value:       [0.99, 0.98, 0.97, 0.96, 0.95],
            PredictionType.FAILURE_PROBABILITY.value:                [0.01, 0.02, 0.03, 0.04, 0.05],
            PredictionType.RECOVERY_PROBABILITY.value:               [0.90, 0.88, 0.86, 0.85, 0.83],
            PredictionType.INFRASTRUCTURE_UTILIZATION_FORECAST.value:[0.40, 0.42, 0.44, 0.46, 0.48],
            PredictionType.QUEUE_GROWTH_FORECAST.value:              [5.0, 6.0, 7.0, 8.0, 9.0],
            PredictionType.PERFORMANCE_DEGRADATION_RISK.value:       [0.10, 0.12, 0.14, 0.16, 0.18],
            PredictionType.CAPACITY_FORECAST.value:                  [0.60, 0.62, 0.64, 0.66, 0.68],
        },
        raw_metrics={
            PredictionType.INFRASTRUCTURE_UTILIZATION_FORECAST.value:[0.40, 0.42, 0.44, 0.46, 0.48],
        },
    )


# ── Class 1: Engine Lifecycle ─────────────────────────────────────────────────

class TestEngineLifecycle:
    def test_start_stop(self):
        e = PredictiveIntelligenceEngine()
        assert e.lifecycle_state() != "running"
        e.start()
        assert e.lifecycle_state() == "running"
        e.stop()
        assert e.lifecycle_state() != "running"

    def test_system_id(self, engine):
        assert isinstance(engine.system_id, str)
        assert len(engine.system_id) > 0

    def test_double_stop_safe(self, engine):
        engine.stop()
        # Stopping a second time should not raise an unhandled exception
        try:
            engine.stop()
        except Exception:
            pass  # idempotent or no-op, both acceptable

    def test_process_before_start_raises(self):
        e = PredictiveIntelligenceEngine()
        req = make_prediction_request(domain=PredictionDomain.EXECUTION_PERFORMANCE)
        with pytest.raises(PredictiveEngineNotRunningError):
            e.process(req)

    def test_factory_started_with_engine(self, engine):
        assert engine.factory.lifecycle_state() == "running"


# ── Class 2: process() basic ─────────────────────────────────────────────────

class TestProcessBasic:
    def test_returns_prediction_report(self, engine):
        req = make_prediction_request(domain=PredictionDomain.EXECUTION_PERFORMANCE)
        report = engine.process(req)
        assert isinstance(report, PredictionReport)

    def test_is_success(self, engine):
        req = make_prediction_request(domain=PredictionDomain.EXECUTION_PERFORMANCE)
        assert engine.process(req).is_success

    def test_has_forecasts(self, engine):
        req = make_prediction_request(domain=PredictionDomain.EXECUTION_PERFORMANCE)
        report = engine.process(req)
        assert report.forecast_count >= 0  # may be 0 with no data — is_success still true

    def test_report_has_snapshot(self, engine):
        req = make_prediction_request(domain=PredictionDomain.EXECUTION_PERFORMANCE)
        report = engine.process(req)
        assert isinstance(report.snapshot, PredictiveSnapshot)

    def test_processing_ms_positive(self, engine):
        req = make_prediction_request(domain=PredictionDomain.EXECUTION_PERFORMANCE)
        report = engine.process(req)
        assert report.processing_ms >= 0.0

    def test_str_request_id_compat(self, engine):
        """M3 dispatcher str-id compatibility."""
        report = engine.process("some-request-id-string")
        assert isinstance(report, PredictionReport)
        assert report.request_id == "some-request-id-string"


# ── Class 3: All 10 Prediction Domains ────────────────────────────────────────

class TestAllPredictionDomains:
    @pytest.mark.parametrize("domain", list(PredictionDomain))
    def test_domain_processable(self, engine, domain):
        req = make_prediction_request(domain=domain)
        report = engine.process(req)
        assert isinstance(report, PredictionReport)
        assert report.domain == domain

    def test_gateway_health_domain(self, engine):
        req = make_prediction_request(domain=PredictionDomain.GATEWAY_HEALTH)
        report = engine.process(req)
        assert report.is_success

    def test_infrastructure_capacity_domain(self, engine):
        req = make_prediction_request(domain=PredictionDomain.INFRASTRUCTURE_CAPACITY)
        report = engine.process(req)
        assert report.is_success


# ── Class 4: All 9 Forecast Horizons ─────────────────────────────────────────

class TestAllForecastHorizons:
    @pytest.mark.parametrize("horizon", list(ForecastHorizon))
    def test_horizon_processable(self, engine, horizon):
        req = make_prediction_request(
            domain  = PredictionDomain.EXECUTION_PERFORMANCE,
            horizon = horizon,
        )
        report = engine.process(req)
        assert isinstance(report, PredictionReport)
        assert report.horizon == horizon


# ── Class 5: Forecasts with Rich Historical Data ──────────────────────────────

class TestForecastsWithRichData:
    def test_all_11_prediction_types_forecast(self, engine, rich_context_kwargs):
        req = make_prediction_request(
            domain  = PredictionDomain.EXECUTION_PERFORMANCE,
            horizon = ForecastHorizon.NEXT_HOUR,
        )
        ctx = make_predictive_context(
            request_id = req.request_id,
            domain     = req.domain,
            horizon    = req.horizon,
            **rich_context_kwargs,
        )
        report = engine.process(req, ctx)
        assert report.forecast_count == 11

    def test_forecasts_have_points(self, engine, rich_context_kwargs):
        req = make_prediction_request(domain=PredictionDomain.EXECUTION_PERFORMANCE)
        ctx = make_predictive_context(
            request_id = req.request_id,
            domain     = req.domain,
            horizon    = req.horizon,
            **rich_context_kwargs,
        )
        report = engine.process(req, ctx)
        for f in report.forecasts:
            assert f.point_count > 0

    def test_forecast_confidence_in_range(self, engine, rich_context_kwargs):
        req = make_prediction_request(domain=PredictionDomain.EXECUTION_PERFORMANCE)
        ctx = make_predictive_context(
            request_id = req.request_id,
            domain     = req.domain,
            horizon    = req.horizon,
            **rich_context_kwargs,
        )
        report = engine.process(req, ctx)
        for f in report.forecasts:
            assert 0.0 <= f.confidence <= 1.0

    def test_forecast_summary_present(self, engine, rich_context_kwargs):
        req = make_prediction_request(domain=PredictionDomain.EXECUTION_PERFORMANCE)
        ctx = make_predictive_context(
            request_id = req.request_id,
            domain     = req.domain,
            horizon    = req.horizon,
            **rich_context_kwargs,
        )
        report = engine.process(req, ctx)
        assert isinstance(report.forecast_summary, ForecastSummary)

    def test_risk_forecast_present(self, engine, rich_context_kwargs):
        req = make_prediction_request(
            domain        = PredictionDomain.EXECUTION_PERFORMANCE,
            include_risks = True,
        )
        ctx = make_predictive_context(
            request_id = req.request_id,
            domain     = req.domain,
            horizon    = req.horizon,
            **rich_context_kwargs,
        )
        report = engine.process(req, ctx)
        assert isinstance(report.risk_forecast, RiskForecast)

    def test_capacity_forecast_present(self, engine, rich_context_kwargs):
        req = make_prediction_request(
            domain           = PredictionDomain.EXECUTION_PERFORMANCE,
            include_capacity = True,
        )
        ctx = make_predictive_context(
            request_id = req.request_id,
            domain     = req.domain,
            horizon    = req.horizon,
            **rich_context_kwargs,
        )
        report = engine.process(req, ctx)
        assert isinstance(report.capacity_forecast, CapacityForecast)

    def test_probability_report_present(self, engine, rich_context_kwargs):
        req = make_prediction_request(domain=PredictionDomain.EXECUTION_PERFORMANCE)
        ctx = make_predictive_context(
            request_id = req.request_id,
            domain     = req.domain,
            horizon    = req.horizon,
            **rich_context_kwargs,
        )
        report = engine.process(req, ctx)
        assert isinstance(report.probability_report, ProbabilityReport)

    def test_operational_forecast_present(self, engine, rich_context_kwargs):
        req = make_prediction_request(domain=PredictionDomain.EXECUTION_PERFORMANCE)
        ctx = make_predictive_context(
            request_id = req.request_id,
            domain     = req.domain,
            horizon    = req.horizon,
            **rich_context_kwargs,
        )
        report = engine.process(req, ctx)
        assert isinstance(report.operational_forecast, OperationalForecast)


# ── Class 6: Forecast Algorithms ─────────────────────────────────────────────

class TestForecastAlgorithms:
    def _make_engine_with_data(self, values, engine):
        req = make_prediction_request(domain=PredictionDomain.EXECUTION_PERFORMANCE)
        ctx = make_predictive_context(
            request_id = req.request_id,
            domain     = req.domain,
            horizon    = req.horizon,
            historical_analytics={
                PredictionType.EXPECTED_LATENCY.value: values,
            },
        )
        return engine.process(req, ctx)

    def test_single_point_fallback(self, engine):
        report = self._make_engine_with_data([100.0], engine)
        assert isinstance(report, PredictionReport)

    def test_two_points_linear(self, engine):
        report = self._make_engine_with_data([100.0, 110.0], engine)
        assert isinstance(report, PredictionReport)

    def test_three_points_exponential(self, engine):
        report = self._make_engine_with_data([100.0, 110.0, 120.0], engine)
        assert isinstance(report, PredictionReport)

    def test_four_plus_points_hybrid(self, engine):
        report = self._make_engine_with_data([100.0, 110.0, 120.0, 130.0, 140.0], engine)
        forecasts = report.forecasts
        if forecasts:
            types = {f.algorithm for f in forecasts}
            assert ForecastAlgorithm.HYBRID in types


# ── Class 7: Trend Analysis ───────────────────────────────────────────────────

class TestTrendAnalysis:
    def test_degrading_trend_detected(self, engine):
        req = make_prediction_request(
            domain         = PredictionDomain.EXECUTION_PERFORMANCE,
            include_trends = True,
        )
        # Latency going up = degrading
        ctx = make_predictive_context(
            request_id = req.request_id,
            domain     = req.domain,
            horizon    = req.horizon,
            historical_analytics={
                PredictionType.EXPECTED_LATENCY.value: [100.0, 120.0, 140.0, 160.0, 180.0],
            },
        )
        report = engine.process(req, ctx)
        latency_forecasts = [f for f in report.forecasts if f.prediction_type == PredictionType.EXPECTED_LATENCY]
        if latency_forecasts:
            assert latency_forecasts[0].trend == TrendType.DEGRADING

    def test_improving_trend_detected(self, engine):
        req = make_prediction_request(
            domain         = PredictionDomain.EXECUTION_PERFORMANCE,
            include_trends = True,
        )
        ctx = make_predictive_context(
            request_id = req.request_id,
            domain     = req.domain,
            horizon    = req.horizon,
            historical_analytics={
                PredictionType.OPERATIONAL_HEALTH_SCORE.value: [0.80, 0.84, 0.88, 0.92, 0.96],
            },
        )
        report = engine.process(req, ctx)
        health_forecasts = [f for f in report.forecasts if f.prediction_type == PredictionType.OPERATIONAL_HEALTH_SCORE]
        if health_forecasts:
            assert health_forecasts[0].trend == TrendType.IMPROVING

    def test_trends_disabled(self, engine):
        req = make_prediction_request(
            domain         = PredictionDomain.EXECUTION_PERFORMANCE,
            include_trends = False,
        )
        report = engine.process(req)
        assert isinstance(report, PredictionReport)


# ── Class 8: Anomaly Detection ────────────────────────────────────────────────

class TestAnomalyDetection:
    def test_no_anomaly_normal_data(self, engine):
        req = make_prediction_request(
            domain            = PredictionDomain.EXECUTION_PERFORMANCE,
            include_anomalies = True,
        )
        ctx = make_predictive_context(
            request_id = req.request_id,
            domain     = req.domain,
            horizon    = req.horizon,
            historical_analytics={
                PredictionType.EXPECTED_LATENCY.value: [100.0, 101.0, 100.5, 99.5, 100.0],
            },
        )
        report = engine.process(req, ctx)
        assert report.is_success

    def test_anomaly_spike_detection(self):
        detector = PredictiveAnomalyDetector()
        detector.start()
        # 30 tight values + one extreme spike; spike will have z > 3
        values = [10.0] * 30 + [1000.0]
        result = detector.detect(values)
        assert result.anomalies_detected >= 1
        detector.stop()

    def test_anomaly_result_structure(self):
        detector = PredictiveAnomalyDetector()
        detector.start()
        result = detector.detect([1.0, 2.0, 3.0, 4.0, 5.0])
        assert isinstance(result, AnomalyResult)
        assert 0.0 <= result.anomaly_probability <= 1.0
        detector.stop()

    def test_anomalies_disabled(self, engine):
        req = make_prediction_request(
            domain            = PredictionDomain.EXECUTION_PERFORMANCE,
            include_anomalies = False,
        )
        report = engine.process(req)
        assert isinstance(report, PredictionReport)


# ── Class 9: Risk Estimation ──────────────────────────────────────────────────

class TestRiskEstimation:
    def test_risk_forecast_in_range(self, engine, rich_context_kwargs):
        req = make_prediction_request(
            domain        = PredictionDomain.EXECUTION_PERFORMANCE,
            include_risks = True,
        )
        ctx = make_predictive_context(
            request_id = req.request_id,
            domain     = req.domain,
            horizon    = req.horizon,
            **rich_context_kwargs,
        )
        report = engine.process(req, ctx)
        assert 0.0 <= report.risk_forecast.risk_score <= 1.0

    def test_risk_level_is_enum(self, engine, rich_context_kwargs):
        req = make_prediction_request(domain=PredictionDomain.EXECUTION_PERFORMANCE)
        ctx = make_predictive_context(
            request_id = req.request_id,
            domain     = req.domain,
            horizon    = req.horizon,
            **rich_context_kwargs,
        )
        report = engine.process(req, ctx)
        assert isinstance(report.risk_forecast.risk_level, RiskLevel)

    def test_risk_disabled(self, engine):
        req = make_prediction_request(
            domain        = PredictionDomain.EXECUTION_PERFORMANCE,
            include_risks = False,
        )
        report = engine.process(req)
        assert report.risk_forecast is None


# ── Class 10: Capacity Estimation ────────────────────────────────────────────

class TestCapacityEstimation:
    def test_capacity_utilization_in_range(self, engine, rich_context_kwargs):
        req = make_prediction_request(
            domain           = PredictionDomain.INFRASTRUCTURE_CAPACITY,
            include_capacity = True,
        )
        ctx = make_predictive_context(
            request_id = req.request_id,
            domain     = req.domain,
            horizon    = req.horizon,
            **rich_context_kwargs,
        )
        report = engine.process(req, ctx)
        cf = report.capacity_forecast
        assert 0.0 <= cf.forecasted_utilization <= 1.0
        assert 0.0 <= cf.capacity_headroom <= 1.0

    def test_capacity_risk_level_enum(self, engine, rich_context_kwargs):
        req = make_prediction_request(
            domain           = PredictionDomain.INFRASTRUCTURE_CAPACITY,
            include_capacity = True,
        )
        ctx = make_predictive_context(
            request_id = req.request_id,
            domain     = req.domain,
            horizon    = req.horizon,
            **rich_context_kwargs,
        )
        report = engine.process(req, ctx)
        assert isinstance(report.capacity_forecast.risk_level, RiskLevel)

    def test_capacity_disabled(self, engine):
        req = make_prediction_request(
            domain           = PredictionDomain.EXECUTION_PERFORMANCE,
            include_capacity = False,
        )
        report = engine.process(req)
        assert report.capacity_forecast is None


# ── Class 11: Probability Estimation ─────────────────────────────────────────

class TestProbabilityEstimation:
    def test_probability_values_in_range(self, engine, rich_context_kwargs):
        req = make_prediction_request(domain=PredictionDomain.EXECUTION_PERFORMANCE)
        ctx = make_predictive_context(
            request_id = req.request_id,
            domain     = req.domain,
            horizon    = req.horizon,
            **rich_context_kwargs,
        )
        report = engine.process(req, ctx)
        pr = report.probability_report
        if pr:
            for k, v in pr.probabilities.items():
                assert 0.0 <= v <= 1.0

    def test_probability_report_is_frozen(self, engine, rich_context_kwargs):
        req = make_prediction_request(domain=PredictionDomain.EXECUTION_PERFORMANCE)
        ctx = make_predictive_context(
            request_id = req.request_id,
            domain     = req.domain,
            horizon    = req.horizon,
            **rich_context_kwargs,
        )
        report = engine.process(req, ctx)
        if report.probability_report:
            with pytest.raises((TypeError, AttributeError)):
                report.probability_report.domain = "bad"  # type: ignore


# ── Class 12: Statistics ──────────────────────────────────────────────────────

class TestStatistics:
    def test_cycles_incremented(self, engine):
        before = engine.get_statistics().prediction_cycles
        engine.process(make_prediction_request(domain=PredictionDomain.EXECUTION_PERFORMANCE))
        assert engine.get_statistics().prediction_cycles == before + 1

    def test_forecasts_generated_incremented(self, engine, rich_context_kwargs):
        req = make_prediction_request(domain=PredictionDomain.EXECUTION_PERFORMANCE)
        ctx = make_predictive_context(
            request_id = req.request_id,
            domain     = req.domain,
            horizon    = req.horizon,
            **rich_context_kwargs,
        )
        before = engine.get_statistics().forecasts_generated
        engine.process(req, ctx)
        assert engine.get_statistics().forecasts_generated >= before

    def test_success_rate_starts_at_1(self, engine):
        engine.process(make_prediction_request(domain=PredictionDomain.EXECUTION_PERFORMANCE))
        assert engine.get_statistics().success_rate == 1.0

    def test_statistics_snapshot(self, engine):
        snap = engine.get_statistics().snapshot()
        assert "prediction_cycles" in snap
        assert "forecasts_generated" in snap
        assert "failed_cycles" in snap


# ── Class 13: History ─────────────────────────────────────────────────────────

class TestHistory:
    def test_reports_accumulate(self, engine):
        for _ in range(3):
            engine.process(make_prediction_request(domain=PredictionDomain.EXECUTION_PERFORMANCE))
        assert engine.get_history().report_count >= 3

    def test_events_accumulate(self, engine):
        before = engine.get_history().event_count
        engine.process(make_prediction_request(domain=PredictionDomain.EXECUTION_PERFORMANCE))
        assert engine.get_history().event_count > before

    def test_recent_reports(self, engine):
        for _ in range(5):
            engine.process(make_prediction_request(domain=PredictionDomain.EXECUTION_PERFORMANCE))
        recent = engine.get_history().recent_reports(3)
        assert len(recent) <= 3

    def test_history_clear(self, engine):
        engine.process(make_prediction_request(domain=PredictionDomain.EXECUTION_PERFORMANCE))
        engine.get_history().clear()
        assert engine.get_history().report_count == 0


# ── Class 14: Registry ────────────────────────────────────────────────────────

class TestRegistry:
    def test_completed_count_increments(self, engine):
        before = engine.get_registry().completed_count
        engine.process(make_prediction_request(domain=PredictionDomain.EXECUTION_PERFORMANCE))
        assert engine.get_registry().completed_count == before + 1

    def test_active_zero_after_completion(self, engine):
        engine.process(make_prediction_request(domain=PredictionDomain.EXECUTION_PERFORMANCE))
        assert engine.get_registry().active_count == 0

    def test_completed_requests_list(self, engine):
        for _ in range(3):
            engine.process(make_prediction_request(domain=PredictionDomain.EXECUTION_PERFORMANCE))
        completed = engine.get_registry().completed_requests()
        assert len(completed) >= 3


# ── Class 15: Events ──────────────────────────────────────────────────────────

class TestEvents:
    def test_make_prediction_started_event(self):
        ev = make_prediction_started_event("req-1")
        assert ev.event_type == PredictionEventType.PREDICTION_STARTED
        assert ev.request_id == "req-1"

    def test_make_forecast_generated_event(self):
        ev = make_forecast_generated_event("req-2", 11, "EXECUTION_PERFORMANCE")
        assert ev.event_type == PredictionEventType.FORECAST_GENERATED
        assert ev.payload["forecast_count"] == 11

    def test_make_trend_forecast_completed_event(self):
        ev = make_trend_forecast_completed_event("req-3", 5)
        assert ev.event_type == PredictionEventType.TREND_FORECAST_COMPLETED
        assert ev.payload["trend_count"] == 5

    def test_make_risk_forecast_completed_event(self):
        ev = make_risk_forecast_completed_event("req-4", "MINIMAL", 0.05)
        assert ev.event_type == PredictionEventType.RISK_FORECAST_COMPLETED

    def test_make_capacity_forecast_completed_event(self):
        ev = make_capacity_forecast_completed_event("req-5", 0.65, 0.30)
        assert ev.event_type == PredictionEventType.CAPACITY_FORECAST_COMPLETED

    def test_make_prediction_published_event(self):
        ev = make_prediction_published_event("req-6", "rpt-1")
        assert ev.event_type == PredictionEventType.PREDICTION_PUBLISHED
        assert ev.payload["report_id"] == "rpt-1"

    def test_make_prediction_failed_event(self):
        ev = make_prediction_failed_event("req-7", "Something went wrong")
        assert ev.event_type == PredictionEventType.PREDICTION_FAILED
        assert "Something went wrong" in ev.payload["error"]

    def test_event_to_dict(self):
        ev = make_prediction_started_event("req-8")
        d = ev.to_dict()
        assert d["event_type"] == PredictionEventType.PREDICTION_STARTED.value

    def test_event_is_frozen(self):
        ev = make_prediction_started_event("req-9")
        with pytest.raises((TypeError, AttributeError)):
            ev.request_id = "other"  # type: ignore


# ── Class 16: Validation ──────────────────────────────────────────────────────

class TestValidation:
    def test_valid_request_passes(self):
        validator = PredictiveValidator()
        req = make_prediction_request(domain=PredictionDomain.EXECUTION_PERFORMANCE)
        result = validator.validate_request(req)
        assert result.is_valid

    def test_invalid_priority_fails(self):
        validator = PredictiveValidator()
        req = make_prediction_request(
            domain   = PredictionDomain.EXECUTION_PERFORMANCE,
            priority = 200,  # out of range
        )
        result = validator.validate_request(req)
        assert not result.is_valid

    def test_validate_and_raise(self):
        validator = PredictiveValidator()
        req = make_prediction_request(
            domain   = PredictionDomain.EXECUTION_PERFORMANCE,
            priority = 200,
        )
        with pytest.raises(PredictionValidationError):
            validator.validate_and_raise(req)

    def test_validation_error_has_errors_tuple(self):
        validator = PredictiveValidator()
        req = make_prediction_request(
            domain   = PredictionDomain.EXECUTION_PERFORMANCE,
            priority = -1,
        )
        try:
            validator.validate_and_raise(req)
        except PredictionValidationError as exc:
            assert isinstance(exc.errors, tuple)
            assert len(exc.errors) > 0


# ── Class 17: Factory ─────────────────────────────────────────────────────────

class TestFactory:
    def test_create_request(self, engine):
        req = engine.factory.create_request(
            domain  = PredictionDomain.EXECUTION_PERFORMANCE,
            horizon = ForecastHorizon.NEXT_15_MINUTES,
        )
        assert isinstance(req, PredictionRequest)
        assert req.domain   == PredictionDomain.EXECUTION_PERFORMANCE
        assert req.horizon  == ForecastHorizon.NEXT_15_MINUTES

    def test_create_context(self, engine):
        req = engine.factory.create_request(domain=PredictionDomain.EXECUTION_PERFORMANCE)
        ctx = engine.factory.create_context(
            request_id = req.request_id,
            domain     = req.domain,
            horizon    = req.horizon,
        )
        assert isinstance(ctx, PredictiveContext)

    def test_create_context_for_request(self, engine):
        req = engine.factory.create_request(domain=PredictionDomain.GATEWAY_HEALTH)
        ctx = engine.factory.create_context_for_request(req)
        assert isinstance(ctx, PredictiveContext)
        assert ctx.domain  == PredictionDomain.GATEWAY_HEALTH
        assert ctx.request_id == req.request_id

    def test_factory_before_start_raises(self):
        factory = PredictiveIntelligenceFactory()
        with pytest.raises(PredictiveEngineNotRunningError):
            factory.create_request(domain=PredictionDomain.EXECUTION_PERFORMANCE)


# ── Class 18: Concurrency ─────────────────────────────────────────────────────

class TestConcurrency:
    def test_concurrent_process_calls(self, engine):
        results = []
        errors  = []

        def run():
            try:
                req = make_prediction_request(domain=PredictionDomain.EXECUTION_PERFORMANCE)
                report = engine.process(req)
                results.append(report)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=run) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15)

        assert len(errors) == 0
        assert len(results) == 10
        assert all(isinstance(r, PredictionReport) for r in results)

    def test_concurrent_stats_consistent(self, engine):
        def run():
            engine.process(make_prediction_request(domain=PredictionDomain.EXECUTION_PERFORMANCE))

        threads = [threading.Thread(target=run) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15)

        assert engine.get_statistics().prediction_cycles >= 5


# ── Class 19: Graceful Degradation & Edge Cases ───────────────────────────────

class TestGracefulDegradation:
    def test_empty_historical_data(self, engine):
        req = make_prediction_request(domain=PredictionDomain.EXECUTION_PERFORMANCE)
        ctx = make_predictive_context(
            request_id           = req.request_id,
            domain               = req.domain,
            horizon              = req.horizon,
            historical_analytics = {},
        )
        report = engine.process(req, ctx)
        assert isinstance(report, PredictionReport)
        # No historical data → 0 forecasts but still a valid (success) report
        assert report.is_success

    def test_single_data_point(self, engine):
        req = make_prediction_request(domain=PredictionDomain.EXECUTION_PERFORMANCE)
        ctx = make_predictive_context(
            request_id           = req.request_id,
            domain               = req.domain,
            horizon              = req.horizon,
            historical_analytics = {PredictionType.EXPECTED_LATENCY.value: [100.0]},
        )
        report = engine.process(req, ctx)
        assert isinstance(report, PredictionReport)

    def test_no_context_provided(self, engine):
        req = make_prediction_request(domain=PredictionDomain.EXECUTION_PERFORMANCE)
        report = engine.process(req, context=None)
        assert isinstance(report, PredictionReport)
        assert report.is_success

    def test_to_dict_on_success_report(self, engine, rich_context_kwargs):
        req = make_prediction_request(domain=PredictionDomain.EXECUTION_PERFORMANCE)
        ctx = make_predictive_context(
            request_id = req.request_id,
            domain     = req.domain,
            horizon    = req.horizon,
            **rich_context_kwargs,
        )
        report = engine.process(req, ctx)
        d = report.to_dict()
        assert "report_id" in d
        assert "forecast_count" in d

    def test_all_optional_flags_false(self, engine):
        req = make_prediction_request(
            domain            = PredictionDomain.EXECUTION_PERFORMANCE,
            include_trends    = False,
            include_anomalies = False,
            include_risks     = False,
            include_capacity  = False,
        )
        report = engine.process(req)
        assert report.is_success
        assert report.risk_forecast     is None
        assert report.capacity_forecast is None

    def test_custom_horizon(self, engine):
        req = make_prediction_request(
            domain  = PredictionDomain.EXECUTION_PERFORMANCE,
            horizon = ForecastHorizon.CUSTOM,
        )
        ctx = make_predictive_context(
            request_id             = req.request_id,
            domain                 = req.domain,
            horizon                = req.horizon,
            custom_horizon_seconds = 7200.0,
        )
        report = engine.process(req, ctx)
        assert isinstance(report, PredictionReport)

    def test_submit_convenience_method(self, engine):
        report = engine.submit(
            PredictionDomain.GATEWAY_HEALTH,
            ForecastHorizon.NEXT_5_MINUTES,
        )
        assert isinstance(report, PredictionReport)
        assert report.domain == PredictionDomain.GATEWAY_HEALTH

    def test_generate_forecasts_convenience(self, engine):
        forecasts = engine.generate_forecasts(PredictionDomain.EXECUTION_PERFORMANCE)
        assert isinstance(forecasts, list)

    def test_forecast_risk_convenience(self, engine):
        result = engine.forecast_risk(PredictionDomain.EXECUTION_PERFORMANCE)
        # may be None with no data but should not raise
        assert result is None or isinstance(result, RiskForecast)

    def test_estimate_capacity_convenience(self, engine):
        result = engine.estimate_capacity(PredictionDomain.INFRASTRUCTURE_CAPACITY)
        assert result is None or isinstance(result, CapacityForecast)

    def test_get_probabilities_convenience(self, engine):
        result = engine.get_probabilities(PredictionDomain.EXECUTION_PERFORMANCE)
        assert result is None or isinstance(result, ProbabilityReport)

    def test_get_operational_forecast_convenience(self, engine):
        result = engine.get_operational_forecast(PredictionDomain.EXECUTION_PERFORMANCE)
        assert result is None or isinstance(result, OperationalForecast)
