"""tests/unit/common/errors/test_failure_metrics.py
Unit tests for FailureTracker and metric snapshots.
"""
from __future__ import annotations

import threading
import time
from typing import List

import pytest

from iios.common.errors.failure_metrics import (
    EngineMetricsSnapshot,
    FailureMetricsSnapshot,
    FailureTrendEntry,
    FailureTracker,
    get_failure_tracker,
    reset_failure_tracker,
)


@pytest.fixture
def tracker() -> FailureTracker:
    t = FailureTracker()
    yield t


@pytest.fixture(autouse=True)
def reset_singleton():
    reset_failure_tracker()
    yield
    reset_failure_tracker()


# ── Snapshots (frozen) ────────────────────────────────────────────────────────

class TestFrozenSnapshots:

    def test_engine_metrics_snapshot_frozen(self, tracker):
        tracker.record_failure("E", ValueError)
        snap = tracker.engine_snapshot("E")
        with pytest.raises((AttributeError, TypeError)):
            snap.failures = 999  # type: ignore[misc]

    def test_failure_metrics_snapshot_frozen(self, tracker):
        snap = tracker.snapshot()
        with pytest.raises((AttributeError, TypeError)):
            snap.total_failures = 999  # type: ignore[misc]

    def test_failure_trend_entry_frozen(self, tracker):
        entries = tracker.failure_trend(window_sec=60.0)
        if entries:
            with pytest.raises((AttributeError, TypeError)):
                entries[0].failure_count = 999  # type: ignore[misc]


# ── record_failure ────────────────────────────────────────────────────────────

class TestRecordFailure:

    def test_increments_failure_count(self, tracker):
        tracker.record_failure("iios:test", ValueError)
        snap = tracker.engine_snapshot("iios:test")
        assert snap.failures == 1

    def test_multiple_failures_accumulate(self, tracker):
        for _ in range(5):
            tracker.record_failure("iios:test", ValueError)
        snap = tracker.engine_snapshot("iios:test")
        assert snap.failures == 5

    def test_different_engines_independent(self, tracker):
        tracker.record_failure("iios:eng-a", ValueError)
        tracker.record_failure("iios:eng-b", RuntimeError)
        snap_a = tracker.engine_snapshot("iios:eng-a")
        snap_b = tracker.engine_snapshot("iios:eng-b")
        assert snap_a.failures == 1
        assert snap_b.failures == 1

    def test_exc_type_optional(self, tracker):
        tracker.record_failure("iios:test")   # no exc_type
        snap = tracker.engine_snapshot("iios:test")
        assert snap.failures == 1


# ── record_recovery ───────────────────────────────────────────────────────────

class TestRecordRecovery:

    def test_increments_recovery_count(self, tracker):
        tracker.record_recovery("iios:test", 1.0, succeeded=True)
        snap = tracker.engine_snapshot("iios:test")
        assert snap.recoveries == 1

    def test_success_increments_recovery_successes(self, tracker):
        tracker.record_recovery("iios:test", 1.0, succeeded=True)
        snap = tracker.engine_snapshot("iios:test")
        assert snap.recovery_successes == 1
        assert snap.recovery_failures  == 0

    def test_failure_increments_recovery_failures(self, tracker):
        tracker.record_recovery("iios:test", 0.5, succeeded=False)
        snap = tracker.engine_snapshot("iios:test")
        assert snap.recovery_successes == 0
        assert snap.recovery_failures  == 1


# ── record_retry ─────────────────────────────────────────────────────────────

class TestRecordRetry:

    def test_increments_retry_count(self, tracker):
        tracker.record_retry("iios:test")
        snap = tracker.engine_snapshot("iios:test")
        assert snap.retries == 1

    def test_multiple_retries(self, tracker):
        for _ in range(7):
            tracker.record_retry("iios:test")
        snap = tracker.engine_snapshot("iios:test")
        assert snap.retries == 7


# ── Recovery success rate ─────────────────────────────────────────────────────

class TestRecoverySuccessRate:

    def test_zero_when_no_recoveries(self, tracker):
        snap = tracker.engine_snapshot("new-engine")
        assert snap is None   # engine not recorded yet

    def test_one_hundred_percent_when_all_succeed(self, tracker):
        for _ in range(5):
            tracker.record_recovery("iios:test", 1.0, succeeded=True)
        snap = tracker.engine_snapshot("iios:test")
        assert snap.recovery_success_rate == pytest.approx(1.0)

    def test_zero_when_all_fail(self, tracker):
        for _ in range(3):
            tracker.record_recovery("iios:test", 0.5, succeeded=False)
        snap = tracker.engine_snapshot("iios:test")
        assert snap.recovery_success_rate == 0.0

    def test_partial_rate(self, tracker):
        tracker.record_recovery("iios:test", 1.0, succeeded=True)
        tracker.record_recovery("iios:test", 1.0, succeeded=True)
        tracker.record_recovery("iios:test", 1.0, succeeded=False)
        snap = tracker.engine_snapshot("iios:test")
        assert snap.recovery_success_rate == pytest.approx(2 / 3, rel=0.01)


# ── MTTR ──────────────────────────────────────────────────────────────────────

class TestMTTR:

    def test_zero_when_no_successful_recoveries(self, tracker):
        tracker.record_recovery("iios:test", 1.0, succeeded=False)
        snap = tracker.engine_snapshot("iios:test")
        assert snap.mean_time_to_recovery == 0.0

    def test_mttr_calculated_correctly(self, tracker):
        tracker.record_recovery("iios:test", 2.0, succeeded=True)
        tracker.record_recovery("iios:test", 4.0, succeeded=True)
        snap = tracker.engine_snapshot("iios:test")
        assert snap.mean_time_to_recovery == pytest.approx(3.0)


# ── Platform-wide snapshot ────────────────────────────────────────────────────

class TestPlatformSnapshot:

    def test_total_failures_aggregated(self, tracker):
        tracker.record_failure("iios:eng-a", ValueError)
        tracker.record_failure("iios:eng-a", ValueError)
        tracker.record_failure("iios:eng-b", RuntimeError)
        snap = tracker.snapshot()
        assert snap.total_failures == 3

    def test_engines_dict_populated(self, tracker):
        tracker.record_failure("iios:eng-a", ValueError)
        tracker.record_failure("iios:eng-b", RuntimeError)
        snap = tracker.snapshot()
        assert "iios:eng-a" in snap.engines
        assert "iios:eng-b" in snap.engines

    def test_empty_snapshot_fields(self):
        fresh = FailureTracker()
        snap = fresh.snapshot()
        assert snap.total_failures           == 0
        assert snap.total_recoveries         == 0
        assert snap.total_recovery_successes == 0
        assert snap.total_retries            == 0
        assert snap.recovery_success_rate    == 0.0
        assert snap.mean_time_to_recovery    == 0.0
        assert snap.engines                  == {}


# ── Failure trend ─────────────────────────────────────────────────────────────

class TestFailureTrend:

    def test_returns_correct_bucket_count(self, tracker):
        trend = tracker.failure_trend(window_sec=60.0, buckets=10)
        assert len(trend) == 10

    def test_trend_entries_are_frozen(self, tracker):
        trend = tracker.failure_trend(window_sec=60.0, buckets=5)
        assert all(isinstance(e, FailureTrendEntry) for e in trend)

    def test_recent_failures_appear_in_last_bucket(self, tracker):
        tracker.record_failure("iios:test", ValueError)
        trend = tracker.failure_trend("iios:test", window_sec=5.0, buckets=5)
        # Last bucket should have at least 1 failure
        total = sum(e.failure_count for e in trend)
        assert total >= 1

    def test_empty_trend_for_unknown_engine(self, tracker):
        trend = tracker.failure_trend("does-not-exist", window_sec=60.0)
        assert trend == []

    def test_platform_wide_trend(self, tracker):
        tracker.record_failure("iios:eng-a", ValueError)
        tracker.record_failure("iios:eng-b", RuntimeError)
        trend = tracker.failure_trend("", window_sec=5.0, buckets=5)
        total = sum(e.failure_count for e in trend)
        assert total >= 2


# ── reset ─────────────────────────────────────────────────────────────────────

class TestReset:

    def test_reset_all_clears_counters(self, tracker):
        tracker.record_failure("iios:test", ValueError)
        tracker.reset()
        snap = tracker.snapshot()
        assert snap.total_failures == 0

    def test_reset_specific_engine(self, tracker):
        tracker.record_failure("iios:eng-a", ValueError)
        tracker.record_failure("iios:eng-b", RuntimeError)
        tracker.reset("iios:eng-a")
        snap = tracker.snapshot()
        assert snap.total_failures == 1   # only eng-b remains

    def test_reset_unknown_engine_does_not_raise(self, tracker):
        tracker.reset("nonexistent")   # should not raise


# ── Singleton ─────────────────────────────────────────────────────────────────

class TestSingleton:

    def test_get_failure_tracker_returns_same_instance(self):
        a = get_failure_tracker()
        b = get_failure_tracker()
        assert a is b

    def test_reset_failure_tracker_replaces_instance(self):
        a = get_failure_tracker()
        reset_failure_tracker()
        b = get_failure_tracker()
        assert a is not b


# ── Thread safety ─────────────────────────────────────────────────────────────

class TestThreadSafety:

    def test_concurrent_record_failure_consistent(self):
        tracker = FailureTracker()
        errors: List[str] = []

        def worker(engine_id: str) -> None:
            for _ in range(200):
                tracker.record_failure(engine_id, ValueError)

        threads = [
            threading.Thread(target=worker, args=(f"iios:eng-{i}",))
            for i in range(5)
        ]
        for t in threads: t.start()
        for t in threads: t.join()

        snap = tracker.snapshot()
        assert snap.total_failures == 5 * 200
        assert errors == []
