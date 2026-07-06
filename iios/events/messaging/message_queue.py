"""
iios/events/messaging/message_queue.py
=======================================
All queue types: FIFO, Priority, Delay, Retry, DLQ, Batch, Streaming.
"""

from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Generator, Generic, Iterator, Optional, TypeVar

from .message import Message
from ..event_exceptions import QueueFullError, QueueEmptyError, QueueTimeoutError
from ..event_constants import DEFAULT_QUEUE_SIZE, DEFAULT_BATCH_SIZE, DEFAULT_STREAM_CHUNK

__all__ = [
    "FifoQueue",
    "PriorityQueue",
    "DelayQueue",
    "RetryQueue",
    "DeadLetterQueue",
    "BatchQueue",
    "StreamingQueue",
]

T = TypeVar("T")


class FifoQueue:
    """Thread-safe FIFO message queue."""

    def __init__(self, name: str = "fifo", max_size: int = DEFAULT_QUEUE_SIZE) -> None:
        self.name = name
        self._q: queue.Queue[Message] = queue.Queue(maxsize=max_size)
        self._max_size = max_size
        self._total_enqueued = 0
        self._total_dequeued = 0
        self._lock = threading.Lock()

    def put(self, msg: Message, timeout: Optional[float] = None) -> None:
        try:
            self._q.put(msg, timeout=timeout)
            with self._lock:
                self._total_enqueued += 1
        except queue.Full:
            raise QueueFullError(self.name, self._max_size)

    def get(self, timeout: Optional[float] = None) -> Message:
        try:
            msg = self._q.get(timeout=timeout if timeout is not None else 0.1)
            with self._lock:
                self._total_dequeued += 1
            return msg
        except queue.Empty:
            raise QueueEmptyError(self.name)

    def get_nowait(self) -> Message:
        try:
            msg = self._q.get_nowait()
            with self._lock:
                self._total_dequeued += 1
            return msg
        except queue.Empty:
            raise QueueEmptyError(self.name)

    def ack(self) -> None:
        self._q.task_done()

    def size(self) -> int:
        return self._q.qsize()

    def is_empty(self) -> bool:
        return self._q.empty()

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "name": self.name,
                "size": self.size(),
                "total_enqueued": self._total_enqueued,
                "total_dequeued": self._total_dequeued,
            }


@dataclass(order=True)
class _PQEntry:
    priority: int
    timestamp: float
    seq: int
    message: Message = field(compare=False)


class PriorityQueue:
    """Thread-safe priority queue. Lower priority value = higher priority."""

    def __init__(self, name: str = "priority", max_size: int = DEFAULT_QUEUE_SIZE) -> None:
        self.name = name
        self._q: queue.PriorityQueue[_PQEntry] = queue.PriorityQueue(maxsize=max_size)
        self._max_size = max_size
        self._seq = 0
        self._lock = threading.Lock()
        self._total_enqueued = 0
        self._total_dequeued = 0

    def put(self, msg: Message, timeout: Optional[float] = None) -> None:
        with self._lock:
            seq = self._seq
            self._seq += 1
        entry = _PQEntry(
            priority=msg.envelope.priority,
            timestamp=msg.envelope.timestamp,
            seq=seq,
            message=msg,
        )
        try:
            self._q.put(entry, timeout=timeout)
            with self._lock:
                self._total_enqueued += 1
        except queue.Full:
            raise QueueFullError(self.name, self._max_size)

    def get(self, timeout: Optional[float] = None) -> Message:
        try:
            entry = self._q.get(timeout=timeout if timeout is not None else 0.1)
            with self._lock:
                self._total_dequeued += 1
            return entry.message
        except queue.Empty:
            raise QueueEmptyError(self.name)

    def size(self) -> int:
        return self._q.qsize()

    def is_empty(self) -> bool:
        return self._q.empty()

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "name": self.name,
                "size": self.size(),
                "total_enqueued": self._total_enqueued,
                "total_dequeued": self._total_dequeued,
            }


class DelayQueue:
    """Queue where messages become available only after their scheduled time."""

    def __init__(self, name: str = "delay") -> None:
        self.name = name
        self._items: list[tuple[float, Message]] = []  # (available_at, msg)
        self._lock = threading.Lock()
        self._total_enqueued = 0
        self._total_dequeued = 0

    def put(self, msg: Message, delay: float = 0.0) -> None:
        available_at = time.time() + delay
        with self._lock:
            self._items.append((available_at, msg))
            self._items.sort(key=lambda x: x[0])
            self._total_enqueued += 1

    def get(self, timeout: Optional[float] = None) -> Message:
        deadline = time.monotonic() + (timeout or 0.0) if timeout else None
        while True:
            now = time.time()
            with self._lock:
                if self._items and self._items[0][0] <= now:
                    _, msg = self._items.pop(0)
                    self._total_dequeued += 1
                    return msg
            if deadline is not None and time.monotonic() >= deadline:
                raise QueueEmptyError(self.name)
            time.sleep(0.01)

    def drain_due(self) -> list[Message]:
        """Return all messages whose delay has expired."""
        now = time.time()
        due, remaining = [], []
        with self._lock:
            for at, msg in self._items:
                (due if at <= now else remaining).append((at, msg))
            self._items = remaining
            self._total_dequeued += len(due)
        return [m for _, m in due]

    def size(self) -> int:
        with self._lock:
            return len(self._items)

    def is_empty(self) -> bool:
        return self.size() == 0


class RetryQueue:
    """Queue with exponential-backoff retry for failed messages."""

    def __init__(
        self,
        name: str = "retry",
        max_retries: int = 3,
        base_delay: float = 1.0,
        backoff: float = 2.0,
    ) -> None:
        self.name = name
        self._max_retries = max_retries
        self._base_delay = base_delay
        self._backoff = backoff
        self._items: list[tuple[float, Message]] = []  # (retry_at, msg)
        self._dlq: list[Message] = []
        self._lock = threading.Lock()
        self._total_retried = 0
        self._total_dead = 0

    def schedule_retry(self, msg: Message) -> bool:
        """Add message for retry. Returns False if max retries exceeded → DLQ."""
        count = msg.envelope.retry_count
        if count >= self._max_retries:
            with self._lock:
                msg.envelope.status = __import__(
                    "iios.events.messaging.message", fromlist=["MessageStatus"]
                ).MessageStatus.DEAD_LETTERED
                self._dlq.append(msg)
                self._total_dead += 1
            return False
        delay = self._base_delay * (self._backoff ** count)
        retry_at = time.time() + delay
        msg.envelope.retry_count += 1
        with self._lock:
            self._items.append((retry_at, msg))
            self._items.sort(key=lambda x: x[0])
            self._total_retried += 1
        return True

    def drain_due(self) -> list[Message]:
        now = time.time()
        due, remaining = [], []
        with self._lock:
            for at, msg in self._items:
                (due if at <= now else remaining).append((at, msg))
            self._items = remaining
        return [m for _, m in due]

    def dead_letters(self) -> list[Message]:
        with self._lock:
            return list(self._dlq)

    def clear_dlq(self) -> int:
        with self._lock:
            n = len(self._dlq)
            self._dlq.clear()
        return n

    def size(self) -> int:
        with self._lock:
            return len(self._items)

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "name": self.name,
                "pending_retries": len(self._items),
                "dead_letters": len(self._dlq),
                "total_retried": self._total_retried,
                "total_dead": self._total_dead,
            }


class DeadLetterQueue:
    """Collects messages that have permanently failed delivery."""

    def __init__(self, name: str = "dlq", max_size: int = DEFAULT_QUEUE_SIZE) -> None:
        self.name = name
        self._max_size = max_size
        from collections import deque
        self._items: "deque[tuple[Message, str]]" = __import__("collections").deque(maxlen=max_size)
        self._lock = threading.Lock()
        self._total_received = 0

    def put(self, msg: Message, reason: str = "") -> None:
        with self._lock:
            self._items.append((msg, reason))
            self._total_received += 1

    def drain(self) -> list[tuple[Message, str]]:
        with self._lock:
            items = list(self._items)
            self._items.clear()
        return items

    def peek(self, limit: int = 20) -> list[tuple[Message, str]]:
        with self._lock:
            return list(self._items)[-limit:]

    def size(self) -> int:
        with self._lock:
            return len(self._items)

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {"name": self.name, "size": len(self._items), "total_received": self._total_received}


class BatchQueue:
    """Accumulates messages and delivers them in batches."""

    def __init__(
        self,
        name: str = "batch",
        batch_size: int = DEFAULT_BATCH_SIZE,
        flush_interval: float = 5.0,
    ) -> None:
        self.name = name
        self._batch_size = batch_size
        self._flush_interval = flush_interval
        self._buffer: list[Message] = []
        self._last_flush = time.monotonic()
        self._lock = threading.Lock()
        self._total_batches = 0

    def put(self, msg: Message) -> Optional[list[Message]]:
        """Add message; returns a batch if ready, else None."""
        with self._lock:
            self._buffer.append(msg)
            if len(self._buffer) >= self._batch_size:
                return self._flush_locked()
        return None

    def flush(self) -> list[Message]:
        with self._lock:
            return self._flush_locked()

    def should_flush(self) -> bool:
        with self._lock:
            if not self._buffer:
                return False
            elapsed = time.monotonic() - self._last_flush
            return elapsed >= self._flush_interval

    def _flush_locked(self) -> list[Message]:
        batch = list(self._buffer)
        self._buffer.clear()
        self._last_flush = time.monotonic()
        self._total_batches += 1
        return batch

    def size(self) -> int:
        with self._lock:
            return len(self._buffer)

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "name": self.name,
                "buffer_size": len(self._buffer),
                "total_batches": self._total_batches,
            }


class StreamingQueue:
    """Queue that can be iterated as a stream of messages."""

    def __init__(
        self,
        name: str = "stream",
        max_size: int = DEFAULT_QUEUE_SIZE,
        chunk_size: int = DEFAULT_STREAM_CHUNK,
    ) -> None:
        self.name = name
        self._q: queue.Queue[Optional[Message]] = queue.Queue(maxsize=max_size)
        self._chunk_size = chunk_size
        self._running = True
        self._total = 0

    def put(self, msg: Message) -> None:
        self._q.put(msg)
        self._total += 1

    def stop(self) -> None:
        self._running = False
        self._q.put(None)  # sentinel

    def __iter__(self) -> Iterator[Message]:
        while True:
            try:
                msg = self._q.get(timeout=0.2)
                if msg is None:  # sentinel from stop()
                    break
                yield msg
            except queue.Empty:
                if not self._running:
                    break
                continue

    def stream_chunks(self) -> Generator[list[Message], None, None]:
        """Yield messages in chunks of *chunk_size*."""
        chunk: list[Message] = []
        for msg in self:
            chunk.append(msg)
            if len(chunk) >= self._chunk_size:
                yield chunk
                chunk = []
        if chunk:
            yield chunk

    def size(self) -> int:
        return self._q.qsize()
