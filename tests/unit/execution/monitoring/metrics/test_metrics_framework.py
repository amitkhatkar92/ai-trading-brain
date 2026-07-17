"""tests/unit/execution/monitoring/metrics/test_metrics_framework.py
===========================================================================
Comprehensive unit tests for the Execution Metrics Framework.

C6 Execution Intelligence — Phase 6, Module 3
"""
from __future__ import annotations

import threading
import time
from typing import List

import pytest

from iios.execution.monitoring.metrics import (
    AggregationType,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_POINTS,
    InsufficientDataError,
    MetricAggregationError,
    MetricCalculationError,
    MetricCategory,
    MetricPoint,
    MetricSeriesNotFoundError,
    MetricType,
    MetricsAggregator,
    MetricsCalculator,
    MetricsCollector,
    MetricsContext,
    MetricsEngine,
    MetricsEngineNotRunningError,
    MetricsEvent,
    MetricsEventType,
    MetricsFactory,
    MetricsFrameworkError,
    MetricsHistory,
    MetricsManager,
    MetricsRegistry,
    MetricsRegistryCapacityError,
    MetricsRequest,
    MetricsResponse,
    MetricsSnapshot,
    MetricsSnapshotError,
    MetricsStatistics,
    MetricsValidationError,
    MetricsValidator,
    ValidationResult,
    VERSION,
    WINDOW_SECONDS,
    WindowSize,
    make_aggregation_completed,
    make_calculation_failed,
    make_metrics_aggregated,
    make_metrics_calculated,
    make_metrics_collected,
    make_metrics_context,
    make_metrics_published,
    make_metrics_request,
    make_metrics_response,
    make_metrics_snapshot,
)


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def engine():
    """Running MetricsEngine instance."""
    e = MetricsEngine()
    e.start()
    yield e
    if e.lifecycle_state() in ("running", "RUNNING"):
        e.stop()


@pytest.fixture
def populated_engine(engine):
    """Engine with some data recorded."""
    for i in range(10):
        engine.record("sess-1", MetricType.P99_LATENCY, float(i + 1))
        engine.record("sess-1", MetricType.EXECUTION_COUNT, 1.0)
        engine.record("sess-1", MetricType.SUCCESS_RATE, 0.9)
    return engine


# ─── TestConstants ────────────────────────────────────────────────────────────

class TestConstants:
    def test_metric_type_count(self):
        assert len(MetricType) == 17

    def test_metric_category_count(self):
        assert len(MetricCategory) == 10

    def test_window_size_count(self):
        assert len(WindowSize) == 7

    def test_aggregation_type_count(self):
        assert len(AggregationType) == 10

    def test_event_type_count(self):
        assert len(MetricsEventType) == 6

    def test_metric_type_values_are_lowercase(self):
        for mt in MetricType:
            assert mt.value == mt.value.lower(), f"{mt.name} value not lowercase"

    def test_window_seconds_covers_all_windows(self):
        for w in WindowSize:
            assert w.value in WINDOW_SECONDS, f"{w.value} missing from WINDOW_SECONDS"

    def test_session_window_is_zero(self):
        assert WINDOW_SECONDS["session"] == 0

    def test_one_minute_window(self):
        assert WINDOW_SECONDS["1m"] == 60

    def test_one_hour_window(self):
        assert WINDOW_SECONDS["1h"] == 3_600

    def test_version_format(self):
        parts = VERSION.split(".")
        assert len(parts) == 3
        assert all(p.isdigit() for p in parts)

    def test_default_max_points(self):
        assert DEFAULT_MAX_POINTS == 10_000

    def test_default_max_history(self):
        assert DEFAULT_MAX_HISTORY == 1_000


# ─── TestExceptions ───────────────────────────────────────────────────────────

class TestExceptions:
    def test_base_error_code(self):
        e = MetricsFrameworkError()
        assert e.error_code == "MF-000"

    def test_not_running_code(self):
        e = MetricsEngineNotRunningError()
        assert e.error_code == "MF-001"

    def test_series_not_found_code(self):
        e = MetricSeriesNotFoundError("s1")
        assert e.error_code == "MF-002"
        assert e.series_id  == "s1"

    def test_calculation_error_code(self):
        e = MetricCalculationError("p99_latency", "division by zero")
        assert e.error_code  == "MF-003"
        assert e.metric_type == "p99_latency"

    def test_aggregation_error_code(self):
        e = MetricAggregationError("1m", "empty window")
        assert e.error_code == "MF-004"
        assert e.window     == "1m"

    def test_registry_capacity_code(self):
        e = MetricsRegistryCapacityError(100)
        assert e.error_code == "MF-005"
        assert e.max_count  == 100

    def test_validation_error_code(self):
        e = MetricsValidationError("bad request", errors=("err1",))
        assert e.error_code == "MF-006"
        assert "err1" in e.errors

    def test_snapshot_error_code(self):
        e = MetricsSnapshotError("missing field")
        assert e.error_code == "MF-007"

    def test_insufficient_data_code(self):
        e = InsufficientDataError(required=5, available=2)
        assert e.error_code == "MF-008"
        assert e.required   == 5
        assert e.available  == 2

    def test_all_inherit_base(self):
        errors = [
            MetricsEngineNotRunningError(),
            MetricSeriesNotFoundError("x"),
            MetricCalculationError(),
            MetricAggregationError(),
            MetricsRegistryCapacityError(1),
            MetricsValidationError(),
            MetricsSnapshotError(),
            InsufficientDataError(),
        ]
        for err in errors:
            assert isinstance(err, MetricsFrameworkError)


# ─── TestMetricsContext ───────────────────────────────────────────────────────

class TestMetricsContext:
    def test_required_fields(self):
        ctx = make_metrics_context("sess-1", "port-1")
        assert ctx.session_id   == "sess-1"
        assert ctx.portfolio_id == "port-1"

    def test_optional_defaults(self):
        ctx = make_metrics_context("sess-1", "port-1")
        assert ctx.strategy_id  is None
        assert ctx.gateway_id   is None
        assert ctx.workflow_id  is None

    def test_optional_fields_set(self):
        ctx = make_metrics_context(
            "sess-1", "port-1",
            strategy_id="strat-1",
            gateway_id="gw-1",
        )
        assert ctx.has_gateway  is True
        assert ctx.has_strategy is True

    def test_default_window(self):
        ctx = make_metrics_context("sess-1", "port-1")
        assert ctx.default_window == WindowSize.FIVE_MINUTES

    def test_frozen(self):
        ctx = make_metrics_context("sess-1", "port-1")
        with pytest.raises((AttributeError, TypeError)):
            ctx.session_id = "other"  # type: ignore

    def test_to_dict(self):
        ctx = make_metrics_context("sess-1", "port-1")
        d   = ctx.to_dict()
        assert d["session_id"]   == "sess-1"
        assert d["portfolio_id"] == "port-1"


# ─── TestMetricsRequest ───────────────────────────────────────────────────────

class TestMetricsRequest:
    def test_basic_fields(self):
        req = make_metrics_request(
            "sess-1",
            (MetricType.P99_LATENCY,),
        )
        assert req.session_id          == "sess-1"
        assert req.metric_types        == (MetricType.P99_LATENCY,)
        assert req.window_size         == WindowSize.FIVE_MINUTES
        assert req.metric_count        == 1
        assert req.has_time_range      is False

    def test_time_range(self):
        now = time.time()
        req = make_metrics_request(
            "sess-1",
            (MetricType.P99_LATENCY,),
            from_timestamp=now - 60,
            to_timestamp=now,
        )
        assert req.has_time_range is True

    def test_unique_request_ids(self):
        r1 = make_metrics_request("s", (MetricType.P99_LATENCY,))
        r2 = make_metrics_request("s", (MetricType.P99_LATENCY,))
        assert r1.request_id != r2.request_id

    def test_frozen(self):
        req = make_metrics_request("sess-1", (MetricType.P99_LATENCY,))
        with pytest.raises((AttributeError, TypeError)):
            req.session_id = "other"  # type: ignore

    def test_to_dict(self):
        req = make_metrics_request("sess-1", (MetricType.P99_LATENCY,))
        d   = req.to_dict()
        assert d["session_id"] == "sess-1"
        assert "p99_latency" in d["metric_types"]


# ─── TestMetricsResponse ──────────────────────────────────────────────────────

class TestMetricsResponse:
    def test_basic_fields(self):
        resp = make_metrics_response(
            "req-1", "sess-1",
            {"p99_latency": 42.5},
        )
        assert resp.session_id    == "sess-1"
        assert resp.request_id   == "req-1"
        assert resp.metric_count == 1
        assert resp.is_complete  is True

    def test_with_errors(self):
        resp = make_metrics_response(
            "req-1", "sess-1",
            {},
            errors=("calculation failed",),
        )
        assert resp.has_errors is True
        assert resp.is_complete is False

    def test_get(self):
        resp = make_metrics_response(
            "req-1", "sess-1",
            {"p99_latency": 42.5},
        )
        assert resp.get("p99_latency")      == 42.5
        assert resp.get("missing", 0.0)     == 0.0

    def test_frozen(self):
        resp = make_metrics_response("req-1", "sess-1", {})
        with pytest.raises((AttributeError, TypeError)):
            resp.session_id = "other"  # type: ignore

    def test_to_dict(self):
        resp = make_metrics_response(
            "req-1", "sess-1",
            {"p99_latency": 42.5},
        )
        d = resp.to_dict()
        assert d["session_id"]              == "sess-1"
        assert d["metrics"]["p99_latency"]  == 42.5


# ─── TestMetricsSnapshot ─────────────────────────────────────────────────────

class TestMetricsSnapshot:
    def test_basic_fields(self):
        snap = make_metrics_snapshot(
            "sess-1", "port-1",
            {"p99_latency": 42.5},
        )
        assert snap.session_id   == "sess-1"
        assert snap.portfolio_id == "port-1"
        assert snap.metric_count == 1

    def test_snapshot_version_default(self):
        snap = make_metrics_snapshot("sess-1", "port-1", {})
        assert snap.snapshot_version == 1

    def test_get(self):
        snap = make_metrics_snapshot(
            "sess-1", "port-1",
            {"p99_latency": 42.5},
        )
        assert snap.get("p99_latency")  == 42.5
        assert snap.get("missing", 9.9) == 9.9

    def test_get_window(self):
        snap = make_metrics_snapshot(
            "sess-1", "port-1",
            {},
            window_metrics={"5m": {"p99_latency": 33.0}},
        )
        assert snap.get_window("5m", "p99_latency")  == 33.0
        assert snap.get_window("1m", "p99_latency")  == 0.0

    def test_is_newer_than(self):
        s1 = make_metrics_snapshot("sess-1", "port-1", {}, snapshot_version=1)
        time.sleep(0.01)
        s2 = make_metrics_snapshot("sess-1", "port-1", {}, snapshot_version=2)
        assert s2.is_newer_than(s1) is True
        assert s1.is_newer_than(s2) is False

    def test_total_points(self):
        snap = make_metrics_snapshot(
            "sess-1", "port-1",
            {},
            point_counts={"p99_latency": 10, "success_rate": 5},
        )
        assert snap.total_points == 15

    def test_frozen(self):
        snap = make_metrics_snapshot("sess-1", "port-1", {})
        with pytest.raises((AttributeError, TypeError)):
            snap.session_id = "other"  # type: ignore

    def test_to_dict_and_json(self):
        snap = make_metrics_snapshot(
            "sess-1", "port-1",
            {"p99_latency": 42.5},
        )
        d = snap.to_dict()
        assert d["session_id"]              == "sess-1"
        assert d["metrics"]["p99_latency"]  == 42.5
        j = snap.to_json()
        assert "sess-1" in j

    def test_unique_snapshot_ids(self):
        s1 = make_metrics_snapshot("sess-1", "port-1", {})
        s2 = make_metrics_snapshot("sess-1", "port-1", {})
        assert s1.snapshot_id != s2.snapshot_id


# ─── TestMetricsHistory ───────────────────────────────────────────────────────

class TestMetricsHistory:
    def _snap(self, session_id="s1", portfolio_id="p"):
        return make_metrics_snapshot(session_id, portfolio_id, {})

    def test_append_snapshot(self):
        h = MetricsHistory()
        h.append_snapshot(self._snap())
        assert h.snapshot_count == 1

    def test_maxlen_snapshots(self):
        h = MetricsHistory(max_snapshots=3)
        for _ in range(5):
            h.append_snapshot(self._snap())
        assert h.snapshot_count == 3

    def test_latest_snapshot(self):
        h = MetricsHistory()
        s1 = self._snap("s1")
        s2 = self._snap("s2")
        h.append_snapshot(s1)
        h.append_snapshot(s2)
        assert h.latest_snapshot() is s2

    def test_latest_snapshot_none_when_empty(self):
        h = MetricsHistory()
        assert h.latest_snapshot() is None

    def test_snapshots_for_session(self):
        h = MetricsHistory()
        h.append_snapshot(self._snap("s1"))
        h.append_snapshot(self._snap("s2"))
        assert len(h.snapshots_for_session("s1")) == 1

    def test_latest_snapshot_for_session(self):
        h = MetricsHistory()
        s1 = self._snap("s1")
        s2 = self._snap("s1")
        h.append_snapshot(s1)
        h.append_snapshot(s2)
        assert h.latest_snapshot_for_session("s1") is s2

    def test_responses_and_events(self):
        h = MetricsHistory()
        resp = make_metrics_response("r1", "s1", {})
        ev   = make_metrics_collected("s1")
        h.append_response(resp)
        h.append_event(ev)
        assert h.response_count == 1
        assert h.event_count    == 1

    def test_events_for_session(self):
        h = MetricsHistory()
        h.append_event(make_metrics_collected("s1"))
        h.append_event(make_metrics_collected("s2"))
        assert len(h.events_for_session("s1")) == 1

    def test_clear(self):
        h = MetricsHistory()
        h.append_snapshot(self._snap())
        h.append_event(make_metrics_collected("x"))
        h.clear()
        assert h.snapshot_count == 0
        assert h.event_count    == 0

    def test_events_matching(self):
        h = MetricsHistory()
        h.append_event(make_metrics_collected("s1"))
        h.append_event(make_metrics_calculated("s1"))
        collected = h.events_matching(
            lambda e: e.event_type == MetricsEventType.METRICS_COLLECTED
        )
        assert len(collected) == 1


# ─── TestMetricsStatistics ────────────────────────────────────────────────────

class TestMetricsStatistics:
    def test_initial_zeroes(self):
        s = MetricsStatistics()
        assert s.metrics_calculated   == 0
        assert s.calculation_failures == 0
        assert s.aggregation_count    == 0
        assert s.metrics_published    == 0

    def test_record_calculation(self):
        s = MetricsStatistics()
        s.record_calculation(100.0)
        assert s.metrics_calculated             == 1
        assert s.average_calculation_time_ms    == 100.0

    def test_average_calculation_time(self):
        s = MetricsStatistics()
        s.record_calculation(200.0)
        s.record_calculation(400.0)
        assert abs(s.average_calculation_time_ms - 300.0) < 1e-6

    def test_calculation_success_rate(self):
        s = MetricsStatistics()
        s.record_calculation()
        s.record_calculation()
        s.record_calculation_failure()
        assert abs(s.calculation_success_rate - (2/3)) < 1e-6

    def test_zero_rates_before_any_data(self):
        s = MetricsStatistics()
        assert s.calculation_success_rate == 0.0
        assert s.aggregation_success_rate == 0.0

    def test_reset(self):
        s = MetricsStatistics()
        s.record_calculation(100.0)
        s.record_published()
        s.reset()
        assert s.metrics_calculated == 0
        assert s.metrics_published  == 0

    def test_copy_is_independent(self):
        s = MetricsStatistics()
        s.record_calculation()
        c = s.copy()
        s.record_calculation()
        assert c.metrics_calculated == 1
        assert s.metrics_calculated == 2

    def test_to_dict(self):
        s = MetricsStatistics()
        d = s.to_dict()
        assert "metrics_calculated"         in d
        assert "average_calculation_time_ms" in d

    def test_thread_safe_increments(self):
        s = MetricsStatistics()
        threads = [threading.Thread(target=s.record_data_point) for _ in range(200)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert s.data_points_recorded == 200


# ─── TestMetricsEvents ────────────────────────────────────────────────────────

class TestMetricsEvents:
    def test_make_collected(self):
        e = make_metrics_collected("s1")
        assert e.event_type == MetricsEventType.METRICS_COLLECTED
        assert e.session_id == "s1"

    def test_make_calculated(self):
        e = make_metrics_calculated("s1")
        assert e.event_type == MetricsEventType.METRICS_CALCULATED

    def test_make_aggregated(self):
        e = make_metrics_aggregated("s1")
        assert e.event_type == MetricsEventType.METRICS_AGGREGATED

    def test_make_published(self):
        e = make_metrics_published("s1")
        assert e.event_type == MetricsEventType.METRICS_PUBLISHED

    def test_make_calculation_failed(self):
        e = make_calculation_failed("s1", reason="div-by-zero")
        assert e.event_type == MetricsEventType.CALCULATION_FAILED
        assert e.reason     == "div-by-zero"

    def test_make_aggregation_completed(self):
        e = make_aggregation_completed("s1")
        assert e.event_type == MetricsEventType.AGGREGATION_COMPLETED

    def test_unique_event_ids(self):
        e1 = make_metrics_collected("s1")
        e2 = make_metrics_collected("s1")
        assert e1.event_id != e2.event_id

    def test_frozen(self):
        e = make_metrics_collected("s1")
        with pytest.raises((AttributeError, TypeError)):
            e.session_id = "other"  # type: ignore

    def test_to_dict(self):
        e = make_metrics_collected("s1")
        d = e.to_dict()
        assert d["event_type"] == "METRICS_COLLECTED"
        assert d["session_id"] == "s1"


# ─── TestMetricsValidation ────────────────────────────────────────────────────

class TestMetricsValidation:
    def test_valid_context(self):
        v   = MetricsValidator()
        ctx = make_metrics_context("sess-1", "port-1")
        r   = v.validate_context(ctx)
        assert r.is_valid is True

    def test_missing_session_id(self):
        v   = MetricsValidator()
        ctx = make_metrics_context("", "port-1")
        r   = v.validate_context(ctx)
        assert r.is_valid is False

    def test_missing_portfolio_id(self):
        v   = MetricsValidator()
        ctx = make_metrics_context("sess-1", "")
        r   = v.validate_context(ctx)
        assert r.is_valid is False

    def test_valid_request(self):
        v   = MetricsValidator()
        req = make_metrics_request("s", (MetricType.P99_LATENCY,))
        r   = v.validate_request(req)
        assert r.is_valid is True

    def test_empty_metric_types(self):
        v   = MetricsValidator()
        req = make_metrics_request("s", ())
        r   = v.validate_request(req)
        assert r.is_valid is False

    def test_invalid_time_range(self):
        v   = MetricsValidator()
        now = time.time()
        req = make_metrics_request(
            "s", (MetricType.P99_LATENCY,),
            from_timestamp=now,
            to_timestamp=now - 60,
        )
        r = v.validate_request(req)
        assert r.is_valid is False

    def test_valid_snapshot(self):
        v    = MetricsValidator()
        snap = make_metrics_snapshot("s", "p", {"p99": 1.0})
        r    = v.validate_snapshot(snap)
        assert r.is_valid is True

    def test_invalid_metric_value_negative_latency(self):
        v = MetricsValidator()
        r = v.validate_metric_value("p99_latency", -5.0)
        assert r.is_valid is False

    def test_rate_out_of_range_is_warning(self):
        v = MetricsValidator()
        r = v.validate_metric_value("success_rate", 1.5)
        assert r.is_valid is True
        assert len(r.warnings) > 0

    def test_validation_result_operations(self):
        r = ValidationResult(is_valid=True)
        r.add_warning("warn")
        r.add_error("error")
        assert r.is_valid      is False
        assert len(r.warnings) == 1
        assert len(r.errors)   == 1
        assert "is_valid" in r.to_dict()


# ─── TestMetricsCalculator ────────────────────────────────────────────────────

class TestMetricsCalculator:
    def test_sum(self):
        assert MetricsCalculator.calculate_sum([1, 2, 3]) == 6.0

    def test_sum_empty(self):
        assert MetricsCalculator.calculate_sum([]) == 0.0

    def test_count(self):
        assert MetricsCalculator.calculate_count([1, 2, 3]) == 3.0

    def test_average(self):
        assert MetricsCalculator.calculate_average([1, 2, 3]) == 2.0

    def test_average_empty(self):
        assert MetricsCalculator.calculate_average([]) == 0.0

    def test_median_odd(self):
        assert MetricsCalculator.calculate_median([3, 1, 2]) == 2.0

    def test_median_even(self):
        assert MetricsCalculator.calculate_median([1, 2, 3, 4]) == 2.5

    def test_median_empty(self):
        assert MetricsCalculator.calculate_median([]) == 0.0

    def test_min(self):
        assert MetricsCalculator.calculate_min([5, 1, 3]) == 1.0

    def test_max(self):
        assert MetricsCalculator.calculate_max([5, 1, 3]) == 5.0

    def test_min_max_empty(self):
        assert MetricsCalculator.calculate_min([]) == 0.0
        assert MetricsCalculator.calculate_max([]) == 0.0

    def test_std_dev(self):
        vals = [2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0]
        assert abs(MetricsCalculator.calculate_std_dev(vals) - 2.0) < 0.01

    def test_std_dev_single_value(self):
        assert MetricsCalculator.calculate_std_dev([42.0]) == 0.0

    def test_percentile_p50(self):
        vals = list(range(1, 101))
        p50  = MetricsCalculator.calculate_percentile(vals, 50)
        assert abs(p50 - 50.5) < 0.5

    def test_percentile_p95(self):
        vals = list(range(1, 101))
        p95  = MetricsCalculator.calculate_p95(vals)
        assert 94.0 <= p95 <= 96.0

    def test_percentile_p99(self):
        vals = list(range(1, 101))
        p99  = MetricsCalculator.calculate_p99(vals)
        assert 98.0 <= p99 <= 100.0

    def test_percentile_empty(self):
        assert MetricsCalculator.calculate_percentile([], 95) == 0.0

    def test_percentile_single(self):
        assert MetricsCalculator.calculate_percentile([42.0], 95) == 42.0

    def test_percentile_invalid_range(self):
        with pytest.raises(ValueError):
            MetricsCalculator.calculate_percentile([1.0], 101)

    def test_rate_normal(self):
        assert MetricsCalculator.calculate_rate(8, 10) == 0.8

    def test_rate_zero_denominator(self):
        assert MetricsCalculator.calculate_rate(5, 0) == 0.0

    def test_rate_clamped(self):
        assert MetricsCalculator.calculate_rate(15, 10) == 1.0
        assert MetricsCalculator.calculate_rate(-1, 10) == 0.0

    def test_throughput(self):
        assert MetricsCalculator.calculate_throughput(60, 60) == 1.0

    def test_throughput_zero_window(self):
        assert MetricsCalculator.calculate_throughput(10, 0) == 0.0

    def test_rolling_average(self):
        vals   = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = MetricsCalculator.calculate_rolling_average(vals, 3)
        assert len(result) == 5
        assert result[-1] == (3.0 + 4.0 + 5.0) / 3

    def test_rolling_average_empty(self):
        assert MetricsCalculator.calculate_rolling_average([], 3) == []

    def test_change_rate(self):
        assert MetricsCalculator.calculate_change_rate(110, 100) == pytest.approx(0.1)

    def test_change_rate_zero_previous(self):
        assert MetricsCalculator.calculate_change_rate(100, 0) == 0.0

    def test_compute_success_rate(self):
        assert MetricsCalculator.compute_success_rate(8, 10) == 0.8

    def test_compute_failure_rate(self):
        assert MetricsCalculator.compute_failure_rate(2, 10) == 0.2


# ─── TestMetricsCollector ─────────────────────────────────────────────────────

class TestMetricsCollector:
    def test_record_and_collect(self):
        c = MetricsCollector()
        c.record("s1", MetricType.P99_LATENCY, 42.5)
        vals = c.collect("s1", MetricType.P99_LATENCY)
        assert vals == [42.5]

    def test_collect_empty(self):
        c = MetricsCollector()
        assert c.collect("s1", MetricType.P99_LATENCY) == []

    def test_collect_limit(self):
        c = MetricsCollector()
        for i in range(10):
            c.record("s1", MetricType.P99_LATENCY, float(i))
        vals = c.collect("s1", MetricType.P99_LATENCY, limit=5)
        assert len(vals) == 5
        assert vals == [5.0, 6.0, 7.0, 8.0, 9.0]

    def test_count(self):
        c = MetricsCollector()
        c.record("s1", MetricType.P99_LATENCY, 1.0)
        c.record("s1", MetricType.P99_LATENCY, 2.0)
        assert c.count("s1", MetricType.P99_LATENCY) == 2

    def test_collect_windowed_includes_recent(self):
        c = MetricsCollector()
        c.record("s1", MetricType.P99_LATENCY, 10.0,
                 timestamp=time.time() - 30)   # 30s ago — within 1m window
        vals = c.collect_windowed("s1", MetricType.P99_LATENCY, WindowSize.ONE_MINUTE)
        assert 10.0 in vals

    def test_collect_windowed_excludes_old(self):
        c = MetricsCollector()
        c.record("s1", MetricType.P99_LATENCY, 10.0,
                 timestamp=time.time() - 200)   # 200s ago — outside 1m window
        vals = c.collect_windowed("s1", MetricType.P99_LATENCY, WindowSize.ONE_MINUTE)
        assert vals == []

    def test_session_window_returns_all(self):
        c = MetricsCollector()
        c.record("s1", MetricType.P99_LATENCY, 10.0,
                 timestamp=time.time() - 200)
        vals = c.collect_windowed("s1", MetricType.P99_LATENCY, WindowSize.SESSION)
        assert 10.0 in vals

    def test_clear_metric(self):
        c = MetricsCollector()
        c.record("s1", MetricType.P99_LATENCY, 1.0)
        c.clear("s1", MetricType.P99_LATENCY)
        assert c.collect("s1", MetricType.P99_LATENCY) == []

    def test_clear_session(self):
        c = MetricsCollector()
        c.record("s1", MetricType.P99_LATENCY, 1.0)
        c.record("s1", MetricType.SUCCESS_RATE, 0.9)
        c.clear("s1")
        assert c.collect("s1", MetricType.P99_LATENCY)  == []
        assert c.collect("s1", MetricType.SUCCESS_RATE) == []

    def test_remove_session(self):
        c = MetricsCollector()
        c.record("s1", MetricType.P99_LATENCY, 1.0)
        c.remove_session("s1")
        assert c.series_count() == 0

    def test_sessions(self):
        c = MetricsCollector()
        c.record("s1", MetricType.P99_LATENCY, 1.0)
        c.record("s2", MetricType.P99_LATENCY, 2.0)
        assert set(c.sessions()) == {"s1", "s2"}

    def test_total_points(self):
        c = MetricsCollector()
        c.record("s1", MetricType.P99_LATENCY, 1.0)
        c.record("s1", MetricType.P99_LATENCY, 2.0)
        c.record("s2", MetricType.SUCCESS_RATE, 0.9)
        assert c.total_points() == 3

    def test_thread_safe_records(self):
        c = MetricsCollector()
        def rec():
            c.record("s1", MetricType.EXECUTION_COUNT, 1.0)
        threads = [threading.Thread(target=rec) for _ in range(100)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert c.count("s1", MetricType.EXECUTION_COUNT) == 100


# ─── TestMetricsAggregator ────────────────────────────────────────────────────

class TestMetricsAggregator:
    def _agg(self):
        collector = MetricsCollector()
        return MetricsAggregator(collector), collector

    def test_aggregate_sum(self):
        agg, _ = self._agg()
        assert agg.aggregate([1.0, 2.0, 3.0], AggregationType.SUM) == 6.0

    def test_aggregate_average(self):
        agg, _ = self._agg()
        assert agg.aggregate([1.0, 2.0, 3.0], AggregationType.AVERAGE) == 2.0

    def test_aggregate_p95(self):
        agg, _ = self._agg()
        vals    = list(range(1, 101))
        result  = agg.aggregate(vals, AggregationType.P95)
        assert 94 <= result <= 96

    def test_aggregate_count(self):
        agg, _ = self._agg()
        assert agg.aggregate([1, 2, 3], AggregationType.COUNT) == 3.0

    def test_aggregate_window(self):
        agg, collector = self._agg()
        collector.record("s1", MetricType.P99_LATENCY, 100.0)
        collector.record("s1", MetricType.P99_LATENCY, 200.0)
        result = agg.aggregate_window(
            "s1", MetricType.P99_LATENCY,
            WindowSize.SESSION, AggregationType.AVERAGE
        )
        assert abs(result - 150.0) < 1e-6

    def test_aggregate_empty_window(self):
        agg, _ = self._agg()
        result = agg.aggregate_window(
            "s1", MetricType.P99_LATENCY,
            WindowSize.ONE_MINUTE, AggregationType.AVERAGE
        )
        assert result == 0.0

    def test_aggregate_all_windows(self):
        agg, collector = self._agg()
        for i in range(5):
            collector.record("s1", MetricType.P99_LATENCY, float(i + 10))
        result = agg.aggregate_all_windows(
            "s1", [MetricType.P99_LATENCY],
            windows=[WindowSize.SESSION],
        )
        assert "session" in result
        assert "p99_latency" in result["session"]

    def test_aggregate_all_session(self):
        agg, collector = self._agg()
        collector.record("s1", MetricType.P99_LATENCY, 100.0)
        collector.record("s1", MetricType.P99_LATENCY, 200.0)
        result = agg.aggregate_all_session("s1", [MetricType.P99_LATENCY])
        assert "p99_latency" in result
        # P99 of [100, 200] via linear interpolation: 100 + 0.99*(200-100) = 199.0
        assert abs(result["p99_latency"] - 199.0) < 1e-6


# ─── TestMetricsRegistry ─────────────────────────────────────────────────────

class TestMetricsRegistry:
    def _reg(self):
        reg = MetricsRegistry()
        reg.start()
        return reg

    def _snap(self, session_id="s1", portfolio_id="p"):
        return make_metrics_snapshot(session_id, portfolio_id, {})

    def test_store_and_get_latest(self):
        reg  = self._reg()
        snap = self._snap("s1")
        reg.store(snap)
        assert reg.get_latest("s1") is snap
        reg.stop()

    def test_not_found_raises(self):
        reg = self._reg()
        with pytest.raises(MetricSeriesNotFoundError) as exc_info:
            reg.get_latest("nonexistent")
        assert exc_info.value.error_code == "MF-002"
        reg.stop()

    def test_capacity_raises(self):
        reg = MetricsRegistry(max_snapshots=2)
        reg.start()
        reg.store(self._snap("s1"))
        reg.store(self._snap("s2"))
        with pytest.raises(MetricsRegistryCapacityError) as exc_info:
            reg.store(self._snap("s3"))
        assert exc_info.value.error_code == "MF-005"
        reg.stop()

    def test_overwrite_same_session(self):
        reg  = self._reg()
        s1   = self._snap("s1")
        s2   = make_metrics_snapshot("s1", "p", {"updated": 1.0})
        reg.store(s1)
        reg.store(s2)  # should overwrite, not exceed capacity
        assert reg.get_latest("s1") is s2
        reg.stop()

    def test_find_latest_none(self):
        reg = self._reg()
        assert reg.find_latest("missing") is None
        reg.stop()

    def test_by_portfolio(self):
        reg = self._reg()
        reg.store(make_metrics_snapshot("s1", "port-A", {}))
        reg.store(make_metrics_snapshot("s2", "port-A", {}))
        reg.store(make_metrics_snapshot("s3", "port-B", {}))
        assert len(reg.by_portfolio("port-A")) == 2
        reg.stop()

    def test_not_running_raises(self):
        reg = MetricsRegistry()
        snap = self._snap()
        with pytest.raises(MetricsEngineNotRunningError) as exc_info:
            reg.store(snap)
        assert exc_info.value.error_code == "MF-001"

    def test_contains(self):
        reg  = self._reg()
        snap = self._snap("s1")
        reg.store(snap)
        assert reg.contains("s1")  is True
        assert reg.contains("xxx") is False
        reg.stop()

    def test_remove(self):
        reg  = self._reg()
        snap = self._snap("s1")
        reg.store(snap)
        reg.remove("s1")
        assert reg.contains("s1") is False
        reg.stop()


# ─── TestMetricsFactory ───────────────────────────────────────────────────────

class TestMetricsFactory:
    def _factory(self):
        f = MetricsFactory()
        f.start()
        return f

    def test_create_snapshot(self):
        f   = self._factory()
        ctx = make_metrics_context("s1", "p1")
        s   = f.create_snapshot(ctx, {"p99": 42.0})
        assert s.session_id   == "s1"
        assert s.portfolio_id == "p1"
        assert s.get("p99")   == 42.0
        f.stop()

    def test_snapshot_version_increments(self):
        f   = self._factory()
        ctx = make_metrics_context("s1", "p1")
        s1  = f.create_snapshot(ctx, {})
        s2  = f.create_snapshot(ctx, {})
        assert s2.snapshot_version == s1.snapshot_version + 1
        f.stop()

    def test_create_request(self):
        f   = self._factory()
        req = f.create_request("s1", (MetricType.P99_LATENCY,))
        assert req.session_id == "s1"
        f.stop()

    def test_create_response(self):
        f   = self._factory()
        req = f.create_request("s1", (MetricType.P99_LATENCY,))
        r   = f.create_response(req, {"p99_latency": 42.0})
        assert r.session_id   == "s1"
        assert r.request_id   == req.request_id
        f.stop()

    def test_not_running_raises(self):
        f   = MetricsFactory()
        ctx = make_metrics_context("s1", "p1")
        with pytest.raises(MetricsEngineNotRunningError):
            f.create_snapshot(ctx, {})


# ─── TestMetricsManager ───────────────────────────────────────────────────────

class TestMetricsManager:
    def _manager(self):
        m = MetricsManager()
        m.start()
        return m

    def test_record(self):
        m = self._manager()
        p = m.record("s1", MetricType.P99_LATENCY, 42.5)
        assert p.value == 42.5
        m.stop()

    def test_not_running_raises(self):
        m = MetricsManager()
        with pytest.raises(MetricsEngineNotRunningError):
            m.record("s1", MetricType.P99_LATENCY, 1.0)

    def test_compute_metric(self):
        m = self._manager()
        for i in range(5):
            m.record("s1", MetricType.P99_LATENCY, float(i + 1))
        result = m.compute_metric("s1", MetricType.P99_LATENCY, WindowSize.SESSION)
        assert result > 0.0
        m.stop()

    def test_compute_all_session(self):
        m = self._manager()
        m.record("s1", MetricType.P99_LATENCY, 42.5)
        result = m.compute_all_session("s1", [MetricType.P99_LATENCY])
        assert "p99_latency" in result
        m.stop()

    def test_compute_window_metrics(self):
        m = self._manager()
        m.record("s1", MetricType.P99_LATENCY, 42.5)
        result = m.compute_window_metrics(
            "s1", [MetricType.P99_LATENCY],
            [WindowSize.SESSION]
        )
        assert "session" in result
        assert "p99_latency" in result["session"]
        m.stop()

    def test_compute_point_counts(self):
        m = self._manager()
        m.record("s1", MetricType.P99_LATENCY, 1.0)
        m.record("s1", MetricType.P99_LATENCY, 2.0)
        counts = m.compute_point_counts("s1", [MetricType.P99_LATENCY])
        assert counts["p99_latency"] == 2
        m.stop()

    def test_raw_values(self):
        m = self._manager()
        m.record("s1", MetricType.P99_LATENCY, 100.0)
        vals = m.raw_values("s1", MetricType.P99_LATENCY)
        assert 100.0 in vals
        m.stop()

    def test_total_points(self):
        m = self._manager()
        m.record("s1", MetricType.P99_LATENCY, 1.0)
        m.record("s1", MetricType.P99_LATENCY, 2.0)
        assert m.total_points == 2
        m.stop()

    def test_clear_session(self):
        m = self._manager()
        m.record("s1", MetricType.P99_LATENCY, 1.0)
        m.clear_session("s1")
        assert m.raw_values("s1", MetricType.P99_LATENCY) == []
        m.stop()


# ─── TestMetricsEngine ────────────────────────────────────────────────────────

class TestMetricsEngine:
    def test_record_single(self, engine):
        engine.record("s1", MetricType.P99_LATENCY, 42.5)
        vals = engine.raw_values("s1", MetricType.P99_LATENCY)
        assert 42.5 in vals

    def test_record_batch(self, engine):
        engine.record_batch("s1", [
            (MetricType.P99_LATENCY, 10.0),
            (MetricType.SUCCESS_RATE, 0.9),
        ])
        assert 10.0 in engine.raw_values("s1", MetricType.P99_LATENCY)
        assert 0.9  in engine.raw_values("s1", MetricType.SUCCESS_RATE)

    def test_snapshot_returns_snapshot(self, populated_engine):
        snap = populated_engine.snapshot("sess-1", "port-1")
        assert isinstance(snap, MetricsSnapshot)
        assert snap.session_id   == "sess-1"
        assert snap.portfolio_id == "port-1"

    def test_snapshot_has_metrics(self, populated_engine):
        snap = populated_engine.snapshot("sess-1", "port-1")
        assert "p99_latency" in snap.metrics
        assert snap.get("p99_latency") > 0.0

    def test_snapshot_has_window_metrics(self, populated_engine):
        snap = populated_engine.snapshot(
            "sess-1", "port-1",
            windows=[WindowSize.SESSION],
        )
        assert snap.has_window_metrics is True
        assert "session" in snap.window_metrics

    def test_publish_stores_snapshot(self, engine):
        snap = engine.snapshot("s1", "p1")
        engine.publish(snap)
        latest = engine.get_latest_snapshot("s1")
        assert latest.snapshot_id == snap.snapshot_id

    def test_snapshot_and_publish(self, populated_engine):
        snap = populated_engine.snapshot_and_publish("sess-1", "port-1")
        latest = populated_engine.get_latest_snapshot("sess-1")
        assert latest.snapshot_id == snap.snapshot_id

    def test_find_latest_snapshot_none(self, engine):
        assert engine.find_latest_snapshot("nonexistent") is None

    def test_process_request(self, populated_engine):
        req  = populated_engine.create_request(
            "sess-1", (MetricType.P99_LATENCY,)
        )
        resp = populated_engine.process_request(req)
        assert isinstance(resp, MetricsResponse)
        assert "p99_latency" in resp.metrics

    def test_process_invalid_request_raises(self, engine):
        req = make_metrics_request("", ())  # invalid: empty session_id + empty metric_types
        with pytest.raises(MetricsValidationError) as exc_info:
            engine.process_request(req)
        assert exc_info.value.error_code == "MF-006"

    def test_statistics_track_operations(self, engine):
        engine.record("s1", MetricType.P99_LATENCY, 10.0)
        engine.snapshot("s1", "p1")
        stats = engine.statistics()
        assert stats.data_points_recorded >= 1
        assert stats.metrics_calculated   >= 1

    def test_event_listeners_called(self, engine):
        received: List[MetricsEvent] = []
        engine.add_event_listener(received.append)
        engine.record("s1", MetricType.P99_LATENCY, 10.0)
        assert any(e.event_type == MetricsEventType.METRICS_COLLECTED
                   for e in received)
        engine.remove_event_listener(received.append)

    def test_listener_exception_does_not_propagate(self, engine):
        def bad_listener(event):
            raise RuntimeError("bad")
        engine.add_event_listener(bad_listener)
        engine.record("s1", MetricType.P99_LATENCY, 1.0)  # must not raise
        engine.remove_event_listener(bad_listener)

    def test_duplicate_listener_not_added_twice(self, engine):
        received: List[MetricsEvent] = []
        engine.add_event_listener(received.append)
        engine.add_event_listener(received.append)  # duplicate
        engine.record("s2", MetricType.P99_LATENCY, 1.0)
        collected = [e for e in received
                     if e.event_type == MetricsEventType.METRICS_COLLECTED
                     and e.session_id == "s2"]
        assert len(collected) == 1
        engine.remove_event_listener(received.append)

    def test_not_running_raises(self):
        e = MetricsEngine()
        with pytest.raises(MetricsEngineNotRunningError) as exc_info:
            e.record("s1", MetricType.P99_LATENCY, 1.0)
        assert exc_info.value.error_code == "MF-001"

    def test_history_tracks_events(self, engine):
        engine.record("s1", MetricType.P99_LATENCY, 1.0)
        hist = engine.history()
        assert hist.event_count >= 1

    def test_history_tracks_snapshots_after_publish(self, engine):
        snap = engine.snapshot("s1", "p1")
        engine.publish(snap)
        hist = engine.history()
        assert hist.snapshot_count >= 1


# ─── TestConcurrency ──────────────────────────────────────────────────────────

class TestConcurrency:
    def test_concurrent_record(self, engine):
        errors = []
        def rec(i):
            try:
                engine.record(f"sess-{i % 5}", MetricType.P99_LATENCY, float(i))
            except Exception as e:
                errors.append(e)
        threads = [threading.Thread(target=rec, args=(i,)) for i in range(100)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert errors == []

    def test_concurrent_snapshot(self, populated_engine):
        results = []
        errors  = []
        def take_snap():
            try:
                s = populated_engine.snapshot("sess-1", "port-1")
                results.append(s)
            except Exception as e:
                errors.append(e)
        threads = [threading.Thread(target=take_snap) for _ in range(20)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert errors  == []
        assert len(results) == 20

    def test_concurrent_publish(self, engine):
        errors  = []
        snaps   = [engine.snapshot(f"sess-{i}", f"port-{i}")
                   for i in range(20)]
        def pub(s):
            try:
                engine.publish(s)
            except Exception as e:
                errors.append(e)
        threads = [threading.Thread(target=pub, args=(s,)) for s in snaps]
        for t in threads: t.start()
        for t in threads: t.join()
        assert errors == []


# ─── TestStressTesting ────────────────────────────────────────────────────────

class TestStressTesting:
    def test_high_volume_record(self, engine):
        for i in range(500):
            engine.record("stress-1", MetricType.P99_LATENCY, float(i))
        vals = engine.raw_values("stress-1", MetricType.P99_LATENCY)
        assert len(vals) <= 10_000  # bounded by max_points

    def test_all_metric_types_record(self, engine):
        for mt in MetricType:
            engine.record("all-types", mt, 1.0)
        snap = engine.snapshot("all-types", "port-stress")
        assert snap.metric_count == len(MetricType)

    def test_many_sessions(self, engine):
        for i in range(50):
            engine.record(f"sess-{i}", MetricType.EXECUTION_COUNT, float(i))
        for i in range(50):
            snap = engine.snapshot(f"sess-{i}", "port-many")
            engine.publish(snap)
        assert engine._registry.session_count == 50


# ─── TestRegressionEdgeCases ──────────────────────────────────────────────────

class TestRegressionEdgeCases:
    def test_snapshot_empty_session(self, engine):
        """Snapshot of session with no data returns zero values."""
        snap = engine.snapshot("empty-sess", "port-1")
        assert snap.metric_count == len(MetricType)
        for v in snap.metrics.values():
            assert v == 0.0

    def test_statistics_independent_copy(self, engine):
        engine.record("s1", MetricType.P99_LATENCY, 1.0)
        before = engine.statistics()
        engine.record("s1", MetricType.P99_LATENCY, 2.0)
        after  = engine.statistics()
        assert before.data_points_recorded < after.data_points_recorded

    def test_version_increments_per_session(self, engine):
        ctx = make_metrics_context("s1", "p1")
        f   = engine._factory
        s1  = f.create_snapshot(ctx, {})
        s2  = f.create_snapshot(ctx, {})
        assert s2.snapshot_version == s1.snapshot_version + 1

    def test_p99_calculation_precision(self):
        vals   = [float(i) for i in range(1, 1001)]
        p99    = MetricsCalculator.calculate_p99(vals)
        assert 989.0 <= p99 <= 1000.0

    def test_percentile_monotone_with_data(self):
        vals = [float(i) for i in range(1, 101)]
        p50  = MetricsCalculator.calculate_percentile(vals, 50)
        p95  = MetricsCalculator.calculate_p95(vals)
        p99  = MetricsCalculator.calculate_p99(vals)
        assert p50 < p95 < p99

    def test_rolling_average_window_larger_than_data(self):
        vals   = [1.0, 2.0, 3.0]
        result = MetricsCalculator.calculate_rolling_average(vals, 10)
        assert len(result) == 3
        assert result[-1] == pytest.approx(2.0)

    def test_response_window_metrics_preserved(self):
        resp = make_metrics_response(
            "r1", "s1",
            {},
            window_metrics={"5m": {"p99_latency": 42.0}},
        )
        d = resp.to_dict()
        assert d["window_metrics"]["5m"]["p99_latency"] == 42.0

    def test_engine_stop_is_clean(self):
        e = MetricsEngine()
        e.start()
        e.record("s1", MetricType.P99_LATENCY, 1.0)
        e.stop()
        state = e.lifecycle_state()
        assert state not in ("running", "RUNNING")

    def test_metrics_framework_no_alert_generation(self, engine):
        """Framework emits events, never alert objects."""
        received: List[MetricsEvent] = []
        engine.add_event_listener(received.append)
        engine.record("s1", MetricType.P99_LATENCY, 99999.0)  # very high value
        snap = engine.snapshot("s1", "p1")
        engine.publish(snap)
        # All received objects are MetricsEvent, never AlertEvent or similar
        for obj in received:
            assert isinstance(obj, MetricsEvent), (
                f"Expected MetricsEvent, got {type(obj).__name__}"
            )
        engine.remove_event_listener(received.append)
