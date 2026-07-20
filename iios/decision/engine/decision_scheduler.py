"""
decision_scheduler.py — iios.decision.engine
==============================================
Priority-aware decision request scheduler.

Supports six scheduling modes:
  REAL_TIME, EVENT_DRIVEN, SCHEDULED, MANUAL, PRIORITY, BATCH

C9 Decision Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import threading
import time
from typing import List, Optional

from .constants import (
    DEFAULT_MAX_QUEUE,
    DecisionMode,
    DecisionPriority,
)
from .decision_request import DecisionRequest


class _ScheduledEntry:
    """Internal wrapper pairing a request with its enqueue time."""
    __slots__ = ("request", "enqueued_at")

    def __init__(self, request: DecisionRequest) -> None:
        self.request    = request
        self.enqueued_at = time.time()

    # Lower priority value → higher urgency → sort first
    def __lt__(self, other: "_ScheduledEntry") -> bool:
        if self.request.priority != other.request.priority:
            return self.request.priority < other.request.priority
        return self.enqueued_at < other.enqueued_at


class DecisionScheduler:
    """
    Thread-safe priority queue for decision requests.

    Requests are accepted regardless of their scheduling mode
    (REAL_TIME, EVENT_DRIVEN, SCHEDULED, MANUAL, PRIORITY, BATCH).
    Priority ordering ensures that higher-urgency requests are dequeued first.

    Parameters
    ----------
    max_queue : Maximum number of queued requests (default 10 000).
    """

    def __init__(self, max_queue: int = DEFAULT_MAX_QUEUE) -> None:
        self._lock      = threading.RLock()
        self._max_queue = max_queue
        self._queue:    List[_ScheduledEntry]        = []
        self._cancelled: set[str]                    = set()   # request_ids
        self._total_scheduled: int                   = 0

    # ------------------------------------------------------------------
    # Schedule
    # ------------------------------------------------------------------
    def schedule(self, request: DecisionRequest) -> None:
        """
        Enqueue *request* for processing.

        Raises
        ------
        RuntimeError
            When the queue is at capacity.
        """
        with self._lock:
            if len(self._queue) >= self._max_queue:
                raise RuntimeError(
                    f"DecisionScheduler: queue at capacity ({self._max_queue})"
                )
            import bisect
            entry = _ScheduledEntry(request)
            bisect.insort(self._queue, entry)
            self._total_scheduled += 1

    # ------------------------------------------------------------------
    # Dequeue
    # ------------------------------------------------------------------
    def next(self) -> Optional[DecisionRequest]:
        """
        Return and remove the highest-priority pending request, or ``None``
        when the queue is empty.

        Skips any cancelled requests.
        """
        with self._lock:
            while self._queue:
                entry = self._queue.pop(0)
                if entry.request.request_id in self._cancelled:
                    self._cancelled.discard(entry.request.request_id)
                    continue
                return entry.request
            return None

    # ------------------------------------------------------------------
    # Cancellation
    # ------------------------------------------------------------------
    def cancel(self, request_id: str) -> bool:
        """
        Mark *request_id* as cancelled so it will be skipped on dequeue.

        Returns ``True`` if the request was in the queue, ``False`` otherwise.
        """
        with self._lock:
            in_queue = any(e.request.request_id == request_id for e in self._queue)
            if in_queue:
                self._cancelled.add(request_id)
            return in_queue

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------
    def pending_count(self) -> int:
        """Number of non-cancelled requests currently queued."""
        with self._lock:
            return sum(
                1 for e in self._queue
                if e.request.request_id not in self._cancelled
            )

    def total_scheduled(self) -> int:
        """Total requests ever scheduled (including completed and cancelled)."""
        with self._lock:
            return self._total_scheduled

    def is_empty(self) -> bool:
        with self._lock:
            return self.pending_count() == 0

    def clear(self) -> None:
        """Discard all pending requests."""
        with self._lock:
            self._queue.clear()
            self._cancelled.clear()
