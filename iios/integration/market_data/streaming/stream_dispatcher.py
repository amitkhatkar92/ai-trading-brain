"""iios/integration/market_data/streaming/stream_dispatcher.py

Dispatches MarketEvent to multiple subscriber buffers concurrently.
"""
from __future__ import annotations

import asyncio
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

from iios.integration.market_data.core.market_event     import MarketEvent
from iios.integration.market_data.market_data_constants import DEFAULT_STREAM_BUFFER_SIZE
from iios.integration.market_data.streaming.stream_buffer import StreamBuffer

logger = logging.getLogger(__name__)


@dataclass
class DispatcherSubscriber:
    """One registered consumer inside StreamDispatcher."""

    sub_id:          str                   = field(default_factory=lambda: str(uuid.uuid4()))
    name:            str                   = ""
    symbols_filter:  set[str]              = field(default_factory=set)
    buffer:          StreamBuffer[MarketEvent] = field(
        default_factory=lambda: StreamBuffer(max_size=DEFAULT_STREAM_BUFFER_SIZE, name="dispatcher")
    )
    created_at:      float                 = field(default_factory=time.time)
    event_count:     int                   = 0


class StreamDispatcher:
    """
    Fan-out dispatcher: one event → N subscriber buffers.

    Thread-safe: producers call ``dispatch()`` from any thread; consumers
    read from their own ``StreamBuffer`` in their own asyncio task.
    """

    def __init__(self) -> None:
        self._lock:  threading.RLock = threading.RLock()
        self._subs:  dict[str, DispatcherSubscriber] = {}
        self._stats: dict[str, int] = {"dispatched": 0, "skipped_filter": 0}

    # ── Registration ───────────────────────────────────────────────────────────

    def register(
        self,
        name:           str = "",
        symbols_filter: list[str] | None = None,
        buffer_size:    int = DEFAULT_STREAM_BUFFER_SIZE,
    ) -> DispatcherSubscriber:
        """Register a new consumer. Returns a ``DispatcherSubscriber`` whose
        ``.buffer`` the consumer should drain."""
        sub = DispatcherSubscriber(
            name           = name,
            symbols_filter = set(symbols_filter) if symbols_filter else set(),
            buffer         = StreamBuffer(max_size=buffer_size, name=name, drop_on_full=True),
        )
        with self._lock:
            self._subs[sub.sub_id] = sub
        logger.debug("[StreamDispatcher] registered %s symbols_filter=%s", sub.sub_id, sub.symbols_filter)
        return sub

    def unregister(self, sub_id: str) -> None:
        with self._lock:
            self._subs.pop(sub_id, None)

    # ── Dispatch ───────────────────────────────────────────────────────────────

    def dispatch(self, event: MarketEvent) -> int:
        """
        Dispatch event to all matching subscriber buffers.
        Returns number of buffers that received the event.
        """
        with self._lock:
            targets = list(self._subs.values())

        sent = 0
        for sub in targets:
            if sub.symbols_filter and event.symbol not in sub.symbols_filter:
                self._stats["skipped_filter"] += 1
                continue
            sub.buffer.put_nowait(event)
            sub.event_count += 1
            sent += 1

        self._stats["dispatched"] += 1
        return sent

    # ── Inspection ─────────────────────────────────────────────────────────────

    def subscriber_count(self) -> int:
        with self._lock:
            return len(self._subs)

    def get_subscriber(self, sub_id: str) -> DispatcherSubscriber | None:
        with self._lock:
            return self._subs.get(sub_id)

    def stats(self) -> dict[str, Any]:
        return dict(self._stats)
