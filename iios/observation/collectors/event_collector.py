"""
iios/observation/collectors/event_collector.py
==============================================
EventCollector — event-triggered data collector.

External producers call ``push_event(event)`` to queue work.
``run()`` drains the queue and converts events to Observations.
"""
from __future__ import annotations

import queue
from typing import Any, Callable, Optional

from ..models.observation import Observation
from .base_collector      import BaseCollector, CollectorConfig
from .collector_constants import ExecutionMode

__all__ = ["EventCollector"]

EventData    = dict[str, Any]
EventFilter  = Callable[[EventData], bool]


class EventCollector(BaseCollector):
    """
    Queue-based event collector.

    Producers call ``push_event(event_dict)``; ``run()`` drains the
    queue up to ``config.batch_size`` items per call.

    Subclass and implement:
    - ``_do_normalise_event(event) -> Optional[Observation]``
    """

    def __init__(
        self,
        config:     CollectorConfig,
        queue_size: int = 1_000,
    ) -> None:
        config.execution_mode = ExecutionMode.BATCH
        super().__init__(config)
        self._queue:   queue.Queue[EventData] = queue.Queue(maxsize=queue_size)
        self._filters: list[EventFilter]      = []

    def push_event(self, event: EventData) -> bool:
        """Enqueue an event. Returns False if the queue is full."""
        try:
            self._queue.put_nowait(event)
            return True
        except queue.Full:
            self._log.warning("Event queue full [%s]", self.name)
            return False

    def add_filter(self, fn: EventFilter) -> None:
        """Add a filter function. Events failing any filter are dropped."""
        self._filters.append(fn)

    @property
    def pending_count(self) -> int:
        return self._queue.qsize()

    def _do_collect(self) -> Any:
        """Drain up to batch_size events from the queue."""
        events: list[EventData] = []
        limit   = self.config.batch_size or 100
        while len(events) < limit:
            try:
                event = self._queue.get_nowait()
            except queue.Empty:
                break
            if all(f(event) for f in self._filters):
                events.append(event)
        return events

    def _do_normalise(self, raw: Any) -> list[Observation]:
        if not isinstance(raw, list):
            return []
        results: list[Observation] = []
        for event in raw:
            obs = self._do_normalise_event(event)
            if obs is not None:
                results.append(obs)
        return results

    def _do_normalise_event(self, event: EventData) -> Optional[Observation]:
        """Override to convert a raw event dict to an Observation."""
        return self._make_observation(
            content    = event,
            title      = str(event.get("type", "event")),
            instrument = str(event.get("symbol", "")),
        )
