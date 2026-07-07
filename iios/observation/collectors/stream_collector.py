"""
iios/observation/collectors/stream_collector.py
===============================================
StreamCollector — generator-based streaming collector.

Use for continuous data sources: WebSocket, SSE, Kafka consumer, etc.
``_do_stream()`` returns an iterator/generator; the collector pulls
items in mini-batches and converts each via ``_do_normalise_item()``.
"""
from __future__ import annotations

import threading
from collections.abc import Iterator
from typing import Any, Optional

from ..models.observation import Observation
from .base_collector      import BaseCollector, CollectorConfig
from .collector_constants import ExecutionMode

__all__ = ["StreamCollector"]


class StreamCollector(BaseCollector):
    """
    Streaming collector that pulls from an iterator/generator.

    Subclass and implement:
    - ``_do_stream() -> Iterator[Any]``        — yield raw stream items
    - ``_do_normalise_item(item) -> Optional[Observation]``

    ``max_items=0`` means unlimited (bounded only by batch_size or flush_every).
    """

    def __init__(
        self,
        config:      CollectorConfig,
        max_items:   int = 0,
        flush_every: int = 10,
    ) -> None:
        config.execution_mode = ExecutionMode.STREAM
        super().__init__(config)
        self._max_items     = max_items
        self._flush_every   = flush_every
        self._stream_active = threading.Event()
        self._stream_active.set()

    def _do_collect(self) -> Any:
        """Pull up to flush_every items from the stream this tick."""
        collected: list[Observation] = []
        count     = 0
        for item in self._do_stream():
            if not self._stream_active.is_set():
                break
            obs = self._do_normalise_item(item)
            if obs is not None:
                collected.append(obs)
                count += 1
            if self._max_items and count >= self._max_items:
                break
            if len(collected) >= self._flush_every:
                break
        return collected

    def _do_normalise(self, raw: Any) -> list[Observation]:
        if isinstance(raw, list):
            return raw
        return []

    def _do_stream(self) -> Iterator[Any]:
        """
        Override to yield raw items from the streaming source.

        Example::

            def _do_stream(self):
                for msg in self._ws.messages():
                    yield msg
        """
        return iter([])

    def _do_normalise_item(self, item: Any) -> Optional[Observation]:
        """
        Override to convert a single stream item to an Observation.
        Return None to skip the item.
        """
        if isinstance(item, Observation):
            return item
        return None

    def stop_stream(self) -> None:
        """Signal the stream iterator to stop after the current item."""
        self._stream_active.clear()

    def resume_stream(self) -> None:
        self._stream_active.set()
