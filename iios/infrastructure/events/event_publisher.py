"""
iios/infrastructure/events/event_publisher.py
=============================================
Publisher API for sending events onto the bus.
"""

from __future__ import annotations

import threading
import uuid
from typing import Any, Optional

from ..infrastructure_constants import EventPriority
from ..infrastructure_models import EventEnvelope
from .event_queue import EventQueue

__all__ = ["EventPublisher"]


class EventPublisher:
    """Convenient API for creating and publishing EventEnvelopes.

    Typically obtained from the EventBus::

        publisher = bus.publisher("my.component")
        publisher.publish("market.price_updated", {"symbol": "RELIANCE", "price": 2850})
    """

    def __init__(self, queue: EventQueue, source: str = "") -> None:
        self._queue = queue
        self._source = source
        self._published = 0
        self._lock = threading.Lock()
        self._correlation_id: Optional[str] = None

    def publish(
        self,
        event_type: str,
        payload: Any = None,
        *,
        priority: int = EventPriority.NORMAL.value,
        correlation_id: Optional[str] = None,
        max_retries: int = 3,
        metadata: Optional[dict[str, Any]] = None,
    ) -> EventEnvelope:
        """Create and enqueue an event envelope.

        Args:
            event_type:     Dotted event type string (e.g. ``"risk.kill_switch"``).
            payload:        Arbitrary serialisable payload.
            priority:       EventPriority value; higher = dispatched first.
            correlation_id: Optional trace/correlation ID.
            max_retries:    Max delivery retries before dead-lettering.
            metadata:       Arbitrary metadata attached to the envelope.

        Returns:
            The ``EventEnvelope`` that was enqueued.
        """
        envelope = EventEnvelope(
            event_type=event_type,
            payload=payload,
            source=self._source,
            priority=priority,
            correlation_id=correlation_id or self._correlation_id or str(uuid.uuid4()),
            max_retries=max_retries,
            metadata=metadata or {},
        )
        self._queue.put(envelope)
        with self._lock:
            self._published += 1
        return envelope

    def publish_high(self, event_type: str, payload: Any = None, **kwargs: Any) -> EventEnvelope:
        return self.publish(event_type, payload, priority=EventPriority.HIGH.value, **kwargs)

    def publish_critical(self, event_type: str, payload: Any = None, **kwargs: Any) -> EventEnvelope:
        return self.publish(event_type, payload, priority=EventPriority.CRITICAL.value, **kwargs)

    def publish_low(self, event_type: str, payload: Any = None, **kwargs: Any) -> EventEnvelope:
        return self.publish(event_type, payload, priority=EventPriority.LOW.value, **kwargs)

    def set_correlation_id(self, correlation_id: str) -> "EventPublisher":
        """Set a sticky correlation ID applied to all published events."""
        self._correlation_id = correlation_id
        return self

    @property
    def published_count(self) -> int:
        return self._published

    @property
    def source(self) -> str:
        return self._source
