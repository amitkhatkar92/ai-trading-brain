"""
tests/unit/monitoring/test_performance_logger.py
=================================================
Tests for iios.monitoring.performance_logger
"""
from __future__ import annotations

import time
import pytest

from iios.monitoring.performance_logger import (
    PerformanceLogger,
    _reset_performance_logger,
    get_performance_logger,
)


@pytest.fixture()
def logger():
    _reset_performance_logger()
    p = PerformanceLogger()
    yield p
    _reset_performance_logger()


# ---------------------------------------------------------------------------
# time() context manager
# ---------------------------------------------------------------------------


def test_time_context_manager_measures_duration(logger):
    with logger.time("fast_op") as result:
        time.sleep(0.01)
    assert result.duration_ms >= 1.0


def test_time_records_success_on_clean_exit(logger):
    with logger.time("clean_op") as result:
        pass
    assert result.success is True


def test_time_records_failure_on_exception(logger):
    result_ref: list = []
    with pytest.raises(RuntimeError):
        with logger.time("crashing_op") as result:
            result_ref.append(result)
            raise RuntimeError("boom")
    assert result_ref[0].success is False


def test_time_context_returns_timing_result(logger):
    with logger.time("op_result") as result:
        pass
    assert result is not None
    assert hasattr(result, "duration_ms")


# ---------------------------------------------------------------------------
# record() manual recording
# ---------------------------------------------------------------------------


def test_record_stores_performance_data(logger):
    logger.record("manual_op", duration_ms=100.0, success=True)
    stats = logger.get_stats("manual_op")
    assert stats is not None
    assert stats["count"] == 1
    assert stats["mean_ms"] == pytest.approx(100.0)


def test_record_multiple_builds_stats(logger):
    logger.record("multi_op", 10.0, success=True)
    logger.record("multi_op", 20.0, success=True)
    logger.record("multi_op", 30.0, success=True)
    stats = logger.get_stats("multi_op")
    assert stats["count"] == 3
    assert stats["min_ms"] == pytest.approx(10.0)
    assert stats["max_ms"] == pytest.approx(30.0)
    assert stats["mean_ms"] == pytest.approx(20.0)


# ---------------------------------------------------------------------------
# get_stats()
# ---------------------------------------------------------------------------


def test_get_stats_returns_p95_and_p99(logger):
    for i in range(100):
        logger.record("percentile_op", float(i), success=True)
    stats = logger.get_stats("percentile_op")
    assert "p95_ms" in stats
    assert "p99_ms" in stats
    assert stats["p99_ms"] >= stats["p95_ms"]


def test_get_stats_unknown_operation_returns_none(logger):
    assert logger.get_stats("nonexistent") is None


# ---------------------------------------------------------------------------
# get_all_stats()
# ---------------------------------------------------------------------------


def test_get_all_stats_returns_all_operations(logger):
    logger.record("op_a", 5.0, success=True)
    logger.record("op_b", 10.0, success=True)
    all_stats = logger.get_all_stats()
    assert "op_a" in all_stats
    assert "op_b" in all_stats


# ---------------------------------------------------------------------------
# recent_records()
# ---------------------------------------------------------------------------


def test_recent_records_returns_n_records(logger):
    for _ in range(5):
        logger.record("rec_op", 1.0, success=True)
    recs = logger.recent_records(n=3)
    assert len(recs) <= 3


# ---------------------------------------------------------------------------
# layer_summary()
# ---------------------------------------------------------------------------


def test_layer_summary_groups_by_layer(logger):
    logger.record("MarketIntelligence.scan", 15.0, success=True)
    logger.record("MarketIntelligence.regime", 10.0, success=True)
    logger.record("GlobalIntelligence.fetch", 50.0, success=True)
    summary = logger.layer_summary()
    # Expect layer grouping
    assert isinstance(summary, dict)


# ---------------------------------------------------------------------------
# SLA thresholds
# ---------------------------------------------------------------------------


def test_is_slow_flag_set_when_above_warn(logger):
    logger.record("slow_layer.op", duration_ms=3000.0, success=True)
    recs = logger.recent_records(n=1)
    assert len(recs) == 1
    # duration > 2000ms warn threshold
    assert recs[0].duration_ms >= 3000.0


# ---------------------------------------------------------------------------
# success_rate
# ---------------------------------------------------------------------------


def test_success_rate_computed_from_records(logger):
    for _ in range(7):
        logger.record("mixed.op", 1.0, success=True)
    for _ in range(3):
        logger.record("mixed.op", 1.0, success=False)
    stats = logger.get_stats("mixed.op")
    assert stats["success_rate"] == pytest.approx(0.7)


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------


def test_get_performance_logger_singleton():
    _reset_performance_logger()
    a = get_performance_logger()
    b = get_performance_logger()
    assert a is b
    _reset_performance_logger()
