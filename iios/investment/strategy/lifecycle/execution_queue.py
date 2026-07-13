"""iios/investment/strategy/lifecycle/execution_queue.py
Thread-safe priority-based execution queue for strategy dispatch.
"""
from __future__ import annotations

import heapq
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import IntEnum
from typing import List, Optional


class SchedulePriority(IntEnum):
    """Execution priority levels.

    Lower numeric value = higher priority (dequeued first).
    """

    CRITICAL   = 0
    HIGH       = 10
    NORMAL     = 20
    LOW        = 30
    BACKGROUND = 40


@dataclass(order=True)
class ExecutionRequest:
    """
    A request to execute one strategy instance.

    Ordered by (priority, submitted_at) so the heap processes critical
    requests first; within the same priority, FIFO order is preserved.
    """

    # Sort keys (must come first for dataclass ordering)
    priority: int = field(default=int(SchedulePriority.NORMAL))
    submitted_at: datetime = field(
        compare=True,
        default_factory=lambda: datetime.now(timezone.utc),
    )

    # Payload (compare=False so they don't affect heap ordering)
    request_id: str = field(
        compare=False,
        default_factory=lambda: f"req-{uuid.uuid4().hex[:10]}",
    )
    strategy_id: str = field(compare=False, default="")
    context_ref: object = field(compare=False, repr=False, default=None)
    deadline: Optional[datetime] = field(compare=False, default=None)
    dependencies: List[str] = field(compare=False, default_factory=list)
    retry_count: int = field(compare=False, default=0)
    max_retries: int = field(compare=False, default=3)
    metadata: dict = field(compare=False, default_factory=dict)

    def is_expired(self) -> bool:
        """True if the deadline has passed."""
        if self.deadline is None:
            return False
        return datetime.now(timezone.utc) > self.deadline


class QueueFullError(Exception):
    """Raised when the execution queue is at maximum capacity."""


class ExecutionQueue:
    """
    Thread-safe min-heap priority queue for ExecutionRequests.

    Lower priority value = dequeued first (CRITICAL before BACKGROUND).
    Same-priority requests are dequeued in submission order (FIFO).
    Expired requests are discarded automatically on dequeue.
    """

    def __init__(self, max_size: int = 10_000) -> None:
        self._max_size = max_size
        self._lock = threading.Lock()
        self._heap: List[ExecutionRequest] = []

    def enqueue(self, request: ExecutionRequest) -> None:
        """Enqueue a request. Raises QueueFullError if at capacity."""
        with self._lock:
            if len(self._heap) >= self._max_size:
                raise QueueFullError(
                    f"ExecutionQueue is full (capacity={self._max_size})"
                )
            heapq.heappush(self._heap, request)

    def dequeue(self) -> Optional[ExecutionRequest]:
        """Remove and return the highest-priority non-expired request, or None."""
        with self._lock:
            while self._heap:
                req = heapq.heappop(self._heap)
                if req.is_expired():
                    continue  # silently discard expired entries
                return req
            return None

    def peek(self) -> Optional[ExecutionRequest]:
        """Return the top request without removing it, or None."""
        with self._lock:
            return self._heap[0] if self._heap else None

    def drain(self) -> List[ExecutionRequest]:
        """Remove and return all pending requests (for graceful shutdown)."""
        with self._lock:
            items = list(self._heap)
            self._heap.clear()
            return items

    def __len__(self) -> int:
        with self._lock:
            return len(self._heap)

    @property
    def depth(self) -> int:
        return len(self)

    def is_empty(self) -> bool:
        with self._lock:
            return not self._heap
