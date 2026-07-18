"""
iios/execution/recovery/engine/recovery_scheduler.py
====================================================
RecoveryScheduler — manages the priority queue of pending recovery requests.

Supports automatic, manual, scheduled, event-driven, and priority modes.
Higher-priority requests are dequeued first; equal-priority requests are
served in arrival order (FIFO).

C7 Execution Recovery & Resilience — Phase 1, Module 2
"""
from __future__ import annotations

import heapq
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import (
    DEFAULT_QUEUE_SIZE,
    SCHEDULER_ID,
    VERSION,
    RecoveryRequestPriority,
    SchedulerMode,
)
from .exceptions import RecoveryEngineNotRunningError, RecoverySchedulerError
from .recovery_request import RecoveryRequest

_log = get_logger(__name__)


@dataclass(order=True)
class _QueueItem:
    """
    Heap item — ordered by (negated_priority, sequence_number) so that
    higher-priority items are at the front and FIFO ordering is preserved
    within the same priority.
    """
    sort_key:   tuple         = field(compare=True)
    request_id: str           = field(compare=False)
    request:    RecoveryRequest = field(compare=False)


class RecoveryScheduler(LifecycleAwareMixin):
    """
    Priority queue for pending recovery requests.

    schedule() adds a request.
    next()     removes and returns the highest-priority request.
    cancel()   removes a request from the queue.
    """

    def __init__(
        self,
        max_queue_size: int   = DEFAULT_QUEUE_SIZE,
        mode:           SchedulerMode = SchedulerMode.AUTOMATIC,
    ) -> None:
        super().__init__()
        self._max_queue_size = max(1, max_queue_size)
        self._mode           = mode
        self._heap:          List[_QueueItem] = []
        self._cancelled_ids: Set[str]         = set()
        self._seq:           int              = 0
        self._lock           = threading.Lock()

    # ── LifecycleAwareMixin ───────────────────────────────────────────────────

    def _on_start(self) -> None:
        _log.info("RecoveryScheduler started.", system_id=SCHEDULER_ID, mode=self._mode.value)

    def _on_stop(self) -> None:
        with self._lock:
            size = len(self._heap)
        _log.info("RecoveryScheduler stopped.", system_id=SCHEDULER_ID, queued=size)

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in (EngineState.RUNNING, "running"):
            raise RecoveryEngineNotRunningError()

    # ── Queue operations ──────────────────────────────────────────────────────

    def schedule(self, request: RecoveryRequest) -> None:
        """Add a request to the priority queue."""
        self._assert_running()
        with self._lock:
            if len(self._heap) >= self._max_queue_size:
                raise RecoverySchedulerError(
                    f"Scheduler queue is full ({self._max_queue_size} items)"
                )
            # Negate priority so that EMERGENCY=5 has the lowest sort key
            sort_key = (-request.priority.value, self._seq)
            self._seq += 1
            item = _QueueItem(sort_key=sort_key, request_id=request.request_id, request=request)
            heapq.heappush(self._heap, item)
        _log.info(
            "Recovery request scheduled.",
            request_id=request.request_id,
            priority=request.priority.name,
            queue_size=self.queue_size,
        )

    def cancel(self, request_id: str) -> bool:
        """
        Mark a request as cancelled.  It will be skipped on the next next() call.
        Returns True if the request was in the queue.
        """
        with self._lock:
            ids_in_queue = {item.request_id for item in self._heap}
            if request_id not in ids_in_queue:
                return False
            self._cancelled_ids.add(request_id)
        _log.info("Recovery request cancelled.", request_id=request_id)
        return True

    def next(self) -> Optional[RecoveryRequest]:
        """
        Remove and return the highest-priority non-cancelled request.
        Returns None if the queue is empty.
        """
        with self._lock:
            while self._heap:
                item = heapq.heappop(self._heap)
                if item.request_id in self._cancelled_ids:
                    self._cancelled_ids.discard(item.request_id)
                    continue
                return item.request
        return None

    def peek(self) -> Optional[RecoveryRequest]:
        """Return the highest-priority request without removing it."""
        with self._lock:
            for item in self._heap:
                if item.request_id not in self._cancelled_ids:
                    return item.request
        return None

    def drain(self) -> List[RecoveryRequest]:
        """Remove and return all non-cancelled requests in priority order."""
        results: List[RecoveryRequest] = []
        while True:
            req = self.next()
            if req is None:
                break
            results.append(req)
        return results

    def clear(self) -> None:
        with self._lock:
            self._heap.clear()
            self._cancelled_ids.clear()
            self._seq = 0

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def queue_size(self) -> int:
        with self._lock:
            return max(0, len(self._heap) - len(self._cancelled_ids))

    @property
    def is_empty(self) -> bool:
        return self.queue_size == 0

    @property
    def mode(self) -> SchedulerMode:
        return self._mode

    @mode.setter
    def mode(self, value: SchedulerMode) -> None:
        self._mode = value
