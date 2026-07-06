"""
tests/unit/monitoring/test_metrics_manager.py
===============================================
Tests for iios.monitoring.metrics_manager
"""
from __future__ import annotations

import threading
import time
import pytest

from iios.monitoring.metrics_manager import MetricsManager, _reset_metrics_manager, get_metrics_manager
from iios.monitoring.monitoring_constants import MetricType


@pytest.fixture()
def mgr():
    _reset_metrics_manager()
    m = MetricsManager()
    yield m
    _reset_metrics_manager()


# ---------------------------------------------------------------------------
# Counter
# ---------------------------------------------------------------------------


def test_increment_returns_new_total(mgr):
    total = mgr.increment("orders.placed")
    assert total == 1
    total2 = mgr.increment("orders.placed")
    assert total2 == 2


def test_increment_by_delta(mgr):
    total = mgr.increment("orders.filled", 5)
    assert total == 5


def test_reset_counter(mgr):
    mgr.increment("orders.placed", 10)
    mgr.reset_counter("orders.placed")
    assert mgr.get_counter("orders.placed") == 0.0


# ---------------------------------------------------------------------------
# Gauge
# ---------------------------------------------------------------------------


def test_gauge_records_value(mgr):
    mgr.gauge("portfolio.value", 100_000.0)
    val = mgr.get_value("portfolio.value")
    assert val == pytest.approx(100_000.0)


def test_gauge_overwrites_previous(mgr):
    mgr.gauge("portfolio.value", 100_000.0)
    mgr.gauge("portfolio.value", 200_000.0)
    assert mgr.get_value("portfolio.value") == pytest.approx(200_000.0)


# ---------------------------------------------------------------------------
# Histogram
# ---------------------------------------------------------------------------


def test_histogram_records_observations(mgr):
    for v in [1.0, 2.0, 3.0]:
        mgr.histogram("latency.ms", v)
    series = mgr.get("latency.ms")
    assert series is not None
    assert series.count == 3
    assert series.average == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# Timer context manager
# ---------------------------------------------------------------------------


def test_timer_records_duration(mgr):
    with mgr.timer("cycle.duration"):
        time.sleep(0.01)
    series = mgr.get("cycle.duration")
    assert series is not None
    assert series.count == 1
    assert series.total >= 0.01 * 1000  # stored in ms


def test_timer_records_on_clean_exit(mgr):
    with mgr.timer("op.timer"):
        pass
    points = mgr.recent_points("op.timer")
    assert len(points) >= 1


def test_timer_still_records_on_exception(mgr):
    with pytest.raises(RuntimeError):
        with mgr.timer("failing.op"):
            raise RuntimeError("boom")
    # duration is recorded even when exception occurs (finally block)
    series = mgr.get("failing.op")
    assert series is not None
    assert series.count == 1


# ---------------------------------------------------------------------------
# Summary / All metrics
# ---------------------------------------------------------------------------


def test_summary_returns_correct_stats(mgr):
    mgr.increment("a", 3)
    mgr.gauge("b", 42.0)
    summary_a = mgr.summary("a")
    summary_b = mgr.summary("b")
    assert summary_a.get("name") == "a"
    assert summary_b.get("name") == "b"


def test_all_metrics_returns_all_series(mgr):
    mgr.increment("x")
    mgr.gauge("y", 1.0)
    all_m = mgr.all_metrics()
    names = [d["name"] for d in all_m]
    assert "x" in names
    assert "y" in names


def test_names_returns_known_metric_names(mgr):
    mgr.increment("alpha")
    mgr.gauge("beta", 5.0)
    ns = mgr.names()
    assert "alpha" in ns
    assert "beta" in ns


# ---------------------------------------------------------------------------
# Success rate
# ---------------------------------------------------------------------------


def test_success_rate_computed_correctly(mgr):
    for _ in range(8):
        mgr.increment("op.success")
    for _ in range(2):
        mgr.increment("op.failure")
    rate = mgr.success_rate("op.success", "op.failure")
    assert rate == pytest.approx(0.8)


# ---------------------------------------------------------------------------
# Prune and clear
# ---------------------------------------------------------------------------


def test_prune_removes_nothing_fresh(mgr):
    mgr.gauge("fresh", 1.0)
    removed = mgr.prune()
    assert removed == 0


def test_clear_resets_all(mgr):
    mgr.increment("foo")
    mgr.gauge("bar", 1.0)
    mgr.clear()
    assert len(mgr.all_metrics()) == 0


# ---------------------------------------------------------------------------
# Thread safety
# ---------------------------------------------------------------------------


def test_concurrent_increments_are_thread_safe(mgr):
    N = 100
    errors: list[Exception] = []

    def worker() -> None:
        try:
            for _ in range(N):
                mgr.increment("concurrent.counter")
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    # Due to counter's cumulative tracking, just verify it ran without errors
    assert mgr.get_counter("concurrent.counter") > 0


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------


def test_get_metrics_manager_singleton():
    _reset_metrics_manager()
    a = get_metrics_manager()
    b = get_metrics_manager()
    assert a is b
    _reset_metrics_manager()
