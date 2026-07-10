"""iios/integration/market_data/streaming/stream_buffer.py

Per-subscription bounded async queue with backpressure.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Generic, TypeVar

from iios.integration.market_data.market_data_constants import DEFAULT_STREAM_BUFFER_SIZE
from iios.integration.market_data.market_data_exceptions import StreamBufferOverflowError

T = TypeVar("T")
logger = logging.getLogger(__name__)


@dataclass
class BufferMetrics:
    enqueued:    int   = 0
    dequeued:    int   = 0
    dropped:     int   = 0
    high_water:  int   = 0    # max size observed
    created_at:  float = field(default_factory=time.time)


class StreamBuffer(Generic[T]):
    """
    Bounded asyncio.Queue wrapper that tracks backpressure metrics.

    When the buffer is full:
    - drop=True  → oldest item is silently dropped (lossy, low-latency)
    - drop=False → StreamBufferOverflowError is raised
    """

    def __init__(
        self,
        max_size: int = DEFAULT_STREAM_BUFFER_SIZE,
        drop_on_full: bool = True,
        name: str = "",
    ) -> None:
        self._q:       asyncio.Queue[T] = asyncio.Queue(maxsize=max_size)
        self._max:     int              = max_size
        self._drop:    bool             = drop_on_full
        self.name:     str              = name
        self.metrics:  BufferMetrics    = BufferMetrics()

    # ── Write ──────────────────────────────────────────────────────────────────

    def put_nowait(self, item: T) -> None:
        """Non-blocking put. Drops or raises on full."""
        current = self._q.qsize()
        if current >= self._max:
            if self._drop:
                self.metrics.dropped += 1
                # drop oldest
                try:
                    self._q.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            else:
                raise StreamBufferOverflowError(
                    f"StreamBuffer '{self.name}' is full ({self._max} items)."
                )
        self._q.put_nowait(item)
        self.metrics.enqueued += 1
        self.metrics.high_water = max(self.metrics.high_water, self._q.qsize())

    async def put(self, item: T) -> None:
        """Async put — waits for space if buffer is full."""
        await self._q.put(item)
        self.metrics.enqueued += 1
        self.metrics.high_water = max(self.metrics.high_water, self._q.qsize())

    # ── Read ───────────────────────────────────────────────────────────────────

    async def get(self) -> T:
        """Wait and return next item."""
        item = await self._q.get()
        self.metrics.dequeued += 1
        return item

    def get_nowait(self) -> T:
        item = self._q.get_nowait()
        self.metrics.dequeued += 1
        return item

    def task_done(self) -> None:
        self._q.task_done()

    # ── Inspection ─────────────────────────────────────────────────────────────

    def qsize(self) -> int:
        return self._q.qsize()

    def empty(self) -> bool:
        return self._q.empty()

    def full(self) -> bool:
        return self._q.full()

    def utilisation_pct(self) -> float:
        return self._q.qsize() / self._max * 100.0 if self._max > 0 else 0.0

    def __repr__(self) -> str:
        return (
            f"StreamBuffer(name={self.name!r}, size={self.qsize()}/{self._max}, "
            f"dropped={self.metrics.dropped})"
        )
