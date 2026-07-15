"""iios/common/async_exec/async_execution_manager.py
Central execution manager for the IIOS async execution framework.

This is the primary entry-point for the entire platform.  Every engine
(C1–C10) should use this manager rather than creating raw executors.

Key capabilities:
  • Thread-pool execution for IO-bound sync callables (never blocks the loop)
  • Auto-classification of callables via ExecutionClassifier
  • Timeout enforcement (via TimeoutPolicy)
  • Cancellation support (via CancellationToken)
  • Task registry with unique task IDs
  • Thread-safe performance metrics (Task 8)
  • Sync API for engines that cannot be async (most current IIOS engines)
  • Singleton with module-level get/reset helpers

Usage (from sync code — most current IIOS engines)::

    from iios.common.async_exec.async_execution_manager import get_execution_manager

    mgr = get_execution_manager()
    result = mgr.execute_sync(blocking_feed_call, symbol, timeout_sec=10.0)

Usage (from async code — native async contexts)::

    mgr = get_execution_manager()
    result = await mgr.execute(my_coroutine_or_fn, timeout_sec=30.0)

Metrics::

    snap = mgr.statistics()
    print(f"tasks completed={snap.total_completed}  avg_latency={snap.avg_latency_ms:.1f}ms")
"""
from __future__ import annotations

import asyncio
import inspect
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Deque, Dict, List, Optional, TypeVar

from iios.common.async_exec.async_executor import AsyncExecutor, ExecutorConfig
from iios.common.async_exec.cancellation import CancellationToken
from iios.common.async_exec.execution_classifier import (
    ExecutionClassifier,
    WorkloadType,
)
from iios.common.async_exec.timeout_policy import TimeoutPolicy, apply_timeout
from iios.common.errors.exceptions import TimeoutError as IIOSTimeoutError


T = TypeVar("T")


# ── Config ────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ExecutionManagerConfig:
    """
    Immutable configuration for ``AsyncExecutionManager``.

    Attributes
    ----------
    executor_config:
        Thread/process pool sizes.
    default_timeout_policy:
        Timeout limits used when callers do not supply one.
    max_task_history:
        Maximum entries kept in the completed-task ring buffer.
        Older entries are dropped automatically.
    track_blocking_detection:
        When True, record calls that appear to block the event loop
        (latency > blocking_threshold_ms).
    blocking_detection_threshold_ms:
        Threshold used to flag a task as a blocking-call candidate.
    """
    executor_config:                 ExecutorConfig  = field(
        default_factory = lambda: ExecutorConfig(max_threads=16)
    )
    default_timeout_policy:          TimeoutPolicy   = field(
        default_factory = TimeoutPolicy
    )
    max_task_history:                int             = 200
    track_blocking_detection:        bool            = True
    blocking_detection_threshold_ms: float           = 100.0


# ── Metrics ───────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class TaskRecord:
    """A snapshot of one executed task."""
    task_id:       str
    workload_type: WorkloadType
    succeeded:     bool
    cancelled:     bool
    duration_ms:   float
    operation:     str


@dataclass(frozen=True)
class ExecutionMetricsSnapshot:
    """
    Immutable point-in-time snapshot of execution metrics.

    Used by monitoring, health checks, and the Streamlit dashboard.
    """
    total_submitted:          int
    total_completed:          int
    total_failed:             int
    total_cancelled:          int
    avg_latency_ms:           float
    max_latency_ms:           float
    blocking_calls_detected:  int


class _MetricsTracker:
    """
    Thread-safe metrics accumulator using a ring buffer for latency history.
    """

    def __init__(self, max_history: int = 200) -> None:
        self._lock                   = threading.RLock()
        self._total_submitted:   int = 0
        self._total_completed:   int = 0
        self._total_failed:      int = 0
        self._total_cancelled:   int = 0
        self._blocking_calls:    int = 0
        self._history:           Deque[TaskRecord] = deque(maxlen=max_history)
        self._active_tasks:      Dict[str, float] = {}   # task_id → start_time

    # ── Internal helpers ──────────────────────────────────────────────────────

    def record_start(self, task_id: str, workload_type: WorkloadType) -> None:
        with self._lock:
            self._total_submitted += 1
            self._active_tasks[task_id] = time.monotonic()

    def record_end(
        self,
        task_id:       str,
        workload_type: WorkloadType,
        *,
        succeeded:  bool,
        cancelled:  bool = False,
        operation:  str  = "",
        blocking_threshold_ms: float = 100.0,
        track_blocking: bool = True,
    ) -> None:
        with self._lock:
            start = self._active_tasks.pop(task_id, None)
            duration_ms = (time.monotonic() - start) * 1000.0 if start else 0.0

            if succeeded:
                self._total_completed += 1
            elif cancelled:
                self._total_cancelled += 1
            else:
                self._total_failed += 1

            if (
                track_blocking
                and workload_type == WorkloadType.IO_BOUND
                and duration_ms > blocking_threshold_ms
            ):
                self._blocking_calls += 1

            self._history.append(TaskRecord(
                task_id       = task_id,
                workload_type = workload_type,
                succeeded     = succeeded,
                cancelled     = cancelled,
                duration_ms   = duration_ms,
                operation     = operation,
            ))

    def snapshot(self) -> ExecutionMetricsSnapshot:
        with self._lock:
            latencies = [r.duration_ms for r in self._history]
            return ExecutionMetricsSnapshot(
                total_submitted         = self._total_submitted,
                total_completed         = self._total_completed,
                total_failed            = self._total_failed,
                total_cancelled         = self._total_cancelled,
                avg_latency_ms          = (
                    sum(latencies) / len(latencies) if latencies else 0.0
                ),
                max_latency_ms          = max(latencies, default=0.0),
                blocking_calls_detected = self._blocking_calls,
            )

    def reset(self) -> None:
        with self._lock:
            self._total_submitted   = 0
            self._total_completed   = 0
            self._total_failed      = 0
            self._total_cancelled   = 0
            self._blocking_calls    = 0
            self._history.clear()
            self._active_tasks.clear()

    def task_history(self) -> List[TaskRecord]:
        with self._lock:
            return list(self._history)


# ── AsyncExecutionManager ─────────────────────────────────────────────────────

class AsyncExecutionManager:
    """
    Central execution manager for the IIOS platform.

    ``execute()``       — async API for use within running event loops.
    ``execute_sync()``  — sync API for engines that cannot use async.

    Both APIs support:
      • Auto-classification of callables (NATIVE_ASYNC / IO_BOUND / CPU_BOUND)
      • Timeout enforcement via ``TimeoutPolicy``
      • Cancellation via ``CancellationToken``
      • Automatic metrics collection

    Singleton pattern:
      Use ``get_execution_manager()`` for the shared instance.
      Use ``reset_execution_manager()`` in tests to get a fresh instance.
    """

    def __init__(self, config: Optional[ExecutionManagerConfig] = None) -> None:
        self._config      = config or ExecutionManagerConfig()
        self._executor    = AsyncExecutor(self._config.executor_config)
        self._classifier  = ExecutionClassifier()
        self._metrics     = _MetricsTracker(
            max_history = self._config.max_task_history,
        )
        self._all_tokens:  List[CancellationToken] = []
        self._tokens_lock: threading.Lock          = threading.Lock()

    # ── Async API ─────────────────────────────────────────────────────────────

    async def execute(
        self,
        fn_or_coro:          Any,
        *args:               Any,
        timeout_policy:      Optional[TimeoutPolicy]       = None,
        timeout_sec:         Optional[float]               = None,
        cancellation_token:  Optional[CancellationToken]   = None,
        workload_type:       Optional[WorkloadType]        = None,
        operation:           str                           = "",
        engine_id:           str                           = "",
        **kwargs:            Any,
    ) -> Any:
        """
        Execute *fn_or_coro* asynchronously.

        Accepts:
          • An already-created coroutine (``async def fn()`` result)
          • A coroutine function (will be called with *args*/*kwargs*)
          • Any sync callable (auto-dispatched via executor)

        :param timeout_policy:     Override the manager's default timeout policy.
        :param timeout_sec:        Direct timeout — overrides ``timeout_policy.engine_timeout_sec``.
        :param cancellation_token: Check token before and after execution.
        :param workload_type:      Override auto-classification.
        :param operation:          Label for logs and metrics.
        :param engine_id:          Engine context for error messages.
        """
        # Resolve timeout
        effective_timeout = self._resolve_timeout(timeout_sec, timeout_policy)

        # Check cancellation before starting
        if cancellation_token is not None:
            cancellation_token.check()

        # Generate task ID for metrics
        task_id       = str(uuid.uuid4())
        resolved_type = workload_type or WorkloadType.IO_BOUND

        # If fn_or_coro is already a coroutine object, wrap and await it
        if asyncio.iscoroutine(fn_or_coro):
            resolved_type = WorkloadType.NATIVE_ASYNC
        elif inspect.iscoroutinefunction(fn_or_coro):
            resolved_type = WorkloadType.NATIVE_ASYNC
        elif workload_type is None:
            resolved_type = self._classifier.classify(fn_or_coro).workload_type

        self._metrics.record_start(task_id, resolved_type)
        succeeded = False
        cancelled = False
        try:
            # Build the awaitable
            if asyncio.iscoroutine(fn_or_coro):
                awaitable = fn_or_coro
            elif inspect.iscoroutinefunction(fn_or_coro):
                awaitable = fn_or_coro(*args, **kwargs)
            else:
                awaitable = self._executor.run_auto(
                    fn_or_coro,
                    *args,
                    workload_type = resolved_type,
                    **kwargs,
                )

            # Apply timeout
            result = await apply_timeout(
                awaitable,
                effective_timeout,
                operation = operation or getattr(fn_or_coro, "__name__", ""),
                engine_id = engine_id,
            )
            succeeded = True
            return result

        except asyncio.CancelledError:
            cancelled = True
            raise
        finally:
            self._metrics.record_end(
                task_id,
                resolved_type,
                succeeded              = succeeded,
                cancelled              = cancelled,
                operation              = operation,
                blocking_threshold_ms  = self._config.blocking_detection_threshold_ms,
                track_blocking         = self._config.track_blocking_detection,
            )

    # ── Sync API ──────────────────────────────────────────────────────────────

    def execute_sync(
        self,
        fn_or_coro:    Any,
        *args:         Any,
        timeout_sec:   Optional[float] = None,
        operation:     str             = "",
        engine_id:     str             = "",
        **kwargs:      Any,
    ) -> Any:
        """
        Execute *fn_or_coro* from synchronous code.

        Creates (or reuses) an event loop to run the coroutine.
        This is the method current IIOS engines should call when they need
        to delegate blocking IO work to the thread pool.

        WARNING: Do NOT call from within an already-running event loop.
                 Use ``execute()`` instead.

        :raises RuntimeError: If called from within a running event loop.
        """
        try:
            loop = asyncio.get_running_loop()
            # Already inside an event loop — cannot use asyncio.run()
            raise RuntimeError(
                "execute_sync() was called from within a running event loop. "
                "Use 'await manager.execute(...)' instead."
            ) from None
        except RuntimeError as err:
            if "no running event loop" not in str(err).lower() and "get_running_loop" not in str(err).lower():
                raise

        coro = self.execute(
            fn_or_coro,
            *args,
            timeout_sec = timeout_sec,
            operation   = operation,
            engine_id   = engine_id,
            **kwargs,
        )
        return asyncio.run(coro)

    # ── Cancellation ─────────────────────────────────────────────────────────

    def create_token(self) -> CancellationToken:
        """Create and register a new CancellationToken."""
        token = CancellationToken()
        with self._tokens_lock:
            self._all_tokens.append(token)
        return token

    def cancel_all(self, reason: str = "") -> None:
        """Cancel all registered tokens."""
        with self._tokens_lock:
            tokens = list(self._all_tokens)
        for token in tokens:
            token.cancel(reason)

    # ── Metrics ───────────────────────────────────────────────────────────────

    def statistics(self) -> ExecutionMetricsSnapshot:
        """Return a point-in-time snapshot of execution metrics."""
        return self._metrics.snapshot()

    def task_history(self) -> List[TaskRecord]:
        """Return the recent task history (up to ``max_task_history`` entries)."""
        return self._metrics.task_history()

    def reset_statistics(self) -> None:
        """Reset all counters (use in tests; not suitable for production)."""
        self._metrics.reset()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def shutdown(self) -> None:
        """Shut down thread and process pools."""
        self._executor.shutdown(wait=True)

    # ── Internal ─────────────────────────────────────────────────────────────

    def _resolve_timeout(
        self,
        explicit_sec:  Optional[float],
        policy:        Optional[TimeoutPolicy],
    ) -> Optional[float]:
        if explicit_sec is not None:
            return explicit_sec
        if policy is not None:
            return policy.engine_timeout_sec
        return self._config.default_timeout_policy.engine_timeout_sec


# ── Singleton ─────────────────────────────────────────────────────────────────

_manager_lock: threading.Lock             = threading.Lock()
_manager:      Optional[AsyncExecutionManager] = None


def get_execution_manager() -> AsyncExecutionManager:
    """
    Return the module-level singleton ``AsyncExecutionManager``.

    Creates the instance on first call (double-checked locking).
    """
    global _manager
    if _manager is None:
        with _manager_lock:
            if _manager is None:
                _manager = AsyncExecutionManager()
    return _manager


def reset_execution_manager(
    config: Optional[ExecutionManagerConfig] = None,
) -> AsyncExecutionManager:
    """
    Replace the singleton with a fresh instance.

    Use in tests and at application startup to apply custom config.
    Always shuts down the previous instance's pools before replacing.
    """
    global _manager
    with _manager_lock:
        if _manager is not None:
            try:
                _manager.shutdown()
            except Exception:
                pass
        _manager = AsyncExecutionManager(config)
        return _manager
