"""iios/common/async_exec/async_executor.py
Low-level async executor for the IIOS async execution framework.

Wraps ThreadPoolExecutor and ProcessPoolExecutor so callers can run
synchronous callables without blocking the asyncio event loop.

Designed to be used via ``AsyncExecutionManager``, but can be used
directly for fine-grained control.

Usage::

    from iios.common.async_exec.async_executor import AsyncExecutor, ExecutorConfig

    executor = AsyncExecutor(ExecutorConfig(max_threads=8))

    # Run a blocking IO call in a thread pool (safe — never blocks loop)
    result = await executor.run_in_thread(blocking_http_call, url, headers=headers)

    # Run a CPU-bound function in a process pool (parallel computation)
    result = await executor.run_in_process(monte_carlo_simulation, 10_000)

    executor.shutdown()
"""
from __future__ import annotations

import asyncio
import functools
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, TypeVar

from iios.common.async_exec.execution_classifier import (
    ExecutionClassifier,
    WorkloadType,
)


T = TypeVar("T")


# ── ExecutorConfig ────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ExecutorConfig:
    """
    Immutable configuration for ``AsyncExecutor``.

    Attributes
    ----------
    max_threads:
        Maximum thread pool workers.
        Rule of thumb: ``2 × CPU_count`` for IO-bound work.
    max_process_workers:
        Maximum process pool workers.
        ``None`` → use ``os.cpu_count()`` (Python default).
        Process pool is only created when ``run_in_process()`` is first called.
    thread_name_prefix:
        Prefix for thread names, useful in logs and debuggers.
    """
    max_threads:         int           = 16
    max_process_workers: Optional[int] = None
    thread_name_prefix:  str           = "iios-worker"


# ── AsyncExecutor ─────────────────────────────────────────────────────────────

class AsyncExecutor:
    """
    Provides ``run_in_thread``, ``run_in_process``, and ``run_auto`` coroutines
    that delegate synchronous work to the appropriate executor without
    blocking the event loop.

    Thread pool is created eagerly on instantiation.
    Process pool is created lazily when ``run_in_process`` is first called.

    Thread safety:
        Pools are created with a threading.Lock during lazy init.
        After creation they are only read (concurrent access is safe).
    """

    def __init__(self, config: Optional[ExecutorConfig] = None) -> None:
        self._config      = config or ExecutorConfig()
        self._classifier  = ExecutionClassifier()
        self._thread_pool = ThreadPoolExecutor(
            max_workers        = self._config.max_threads,
            thread_name_prefix = self._config.thread_name_prefix,
        )
        self._process_pool: Optional[ProcessPoolExecutor] = None
        import threading
        self._pp_lock = threading.Lock()

    # ── Public coroutine API ──────────────────────────────────────────────────

    async def run_in_thread(
        self,
        fn:   Callable[..., T],
        /,
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """
        Run synchronous *fn* in the thread pool.

        Equivalent to ``loop.run_in_executor(self._thread_pool, fn, *args)``.
        Keyword arguments are wrapped in ``functools.partial``.

        :raises: Any exception raised by *fn* (propagated through the future).
        """
        loop = asyncio.get_running_loop()
        if kwargs:
            fn = functools.partial(fn, **kwargs)
        return await loop.run_in_executor(self._thread_pool, fn, *args)

    async def run_in_process(
        self,
        fn:   Callable[..., T],
        /,
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """
        Run CPU-bound *fn* in the process pool.

        The process pool is created lazily on first call.
        *fn* must be picklable (top-level functions, not lambdas or closures).

        :raises: Any exception raised by *fn*.
        """
        pool = self._get_or_create_process_pool()
        loop = asyncio.get_running_loop()
        if kwargs:
            fn = functools.partial(fn, **kwargs)
        return await loop.run_in_executor(pool, fn, *args)

    async def run_auto(
        self,
        fn:    Callable[..., T],
        /,
        *args: Any,
        workload_type: Optional[WorkloadType] = None,
        **kwargs: Any,
    ) -> T:
        """
        Classify *fn* and dispatch to the appropriate executor.

        If *workload_type* is provided it overrides the classifier.

        Dispatch logic:
          • NATIVE_ASYNC → call directly (``await fn(*args, **kwargs)``)
          • CPU_BOUND    → ``run_in_process``
          • All others   → ``run_in_thread``

        :param fn:           Callable to execute.
        :param workload_type: Override the automatic classification.
        """
        if workload_type is None:
            result = self._classifier.classify(fn)
            workload_type = result.workload_type

        if workload_type == WorkloadType.NATIVE_ASYNC:
            return await fn(*args, **kwargs)
        if workload_type == WorkloadType.CPU_BOUND:
            return await self.run_in_process(fn, *args, **kwargs)
        return await self.run_in_thread(fn, *args, **kwargs)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def shutdown(self, wait: bool = True, cancel_futures: bool = False) -> None:
        """
        Shut down both executors.

        :param wait:            Wait for pending futures to complete.
        :param cancel_futures:  Cancel pending futures (Python 3.9+).
        """
        self._thread_pool.shutdown(wait=wait, cancel_futures=cancel_futures)
        with self._pp_lock:
            if self._process_pool is not None:
                self._process_pool.shutdown(wait=wait, cancel_futures=cancel_futures)
                self._process_pool = None

    @property
    def thread_pool(self) -> ThreadPoolExecutor:
        return self._thread_pool

    @property
    def process_pool(self) -> Optional[ProcessPoolExecutor]:
        return self._process_pool

    # ── Internal ──────────────────────────────────────────────────────────────

    def _get_or_create_process_pool(self) -> ProcessPoolExecutor:
        with self._pp_lock:
            if self._process_pool is None:
                self._process_pool = ProcessPoolExecutor(
                    max_workers = self._config.max_process_workers,
                )
            return self._process_pool
