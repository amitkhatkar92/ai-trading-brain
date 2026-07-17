"""iios/execution/gateway/engine/gateway_operation_queue.py
==================================================
GatewayOperationQueue — thread-safe multi-queue system for the
Execution Gateway Engine.

Provides four specialised queues:
  FifoQueue        — standard FIFO processing queue
  EnginePriorityQueue — priority-based processing queue (higher priority first)
  RetryQueue       — deferred retry queue with per-entry delay
  CancellationQueue — set of request IDs pending cancellation

GatewayOperationQueue is the public facade managing all four.

C6 Execution Intelligence — Phase 5, Module 2
"""
from __future__ import annotations

import heapq
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .constants import DEFAULT_MAX_QUEUE_SIZE, QueueType
from .exceptions import GatewayQueueFullError
from .gateway_request import EngineGatewayRequest


# ── FifoQueue ─────────────────────────────────────────────────────────────────

class FifoQueue:
    """Thread-safe FIFO queue for gateway requests."""

    def __init__(self, max_size: int = DEFAULT_MAX_QUEUE_SIZE) -> None:
        self._max_size  = max(1, max_size)
        self._queue:    deque[EngineGatewayRequest] = deque()
        self._lock      = threading.Lock()
        self._enqueued  = 0
        self._dequeued  = 0

    def enqueue(self, request: EngineGatewayRequest) -> None:
        with self._lock:
            if len(self._queue) >= self._max_size:
                raise GatewayQueueFullError(QueueType.FIFO.value, self._max_size)
            self._queue.append(request)
            self._enqueued += 1

    def dequeue(self) -> Optional[EngineGatewayRequest]:
        with self._lock:
            if not self._queue:
                return None
            self._dequeued += 1
            return self._queue.popleft()

    def peek(self) -> Optional[EngineGatewayRequest]:
        with self._lock:
            return self._queue[0] if self._queue else None

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._queue)

    @property
    def is_empty(self) -> bool:
        with self._lock:
            return len(self._queue) == 0

    @property
    def is_full(self) -> bool:
        with self._lock:
            return len(self._queue) >= self._max_size

    @property
    def enqueued_count(self) -> int:
        return self._enqueued

    @property
    def dequeued_count(self) -> int:
        return self._dequeued


# ── EnginePriorityQueue ───────────────────────────────────────────────────────

class EnginePriorityQueue:
    """
    Thread-safe priority queue for gateway requests.

    Higher ``request.priority`` values are dequeued first.
    Ties are broken by insertion order (FIFO within same priority).
    """

    def __init__(self, max_size: int = DEFAULT_MAX_QUEUE_SIZE) -> None:
        self._max_size  = max(1, max_size)
        self._heap:     List[Tuple[int, int, EngineGatewayRequest]] = []
        self._counter   = 0   # tie-breaker: lower = earlier insertion
        self._lock      = threading.Lock()
        self._enqueued  = 0
        self._dequeued  = 0

    def enqueue(self, request: EngineGatewayRequest) -> None:
        with self._lock:
            if len(self._heap) >= self._max_size:
                raise GatewayQueueFullError(QueueType.PRIORITY.value, self._max_size)
            # negate priority so that higher values are popped first
            heapq.heappush(self._heap, (-request.priority, self._counter, request))
            self._counter  += 1
            self._enqueued += 1

    def dequeue(self) -> Optional[EngineGatewayRequest]:
        with self._lock:
            if not self._heap:
                return None
            self._dequeued += 1
            _, _, request = heapq.heappop(self._heap)
            return request

    def peek(self) -> Optional[EngineGatewayRequest]:
        with self._lock:
            if not self._heap:
                return None
            _, _, request = self._heap[0]
            return request

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._heap)

    @property
    def is_empty(self) -> bool:
        with self._lock:
            return len(self._heap) == 0

    @property
    def is_full(self) -> bool:
        with self._lock:
            return len(self._heap) >= self._max_size

    @property
    def enqueued_count(self) -> int:
        return self._enqueued

    @property
    def dequeued_count(self) -> int:
        return self._dequeued


# ── RetryEntry ────────────────────────────────────────────────────────────────

@dataclass
class _RetryEntry:
    request:    EngineGatewayRequest
    retry_at:   float          # Unix timestamp when this entry becomes ready


# ── RetryQueue ────────────────────────────────────────────────────────────────

class RetryQueue:
    """
    Thread-safe retry queue.

    Entries are dequeued only when their ``retry_at`` timestamp has passed.
    """

    def __init__(self, max_size: int = DEFAULT_MAX_QUEUE_SIZE) -> None:
        self._max_size  = max(1, max_size)
        self._queue:    deque[_RetryEntry] = deque()
        self._lock      = threading.Lock()
        self._enqueued  = 0
        self._dequeued  = 0

    def enqueue(
        self,
        request:     EngineGatewayRequest,
        delay_secs:  float = 0.0,
    ) -> None:
        with self._lock:
            if len(self._queue) >= self._max_size:
                raise GatewayQueueFullError(QueueType.RETRY.value, self._max_size)
            retry_at = time.time() + max(0.0, delay_secs)
            self._queue.append(_RetryEntry(request=request, retry_at=retry_at))
            self._enqueued += 1

    def dequeue_ready(self) -> List[EngineGatewayRequest]:
        """Return all entries whose retry time has passed and remove them."""
        now = time.time()
        ready: List[EngineGatewayRequest] = []
        with self._lock:
            remaining: deque[_RetryEntry] = deque()
            for entry in self._queue:
                if entry.retry_at <= now:
                    ready.append(entry.request)
                    self._dequeued += 1
                else:
                    remaining.append(entry)
            self._queue = remaining
        return ready

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._queue)

    @property
    def is_empty(self) -> bool:
        with self._lock:
            return len(self._queue) == 0

    @property
    def enqueued_count(self) -> int:
        return self._enqueued

    @property
    def dequeued_count(self) -> int:
        return self._dequeued


# ── CancellationQueue ─────────────────────────────────────────────────────────

class CancellationQueue:
    """
    Thread-safe cancellation queue.

    Stores request IDs (strings) pending cancellation.
    Membership check is O(1).
    """

    def __init__(self, max_size: int = DEFAULT_MAX_QUEUE_SIZE) -> None:
        self._max_size  = max(1, max_size)
        self._queue:    deque[str] = deque()
        self._pending:  set[str]  = set()
        self._lock      = threading.Lock()
        self._enqueued  = 0
        self._dequeued  = 0

    def enqueue(self, request_id: str) -> None:
        with self._lock:
            if request_id in self._pending:
                return    # idempotent — already queued
            if len(self._queue) >= self._max_size:
                raise GatewayQueueFullError(QueueType.CANCELLATION.value, self._max_size)
            self._queue.append(request_id)
            self._pending.add(request_id)
            self._enqueued += 1

    def dequeue(self) -> Optional[str]:
        with self._lock:
            if not self._queue:
                return None
            request_id = self._queue.popleft()
            self._pending.discard(request_id)
            self._dequeued += 1
            return request_id

    def contains(self, request_id: str) -> bool:
        with self._lock:
            return request_id in self._pending

    def remove(self, request_id: str) -> bool:
        """Remove a specific ID without dequeuing in order."""
        with self._lock:
            if request_id not in self._pending:
                return False
            self._pending.discard(request_id)
            try:
                self._queue.remove(request_id)
            except ValueError:
                pass
            self._dequeued += 1
            return True

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._queue)

    @property
    def is_empty(self) -> bool:
        with self._lock:
            return len(self._queue) == 0

    @property
    def enqueued_count(self) -> int:
        return self._enqueued

    @property
    def dequeued_count(self) -> int:
        return self._dequeued


# ── QueueStatistics ───────────────────────────────────────────────────────────

@dataclass
class QueueStatistics:
    """Aggregated counters for all four queues."""
    fifo_enqueued:         int = 0
    fifo_dequeued:         int = 0
    priority_enqueued:     int = 0
    priority_dequeued:     int = 0
    retry_enqueued:        int = 0
    retry_dequeued:        int = 0
    cancellation_enqueued: int = 0
    cancellation_dequeued: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fifo_enqueued":         self.fifo_enqueued,
            "fifo_dequeued":         self.fifo_dequeued,
            "priority_enqueued":     self.priority_enqueued,
            "priority_dequeued":     self.priority_dequeued,
            "retry_enqueued":        self.retry_enqueued,
            "retry_dequeued":        self.retry_dequeued,
            "cancellation_enqueued": self.cancellation_enqueued,
            "cancellation_dequeued": self.cancellation_dequeued,
        }


# ── GatewayOperationQueue ─────────────────────────────────────────────────────

class GatewayOperationQueue:
    """
    Facade managing FIFO, priority, retry, and cancellation queues.

    Priority queue takes precedence over FIFO when dequeuing the next
    request for processing.
    """

    def __init__(self, max_size: int = DEFAULT_MAX_QUEUE_SIZE) -> None:
        self._fifo         = FifoQueue(max_size=max_size)
        self._priority     = EnginePriorityQueue(max_size=max_size)
        self._retry        = RetryQueue(max_size=max_size)
        self._cancellation = CancellationQueue(max_size=max_size)

    # ── Enqueue ───────────────────────────────────────────────────────────────

    def enqueue_fifo(self, request: EngineGatewayRequest) -> None:
        """Add to the FIFO queue."""
        self._fifo.enqueue(request)

    def enqueue_priority(self, request: EngineGatewayRequest) -> None:
        """Add to the priority queue."""
        self._priority.enqueue(request)

    def enqueue_retry(
        self,
        request:     EngineGatewayRequest,
        delay_secs:  float = 0.0,
    ) -> None:
        """Add to the retry queue with an optional delay."""
        self._retry.enqueue(request, delay_secs=delay_secs)

    def enqueue_cancellation(self, request_id: str) -> None:
        """Mark a request ID as pending cancellation."""
        self._cancellation.enqueue(request_id)

    # ── Dequeue ───────────────────────────────────────────────────────────────

    def dequeue_next(self) -> Optional[EngineGatewayRequest]:
        """
        Dequeue the next request for processing.

        Priority queue is checked first; falls back to FIFO.
        """
        request = self._priority.dequeue()
        if request is not None:
            return request
        return self._fifo.dequeue()

    def dequeue_retry_ready(self) -> List[EngineGatewayRequest]:
        """Return all retry entries whose delay has elapsed."""
        return self._retry.dequeue_ready()

    def dequeue_cancellation(self) -> Optional[str]:
        """Dequeue one pending cancellation request ID."""
        return self._cancellation.dequeue()

    # ── Query ─────────────────────────────────────────────────────────────────

    def is_cancellation_pending(self, request_id: str) -> bool:
        return self._cancellation.contains(request_id)

    def remove_cancellation(self, request_id: str) -> bool:
        return self._cancellation.remove(request_id)

    # ── Sizes ─────────────────────────────────────────────────────────────────

    def sizes(self) -> Dict[str, int]:
        return {
            QueueType.FIFO.value:         self._fifo.size,
            QueueType.PRIORITY.value:     self._priority.size,
            QueueType.RETRY.value:        self._retry.size,
            QueueType.CANCELLATION.value: self._cancellation.size,
        }

    @property
    def total_pending(self) -> int:
        """Total requests in fifo + priority queues."""
        return self._fifo.size + self._priority.size

    @property
    def is_empty(self) -> bool:
        """True if both main queues are empty."""
        return self._fifo.is_empty and self._priority.is_empty

    # ── Statistics ────────────────────────────────────────────────────────────

    @property
    def statistics(self) -> QueueStatistics:
        return QueueStatistics(
            fifo_enqueued=self._fifo.enqueued_count,
            fifo_dequeued=self._fifo.dequeued_count,
            priority_enqueued=self._priority.enqueued_count,
            priority_dequeued=self._priority.dequeued_count,
            retry_enqueued=self._retry.enqueued_count,
            retry_dequeued=self._retry.dequeued_count,
            cancellation_enqueued=self._cancellation.enqueued_count,
            cancellation_dequeued=self._cancellation.dequeued_count,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sizes":      self.sizes(),
            "statistics": self.statistics.to_dict(),
        }
