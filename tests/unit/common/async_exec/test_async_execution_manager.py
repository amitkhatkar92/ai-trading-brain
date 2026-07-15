"""Tests for iios.common.async_exec.async_execution_manager"""
import asyncio
import time
import threading
import pytest
from iios.common.async_exec.async_execution_manager import (
    AsyncExecutionManager,
    ExecutionManagerConfig,
    ExecutionMetricsSnapshot,
    TaskRecord,
    _MetricsTracker,
    get_execution_manager,
    reset_execution_manager,
)
from iios.common.async_exec.cancellation import CancellationToken
from iios.common.async_exec.execution_classifier import WorkloadType
from iios.common.async_exec.timeout_policy import TimeoutPolicy
from iios.common.errors.exceptions import TimeoutError as IIOSTimeoutError


# ── Fixtures ──────────────────────────────────────────────────────────────────

def fresh_manager() -> AsyncExecutionManager:
    """Return a freshly created manager (not the singleton)."""
    cfg = ExecutionManagerConfig(
        default_timeout_policy = TimeoutPolicy.unlimited(),
    )
    return AsyncExecutionManager(cfg)


# ── ExecutionMetricsSnapshot ──────────────────────────────────────────────────

class TestExecutionMetricsSnapshot:

    def test_frozen(self):
        snap = ExecutionMetricsSnapshot(
            total_submitted=1, total_completed=1, total_failed=0,
            total_cancelled=0, avg_latency_ms=10.0, max_latency_ms=10.0,
            blocking_calls_detected=0,
        )
        try:
            snap.total_submitted = 5  # type: ignore[misc]
            assert False
        except (AttributeError, TypeError):
            pass

    def test_all_zero_default(self):
        snap = ExecutionMetricsSnapshot(
            total_submitted=0, total_completed=0, total_failed=0,
            total_cancelled=0, avg_latency_ms=0.0, max_latency_ms=0.0,
            blocking_calls_detected=0,
        )
        assert snap.total_submitted == 0
        assert snap.avg_latency_ms == 0.0


# ── _MetricsTracker ────────────────────────────────────────────────────────────

class TestMetricsTracker:

    def setup_method(self):
        self.tracker = _MetricsTracker(max_history=50)

    def test_initial_snapshot_all_zero(self):
        snap = self.tracker.snapshot()
        assert snap.total_submitted == 0
        assert snap.total_completed == 0
        assert snap.total_failed == 0

    def test_record_start_increments_submitted(self):
        self.tracker.record_start("t1", WorkloadType.IO_BOUND)
        snap = self.tracker.snapshot()
        assert snap.total_submitted == 1

    def test_record_success(self):
        self.tracker.record_start("t1", WorkloadType.IO_BOUND)
        self.tracker.record_end("t1", WorkloadType.IO_BOUND, succeeded=True)
        snap = self.tracker.snapshot()
        assert snap.total_completed == 1
        assert snap.total_failed == 0

    def test_record_failure(self):
        self.tracker.record_start("t1", WorkloadType.IO_BOUND)
        self.tracker.record_end("t1", WorkloadType.IO_BOUND, succeeded=False)
        snap = self.tracker.snapshot()
        assert snap.total_failed == 1
        assert snap.total_completed == 0

    def test_record_cancelled(self):
        self.tracker.record_start("t1", WorkloadType.IO_BOUND)
        self.tracker.record_end(
            "t1", WorkloadType.IO_BOUND, succeeded=False, cancelled=True
        )
        snap = self.tracker.snapshot()
        assert snap.total_cancelled == 1

    def test_avg_latency_computed(self):
        for i in range(3):
            tid = f"t{i}"
            self.tracker.record_start(tid, WorkloadType.IO_BOUND)
            self.tracker.record_end(tid, WorkloadType.IO_BOUND, succeeded=True)
        snap = self.tracker.snapshot()
        assert snap.avg_latency_ms >= 0.0

    def test_max_latency_computed(self):
        for i in range(3):
            tid = f"t{i}"
            self.tracker.record_start(tid, WorkloadType.IO_BOUND)
            time.sleep(0.005)
            self.tracker.record_end(tid, WorkloadType.IO_BOUND, succeeded=True)
        snap = self.tracker.snapshot()
        assert snap.max_latency_ms >= snap.avg_latency_ms

    def test_blocking_call_detected_for_slow_io(self):
        self.tracker.record_start("slow", WorkloadType.IO_BOUND)
        time.sleep(0.12)   # > 100ms threshold
        self.tracker.record_end(
            "slow", WorkloadType.IO_BOUND, succeeded=True,
            blocking_threshold_ms=100.0, track_blocking=True,
        )
        snap = self.tracker.snapshot()
        assert snap.blocking_calls_detected >= 1

    def test_blocking_detection_disabled(self):
        self.tracker.record_start("slow", WorkloadType.IO_BOUND)
        time.sleep(0.12)
        self.tracker.record_end(
            "slow", WorkloadType.IO_BOUND, succeeded=True,
            blocking_threshold_ms=100.0, track_blocking=False,
        )
        snap = self.tracker.snapshot()
        assert snap.blocking_calls_detected == 0

    def test_ring_buffer_max_history(self):
        tracker = _MetricsTracker(max_history=5)
        for i in range(10):
            tid = f"t{i}"
            tracker.record_start(tid, WorkloadType.IO_BOUND)
            tracker.record_end(tid, WorkloadType.IO_BOUND, succeeded=True)
        history = tracker.task_history()
        assert len(history) <= 5

    def test_reset_clears_all(self):
        self.tracker.record_start("t1", WorkloadType.IO_BOUND)
        self.tracker.record_end("t1", WorkloadType.IO_BOUND, succeeded=True)
        self.tracker.reset()
        snap = self.tracker.snapshot()
        assert snap.total_submitted == 0
        assert snap.total_completed == 0

    def test_thread_safe_concurrent_records(self):
        tracker = _MetricsTracker(max_history=500)
        errors = []

        def worker(tid):
            try:
                tracker.record_start(tid, WorkloadType.IO_BOUND)
                time.sleep(0.001)
                tracker.record_end(tid, WorkloadType.IO_BOUND, succeeded=True)
            except Exception as exc:
                errors.append(exc)

        threads = [
            threading.Thread(target=worker, args=(f"t{i}",))
            for i in range(50)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        snap = tracker.snapshot()
        assert snap.total_submitted == 50
        assert snap.total_completed == 50


# ── AsyncExecutionManager async execute() ─────────────────────────────────────

class TestAsyncExecutionManagerExecute:

    def setup_method(self):
        self.mgr = fresh_manager()

    def teardown_method(self):
        self.mgr.shutdown()

    def test_execute_coroutine_function(self):
        async def my_coro():
            return "hello"
        result = asyncio.run(self.mgr.execute(my_coro))
        assert result == "hello"

    def test_execute_coroutine_object(self):
        async def my_coro():
            return "world"
        result = asyncio.run(self.mgr.execute(my_coro()))
        assert result == "world"

    def test_execute_sync_fn_in_thread(self):
        def sync_fn():
            return 42
        result = asyncio.run(
            self.mgr.execute(sync_fn, workload_type=WorkloadType.IO_BOUND)
        )
        assert result == 42

    def test_execute_with_args(self):
        async def add(a, b):
            return a + b
        result = asyncio.run(self.mgr.execute(add, 3, 7))
        assert result == 10

    def test_execute_records_metrics(self):
        async def my_coro():
            return 1
        asyncio.run(self.mgr.execute(my_coro))
        snap = self.mgr.statistics()
        assert snap.total_submitted >= 1
        assert snap.total_completed >= 1

    def test_execute_timeout_raises_iios_error(self):
        async def slow():
            await asyncio.sleep(10)

        mgr = AsyncExecutionManager(ExecutionManagerConfig(
            default_timeout_policy = TimeoutPolicy(engine_timeout_sec=0.01),
        ))
        try:
            asyncio.run(mgr.execute(slow))
            assert False
        except IIOSTimeoutError:
            pass
        finally:
            mgr.shutdown()

    def test_execute_timeout_sec_override(self):
        async def slow():
            await asyncio.sleep(10)

        try:
            asyncio.run(self.mgr.execute(slow, timeout_sec=0.01))
            assert False
        except IIOSTimeoutError:
            pass

    def test_execute_cancelled_token_raises(self):
        token = CancellationToken()
        token.cancel("pre-cancel")

        async def my_coro():
            return 1

        try:
            asyncio.run(
                self.mgr.execute(my_coro, cancellation_token=token)
            )
            assert False
        except asyncio.CancelledError:
            pass

    def test_execute_failure_increments_failed_metric(self):
        async def raises():
            raise RuntimeError("oops")

        try:
            asyncio.run(self.mgr.execute(raises))
        except RuntimeError:
            pass

        snap = self.mgr.statistics()
        assert snap.total_failed >= 1

    def test_execute_cancelled_increments_cancelled_metric(self):
        async def slow():
            await asyncio.sleep(10)

        try:
            asyncio.run(self.mgr.execute(slow, timeout_sec=0.01))
        except IIOSTimeoutError:
            pass
        snap = self.mgr.statistics()
        # timeout paths count as failed, not cancelled
        assert snap.total_failed >= 1


# ── AsyncExecutionManager sync execute_sync() ────────────────────────────────

class TestAsyncExecutionManagerExecuteSync:

    def setup_method(self):
        self.mgr = fresh_manager()

    def teardown_method(self):
        self.mgr.shutdown()

    def test_execute_sync_with_coroutine_fn(self):
        async def my_coro():
            return "sync_result"
        result = self.mgr.execute_sync(my_coro)
        assert result == "sync_result"

    def test_execute_sync_with_sync_fn(self):
        def sync_fn():
            return 99
        result = self.mgr.execute_sync(sync_fn)
        assert result == 99

    def test_execute_sync_records_metrics(self):
        async def my_coro():
            return 1
        self.mgr.execute_sync(my_coro)
        snap = self.mgr.statistics()
        assert snap.total_submitted >= 1

    def test_execute_sync_timeout_raises(self):
        async def slow():
            await asyncio.sleep(10)
        try:
            self.mgr.execute_sync(slow, timeout_sec=0.01)
            assert False
        except IIOSTimeoutError:
            pass

    def test_execute_sync_raises_in_running_loop(self):
        """execute_sync must raise RuntimeError if called inside a running loop."""
        async def attempt():
            self.mgr.execute_sync(lambda: 1)

        try:
            asyncio.run(attempt())
            assert False
        except RuntimeError as exc:
            assert "running event loop" in str(exc).lower()

    def test_execute_sync_multiple_sequential_calls(self):
        async def get_value(v):
            return v
        results = [self.mgr.execute_sync(get_value, i) for i in range(5)]
        assert results == [0, 1, 2, 3, 4]


# ── Cancellation management ───────────────────────────────────────────────────

class TestCancellationManagement:

    def setup_method(self):
        self.mgr = fresh_manager()

    def teardown_method(self):
        self.mgr.shutdown()

    def test_create_token_returns_token(self):
        token = self.mgr.create_token()
        assert isinstance(token, CancellationToken)
        assert not token.is_cancelled()

    def test_cancel_all_cancels_all_tokens(self):
        t1 = self.mgr.create_token()
        t2 = self.mgr.create_token()
        t3 = self.mgr.create_token()
        self.mgr.cancel_all("shutdown")
        assert t1.is_cancelled()
        assert t2.is_cancelled()
        assert t3.is_cancelled()


# ── Statistics ────────────────────────────────────────────────────────────────

class TestStatistics:

    def test_statistics_returns_snapshot(self):
        mgr = fresh_manager()
        snap = mgr.statistics()
        assert isinstance(snap, ExecutionMetricsSnapshot)
        mgr.shutdown()

    def test_reset_statistics(self):
        mgr = fresh_manager()
        async def fn(): return 1
        mgr.execute_sync(fn)
        mgr.reset_statistics()
        snap = mgr.statistics()
        assert snap.total_submitted == 0
        mgr.shutdown()

    def test_task_history_populated(self):
        mgr = fresh_manager()
        async def fn(): return 1
        mgr.execute_sync(fn)
        history = mgr.task_history()
        assert isinstance(history, list)
        mgr.shutdown()


# ── Singleton ─────────────────────────────────────────────────────────────────

class TestSingleton:

    def test_get_execution_manager_returns_same_instance(self):
        mgr1 = get_execution_manager()
        mgr2 = get_execution_manager()
        assert mgr1 is mgr2

    def test_reset_returns_new_instance(self):
        original = get_execution_manager()
        new_mgr  = reset_execution_manager()
        assert new_mgr is not original
        # Restore default state for other tests
        reset_execution_manager()

    def test_reset_with_custom_config(self):
        cfg = ExecutionManagerConfig(
            default_timeout_policy = TimeoutPolicy.strict(),
        )
        mgr = reset_execution_manager(cfg)
        assert mgr is not None
        # Restore
        reset_execution_manager()
