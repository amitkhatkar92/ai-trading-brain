"""
supervisor_scheduler.py — iios.supervisor.engine
-------------------------------------------------
Thread-safe priority-based supervisor workflow scheduler.

Supports continuous supervision, scheduled supervision, event-driven
supervision, health monitoring, priority supervision, and batch supervision.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 2
"""
from __future__ import annotations

import heapq
import threading
import time
from typing import List, Optional

from .constants import (
    DEFAULT_MAX_SCHEDULER_QUEUE,
    SchedulerPriority,
)
from .supervisor_request import SupervisorRequest
from .exceptions import SupervisorEngineCapacityError, SupervisorSchedulerError


class SupervisorScheduler:
    """
    Thread-safe priority queue scheduler for supervisor workflow requests.

    Requests are ordered by :class:`SchedulerPriority` (lower integer =
    higher priority) with ties broken by arrival time (FIFO within a
    priority band).

    Parameters
    ----------
    max_queue_size : Maximum pending requests before raising
                     SupervisorEngineCapacityError.
    """

    def __init__(
        self,
        max_queue_size: int = DEFAULT_MAX_SCHEDULER_QUEUE,
    ) -> None:
        self._lock               = threading.Lock()
        self._heap:  List        = []
        self._index: dict        = {}
        self._cancelled: set     = set()
        self._seq:           int = 0
        self._max                = max_queue_size
        self._scheduled:     int = 0
        self._dispatched:    int = 0
        self._cancelled_count: int = 0

    # ------------------------------------------------------------------
    # Scheduling
    # ------------------------------------------------------------------

    def schedule(
        self,
        request:  SupervisorRequest,
        priority: Optional[SchedulerPriority] = None,
    ) -> str:
        """
        Add a request to the scheduler queue.

        Returns
        -------
        str
            The request_id of the scheduled request.

        Raises
        ------
        SupervisorEngineCapacityError
            When the queue is full.
        SupervisorSchedulerError
            When the request_id is already queued.
        """
        with self._lock:
            if len(self._heap) >= self._max:
                raise SupervisorEngineCapacityError(self._max)
            if request.request_id in self._index:
                raise SupervisorSchedulerError(
                    f"Request already scheduled: {request.request_id!r}"
                )
            prio = (priority or request.priority).value
            self._seq += 1
            heapq.heappush(
                self._heap, (prio, self._seq, time.time(), request)
            )
            self._index[request.request_id] = True
            self._scheduled += 1
        return request.request_id

    # ------------------------------------------------------------------
    # Dequeue
    # ------------------------------------------------------------------

    def next(self) -> Optional[SupervisorRequest]:
        """
        Pop and return the highest-priority non-cancelled request.

        Returns None when the queue is empty or all remaining items are
        cancelled.
        """
        with self._lock:
            while self._heap:
                prio, seq, arrived, req = heapq.heappop(self._heap)
                self._index.pop(req.request_id, None)
                if req.request_id in self._cancelled:
                    self._cancelled.discard(req.request_id)
                    continue
                self._dispatched += 1
                return req
        return None

    # ------------------------------------------------------------------
    # Cancellation
    # ------------------------------------------------------------------

    def cancel(self, request_id: str) -> bool:
        """Mark a queued request as cancelled. Returns True if it was queued."""
        with self._lock:
            if request_id in self._index:
                self._cancelled.add(request_id)
                self._cancelled_count += 1
                return True
        return False

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def queue_depth(self) -> int:
        with self._lock:
            return len(self._heap) - len(self._cancelled)

    def statistics(self) -> dict:
        with self._lock:
            return {
                "scheduled":   self._scheduled,
                "dispatched":  self._dispatched,
                "cancelled":   self._cancelled_count,
                "queue_depth": max(0, len(self._heap) - len(self._cancelled)),
            }

    def clear(self) -> None:
        with self._lock:
            self._heap.clear()
            self._index.clear()
            self._cancelled.clear()
