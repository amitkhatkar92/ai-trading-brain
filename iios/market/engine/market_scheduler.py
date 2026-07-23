"""
market_scheduler.py — iios.market.engine
===========================================
Thread-safe priority-based market workflow scheduler.

Supports real-time monitoring, event-driven workflows, scheduled
market reviews, manual analysis, priority sessions, and batch
market processing.

C12 Market Intelligence — Phase 1, Module 2
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
from .market_request import MarketRequest
from .exceptions import MarketEngineCapacityError, MarketSchedulerError


class MarketScheduler:
    """
    Thread-safe priority queue scheduler for market workflow requests.

    Requests are ordered by :class:`SchedulerPriority` (lower integer =
    higher priority) with ties broken by arrival time (FIFO within a
    priority band).

    Parameters
    ----------
    max_queue_size : Maximum pending requests before raising
                     MarketEngineCapacityError.
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
        request:  MarketRequest,
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
        MarketEngineCapacityError
            When the queue is full.
        MarketSchedulerError
            When the request_id is already queued.
        """
        with self._lock:
            if len(self._heap) >= self._max:
                raise MarketEngineCapacityError(self._max)
            if request.request_id in self._index:
                raise MarketSchedulerError(
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

    def next(self) -> Optional[MarketRequest]:
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
        Cancel a pending request.

        Returns True if the request was found and marked for cancellation,
        False if already dispatched or not found.
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
        with self._lock:
            return max(0, len(self._heap) - len(self._cancelled))

    def scheduled_count(self) -> int:
        with self._lock:
            return self._scheduled

    def dispatched_count(self) -> int:
        with self._lock:
            return self._dispatched

    def cancelled_count(self) -> int:
        with self._lock:
            return self._cancelled_count

    def is_empty(self) -> bool:
        return self.pending_count() == 0

    def clear(self) -> None:
        with self._lock:
            self._heap.clear()
            self._index.clear()
            self._cancelled.clear()

    def statistics(self) -> dict:
        with self._lock:
            return {
                "scheduled":  self._scheduled,
                "dispatched": self._dispatched,
                "cancelled":  self._cancelled_count,
                "pending":    max(0, len(self._heap) - len(self._cancelled)),
            }
