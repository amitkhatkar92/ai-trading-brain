"""
iios/infrastructure/events/event_queue.py
==========================================
Priority queue for event envelopes used by the event bus.
"""

from __future__ import annotations

import queue
import threading
import time
from collections import deque
from typing import Optional

from ..infrastructure_constants import DEFAULT_EVENT_QUEUE_SIZE, MAX_DEAD_LETTER_SIZE
from ..infrastructure_exceptions import DeadLetterError
from ..infrastructure_models import EventEnvelope, DeadLetterEntry

__all__ = ["EventQueue", "DeadLetterQueue"]


class EventQueue:
    """Thread-safe priority queue for ``EventEnvelope`` objects.

    Higher ``priority`` values are dequeued first.
    """

    def __init__(self, maxsize: int = DEFAULT_EVENT_QUEUE_SIZE) -> None:
        # Python's heapq is min-heap; EventEnvelope.__lt__ inverts priority
        self._q: queue.PriorityQueue = queue.PriorityQueue(maxsize=maxsize)
        self._enqueued = 0
        self._dequeued = 0
        self._lock = threading.Lock()

    def put(self, envelope: EventEnvelope, block: bool = True, timeout: Optional[float] = None) -> None:
        """Enqueue an event. Raises ``queue.Full`` if the queue is full and block=False."""
        self._q.put(envelope, block=block, timeout=timeout)
        with self._lock:
            self._enqueued += 1

    def get(self, block: bool = True, timeout: Optional[float] = None) -> EventEnvelope:
        """Dequeue the highest-priority event."""
        item = self._q.get(block=block, timeout=timeout)
        with self._lock:
            self._dequeued += 1
        return item

    def get_nowait(self) -> Optional[EventEnvelope]:
        try:
            return self.get(block=False)
        except queue.Empty:
            return None

    def task_done(self) -> None:
        self._q.task_done()

    def join(self) -> None:
        self._q.join()

    @property
    def qsize(self) -> int:
        return self._q.qsize()

    @property
    def empty(self) -> bool:
        return self._q.empty()

    @property
    def total_enqueued(self) -> int:
        with self._lock:
            return self._enqueued

    @property
    def total_dequeued(self) -> int:
        with self._lock:
            return self._dequeued


class DeadLetterQueue:
    """Stores events that failed all delivery attempts.

    Capacity-bounded ring buffer; oldest entries are evicted when full.
    """

    def __init__(self, maxsize: int = MAX_DEAD_LETTER_SIZE) -> None:
        self._q: deque[DeadLetterEntry] = deque(maxlen=maxsize)
        self._lock = threading.Lock()
        self._total = 0

    def add(self, envelope: EventEnvelope, reason: str, subscriber: str = "") -> None:
        entry = DeadLetterEntry(
            envelope=envelope,
            failure_reason=reason,
            subscriber=subscriber,
        )
        with self._lock:
            self._q.append(entry)
            self._total += 1

    def drain(self, n: int = 100) -> list[DeadLetterEntry]:
        """Pop up to *n* oldest entries."""
        with self._lock:
            entries = []
            for _ in range(min(n, len(self._q))):
                entries.append(self._q.popleft())
            return entries

    def all(self) -> list[DeadLetterEntry]:
        with self._lock:
            return list(self._q)

    def clear(self) -> None:
        with self._lock:
            self._q.clear()

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._q)

    @property
    def total_failed(self) -> int:
        return self._total
