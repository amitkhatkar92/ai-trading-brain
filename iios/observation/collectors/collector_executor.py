"""
iios/observation/collectors/collector_executor.py
=================================================
CollectorExecutor — parallel and sequential collector execution engine.

Wraps a thread-pool so multiple collectors can run concurrently.
Records run metrics for every execution.
"""
from __future__ import annotations

import concurrent.futures
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from ..models.observation  import Observation
from .base_collector       import BaseCollector
from .collector_constants  import MAX_PARALLEL_COLLECTORS
from .collector_metrics    import CollectorMetrics, RunRecord, get_collector_metrics

__all__ = [
    "ExecutionResult",
    "CollectorExecutor",
    "get_collector_executor",
    "reset_collector_executor",
]

_LOG  = logging.getLogger("iios.collector.executor")
_lock = threading.Lock()
_exec: Optional["CollectorExecutor"] = None


@dataclass
class ExecutionResult:
    """Result of a single collector run."""
    collector_name: str
    observations:   list[Observation] = field(default_factory=list)
    error:          Optional[Exception] = None
    duration_ms:    float = 0.0
    success:        bool  = True

    @property
    def count(self) -> int:
        return len(self.observations)


class CollectorExecutor:
    """
    Runs collectors in a thread pool.

    * ``run_one(c)``          — single collector, blocking
    * ``run_many(cs)``        — parallel, waits for all
    * ``run_all(registry)``   — all collectors in registry
    * ``run_by_category()``   — filtered by category
    """

    def __init__(self, max_workers: int = MAX_PARALLEL_COLLECTORS) -> None:
        self._max_workers = max_workers
        self._metrics     = get_collector_metrics()

    def run_one(self, collector: BaseCollector) -> ExecutionResult:
        """Execute one collector and return the result."""
        run_id = f"{collector.name}:{time.time():.3f}"
        record = RunRecord(
            run_id     = run_id,
            collector  = collector.name,
            started_at = time.time(),
        )
        try:
            observations    = collector.run()
            record.items    = len(observations)
            record.success  = True
            return ExecutionResult(
                collector_name = collector.name,
                observations   = observations,
                duration_ms    = (time.time() - record.started_at) * 1_000.0,
                success        = True,
            )
        except Exception as exc:
            record.errors += 1
            _LOG.warning("Collector '%s' failed: %s", collector.name, exc)
            return ExecutionResult(
                collector_name = collector.name,
                error          = exc,
                duration_ms    = (time.time() - record.started_at) * 1_000.0,
                success        = False,
            )
        finally:
            record.ended_at = time.time()
            self._metrics.record_run(record)

    def run_many(
        self,
        collectors: list[BaseCollector],
        timeout_s:  Optional[float] = None,
    ) -> list[ExecutionResult]:
        """Run collectors in parallel. Results maintain input order."""
        if not collectors:
            return []
        workers  = min(len(collectors), self._max_workers)
        results: list[Optional[ExecutionResult]] = [None] * len(collectors)

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            future_to_idx = {
                pool.submit(self.run_one, c): i
                for i, c in enumerate(collectors)
            }
            done, _ = concurrent.futures.wait(
                future_to_idx, timeout=timeout_s
            )
            for future in done:
                idx = future_to_idx[future]
                try:
                    results[idx] = future.result()
                except Exception as exc:
                    results[idx] = ExecutionResult(
                        collector_name = collectors[idx].name,
                        error          = exc,
                        success        = False,
                    )
            # Fill any timed-out futures with error results
            for future, idx in future_to_idx.items():
                if results[idx] is None:
                    results[idx] = ExecutionResult(
                        collector_name = collectors[idx].name,
                        error          = TimeoutError(
                            f"Collector '{collectors[idx].name}' timed out"
                        ),
                        success = False,
                    )
        return results  # type: ignore[return-value]

    def run_all(
        self,
        registry: Any,
        timeout_s: Optional[float] = None,
    ) -> list[ExecutionResult]:
        """Run every collector in *registry* in parallel."""
        return self.run_many(registry.all(), timeout_s=timeout_s)

    def run_by_category(
        self,
        registry: Any,
        category: Any,
        timeout_s: Optional[float] = None,
    ) -> list[ExecutionResult]:
        """Run all collectors in *registry* with the given *category*."""
        return self.run_many(registry.by_category(category), timeout_s=timeout_s)

    def run_enabled(
        self,
        registry: Any,
        timeout_s: Optional[float] = None,
    ) -> list[ExecutionResult]:
        """Run only enabled collectors."""
        return self.run_many(registry.enabled(), timeout_s=timeout_s)


def get_collector_executor() -> CollectorExecutor:
    global _exec
    if _exec is None:
        with _lock:
            if _exec is None:
                _exec = CollectorExecutor()
    return _exec


def reset_collector_executor() -> None:
    global _exec
    with _lock:
        _exec = None
