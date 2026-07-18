"""
iios/execution/analytics/engine/analytics_scheduler.py
======================================================
AnalyticsScheduler — schedules analytics requests for the Execution
Analytics Engine.

Supports:
  - Periodic analytics  (fixed-interval recurring)
  - On-demand analytics (immediate dispatch)
  - Event-driven        (triggered by external events)
  - Scheduled           (at a specific wall-time)
  - Priority            (elevated dispatch priority)

The scheduler maintains a priority-ordered queue of AnalyticsRequest objects.
It does NOT execute analytics; it only queues requests for the engine to
dequeue and process.

C8 Execution Analytics & Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import heapq
import threading
import time
from dataclasses import dataclass, field
from typing import List, Optional

from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import (
    ACTOR_SCHEDULER,
    DEFAULT_SCHEDULER_QUEUE,
    SCHEDULER_SYSTEM_ID,
    AnalyticsRequestType,
    ScheduleType,
)
from .exceptions import AnalyticsEngineNotRunningError, AnalyticsSchedulerError
from .analytics_request import AnalyticsRequest, make_analytics_request

_log = get_logger(__name__)

_RUNNING = frozenset({EngineState.RUNNING, "running"})


@dataclass(order=True)
class _ScheduledEntry:
    """
    Priority-queue entry.  Ordered by (priority, sequence) so high-priority
    items (lower number) are dequeued first.  Tie-break by insertion sequence.
    """

    priority:      int
    sequence:      int               = field(compare=True)
    schedule_at:   float             = field(compare=False)
    request:       AnalyticsRequest  = field(compare=False)
    schedule_type: ScheduleType      = field(compare=False, default=ScheduleType.ON_DEMAND)
    interval_s:    Optional[float]   = field(compare=False, default=None)


class AnalyticsScheduler(LifecycleAwareMixin):
    """
    Priority-based analytics request scheduler.

    Maintains an ordered heap of AnalyticsRequest objects ready for
    dequeue by the engine.  Thread-safe.  Must be started before use.
    """

    def __init__(self, max_queue: int = DEFAULT_SCHEDULER_QUEUE) -> None:
        super().__init__()
        self._max_queue     = max(1, max_queue)
        self._heap:         List[_ScheduledEntry] = []
        self._seq_counter   = 0
        self._lock          = threading.RLock()

    # ── LifecycleAwareMixin hooks ──────────────────────────────────────────────

    def _on_start(self) -> None:
        _log.info("AnalyticsScheduler started.", system_id=SCHEDULER_SYSTEM_ID)

    def _on_stop(self) -> None:
        with self._lock:
            pending = len(self._heap)
        _log.info(
            "AnalyticsScheduler stopped.",
            system_id       = SCHEDULER_SYSTEM_ID,
            pending_entries = pending,
        )

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in _RUNNING:
            raise AnalyticsEngineNotRunningError()

    # ── Scheduling API ────────────────────────────────────────────────────────

    def schedule(
        self,
        request:       AnalyticsRequest,
        *,
        schedule_type: ScheduleType        = ScheduleType.ON_DEMAND,
        schedule_at:   Optional[float]     = None,
        interval_s:    Optional[float]     = None,
    ) -> str:
        """
        Add a request to the queue.

        Returns the request_id.
        Raises AnalyticsSchedulerError if the queue is full.
        """
        self._assert_running()
        with self._lock:
            if len(self._heap) >= self._max_queue:
                raise AnalyticsSchedulerError(
                    f"Scheduler queue is full ({self._max_queue} entries)."
                )
            self._seq_counter += 1
            entry = _ScheduledEntry(
                priority      = request.priority,
                sequence      = self._seq_counter,
                schedule_at   = schedule_at or time.time(),
                request       = request,
                schedule_type = schedule_type,
                interval_s    = interval_s,
            )
            heapq.heappush(self._heap, entry)
            _log.debug(
                "Analytics request scheduled.",
                request_id   = request.request_id,
                request_type = request.request_type.value,
                priority     = request.priority,
                queue_depth  = len(self._heap),
            )
        return request.request_id

    def schedule_on_demand(
        self,
        execution_session_id: str,
        *,
        priority:  int = 5,
        requester: str = ACTOR_SCHEDULER,
        reason:    str = "",
    ) -> str:
        """Schedule an immediate on-demand analytics request."""
        self._assert_running()
        request = make_analytics_request(
            execution_session_id,
            request_type = AnalyticsRequestType.ON_DEMAND,
            requester    = requester,
            priority     = priority,
            reason       = reason,
        )
        return self.schedule(request, schedule_type=ScheduleType.ON_DEMAND)

    def schedule_periodic(
        self,
        execution_session_id: str,
        interval_s:           float,
        *,
        priority:  int = 7,
        requester: str = ACTOR_SCHEDULER,
    ) -> str:
        """Schedule a periodic analytics request."""
        self._assert_running()
        request = make_analytics_request(
            execution_session_id,
            request_type = AnalyticsRequestType.PERIODIC,
            requester    = requester,
            priority     = priority,
        )
        return self.schedule(
            request,
            schedule_type = ScheduleType.PERIODIC,
            interval_s    = interval_s,
        )

    def schedule_event_driven(
        self,
        execution_session_id: str,
        *,
        priority:  int = 3,
        requester: str = ACTOR_SCHEDULER,
        reason:    str = "",
    ) -> str:
        """Schedule an event-driven analytics request."""
        self._assert_running()
        request = make_analytics_request(
            execution_session_id,
            request_type = AnalyticsRequestType.EVENT,
            requester    = requester,
            priority     = priority,
            reason       = reason,
        )
        return self.schedule(request, schedule_type=ScheduleType.EVENT)

    def schedule_priority(
        self,
        execution_session_id: str,
        *,
        priority:  int = 1,
        requester: str = ACTOR_SCHEDULER,
        reason:    str = "",
    ) -> str:
        """Schedule a high-priority analytics request."""
        self._assert_running()
        request = make_analytics_request(
            execution_session_id,
            request_type = AnalyticsRequestType.PRIORITY,
            requester    = requester,
            priority     = priority,
            reason       = reason,
        )
        return self.schedule(request, schedule_type=ScheduleType.ONCE)

    # ── Dequeue API ───────────────────────────────────────────────────────────

    def dequeue(self) -> Optional[AnalyticsRequest]:
        """
        Dequeue the highest-priority request that is due now.

        Returns None if no request is ready.
        """
        self._assert_running()
        now = time.time()
        with self._lock:
            if not self._heap:
                return None
            if self._heap[0].schedule_at > now:
                return None
            entry = heapq.heappop(self._heap)
            return entry.request

    def dequeue_all_due(self) -> List[AnalyticsRequest]:
        """Dequeue ALL requests that are due right now, ordered by priority."""
        self._assert_running()
        now = time.time()
        result: List[AnalyticsRequest] = []
        with self._lock:
            while self._heap and self._heap[0].schedule_at <= now:
                entry = heapq.heappop(self._heap)
                result.append(entry.request)
        return result

    def peek(self) -> Optional[AnalyticsRequest]:
        """Peek at the next due request without dequeuing."""
        with self._lock:
            if self._heap:
                return self._heap[0].request
            return None

    def clear(self) -> int:
        """Clear all queued requests.  Returns the number removed."""
        with self._lock:
            count = len(self._heap)
            self._heap.clear()
        return count

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def queue_depth(self) -> int:
        with self._lock:
            return len(self._heap)

    @property
    def is_empty(self) -> bool:
        with self._lock:
            return len(self._heap) == 0
