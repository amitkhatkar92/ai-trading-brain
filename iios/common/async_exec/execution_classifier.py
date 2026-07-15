"""iios/common/async_exec/execution_classifier.py
Workload classifier for the IIOS async execution framework.

Automatically determines how a callable should be executed:
  • NATIVE_ASYNC   — already a coroutine function → run directly
  • IO_BOUND       — blocks on I/O (network, disk, broker API) → thread pool
  • CPU_BOUND      — pure computation (scoring, Monte Carlo) → process pool or sync
  • MIXED          — combination of I/O and CPU work
  • SYNC_WRAPPER   — synchronous wrapper around async logic → unwrap or thread pool

Classification uses four mechanisms in priority order:
  1. Explicit annotation via ``@classify_as(WorkloadType.IO_BOUND)``
  2. ``asyncio.iscoroutinefunction()`` → NATIVE_ASYNC
  3. Name-based heuristics (e.g. ``fetch_``, ``get_``, ``load_`` → IO_BOUND)
  4. Default → IO_BOUND (safer: thread pool over blocking the event loop)

Usage::

    from iios.common.async_exec.execution_classifier import (
        ExecutionClassifier, WorkloadType
    )

    clf = ExecutionClassifier()
    result = clf.classify(my_function)
    print(result.workload_type)   # WorkloadType.IO_BOUND
    print(result.recommended_executor)  # "thread_pool"
"""
from __future__ import annotations

import functools
import inspect
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, FrozenSet, Mapping, Optional


# ── WorkloadType ──────────────────────────────────────────────────────────────

class WorkloadType(str, Enum):
    """
    Classifies the execution characteristics of a callable.

    NATIVE_ASYNC:
        A coroutine function — should be awaited directly.
    IO_BOUND:
        Blocks on I/O (network, disk, broker API, market data feed).
        Delegate to ThreadPoolExecutor so the event loop is never blocked.
    CPU_BOUND:
        Pure computation (scoring, risk calculation, Monte Carlo).
        Remains synchronous; delegated to ProcessPoolExecutor for parallelism
        or run inline when parallelism is not needed.
    MIXED:
        Combination of I/O and CPU work.
        Treated as IO_BOUND for executor selection.
    SYNC_WRAPPER:
        Synchronous wrapper around async logic.
        May be refactored to NATIVE_ASYNC or delegated to thread pool.
    """
    NATIVE_ASYNC = "native_async"
    IO_BOUND     = "io_bound"
    CPU_BOUND    = "cpu_bound"
    MIXED        = "mixed"
    SYNC_WRAPPER = "sync_wrapper"


# ── Classification result ─────────────────────────────────────────────────────

@dataclass(frozen=True)
class ClassificationResult:
    """
    Immutable result of classifying a single callable.

    Attributes
    ----------
    workload_type:
        The determined workload category.
    confidence:
        0.0–1.0 confidence in the classification.
        1.0 = explicit annotation; 0.5 = name heuristic; 0.4 = default.
    reason:
        Human-readable explanation of the classification decision.
    recommended_executor:
        One of: ``"native"``, ``"thread_pool"``, ``"process_pool"``, ``"inline"``.
    callable_name:
        The name of the classified callable.
    """
    workload_type:        WorkloadType
    confidence:           float
    reason:               str
    recommended_executor: str
    callable_name:        str = ""


# ── Annotation decorator ──────────────────────────────────────────────────────

_ANNOTATION_ATTR = "__iios_workload_type__"

def classify_as(workload_type: WorkloadType) -> Callable:
    """
    Decorator that explicitly marks a callable's workload type.

    This provides the highest-confidence classification (1.0) and overrides
    all heuristics.

    Usage::

        @classify_as(WorkloadType.CPU_BOUND)
        def compute_portfolio_risk(weights, returns): ...
    """
    def decorator(fn: Callable) -> Callable:
        setattr(fn, _ANNOTATION_ATTR, workload_type)
        return fn
    return decorator


# ── Name-based heuristics ─────────────────────────────────────────────────────

_IO_PREFIXES: FrozenSet[str] = frozenset({
    "fetch_", "get_", "load_", "download_", "upload_", "send_", "receive_",
    "read_", "write_", "query_", "request_", "call_", "connect_", "subscribe_",
    "publish_", "push_", "pull_", "stream_", "poll_",
})

_IO_SUFFIXES: FrozenSet[str] = frozenset({
    "_quotes", "_data", "_price", "_feed", "_api", "_request",
    "_response", "_connection", "_session", "_client",
})

_IO_SUBSTRINGS: FrozenSet[str] = frozenset({
    "http", "socket", "broker", "feed", "market", "database", "db",
    "redis", "kafka", "mqtt", "websocket", "rest", "grpc",
})

_CPU_PREFIXES: FrozenSet[str] = frozenset({
    "compute_", "calculate_", "score_", "rank_", "optimize_", "simulate_",
    "backtest_", "montecarlo_", "run_montecarlo", "train_", "fit_", "predict_",
    "aggregate_", "transform_", "process_",
})

_CPU_SUBSTRINGS: FrozenSet[str] = frozenset({
    "risk", "alpha", "sharpe", "sortino", "correlation", "covariance",
    "regression", "optimization", "simulation", "montecarlo", "drawdown",
    "volatility", "portfolio_weight",
})


def _classify_by_name(name: str) -> Optional[tuple[WorkloadType, float, str]]:
    """
    Return (WorkloadType, confidence, reason) based on naming convention,
    or None if no heuristic applies.
    """
    lower = name.lower()

    for prefix in _IO_PREFIXES:
        if lower.startswith(prefix):
            return (WorkloadType.IO_BOUND, 0.6,
                    f"Name starts with IO prefix '{prefix}'")

    for suffix in _IO_SUFFIXES:
        if lower.endswith(suffix):
            return (WorkloadType.IO_BOUND, 0.55,
                    f"Name ends with IO suffix '{suffix}'")

    for sub in _IO_SUBSTRINGS:
        if sub in lower:
            return (WorkloadType.IO_BOUND, 0.5,
                    f"Name contains IO keyword '{sub}'")

    for prefix in _CPU_PREFIXES:
        if lower.startswith(prefix):
            return (WorkloadType.CPU_BOUND, 0.6,
                    f"Name starts with CPU prefix '{prefix}'")

    for sub in _CPU_SUBSTRINGS:
        if sub in lower:
            return (WorkloadType.CPU_BOUND, 0.5,
                    f"Name contains CPU keyword '{sub}'")

    return None


# ── Executor mapping ──────────────────────────────────────────────────────────

_EXECUTOR_MAP: Mapping[WorkloadType, str] = {
    WorkloadType.NATIVE_ASYNC: "native",
    WorkloadType.IO_BOUND:     "thread_pool",
    WorkloadType.CPU_BOUND:    "process_pool",
    WorkloadType.MIXED:        "thread_pool",
    WorkloadType.SYNC_WRAPPER: "thread_pool",
}


# ── ExecutionClassifier ───────────────────────────────────────────────────────

class ExecutionClassifier:
    """
    Classifies callables to determine the optimal execution strategy.

    Classification priority:
    1. Explicit ``@classify_as(WorkloadType.X)`` annotation (confidence=1.0)
    2. ``asyncio.iscoroutinefunction()`` → NATIVE_ASYNC (confidence=1.0)
    3. Name-based heuristics (confidence=0.5–0.6)
    4. Default: IO_BOUND (confidence=0.4) — safe default for unknown callables
    """

    def classify(self, fn: Callable) -> ClassificationResult:
        """
        Classify *fn* and return a ``ClassificationResult``.

        :param fn: Any callable — coroutine function, regular function, lambda,
                   bound method, or partial.
        """
        name = self._get_name(fn)

        # 1. Explicit annotation
        explicit = getattr(fn, _ANNOTATION_ATTR, None)
        if explicit is not None:
            return ClassificationResult(
                workload_type        = explicit,
                confidence           = 1.0,
                reason               = f"Explicit @classify_as({explicit.value}) annotation",
                recommended_executor = _EXECUTOR_MAP[explicit],
                callable_name        = name,
            )

        # 2. Coroutine function
        if inspect.iscoroutinefunction(fn):
            return ClassificationResult(
                workload_type        = WorkloadType.NATIVE_ASYNC,
                confidence           = 1.0,
                reason               = "asyncio.iscoroutinefunction() is True",
                recommended_executor = "native",
                callable_name        = name,
            )

        # 3. Name heuristics
        heuristic = _classify_by_name(name)
        if heuristic is not None:
            wt, conf, reason = heuristic
            return ClassificationResult(
                workload_type        = wt,
                confidence           = conf,
                reason               = reason,
                recommended_executor = _EXECUTOR_MAP[wt],
                callable_name        = name,
            )

        # 4. Default: IO_BOUND (thread pool is safer than blocking the loop)
        return ClassificationResult(
            workload_type        = WorkloadType.IO_BOUND,
            confidence           = 0.4,
            reason               = "Default classification: IO_BOUND (safe default)",
            recommended_executor = "thread_pool",
            callable_name        = name,
        )

    def classify_method(
        self,
        instance: Any,
        method_name: str,
    ) -> ClassificationResult:
        """
        Classify a named method on *instance*.

        Convenience wrapper for classifying engine methods by name.
        """
        fn = getattr(type(instance), method_name, None) or getattr(instance, method_name)
        return self.classify(fn)

    # ── Internal ──────────────────────────────────────────────────────────────

    @staticmethod
    def _get_name(fn: Callable) -> str:
        """Extract a human-readable name from any callable type."""
        if hasattr(fn, "__name__"):
            return fn.__name__
        if hasattr(fn, "__func__"):
            return fn.__func__.__name__
        if isinstance(fn, functools.partial):
            return getattr(fn.func, "__name__", repr(fn))
        return repr(fn)


# ── Module-level convenience ──────────────────────────────────────────────────

_default_classifier = ExecutionClassifier()


def classify(fn: Callable) -> ClassificationResult:
    """Module-level shortcut for ``ExecutionClassifier().classify(fn)``."""
    return _default_classifier.classify(fn)
