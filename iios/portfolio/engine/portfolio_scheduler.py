"""
portfolio_scheduler.py — iios.portfolio.engine
===============================================
Thread-safe priority-based portfolio workflow scheduler.

Supports real-time, event-driven, scheduled, manual, priority,
and batch portfolio processing.

C10 Portfolio Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import heapq
import threading
import time
from typing import List, Optional, Tuple

from .constants import (
    DEFAULT_MAX_SCHEDULER_QUEUE,
    SchedulerPriority,
)
from .portfolio_request import PortfolioRequest
from .exceptions import PortfolioCapacityError, PortfolioSchedulerError


class PortfolioScheduler:
    """
    Thread-safe priority queue scheduler for portfolio workflow requests.

    Requests are ordered by :class:`SchedulerPriority` (lower integer = higher
    priority) with ties broken by arrival time (FIFO within a priority band).

    Usage
    -----
    ::

        scheduler = PortfolioScheduler()
        scheduler.schedule(request)              # NORMAL priority
        scheduler.schedule(request, SchedulerPriority.CRITICAL)
        next_req = scheduler.next()              # returns highest-priority item
        scheduler.cancel(request.request_id)

    Parameters
    ----------
    max_queue_size : Maximum pending requests before raising CapacityError.
    """

    def __init__(self, max_queue_size: int = DEFAULT_MAX_SCHEDULER_QUEUE) -> None:
        self._lock          = threading.Lock()
        self._heap:  List   = []          # (priority_int, arrival_seq, request)
        self._index: dict   = {}          # request_id → True (for cancel check)
        self._cancelled: set = set()      # cancelled request_ids
        self._seq:          int   = 0
        self._max           = max_queue_size
        self._scheduled:    int   = 0
        self._dispatched:   int   = 0
        self._cancelled_count: int = 0

    # ------------------------------------------------------------------
    # Scheduling
    # ------------------------------------------------------------------

    def schedule(
        self,
        request:  PortfolioRequest,
        priority: Optional[SchedulerPriority] = None,
    ) -> str:
        """
        Add a request to the scheduler queue.

        Parameters
        ----------
        request :  Portfolio workflow request.
        priority : Override scheduling priority. If None, uses request's priority.

        Returns
        -------
        str
            The request_id of the scheduled request.

        Raises
        ------
        PortfolioCapacityError
            When the queue is full.
        PortfolioSchedulerError
            When the request_id is already queued.
        """
        with self._lock:
            if len(self._heap) >= self._max:
                raise PortfolioCapacityError(self._max)
            if request.request_id in self._index:
                raise PortfolioSchedulerError(
                    f"Request already scheduled: {request.request_id!r}"
                )
            prio = (priority or request.priority).value
            self._seq += 1
            heapq.heappush(self._heap, (prio, self._seq, time.time(), request))
            self._index[request.request_id] = True
            self._scheduled += 1
        return request.request_id

    # ------------------------------------------------------------------
    # Dequeue
    # ------------------------------------------------------------------

    def next(self) -> Optional[PortfolioRequest]:
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
        """
        Cancel a pending request by its request_id.

        Returns True if the request was found and marked for cancellation,
        False if it was already dispatched or not found.
        """
        with self._lock:
            if request_id in self._index:
                self._cancelled.add(request_id)
                self._cancelled_count += 1
                return True
        return False

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def pending_count(self) -> int:
        """Number of pending (non-cancelled) requests in the queue."""
        with self._lock:
            return len(self._heap) - len(self._cancelled)

    def queue_size(self) -> int:
        """Raw queue size including cancelled items."""
        with self._lock:
            return len(self._heap)

    def statistics(self) -> dict:
        with self._lock:
            return {
                "scheduled":   self._scheduled,
                "dispatched":  self._dispatched,
                "cancelled":   self._cancelled_count,
                "pending":     max(0, len(self._heap) - len(self._cancelled)),
            }

    # ------------------------------------------------------------------
    # Clear
    # ------------------------------------------------------------------

    def clear(self) -> None:
        with self._lock:
            self._heap.clear()
            self._index.clear()
            self._cancelled.clear()
