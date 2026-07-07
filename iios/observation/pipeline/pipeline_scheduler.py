"""
iios/observation/pipeline/pipeline_scheduler.py
===============================================
Batch, priority-queue, and streaming schedulers.

``PipelineScheduler`` is the public entry point that delegates to the
appropriate internal scheduler based on configuration.
"""
from __future__ import annotations

import heapq
import logging
import queue
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Iterator, Optional

from ..models.observation    import Observation
from ..observation_constants import ObservationPriority
from .pipeline_constants     import (
    DEFAULT_BATCH_SIZE, DEFAULT_BATCH_TIMEOUT_S, PIPELINE_STANDARD,
    SchedulerType,
)
from .pipeline_executor      import PipelineExecutionResult
from .pipeline_manager       import PipelineManager, get_pipeline_manager

__all__ = [
    "ScheduledItem",
    "BatchScheduler",
    "PriorityScheduler",
    "PipelineScheduler",
    "get_pipeline_scheduler",
    "reset_pipeline_scheduler",
]

_LOG      = logging.getLogger("iios.observation.pipeline.scheduler")
_lock     = threading.Lock()
_scheduler: Optional["PipelineScheduler"] = None

_PRIORITY_ORDER: dict[ObservationPriority, int] = {
    ObservationPriority.CRITICAL: 0,
    ObservationPriority.HIGH:     1,
    ObservationPriority.MEDIUM:   2,
    ObservationPriority.LOW:      3,
    ObservationPriority.MINIMAL:  4,
}


@dataclass(order=True)
class ScheduledItem:
    """Priority-queue item wrapping an observation."""
    priority:  int
    seq:       int           = field(compare=True)
    obs:       Observation   = field(compare=False)
    pipeline:  str           = field(compare=False, default=PIPELINE_STANDARD)


class BatchScheduler:
    """
    Accumulates observations and processes them in batches.

    Call ``submit()`` to enqueue; call ``flush()`` to process immediately.
    The background flush loop runs when ``start()`` is called.
    """

    def __init__(
        self,
        manager:       Optional[PipelineManager] = None,
        batch_size:    int                       = DEFAULT_BATCH_SIZE,
        timeout_s:     float                     = DEFAULT_BATCH_TIMEOUT_S,
        pipeline_name: str                       = PIPELINE_STANDARD,
    ) -> None:
        self._manager       = manager or get_pipeline_manager()
        self._batch_size    = batch_size
        self._timeout_s     = timeout_s
        self._pipeline_name = pipeline_name
        self._pending:      list[Observation]    = []
        self._results:      list[PipelineExecutionResult] = []
        self._lock          = threading.RLock()
        self._running       = False
        self._thread:       Optional[threading.Thread] = None
        self._flush_event   = threading.Event()
        self._total_flushed = 0

    def submit(self, obs: Observation) -> None:
        with self._lock:
            self._pending.append(obs)
            if len(self._pending) >= self._batch_size:
                self._flush_event.set()

    def submit_many(self, observations: list[Observation]) -> None:
        for obs in observations:
            self.submit(obs)

    def flush(self) -> list[PipelineExecutionResult]:
        """Process all pending observations immediately; return results."""
        with self._lock:
            batch = list(self._pending)
            self._pending.clear()
        if not batch:
            return []
        results = self._manager.process_batch(batch, self._pipeline_name)
        with self._lock:
            self._results.extend(results)
            self._total_flushed += len(results)
        return results

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread  = threading.Thread(
            target    = self._loop,
            daemon    = True,
            name      = "batch-scheduler",
        )
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        self._flush_event.set()
        if self._thread:
            self._thread.join(timeout=5.0)

    def _loop(self) -> None:
        while self._running:
            triggered = self._flush_event.wait(timeout=self._timeout_s)
            self._flush_event.clear()
            try:
                self.flush()
            except Exception as exc:
                _LOG.warning("BatchScheduler flush error: %s", exc)

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "pending":        len(self._pending),
                "total_flushed":  self._total_flushed,
                "running":        self._running,
                "batch_size":     self._batch_size,
            }


class PriorityScheduler:
    """
    Priority-queue based scheduler — CRITICAL observations first.
    """

    def __init__(
        self,
        manager:       Optional[PipelineManager] = None,
        pipeline_name: str                       = PIPELINE_STANDARD,
    ) -> None:
        self._manager       = manager or get_pipeline_manager()
        self._pipeline_name = pipeline_name
        self._heap:  list[ScheduledItem] = []
        self._seq    = 0
        self._lock   = threading.RLock()
        self._results: list[PipelineExecutionResult] = []

    def submit(self, obs: Observation, pipeline_name: Optional[str] = None) -> None:
        prio = _PRIORITY_ORDER.get(obs.metadata.priority, 99)
        with self._lock:
            self._seq += 1
            item = ScheduledItem(
                priority = prio,
                seq      = self._seq,
                obs      = obs,
                pipeline = pipeline_name or self._pipeline_name,
            )
            heapq.heappush(self._heap, item)

    def process_next(self) -> Optional[PipelineExecutionResult]:
        """Pop and process the highest-priority observation."""
        with self._lock:
            if not self._heap:
                return None
            item = heapq.heappop(self._heap)
        result = self._manager.process(item.obs, item.pipeline)
        with self._lock:
            self._results.append(result)
        return result

    def process_all(self) -> list[PipelineExecutionResult]:
        """Drain the queue and process all pending observations."""
        results = []
        while True:
            r = self.process_next()
            if r is None:
                break
            results.append(r)
        return results

    def depth(self) -> int:
        with self._lock:
            return len(self._heap)

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "depth":         len(self._heap),
                "total_results": len(self._results),
            }


class PipelineScheduler:
    """
    Unified scheduler that wraps both ``BatchScheduler`` and
    ``PriorityScheduler`` and routes submissions by priority tier.

    High-priority observations go directly via priority scheduler;
    normal/low-priority observations are batched.
    """

    def __init__(
        self,
        manager:         Optional[PipelineManager] = None,
        batch_size:      int                       = DEFAULT_BATCH_SIZE,
        batch_timeout_s: float                     = DEFAULT_BATCH_TIMEOUT_S,
        pipeline_name:   str                       = PIPELINE_STANDARD,
    ) -> None:
        mgr = manager or get_pipeline_manager()
        self._batch    = BatchScheduler(mgr, batch_size, batch_timeout_s, pipeline_name)
        self._priority = PriorityScheduler(mgr, pipeline_name)
        self._lock     = threading.RLock()

    def submit(self, obs: Observation, pipeline_name: Optional[str] = None) -> None:
        """Route observation to batch or priority queue."""
        if obs.metadata.priority in (ObservationPriority.CRITICAL, ObservationPriority.HIGH):
            self._priority.submit(obs, pipeline_name)
        else:
            self._batch.submit(obs)

    def submit_many(self, observations: list[Observation]) -> None:
        for obs in observations:
            self.submit(obs)

    def flush(self) -> list[PipelineExecutionResult]:
        """Process priority queue + batch queue; return all results."""
        results = []
        results.extend(self._priority.process_all())
        results.extend(self._batch.flush())
        return results

    def start(self) -> None:
        self._batch.start()

    def stop(self) -> None:
        self._batch.stop()

    def stats(self) -> dict[str, Any]:
        return {
            "batch":    self._batch.stats(),
            "priority": self._priority.stats(),
        }


def get_pipeline_scheduler() -> PipelineScheduler:
    global _scheduler
    if _scheduler is None:
        with _lock:
            if _scheduler is None:
                _scheduler = PipelineScheduler()
    return _scheduler


def reset_pipeline_scheduler() -> None:
    global _scheduler
    with _lock:
        if _scheduler is not None:
            try:
                _scheduler.stop()
            except Exception:
                pass
        _scheduler = None
