"""Tests for iios.common.async_exec.async_executor"""
import asyncio
import time
import threading
from iios.common.async_exec.async_executor import AsyncExecutor, ExecutorConfig
from iios.common.async_exec.execution_classifier import WorkloadType


# ── ExecutorConfig ────────────────────────────────────────────────────────────

class TestExecutorConfig:

    def test_defaults(self):
        cfg = ExecutorConfig()
        assert cfg.max_threads == 16
        assert cfg.max_process_workers is None
        assert cfg.thread_name_prefix == "iios-worker"

    def test_custom_values(self):
        cfg = ExecutorConfig(max_threads=4, thread_name_prefix="test")
        assert cfg.max_threads == 4
        assert cfg.thread_name_prefix == "test"

    def test_frozen(self):
        cfg = ExecutorConfig()
        try:
            cfg.max_threads = 2  # type: ignore[misc]
            assert False
        except (AttributeError, TypeError):
            pass


# ── AsyncExecutor ─────────────────────────────────────────────────────────────

class TestAsyncExecutor:

    def setup_method(self):
        self.executor = AsyncExecutor(ExecutorConfig(max_threads=4))

    def teardown_method(self):
        self.executor.shutdown(wait=False, cancel_futures=True)

    # ── run_in_thread ────────────────────────────────────────────────────────

    def test_run_in_thread_returns_value(self):
        def add(a, b):
            return a + b
        result = asyncio.run(self.executor.run_in_thread(add, 3, 4))
        assert result == 7

    def test_run_in_thread_runs_in_different_thread(self):
        main_tid = threading.current_thread().ident
        captured = []

        def record_tid():
            captured.append(threading.current_thread().ident)

        asyncio.run(self.executor.run_in_thread(record_tid))
        assert len(captured) == 1
        # Thread pool runs in worker thread, NOT main thread
        assert captured[0] != main_tid

    def test_run_in_thread_with_kwargs(self):
        def greet(name, greeting="Hello"):
            return f"{greeting}, {name}!"

        result = asyncio.run(self.executor.run_in_thread(greet, "World", greeting="Hi"))
        assert result == "Hi, World!"

    def test_run_in_thread_propagates_exception(self):
        def boom():
            raise ValueError("thread error")

        try:
            asyncio.run(self.executor.run_in_thread(boom))
            assert False
        except ValueError as exc:
            assert "thread error" in str(exc)

    def test_run_in_thread_concurrent_tasks(self):
        results = []

        async def run_all():
            coros = [self.executor.run_in_thread(lambda i=i: i * 2, i) for i in range(8)]
            return await asyncio.gather(*coros)

        results = asyncio.run(run_all())
        assert sorted(results) == [0, 2, 4, 6, 8, 10, 12, 14]

    # ── run_auto ─────────────────────────────────────────────────────────────

    def test_run_auto_native_async(self):
        async def native():
            return "native"

        result = asyncio.run(self.executor.run_auto(native))
        assert result == "native"

    def test_run_auto_io_bound_uses_thread(self):
        def fetch_something():
            return "fetched"

        result = asyncio.run(
            self.executor.run_auto(
                fetch_something, workload_type=WorkloadType.IO_BOUND
            )
        )
        assert result == "fetched"

    def test_run_auto_explicit_workload_override(self):
        def sync_fn():
            return 42

        result = asyncio.run(
            self.executor.run_auto(sync_fn, workload_type=WorkloadType.IO_BOUND)
        )
        assert result == 42

    def test_run_auto_auto_classify(self):
        def fetch_quotes():
            return [1, 2, 3]

        result = asyncio.run(self.executor.run_auto(fetch_quotes))
        assert result == [1, 2, 3]

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def test_thread_pool_accessible(self):
        assert self.executor.thread_pool is not None

    def test_process_pool_none_before_first_use(self):
        fresh = AsyncExecutor(ExecutorConfig(max_threads=2))
        assert fresh.process_pool is None
        fresh.shutdown(wait=False)

    def test_shutdown_is_safe_to_call_multiple_times(self):
        ex = AsyncExecutor(ExecutorConfig(max_threads=2))
        ex.shutdown(wait=False, cancel_futures=True)
        ex.shutdown(wait=False, cancel_futures=True)  # should not raise

    def test_run_in_thread_blocking_io_simulation(self):
        def blocking_read():
            time.sleep(0.02)   # simulate short I/O wait
            return "data"

        result = asyncio.run(self.executor.run_in_thread(blocking_read))
        assert result == "data"
