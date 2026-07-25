"""
workflow_queue_manager.py — iios.workflow.orchestration
--------------------------------------------------------
WorkflowQueueManager — priority queue of pending workflow execution
requests with a configurable worker pool.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 4
"""
from __future__ import annotations

import queue
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import DEFAULT_QUEUE_CAPACITY, PREFIX_JOB
from .exceptions import WorkflowQueueError
from .workflow_definition import WorkflowExecutionRequest
from .workflow_runtime import WorkflowExecutionResult

_log = get_logger(__name__)


@dataclass(order=True)
class _QueueItem:
    """Priority-ordered wrapper for execution requests."""
    priority:   int
    sequence:   int
    job_id:     str               = field(compare=False)
    request:    WorkflowExecutionRequest = field(compare=False)
    created_at: str               = field(compare=False)


@dataclass(order=True)
class _StopSentinel:
    """Comparable poison-pill for PriorityQueue worker shutdown."""
    priority: int = 2**31   # always sorts last
    sequence: int = 2**31


class WorkflowQueueManager:
    """
    Priority queue manager for workflow execution requests.

    Requests are ordered by (priority, sequence) — lower value = higher
    priority (critical workflows get priority 0).

    Thread-safe.
    """

    def __init__(
        self,
        capacity:    int = DEFAULT_QUEUE_CAPACITY,
        num_workers: int = 4,
    ) -> None:
        self._capacity  = capacity
        self._queue:    queue.PriorityQueue = queue.PriorityQueue(maxsize=capacity)
        self._lock      = threading.Lock()
        self._sequence  = 0
        self._workers:  List[threading.Thread] = []
        self._running   = False
        self._executor_fn: Optional[Callable[[WorkflowExecutionRequest], WorkflowExecutionResult]] = None
        self._num_workers = num_workers

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self, executor_fn: Callable[[WorkflowExecutionRequest], WorkflowExecutionResult]) -> None:
        """Start worker threads.  executor_fn is called for each request."""
        with self._lock:
            if self._running:
                return
            self._executor_fn = executor_fn
            self._running     = True

        for i in range(self._num_workers):
            t = threading.Thread(
                target=self._worker_loop, daemon=True, name=f"wf-queue-worker-{i}"
            )
            t.start()
            self._workers.append(t)
        _log.info(f"QueueManager: started {self._num_workers} workers")

    def stop(self) -> None:
        """Signal workers to stop after current tasks complete."""
        with self._lock:
            if not self._running:
                return
            self._running = False

        # Poison pills to unblock workers
        for _ in self._workers:
            try:
                self._queue.put_nowait(_StopSentinel())
            except queue.Full:
                pass
        _log.info("QueueManager: stopped")

    # ── Enqueue ───────────────────────────────────────────────────────────────

    def enqueue(self, request: WorkflowExecutionRequest) -> str:
        """
        Add a request to the queue.

        Returns:
            job_id for tracking.

        Raises:
            WorkflowQueueError if queue is full.
        """
        with self._lock:
            if not self._running:
                raise WorkflowQueueError("Queue is not started")
            seq    = self._sequence
            self._sequence += 1

        job_id = f"{PREFIX_JOB}{uuid.uuid4().hex[:8]}"
        item   = _QueueItem(
            priority   = request.priority,
            sequence   = seq,
            job_id     = job_id,
            request    = request,
            created_at = datetime.now(tz=timezone.utc).isoformat(),
        )
        try:
            self._queue.put_nowait(item)
        except queue.Full:
            raise WorkflowQueueError(
                f"Queue is full: capacity={self._capacity}"
            )
        _log.debug(
            f"QueueManager: enqueued job={job_id!r} "
            f"workflow={request.workflow_id!r} "
            f"priority={request.priority}"
        )
        return job_id

    # ── Worker ────────────────────────────────────────────────────────────────

    def _worker_loop(self) -> None:
        while True:
            try:
                item = self._queue.get(timeout=1.0)
            except queue.Empty:
                with self._lock:
                    if not self._running:
                        break
                continue

            if isinstance(item, _StopSentinel):   # poison pill
                self._queue.task_done()
                break

            try:
                if self._executor_fn:
                    self._executor_fn(item.request)
            except Exception as exc:
                _log.error(
                    f"QueueManager: worker error for "
                    f"job={item.job_id!r}: {exc!r}"
                )
            finally:
                self._queue.task_done()

    # ── Introspection ─────────────────────────────────────────────────────────

    def queue_size(self) -> int:
        return self._queue.qsize()

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._running
