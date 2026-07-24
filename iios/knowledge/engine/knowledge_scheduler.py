"""
knowledge_scheduler.py — iios.knowledge.engine
------------------------------------------------
Knowledge collection scheduler.

Supports five scheduling modes:
  - Continuous collection
  - Scheduled collection
  - Event-driven collection
  - Priority collection
  - Batch collection

C14 Enterprise Knowledge Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import queue
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from .constants import (
    DEFAULT_MAX_SCHEDULER_QUEUE,
    ACTOR_SCHEDULER,
    SchedulerMode,
    SchedulerPriority,
)
from .exceptions import KnowledgeSchedulerError
from .knowledge_request import KnowledgeRequest


# ---------------------------------------------------------------------------
# ScheduledItem — priority queue entry
# ---------------------------------------------------------------------------

class _ScheduledItem:
    """Priority queue entry wrapping a KnowledgeRequest."""
    __slots__ = ("priority", "enqueued_at", "request")

    def __init__(self, request: KnowledgeRequest) -> None:
        self.priority    = int(request.priority)
        self.enqueued_at = time.time()
        self.request     = request

    def __lt__(self, other: "_ScheduledItem") -> bool:
        if self.priority != other.priority:
            return self.priority < other.priority
        return self.enqueued_at < other.enqueued_at


# ---------------------------------------------------------------------------
# KnowledgeScheduler
# ---------------------------------------------------------------------------

class KnowledgeScheduler:
    """
    Thread-safe scheduler for knowledge collection requests.

    Requests are enqueued into a priority queue and dequeued by the
    Knowledge Engine for processing.  The scheduler tracks queue depth
    and eviction counts for observability.
    """

    def __init__(self, max_queue_size: int = DEFAULT_MAX_SCHEDULER_QUEUE) -> None:
        self._max_queue    = max(1, max_queue_size)
        self._queue: queue.PriorityQueue = queue.PriorityQueue()
        self._lock         = threading.Lock()
        self._enqueue_count = 0
        self._dequeue_count = 0
        self._drop_count    = 0
        self._running       = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        with self._lock:
            self._running = True

    def stop(self) -> None:
        with self._lock:
            self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    # ------------------------------------------------------------------
    # Queue operations
    # ------------------------------------------------------------------

    def enqueue(self, request: KnowledgeRequest) -> bool:
        """
        Enqueue a request.

        Returns ``True`` if the request was accepted, ``False`` if dropped
        (queue full or scheduler stopped).
        """
        with self._lock:
            if not self._running:
                return False
            if self._queue.qsize() >= self._max_queue:
                self._drop_count += 1
                return False
            self._queue.put(_ScheduledItem(request))
            self._enqueue_count += 1
            return True

    def dequeue(self, timeout: float = 0.1) -> Optional[KnowledgeRequest]:
        """
        Dequeue the next highest-priority request.

        Returns ``None`` if the queue is empty or the timeout elapses.
        """
        try:
            item = self._queue.get(timeout=timeout)
            with self._lock:
                self._dequeue_count += 1
            return item.request
        except queue.Empty:
            return None

    def enqueue_batch(self, requests: List[KnowledgeRequest]) -> int:
        """Enqueue a batch of requests.  Returns the count accepted."""
        accepted = 0
        for req in requests:
            if self.enqueue(req):
                accepted += 1
        return accepted

    def queue_depth(self) -> int:
        return self._queue.qsize()

    def statistics(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "enqueue_count": self._enqueue_count,
                "dequeue_count": self._dequeue_count,
                "drop_count":    self._drop_count,
                "queue_depth":   self._queue.qsize(),
                "max_queue":     self._max_queue,
                "is_running":    self._running,
            }

    def clear(self) -> int:
        """Drain all pending requests.  Returns count removed."""
        removed = 0
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                removed += 1
            except queue.Empty:
                break
        return removed
