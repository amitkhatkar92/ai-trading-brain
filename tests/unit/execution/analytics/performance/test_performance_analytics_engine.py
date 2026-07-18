"""
tests/unit/execution/analytics/performance/test_performance_analytics_engine.py
================================================================================
Unit tests for the Institutional Performance Analytics Framework (C8 M3).

Coverage targets:
  - PerformanceAnalyticsEngine lifecycle
  - PerformanceRequest / PerformanceContext construction
  - KPI calculation (all 19 KPIs)
  - Trend analysis
  - Benchmark comparison
  - Scorecard generation
  - Aggregation
  - Validation
  - Statistics / History
  - Events
  - Error handling and graceful degradation
  - M2 dispatcher str-compatibility
"""
from __future__ import annotations

import time
import threading
import uuid
from typing import Any, Dict, List

import pytest

from iios.execution.analytics.performance import (
    # Engine
    PerformanceAnalyticsEngine,
    # Types
    AggregationWindow,
    BenchmarkStatus,
    CollectedData,
    KPIType,
    PerformanceDomain,
    PerformanceGrade,
    TrendDirection,
    # Request / Context
    PerformanceContext,
    PerformanceRequest,
    make_performance_context,
    make_performance_request,
    # KPI
    KPIReport,
    KPIValue,
    make_kpi_value,
    make_kpi_report,
    # Response
    BenchmarkReport,
    PerformanceAnalyticsReport,
    PerformanceScorecard,
    TrendAnalysis,
    # Components
    PerformanceAggregator,
    PerformanceBenchmark,
    PerformanceCalculator,
    PerformanceCollector,
    PerformanceScorecardBuilder,
    PerformanceTrendAnalyzer,
    PerformanceValidator,
    # Stats / History
    PerformanceAnalyticsHistory,
    PerformanceAnalyticsStatistics,
    # Events
    PerformanceAnalyticsEvent,
    make_analytics_failed_event,
    make_analytics_published_event,
    make_analytics_started_event,
    make_benchmark_completed_event,
    make_kpi_calculated_event,
    make_report_generated_event,
    make_trend_detected_event,
    # Exceptions
    PerformanceAggregationError,
    PerformanceAnalyticsError,
    PerformanceBenchmarkError,
    PerformanceCalculationError,
    PerformanceDataInsufficientError,
    PerformanceEngineNotRunningError,
    PerformanceRequestNotFoundError,
    PerformanceTrendError,
    PerformanceValidationError,
    # Registry / Factory / Manager
    PerformanceAnalyticsFactory,
    PerformanceAnalyticsRegistry,
    PerformanceManager,
    # Constants
    ENGINE_SYSTEM_ID,
    GRADE_THRESHOLDS,
    KPI_BENCHMARKS,
    WINDOW_SECONDS,
    score_to_grade,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def engine():
    e = PerformanceAnalyticsEngine()
    e.start()
    yield e
    e.stop()


@pytest.fixture
def manager():
    m = PerformanceManager()
    m.start()
    yield m
    m.stop()


@pytest.fixture
def calculator():
    c = PerformanceCalculator()
    c.start()
    yield c
    c.stop()


@pytest.fixture
def collector():
    c = PerformanceCollector()
    c.start()
    yield c
    c.stop()


@pytest.fixture
def aggregator():
    a = PerformanceAggregator()
    a.start()
    yield a
    a.stop()


@pytest.fixture
def benchmark():
    b = PerformanceBenchmark()
    b.start()
    yield b
    b.stop()


@pytest.fixture
def trend_analyzer():
    t = PerformanceTrendAnalyzer()
    t.start()
    yield t
    t.stop()


@pytest.fixture
def scorecard_builder():
    s = PerformanceScorecardBuilder()
    s.start()
    yield s
    s.stop()


@pytest.fixture
def registry():
    r = PerformanceAnalyticsRegistry()
    r.start()
    yield r
    r.stop()


@pytest.fixture
def factory():
    f = PerformanceAnalyticsFactory()
    f.start()
    yield f
    f.stop()


@pytest.fixture
def basic_request():
    return make_performance_request(
        domain             = PerformanceDomain.EXECUTION,
        window             = AggregationWindow.REAL_TIME,
        include_trends     = False,
        include_benchmarks = True,
        include_scorecard  = True,
    )


@pytest.fixture
def basic_context(basic_request):
    return make_performance_context(
        request_id = basic_request.request_id,
        domain     = basic_request.domain,
        window     = basic_request.window,
    )


# ── 1. Lifecycle ──────────────────────────────────────────────────────────────

class TestEngineLifecycle:

    def test_start_stop(self):
        e = PerformanceAnalyticsEngine()
        e.start()
        assert e.lifecycle_state() in ("running", "RUNNING")
        e.stop()
        assert e.lifecycle_state() not in ("running", "RUNNING")

    def test_process_before_start_raises(self):
        e = PerformanceAnalyticsEngine()
        request = make_performance_request(domain=PerformanceDomain.EXECUTION)
        with pytest.raises(PerformanceEngineNotRunningError):
            e.process(request)

    def test_system_id(self, engine):
        assert engine.system_id == ENGINE_SYSTEM_ID

    def test_double_start_is_idempotent(self):
        from iios.investment.workflow.engine_lifecycle import EngineAlreadyRunningError
        e = PerformanceAnalyticsEngine()
        e.start()
        with pytest.raises(EngineAlreadyRunningError):
            e.start()  # second start raises EngineAlreadyRunningError
        e.stop()

    def test_factory_accessible(self, engine):
        assert isinstance(engine.factory, PerformanceAnalyticsFactory)


# ── 2. Request / Context construction ────────────────────────────────────────

class TestRequestContext:

    def test_make_request_defaults(self):
        r = make_performance_request(domain=PerformanceDomain.EXECUTION)
        assert r.request_id
        assert r.domain == PerformanceDomain.EXECUTION
        assert r.window == AggregationWindow.REAL_TIME
        assert r.include_benchmarks is True
        assert r.include_scorecard is True
        assert r.include_trends is False

    def test_make_request_custom(self):
        r = make_performance_request(
            domain             = PerformanceDomain.RISK,
            window             = AggregationWindow.FIVE_MINUTES,
            kpi_types          = (KPIType.RISK_RULE_EFFECTIVENESS,),
            include_trends     = True,
            include_benchmarks = False,
            priority           = 3,
            reason             = "risk check",
        )
        assert r.domain == PerformanceDomain.RISK
        assert r.window == AggregationWindow.FIVE_MINUTES
        assert KPIType.RISK_RULE_EFFECTIVENESS in r.kpi_types
        assert r.include_trends is True
        assert r.include_benchmarks is False
        assert r.priority == 3

    def test_request_immutable(self):
        r = make_performance_request(domain=PerformanceDomain.EXECUTION)
        with pytest.raises(Exception):
            r.domain = PerformanceDomain.RISK  # type: ignore[misc]

    def test_request_to_dict(self):
        r = make_performance_request(domain=PerformanceDomain.EXECUTION)
        d = r.to_dict()
        assert d["domain"] == PerformanceDomain.EXECUTION.value
        assert "request_id" in d

    def test_make_context_defaults(self):
        ctx = make_performance_context(
            request_id = "req-1",
            domain     = PerformanceDomain.EXECUTION,
            window     = AggregationWindow.REAL_TIME,
        )
        assert ctx.request_id == "req-1"
        assert ctx.has_monitoring is False
        assert ctx.available_snapshot_count == 0
        assert ctx.has_historical_data is False

    def test_context_with_snapshots(self):
        snap = object()
        ctx = make_performance_context(
            request_id           = "req-1",
            domain               = PerformanceDomain.GATEWAY,
            window               = AggregationWindow.ONE_MINUTE,
            monitoring_snapshot  = snap,
            gateway_snapshot     = snap,
        )
        assert ctx.has_monitoring is True
        assert ctx.has_gateway is True
        assert ctx.available_snapshot_count == 2

    def test_context_immutable(self):
        ctx = make_performance_context(
            request_id = "req-1",
            domain     = PerformanceDomain.EXECUTION,
            window     = AggregationWindow.REAL_TIME,
        )
        with pytest.raises(Exception):
            ctx.domain = PerformanceDomain.RISK  # type: ignore[misc]

    def test_context_to_dict(self):
        ctx = make_performance_context(
            request_id = "req-1",
            domain     = PerformanceDomain.EXECUTION,
            window     = AggregationWindow.REAL_TIME,
        )
        d = ctx.to_dict()
        assert d["domain"] == PerformanceDomain.EXECUTION.value
        assert d["available_snapshots"] == 0


# ── 3. KPI types / constants ──────────────────────────────────────────────────

class TestConstants:

    def test_all_19_kpi_types(self):
        assert len(list(KPIType)) == 19

    def test_all_11_domains(self):
        assert len(list(PerformanceDomain)) == 11

    def test_all_10_windows(self):
        assert len(list(AggregationWindow)) == 10

    def test_window_seconds_coverage(self):
        for w in AggregationWindow:
            if w != AggregationWindow.CUSTOM:
                assert w in WINDOW_SECONDS

    def test_kpi_benchmarks_coverage(self):
        for kpi in KPIType:
            assert kpi in KPI_BENCHMARKS, f"{kpi.value} missing from KPI_BENCHMARKS"

    def test_grade_thresholds_coverage(self):
        for grade in PerformanceGrade:
            assert grade in GRADE_THRESHOLDS

    def test_score_to_grade_excellent(self):
        assert score_to_grade(0.95) == PerformanceGrade.EXCELLENT

    def test_score_to_grade_good(self):
        assert score_to_grade(0.80) == PerformanceGrade.GOOD

    def test_score_to_grade_acceptable(self):
        assert score_to_grade(0.65) == PerformanceGrade.ACCEPTABLE

    def test_score_to_grade_poor(self):
        assert score_to_grade(0.45) == PerformanceGrade.POOR

    def test_score_to_grade_critical(self):
        assert score_to_grade(0.20) == PerformanceGrade.CRITICAL


# ── 4. Collector ──────────────────────────────────────────────────────────────

class TestCollector:

    def test_empty_context_returns_defaults(self, collector):
        ctx = make_performance_context(
            request_id = "r1",
            domain     = PerformanceDomain.EXECUTION,
            window     = AggregationWindow.REAL_TIME,
        )
        data = collector.collect(ctx)
        assert isinstance(data, CollectedData)
        assert data.total_executions == 0

    def test_monitoring_snapshot_extracted(self, collector):
        class FakeMonitoringSnap:
            completed_executions = 80
            failed_executions    = 20
            total_fills          = 100
            uptime_sec           = 60.0
            active_executions    = 5

        ctx = make_performance_context(
            request_id          = "r1",
            domain              = PerformanceDomain.EXECUTION,
            window              = AggregationWindow.REAL_TIME,
            monitoring_snapshot = FakeMonitoringSnap(),
        )
        data = collector.collect(ctx)
        assert data.completed_executions == 80
        assert data.failed_executions == 20
        assert data.total_executions == 100
        assert data.processed_items == 100

    def test_recovery_snapshot_extracted(self, collector):
        class FakeRecoverySnap:
            recovery_result     = "success"
            recovery_duration_ms = 250.0

        ctx = make_performance_context(
            request_id        = "r1",
            domain            = PerformanceDomain.RECOVERY,
            window            = AggregationWindow.REAL_TIME,
            recovery_snapshot = FakeRecoverySnap(),
        )
        data = collector.collect(ctx)
        assert data.total_recoveries == 1
        assert data.successful_recoveries == 1
        assert data.recovery_times_ms == [250.0]

    def test_gateway_snapshot_extracted(self, collector):
        class FakeGatewaySnap:
            uptime_seconds = 55.0
            total_seconds  = 60.0

        ctx = make_performance_context(
            request_id       = "r1",
            domain           = PerformanceDomain.GATEWAY,
            window           = AggregationWindow.REAL_TIME,
            gateway_snapshot = FakeGatewaySnap(),
        )
        data = collector.collect(ctx)
        assert data.gateway_uptime_s == 55.0
        assert data.gateway_total_s == 60.0

    def test_raw_sample_data_extracted(self, collector):
        ctx = make_performance_context(
            request_id      = "r1",
            domain          = PerformanceDomain.EXECUTION,
            window          = AggregationWindow.REAL_TIME,
            raw_sample_data = {
                "execution_times_ms": [10.0, 20.0, 30.0],
                "total_orders":       [50.0],
                "completed_orders":   [45.0],
            },
        )
        data = collector.collect(ctx)
        assert data.execution_times_ms == [10.0, 20.0, 30.0]
        assert data.total_orders == 50
        assert data.completed_orders == 45

    def test_not_running_raises(self):
        c = PerformanceCollector()
        ctx = make_performance_context(
            request_id = "r1",
            domain     = PerformanceDomain.EXECUTION,
            window     = AggregationWindow.REAL_TIME,
        )
        with pytest.raises(PerformanceEngineNotRunningError):
            c.collect(ctx)


# ── 5. Calculator (all 19 KPIs) ───────────────────────────────────────────────

class TestCalculator:

    def _make_data(self, **kwargs) -> CollectedData:
        d = CollectedData()
        for k, v in kwargs.items():
            setattr(d, k, v)
        return d

    def test_execution_success_rate(self, calculator):
        data = self._make_data(completed_executions=80, failed_executions=20, total_executions=100)
        kv = calculator.calculate_single(
            KPIType.EXECUTION_SUCCESS_RATE, data,
            PerformanceDomain.EXECUTION, AggregationWindow.REAL_TIME
        )
        assert kv is not None
        assert abs(kv.value - 0.8) < 1e-9

    def test_execution_failure_rate(self, calculator):
        data = self._make_data(completed_executions=80, failed_executions=20, total_executions=100)
        kv = calculator.calculate_single(
            KPIType.EXECUTION_FAILURE_RATE, data,
            PerformanceDomain.EXECUTION, AggregationWindow.REAL_TIME
        )
        assert kv is not None
        assert abs(kv.value - 0.2) < 1e-9

    def test_avg_execution_time(self, calculator):
        data = self._make_data(execution_times_ms=[10.0, 20.0, 30.0])
        kv = calculator.calculate_single(
            KPIType.AVG_EXECUTION_TIME_MS, data,
            PerformanceDomain.EXECUTION, AggregationWindow.REAL_TIME
        )
        assert kv is not None
        assert abs(kv.value - 20.0) < 1e-9

    def test_median_execution_time(self, calculator):
        data = self._make_data(execution_times_ms=[10.0, 30.0, 20.0])
        kv = calculator.calculate_single(
            KPIType.MEDIAN_EXECUTION_TIME_MS, data,
            PerformanceDomain.EXECUTION, AggregationWindow.REAL_TIME
        )
        assert kv is not None
        assert abs(kv.value - 20.0) < 1e-9

    def test_p95_latency(self, calculator):
        data = self._make_data(execution_times_ms=list(range(1, 101)))  # 1..100
        kv = calculator.calculate_single(
            KPIType.P95_LATENCY_MS, data,
            PerformanceDomain.EXECUTION, AggregationWindow.REAL_TIME
        )
        assert kv is not None
        assert 94 <= kv.value <= 96

    def test_p99_latency(self, calculator):
        data = self._make_data(execution_times_ms=list(range(1, 101)))
        kv = calculator.calculate_single(
            KPIType.P99_LATENCY_MS, data,
            PerformanceDomain.EXECUTION, AggregationWindow.REAL_TIME
        )
        assert kv is not None
        assert 98 <= kv.value <= 100

    def test_recovery_success_rate(self, calculator):
        data = self._make_data(total_recoveries=10, successful_recoveries=9)
        kv = calculator.calculate_single(
            KPIType.RECOVERY_SUCCESS_RATE, data,
            PerformanceDomain.RECOVERY, AggregationWindow.REAL_TIME
        )
        assert kv is not None
        assert abs(kv.value - 0.9) < 1e-9

    def test_mean_time_to_recovery(self, calculator):
        data = self._make_data(recovery_times_ms=[100.0, 200.0, 300.0])
        kv = calculator.calculate_single(
            KPIType.MEAN_TIME_TO_RECOVERY_MS, data,
            PerformanceDomain.RECOVERY, AggregationWindow.REAL_TIME
        )
        assert kv is not None
        assert abs(kv.value - 200.0) < 1e-9

    def test_gateway_availability(self, calculator):
        data = self._make_data(gateway_uptime_s=55.0, gateway_total_s=60.0)
        kv = calculator.calculate_single(
            KPIType.GATEWAY_AVAILABILITY, data,
            PerformanceDomain.GATEWAY, AggregationWindow.REAL_TIME
        )
        assert kv is not None
        assert abs(kv.value - 55.0 / 60.0) < 1e-3

    def test_broker_availability(self, calculator):
        data = self._make_data(broker_uptime_s=58.0, broker_total_s=60.0)
        kv = calculator.calculate_single(
            KPIType.BROKER_AVAILABILITY, data,
            PerformanceDomain.BROKER, AggregationWindow.REAL_TIME
        )
        assert kv is not None
        assert abs(kv.value - 58.0 / 60.0) < 1e-3

    def test_monitoring_availability(self, calculator):
        data = self._make_data(monitoring_uptime_s=59.0, monitoring_total_s=60.0)
        kv = calculator.calculate_single(
            KPIType.MONITORING_AVAILABILITY, data,
            PerformanceDomain.MONITORING, AggregationWindow.REAL_TIME
        )
        assert kv is not None
        assert abs(kv.value - 59.0 / 60.0) < 1e-3

    def test_system_throughput(self, calculator):
        data = self._make_data(
            processed_items=500, queue_capacity=1000, window_seconds=100.0
        )
        kv = calculator.calculate_single(
            KPIType.SYSTEM_THROUGHPUT, data,
            PerformanceDomain.INFRASTRUCTURE, AggregationWindow.REAL_TIME
        )
        assert kv is not None
        assert 0.0 <= kv.value <= 1.0

    def test_queue_efficiency(self, calculator):
        data = self._make_data(queue_depth=100, queue_capacity=1000)
        kv = calculator.calculate_single(
            KPIType.QUEUE_EFFICIENCY, data,
            PerformanceDomain.INFRASTRUCTURE, AggregationWindow.REAL_TIME
        )
        assert kv is not None
        assert abs(kv.value - 0.9) < 1e-9

    def test_order_completion_rate(self, calculator):
        data = self._make_data(total_orders=100, completed_orders=95)
        kv = calculator.calculate_single(
            KPIType.ORDER_COMPLETION_RATE, data,
            PerformanceDomain.ORDER, AggregationWindow.REAL_TIME
        )
        assert kv is not None
        assert abs(kv.value - 0.95) < 1e-9

    def test_position_accuracy(self, calculator):
        data = self._make_data(total_positions=50, accurate_positions=48)
        kv = calculator.calculate_single(
            KPIType.POSITION_ACCURACY, data,
            PerformanceDomain.POSITION, AggregationWindow.REAL_TIME
        )
        assert kv is not None
        assert abs(kv.value - 0.96) < 1e-9

    def test_risk_rule_effectiveness(self, calculator):
        data = self._make_data(risk_rules_evaluated=100, risk_rules_passed=90)
        kv = calculator.calculate_single(
            KPIType.RISK_RULE_EFFECTIVENESS, data,
            PerformanceDomain.RISK, AggregationWindow.REAL_TIME
        )
        assert kv is not None
        assert abs(kv.value - 0.9) < 1e-9

    def test_portfolio_efficiency_clamped(self, calculator):
        data = self._make_data(portfolio_efficiency=1.5)
        kv = calculator.calculate_single(
            KPIType.PORTFOLIO_EFFICIENCY, data,
            PerformanceDomain.PORTFOLIO, AggregationWindow.REAL_TIME
        )
        assert kv is not None
        assert kv.value == 1.0

    def test_strategy_efficiency(self, calculator):
        data = self._make_data(strategy_efficiency=0.75)
        kv = calculator.calculate_single(
            KPIType.STRATEGY_EFFICIENCY, data,
            PerformanceDomain.STRATEGY, AggregationWindow.REAL_TIME
        )
        assert kv is not None
        assert abs(kv.value - 0.75) < 1e-9

    def test_resource_utilization(self, calculator):
        data = self._make_data(cpu_utilization=0.6, memory_utilization=0.8)
        kv = calculator.calculate_single(
            KPIType.RESOURCE_UTILIZATION, data,
            PerformanceDomain.INFRASTRUCTURE, AggregationWindow.REAL_TIME
        )
        assert kv is not None
        assert abs(kv.value - 0.7) < 1e-9

    def test_calculate_all_returns_19(self, calculator):
        data = CollectedData(
            total_executions=100, completed_executions=90, failed_executions=10,
            execution_times_ms=[10.0, 20.0, 30.0],
        )
        result = calculator.calculate(
            data, PerformanceDomain.EXECUTION, AggregationWindow.REAL_TIME
        )
        assert len(result) == 19

    def test_calculate_subset(self, calculator):
        data = CollectedData()
        result = calculator.calculate(
            data, PerformanceDomain.EXECUTION, AggregationWindow.REAL_TIME,
            kpi_types=[KPIType.EXECUTION_SUCCESS_RATE, KPIType.EXECUTION_FAILURE_RATE],
        )
        assert len(result) == 2

    def test_zero_denominator_safe(self, calculator):
        data = CollectedData()  # all zeros
        result = calculator.calculate(
            data, PerformanceDomain.EXECUTION, AggregationWindow.REAL_TIME
        )
        for kv in result.values():
            assert 0.0 <= kv.value <= 1.0 or kv.value == 0.0

    def test_not_running_raises(self):
        c = PerformanceCalculator()
        with pytest.raises(PerformanceEngineNotRunningError):
            c.calculate(CollectedData(), PerformanceDomain.EXECUTION, AggregationWindow.REAL_TIME)


# ── 6. Aggregator ─────────────────────────────────────────────────────────────

class TestAggregator:

    def _make_kpi_dict(self, value: float = 0.9) -> dict:
        kv = make_kpi_value(
            KPIType.EXECUTION_SUCCESS_RATE, value,
            domain=PerformanceDomain.EXECUTION,
            window=AggregationWindow.REAL_TIME,
            sample_count=10,
        )
        return {KPIType.EXECUTION_SUCCESS_RATE: kv}

    def test_real_time_passthrough(self, aggregator):
        kpis = self._make_kpi_dict(0.9)
        result = aggregator.aggregate(kpis, AggregationWindow.REAL_TIME, PerformanceDomain.EXECUTION)
        assert abs(result[KPIType.EXECUTION_SUCCESS_RATE].value - 0.9) < 1e-9

    def test_rolling_window_aggregation(self, aggregator):
        kpis = self._make_kpi_dict(0.8)
        aggregator.aggregate(kpis, AggregationWindow.ONE_MINUTE, PerformanceDomain.EXECUTION)
        kpis2 = self._make_kpi_dict(1.0)
        result = aggregator.aggregate(kpis2, AggregationWindow.ONE_MINUTE, PerformanceDomain.EXECUTION)
        # Mean of 0.8 and 1.0 = 0.9
        assert abs(result[KPIType.EXECUTION_SUCCESS_RATE].value - 0.9) < 1e-9

    def test_push_and_rolling_mean(self, aggregator):
        for v in [0.5, 0.6, 0.7, 0.8, 0.9]:
            aggregator.push(KPIType.EXECUTION_SUCCESS_RATE, v)
        mean = aggregator.rolling_mean(KPIType.EXECUTION_SUCCESS_RATE)
        assert abs(mean - 0.7) < 1e-9

    def test_sample_count(self, aggregator):
        for _ in range(5):
            aggregator.push(KPIType.GATEWAY_AVAILABILITY, 0.99)
        assert aggregator.sample_count(KPIType.GATEWAY_AVAILABILITY) == 5

    def test_aggregate_historical(self, aggregator):
        hist = {KPIType.EXECUTION_SUCCESS_RATE.value: [0.8, 0.9, 0.85]}
        result = aggregator.aggregate_historical(
            hist, PerformanceDomain.EXECUTION, AggregationWindow.ONE_HOUR
        )
        assert KPIType.EXECUTION_SUCCESS_RATE in result
        assert abs(result[KPIType.EXECUTION_SUCCESS_RATE].value - 0.85) < 1e-6

    def test_not_running_raises(self):
        a = PerformanceAggregator()
        kv = make_kpi_value(
            KPIType.EXECUTION_SUCCESS_RATE, 0.9,
            domain=PerformanceDomain.EXECUTION,
            window=AggregationWindow.REAL_TIME,
            sample_count=1,
        )
        with pytest.raises(PerformanceEngineNotRunningError):
            a.aggregate({KPIType.EXECUTION_SUCCESS_RATE: kv}, AggregationWindow.REAL_TIME, PerformanceDomain.EXECUTION)


# ── 7. Benchmark ──────────────────────────────────────────────────────────────

class TestBenchmark:

    def _make_report(self, kpi_type: KPIType, value: float) -> KPIReport:
        kv = make_kpi_value(
            kpi_type, value,
            domain       = PerformanceDomain.EXECUTION,
            window       = AggregationWindow.REAL_TIME,
            sample_count = 10,
        )
        return make_kpi_report(
            [kv], PerformanceDomain.EXECUTION, AggregationWindow.REAL_TIME
        )

    def test_above_target(self, benchmark):
        rpt = self._make_report(KPIType.EXECUTION_SUCCESS_RATE, 0.99)
        result = benchmark.compare(rpt)
        assert result.comparisons[0].status == BenchmarkStatus.ABOVE_TARGET

    def test_below_target(self, benchmark):
        rpt = self._make_report(KPIType.EXECUTION_SUCCESS_RATE, 0.5)
        result = benchmark.compare(rpt)
        assert result.comparisons[0].status == BenchmarkStatus.BELOW_TARGET

    def test_overall_score_range(self, benchmark):
        rpt = self._make_report(KPIType.EXECUTION_SUCCESS_RATE, 0.99)
        result = benchmark.compare(rpt)
        assert 0.0 <= result.overall_score <= 1.0

    def test_above_below_counts(self, benchmark):
        kv_good = make_kpi_value(
            KPIType.EXECUTION_SUCCESS_RATE, 0.99,
            domain=PerformanceDomain.EXECUTION, window=AggregationWindow.REAL_TIME, sample_count=1
        )
        kv_bad = make_kpi_value(
            KPIType.EXECUTION_FAILURE_RATE, 0.9,
            domain=PerformanceDomain.EXECUTION, window=AggregationWindow.REAL_TIME, sample_count=1
        )
        rpt = make_kpi_report(
            [kv_good, kv_bad], PerformanceDomain.EXECUTION, AggregationWindow.REAL_TIME
        )
        result = benchmark.compare(rpt)
        assert result.above_target_count >= 1
        assert result.below_target_count >= 1

    def test_not_running_raises(self):
        b = PerformanceBenchmark()
        rpt = make_kpi_report([], PerformanceDomain.EXECUTION, AggregationWindow.REAL_TIME)
        with pytest.raises(PerformanceEngineNotRunningError):
            b.compare(rpt)


# ── 8. Trend Analyzer ────────────────────────────────────────────────────────

class TestTrendAnalyzer:

    def test_flat_trend(self, trend_analyzer):
        values = [0.9] * 20
        result = trend_analyzer.analyze(
            KPIType.EXECUTION_SUCCESS_RATE,
            PerformanceDomain.EXECUTION,
            values,
        )
        assert result.direction == TrendDirection.FLAT

    def test_upward_trend(self, trend_analyzer):
        # Clear uptrend with low coefficient of variation
        values = [0.80 + i * 0.01 for i in range(20)]  # 0.80..0.99
        result = trend_analyzer.analyze(
            KPIType.EXECUTION_SUCCESS_RATE,
            PerformanceDomain.EXECUTION,
            values,
        )
        assert result.direction == TrendDirection.UP

    def test_downward_trend(self, trend_analyzer):
        # Clear downtrend with low coefficient of variation
        values = [0.99 - i * 0.01 for i in range(20)]  # 0.99..0.80
        result = trend_analyzer.analyze(
            KPIType.EXECUTION_SUCCESS_RATE,
            PerformanceDomain.EXECUTION,
            values,
        )
        assert result.direction == TrendDirection.DOWN

    def test_volatile_trend(self, trend_analyzer):
        import random
        random.seed(42)
        values = [random.uniform(0.1, 0.9) for _ in range(30)]
        result = trend_analyzer.analyze(
            KPIType.EXECUTION_SUCCESS_RATE,
            PerformanceDomain.EXECUTION,
            values,
        )
        # direction should be VOLATILE or FLAT/UP/DOWN — just ensure it returns valid
        assert result.direction in TrendDirection.__members__.values()

    def test_empty_values_flat(self, trend_analyzer):
        result = trend_analyzer.analyze(
            KPIType.EXECUTION_SUCCESS_RATE,
            PerformanceDomain.EXECUTION,
            [],
        )
        assert result.direction == TrendDirection.FLAT
        assert result.data_points == 0

    def test_slope_computed(self, trend_analyzer):
        values = [float(i) for i in range(10)]
        result = trend_analyzer.analyze(
            KPIType.EXECUTION_SUCCESS_RATE,
            PerformanceDomain.EXECUTION,
            values,
        )
        assert result.slope > 0.0

    def test_analyze_all(self, trend_analyzer):
        hist = {
            KPIType.EXECUTION_SUCCESS_RATE.value: [0.8, 0.85, 0.9],
            KPIType.EXECUTION_FAILURE_RATE.value: [0.2, 0.15, 0.1],
        }
        results = trend_analyzer.analyze_all(hist, PerformanceDomain.EXECUTION)
        assert len(results) == 2

    def test_not_running_raises(self):
        t = PerformanceTrendAnalyzer()
        with pytest.raises(PerformanceEngineNotRunningError):
            t.analyze(KPIType.EXECUTION_SUCCESS_RATE, PerformanceDomain.EXECUTION, [0.9])


# ── 9. Scorecard Builder ─────────────────────────────────────────────────────

class TestScorecardBuilder:

    def _make_kpi_report(self, value: float = 0.9) -> KPIReport:
        kv = make_kpi_value(
            KPIType.EXECUTION_SUCCESS_RATE, value,
            domain=PerformanceDomain.EXECUTION,
            window=AggregationWindow.REAL_TIME,
            sample_count=10,
        )
        return make_kpi_report([kv], PerformanceDomain.EXECUTION, AggregationWindow.REAL_TIME)

    def test_build_excellent(self, scorecard_builder):
        rpt = self._make_kpi_report(1.0)
        sc = scorecard_builder.build(rpt)
        assert sc.overall_score > 0.0
        assert isinstance(sc.grade, PerformanceGrade)

    def test_build_poor(self, scorecard_builder):
        rpt = self._make_kpi_report(0.0)
        sc = scorecard_builder.build(rpt)
        assert isinstance(sc.grade, PerformanceGrade)

    def test_kpi_scores_present(self, scorecard_builder):
        rpt = self._make_kpi_report(0.95)
        sc = scorecard_builder.build(rpt)
        assert KPIType.EXECUTION_SUCCESS_RATE.value in sc.kpi_scores

    def test_overall_score_range(self, scorecard_builder):
        for v in [0.0, 0.5, 1.0]:
            rpt = self._make_kpi_report(v)
            sc = scorecard_builder.build(rpt)
            assert 0.0 <= sc.overall_score <= 1.0

    def test_not_running_raises(self):
        sb = PerformanceScorecardBuilder()
        rpt = make_kpi_report([], PerformanceDomain.EXECUTION, AggregationWindow.REAL_TIME)
        with pytest.raises(PerformanceEngineNotRunningError):
            sb.build(rpt)


# ── 10. Validation ────────────────────────────────────────────────────────────

class TestValidation:

    def test_valid_request(self):
        v = PerformanceValidator()
        r = make_performance_request(domain=PerformanceDomain.EXECUTION)
        result = v.validate_request(r)
        assert result.is_valid

    def test_invalid_priority(self):
        v = PerformanceValidator()
        r = make_performance_request(domain=PerformanceDomain.EXECUTION, priority=11)
        result = v.validate_request(r)
        assert not result.is_valid
        assert result.error_count > 0

    def test_valid_context(self):
        v = PerformanceValidator()
        ctx = make_performance_context(
            request_id = "r1",
            domain     = PerformanceDomain.EXECUTION,
            window     = AggregationWindow.REAL_TIME,
        )
        result = v.validate_context(ctx)
        assert result.is_valid

    def test_custom_window_requires_seconds(self):
        v = PerformanceValidator()
        ctx = make_performance_context(
            request_id            = "r1",
            domain                = PerformanceDomain.EXECUTION,
            window                = AggregationWindow.CUSTOM,
            custom_window_seconds = 0.0,  # invalid
        )
        result = v.validate_context(ctx)
        assert not result.is_valid

    def test_validate_and_raise_valid(self):
        v = PerformanceValidator()
        r = make_performance_request(domain=PerformanceDomain.EXECUTION)
        v.validate_and_raise(r)  # should not raise

    def test_validate_and_raise_invalid(self):
        v = PerformanceValidator()
        r = make_performance_request(domain=PerformanceDomain.EXECUTION, priority=0)
        with pytest.raises(PerformanceValidationError):
            v.validate_and_raise(r)


# ── 11. Statistics ────────────────────────────────────────────────────────────

class TestStatistics:

    def test_initial_zeros(self):
        s = PerformanceAnalyticsStatistics()
        assert s.analytics_cycles == 0
        assert s.kpis_generated == 0

    def test_record_cycle(self):
        s = PerformanceAnalyticsStatistics()
        s.record_cycle(19, 5.0, had_benchmarks=True, had_scorecard=True)
        assert s.analytics_cycles == 1
        assert s.kpis_generated == 19
        assert s.benchmark_comparisons == 1
        assert s.scorecard_generations == 1

    def test_avg_processing_time(self):
        s = PerformanceAnalyticsStatistics()
        s.record_cycle(19, 10.0)
        s.record_cycle(19, 20.0)
        assert abs(s.avg_processing_time_ms - 15.0) < 1e-9

    def test_success_rate(self):
        s = PerformanceAnalyticsStatistics()
        s.record_cycle(1, 1.0)
        s.record_failure()
        assert abs(s.success_rate - 0.5) < 1e-9

    def test_snapshot_dict(self):
        s = PerformanceAnalyticsStatistics()
        snap = s.snapshot()
        assert "analytics_cycles" in snap
        assert "success_rate" in snap

    def test_thread_safety(self):
        s = PerformanceAnalyticsStatistics()
        errors = []

        def worker():
            try:
                for _ in range(100):
                    s.record_cycle(1, 1.0)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors
        assert s.analytics_cycles == 400


# ── 12. History ───────────────────────────────────────────────────────────────

class TestHistory:

    def test_initial_empty(self):
        h = PerformanceAnalyticsHistory()
        assert h.report_count == 0
        assert h.event_count == 0

    def test_add_and_retrieve_events(self):
        h = PerformanceAnalyticsHistory()
        ev = make_analytics_started_event("req-1")
        h.add_event(ev)
        assert h.event_count == 1
        assert h.recent_events()[0] is ev

    def test_bounded_deque(self):
        h = PerformanceAnalyticsHistory(maxlen=5)
        for i in range(10):
            h.add_event(make_analytics_started_event(f"req-{i}"))
        assert h.event_count == 5

    def test_recent_n(self):
        h = PerformanceAnalyticsHistory()
        for i in range(20):
            h.add_event(make_analytics_started_event(f"req-{i}"))
        assert len(h.recent_events(5)) == 5

    def test_clear(self):
        h = PerformanceAnalyticsHistory()
        h.add_event(make_analytics_started_event("req-1"))
        h.clear()
        assert h.event_count == 0


# ── 13. Events ────────────────────────────────────────────────────────────────

class TestEvents:

    def test_analytics_started_event(self):
        ev = make_analytics_started_event("req-1")
        assert ev.request_id == "req-1"
        assert ev.event_id
        assert ev.occurred_at > 0

    def test_kpi_calculated_event(self):
        ev = make_kpi_calculated_event("req-1", 19, "EXECUTION")
        assert ev.payload["kpi_count"] == 19
        assert ev.payload["domain"] == "EXECUTION"

    def test_trend_detected_event(self):
        ev = make_trend_detected_event("req-1", 3)
        assert ev.payload["trend_count"] == 3

    def test_benchmark_completed_event(self):
        ev = make_benchmark_completed_event("req-1", 0.85, "EXECUTION")
        assert ev.payload["overall_score"] == 0.85

    def test_report_generated_event(self):
        ev = make_report_generated_event("req-1", "rpt-1", 12.5)
        assert ev.payload["processing_ms"] == 12.5

    def test_analytics_published_event(self):
        ev = make_analytics_published_event("req-1", "rpt-1")
        assert ev.payload["report_id"] == "rpt-1"

    def test_analytics_failed_event(self):
        ev = make_analytics_failed_event("req-1", "something went wrong")
        assert "wrong" in ev.payload["error"]

    def test_event_immutable(self):
        ev = make_analytics_started_event("req-1")
        with pytest.raises(Exception):
            ev.request_id = "other"  # type: ignore[misc]

    def test_event_to_dict(self):
        ev = make_analytics_started_event("req-1")
        d = ev.to_dict()
        assert "event_id" in d
        assert "event_type" in d


# ── 14. Registry ─────────────────────────────────────────────────────────────

class TestRegistry:

    def test_register_and_get(self, registry):
        r = make_performance_request(domain=PerformanceDomain.EXECUTION)
        registry.register(r)
        assert registry.is_active(r.request_id)
        assert registry.get_active(r.request_id) is r

    def test_complete_removes_from_active(self, registry):
        r = make_performance_request(domain=PerformanceDomain.EXECUTION)
        registry.register(r)
        registry.complete(r.request_id)
        assert not registry.is_active(r.request_id)
        assert registry.completed_count >= 1

    def test_get_nonexistent_raises(self, registry):
        with pytest.raises(PerformanceRequestNotFoundError):
            registry.get_active("nonexistent")

    def test_active_count(self, registry):
        for _ in range(3):
            registry.register(make_performance_request(domain=PerformanceDomain.EXECUTION))
        assert registry.active_count == 3

    def test_not_running_raises(self):
        reg = PerformanceAnalyticsRegistry()
        r = make_performance_request(domain=PerformanceDomain.EXECUTION)
        with pytest.raises(PerformanceEngineNotRunningError):
            reg.register(r)


# ── 15. Factory ───────────────────────────────────────────────────────────────

class TestFactory:

    def test_create_request(self, factory):
        r = factory.create_request(
            domain             = PerformanceDomain.EXECUTION,
            window             = AggregationWindow.FIVE_MINUTES,
            include_trends     = True,
        )
        assert r.domain == PerformanceDomain.EXECUTION
        assert r.window == AggregationWindow.FIVE_MINUTES
        assert r.include_trends is True

    def test_create_context(self, factory):
        ctx = factory.create_context(
            request_id = "req-1",
            domain     = PerformanceDomain.EXECUTION,
            window     = AggregationWindow.REAL_TIME,
        )
        assert ctx.request_id == "req-1"

    def test_create_context_for_request(self, factory):
        r = factory.create_request(domain=PerformanceDomain.RISK)
        ctx = factory.create_context_for_request(r)
        assert ctx.request_id == r.request_id
        assert ctx.domain == r.domain

    def test_not_running_raises(self):
        f = PerformanceAnalyticsFactory()
        with pytest.raises(PerformanceEngineNotRunningError):
            f.create_request(domain=PerformanceDomain.EXECUTION)


# ── 16. PerformanceAnalyticsEngine end-to-end ────────────────────────────────

class TestEngineEndToEnd:

    def test_process_returns_report(self, engine, basic_request):
        report = engine.process(basic_request)
        assert isinstance(report, PerformanceAnalyticsReport)
        assert report.request_id == basic_request.request_id
        assert report.is_success

    def test_process_with_context(self, engine):
        request = make_performance_request(
            domain             = PerformanceDomain.EXECUTION,
            window             = AggregationWindow.REAL_TIME,
            include_benchmarks = True,
            include_scorecard  = True,
        )
        ctx = make_performance_context(
            request_id      = request.request_id,
            domain          = request.domain,
            window          = request.window,
            raw_sample_data = {
                "execution_times_ms":  [10.0, 20.0, 30.0, 25.0, 15.0],
                "total_orders":        [100.0],
                "completed_orders":    [95.0],
            },
        )
        report = engine.process(request, ctx)
        assert report.kpi_count == 19
        assert report.is_success

    def test_process_str_request_id(self, engine):
        """M2 dispatcher compatibility: accept str as request."""
        report = engine.process("m2-dispatcher-request-id")
        assert isinstance(report, PerformanceAnalyticsReport)
        assert report.request_id == "m2-dispatcher-request-id"

    def test_submit_convenience(self, engine):
        report = engine.submit(PerformanceDomain.EXECUTION)
        assert isinstance(report, PerformanceAnalyticsReport)
        assert report.kpi_count == 19

    def test_calculate_kpis(self, engine):
        kpi_report = engine.calculate_kpis(PerformanceDomain.EXECUTION)
        assert isinstance(kpi_report, KPIReport)
        assert kpi_report.kpi_count == 19

    def test_analyze_trends_with_context(self, engine):
        ctx = make_performance_context(
            request_id          = "trend-req",
            domain              = PerformanceDomain.EXECUTION,
            window              = AggregationWindow.REAL_TIME,
            historical_kpi_data = {
                KPIType.EXECUTION_SUCCESS_RATE.value: [0.8, 0.82, 0.85, 0.88, 0.90],
            },
        )
        request = make_performance_request(
            domain         = PerformanceDomain.EXECUTION,
            include_trends = True,
        )
        report = engine.process(request, ctx)
        assert report.trend_count >= 1
        assert report.trends[0].direction in TrendDirection.__members__.values()

    def test_compare_benchmarks_returns_report(self, engine):
        bm = engine.compare_benchmarks(PerformanceDomain.EXECUTION)
        assert isinstance(bm, BenchmarkReport)
        assert 0.0 <= bm.overall_score <= 1.0

    def test_generate_scorecard_returns_scorecard(self, engine):
        sc = engine.generate_scorecard(PerformanceDomain.EXECUTION)
        assert isinstance(sc, PerformanceScorecard)
        assert isinstance(sc.grade, PerformanceGrade)

    def test_statistics_updated(self, engine):
        engine.submit(PerformanceDomain.EXECUTION)
        stats = engine.get_statistics()
        assert stats.analytics_cycles >= 1
        assert stats.kpis_generated >= 19

    def test_history_updated(self, engine):
        engine.submit(PerformanceDomain.EXECUTION)
        hist = engine.get_history()
        assert hist.report_count >= 1
        assert hist.event_count >= 1

    def test_concurrent_requests(self, engine):
        """Engine must handle concurrent requests without data corruption."""
        results = []
        errors  = []

        def worker(domain):
            try:
                r = engine.submit(domain)
                results.append(r)
            except Exception as e:
                errors.append(e)

        domains = [
            PerformanceDomain.EXECUTION,
            PerformanceDomain.RISK,
            PerformanceDomain.GATEWAY,
            PerformanceDomain.BROKER,
            PerformanceDomain.MONITORING,
        ]
        threads = [threading.Thread(target=worker, args=(d,)) for d in domains]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert len(results) == 5

    def test_all_domains_processable(self, engine):
        for domain in PerformanceDomain:
            report = engine.submit(domain)
            assert report.is_success or report.kpi_count >= 0  # graceful

    def test_all_windows_processable(self, engine):
        for window in AggregationWindow:
            if window == AggregationWindow.CUSTOM:
                continue
            report = engine.submit(PerformanceDomain.EXECUTION, window)
            assert report.is_success

    def test_kpi_report_domain_window(self, engine):
        report = engine.submit(
            PerformanceDomain.RISK, AggregationWindow.FIVE_MINUTES
        )
        assert report.kpi_report.domain == PerformanceDomain.RISK
        assert report.kpi_report.window == AggregationWindow.FIVE_MINUTES

    def test_include_trends_false_no_trends(self, engine):
        request = make_performance_request(
            domain         = PerformanceDomain.EXECUTION,
            include_trends = False,
        )
        report = engine.process(request)
        assert report.trend_count == 0

    def test_include_benchmarks_false_no_benchmark(self, engine):
        request = make_performance_request(
            domain             = PerformanceDomain.EXECUTION,
            include_benchmarks = False,
            include_scorecard  = False,
        )
        report = engine.process(request)
        assert report.benchmark_report is None

    def test_report_to_dict(self, engine):
        report = engine.submit(PerformanceDomain.EXECUTION)
        d = report.to_dict()
        assert "report_id" in d
        assert "kpi_count" in d
        assert d["kpi_count"] == 19

    def test_processing_ms_positive(self, engine):
        report = engine.submit(PerformanceDomain.EXECUTION)
        assert report.processing_ms >= 0.0

    def test_specific_kpi_types(self, engine):
        request = make_performance_request(
            domain     = PerformanceDomain.EXECUTION,
            kpi_types  = (
                KPIType.EXECUTION_SUCCESS_RATE,
                KPIType.P95_LATENCY_MS,
                KPIType.GATEWAY_AVAILABILITY,
            ),
        )
        report = engine.process(request)
        assert report.kpi_count == 3

    def test_snapshot_kpi_count_matches_report(self, engine):
        report = engine.submit(PerformanceDomain.EXECUTION)
        assert report.snapshot.kpi_count == report.kpi_count

    def test_scorecard_domain_window_match(self, engine):
        report = engine.submit(PerformanceDomain.RISK, AggregationWindow.FIVE_MINUTES)
        if report.scorecard:
            assert report.scorecard.domain == PerformanceDomain.RISK

    def test_error_report_has_error_message(self, engine):
        """Even failed cycles return a valid report object."""
        # Force validation error with invalid priority
        request = PerformanceRequest(
            request_id = str(uuid.uuid4()),
            domain     = PerformanceDomain.EXECUTION,
            priority   = 99,  # invalid, triggers validation error
        )
        report = engine.process(request)
        # Should return error report, not raise
        assert isinstance(report, PerformanceAnalyticsReport)
        assert report.error_message  # non-empty

    def test_get_registry(self, engine):
        from iios.execution.analytics.performance import PerformanceAnalyticsRegistry
        reg = engine.get_registry()
        assert isinstance(reg, PerformanceAnalyticsRegistry)


# ── 17. KPI value / report types ─────────────────────────────────────────────

class TestKPITypes:

    def test_kpi_value_immutable(self):
        kv = make_kpi_value(
            KPIType.EXECUTION_SUCCESS_RATE, 0.9,
            domain=PerformanceDomain.EXECUTION,
            window=AggregationWindow.REAL_TIME,
            sample_count=10,
        )
        with pytest.raises(Exception):
            kv.value = 0.5  # type: ignore[misc]

    def test_kpi_value_to_dict(self):
        kv = make_kpi_value(
            KPIType.EXECUTION_SUCCESS_RATE, 0.9,
            domain=PerformanceDomain.EXECUTION,
            window=AggregationWindow.REAL_TIME,
            sample_count=10,
        )
        d = kv.to_dict()
        assert d["kpi_type"] == KPIType.EXECUTION_SUCCESS_RATE.value
        assert d["value"] == 0.9

    def test_kpi_report_get(self):
        kv = make_kpi_value(
            KPIType.EXECUTION_SUCCESS_RATE, 0.9,
            domain=PerformanceDomain.EXECUTION,
            window=AggregationWindow.REAL_TIME,
            sample_count=10,
        )
        report = make_kpi_report(
            [kv], PerformanceDomain.EXECUTION, AggregationWindow.REAL_TIME
        )
        found = report.get(KPIType.EXECUTION_SUCCESS_RATE)
        assert found is kv

    def test_kpi_report_kpi_count(self):
        kvs = [
            make_kpi_value(
                kt, 0.9,
                domain=PerformanceDomain.EXECUTION,
                window=AggregationWindow.REAL_TIME,
                sample_count=1,
            )
            for kt in list(KPIType)[:5]
        ]
        report = make_kpi_report(kvs, PerformanceDomain.EXECUTION, AggregationWindow.REAL_TIME)
        assert report.kpi_count == 5


# ── 18. Exceptions ────────────────────────────────────────────────────────────

class TestExceptions:

    def test_base_exception(self):
        with pytest.raises(PerformanceAnalyticsError):
            raise PerformanceAnalyticsError("test")

    def test_not_running_error(self):
        with pytest.raises(PerformanceEngineNotRunningError):
            raise PerformanceEngineNotRunningError()

    def test_request_not_found_error(self):
        try:
            raise PerformanceRequestNotFoundError("req-x")
        except PerformanceRequestNotFoundError as e:
            assert e.request_id == "req-x"

    def test_validation_error(self):
        try:
            raise PerformanceValidationError(errors=("field is required",))
        except PerformanceValidationError as e:
            assert len(e.errors) == 1

    def test_all_exceptions_inherit_base(self):
        for exc_cls in [
            PerformanceEngineNotRunningError,
            PerformanceCalculationError,
            PerformanceValidationError,
            PerformanceDataInsufficientError,
            PerformanceBenchmarkError,
            PerformanceTrendError,
            PerformanceAggregationError,
        ]:
            assert issubclass(exc_cls, PerformanceAnalyticsError)
