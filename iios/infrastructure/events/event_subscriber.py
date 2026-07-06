"""
iios/infrastructure/events/event_subscriber.py
===============================================
Subscriber descriptors and base class for event handlers.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from ..infrastructure_models import EventEnvelope

__all__ = [
    "Subscriber",
    "SubscriberDescriptor",
    "EventHandler",
    "AsyncEventHandler",
]

EventHandler = Callable[[EventEnvelope], None]


@dataclass
class SubscriberDescriptor:
    """Metadata about a registered subscription."""

    subscription_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = "*"           # "*" matches all events
    handler: Optional[EventHandler] = field(default=None, repr=False)
    priority: int = 50              # higher = called first among peers
    name: str = ""
    max_retries: int = 3
    enabled: bool = True
    call_count: int = 0
    error_count: int = 0

    def matches(self, event_type: str) -> bool:
        """Check whether this subscriber handles *event_type*."""
        if self.event_type == "*":
            return True
        # Allow simple prefix glob: "market.*"
        if self.event_type.endswith(".*"):
            prefix = self.event_type[:-2]
            return event_type.startswith(prefix)
        return self.event_type == event_type


class Subscriber:
    """Base class for event subscribers.

    Subclass and override ``handle()``::

        class RiskSubscriber(Subscriber):
            event_type = "risk.breach"

            def handle(self, envelope: EventEnvelope) -> None:
                ...
    """

    event_type: str = "*"
    priority: int = 50
    max_retries: int = 3
    name: str = ""

    def __init__(self) -> None:
        self._descriptor = SubscriberDescriptor(
            event_type=self.__class__.event_type,
            handler=self.handle,
            priority=self.__class__.priority,
            name=self.__class__.name or self.__class__.__name__,
            max_retries=self.__class__.max_retries,
        )

    def handle(self, envelope: EventEnvelope) -> None:
        """Override to implement event handling logic."""
        raise NotImplementedError

    @property
    def descriptor(self) -> SubscriberDescriptor:
        return self._descriptor

    @property
    def subscription_id(self) -> str:
        return self._descriptor.subscription_id


class AsyncEventHandler:
    """Wraps a synchronous handler for asynchronous dispatch (thread-based)."""

    def __init__(self, handler: EventHandler) -> None:
        self._handler = handler
        self._lock = threading.Lock()

    def __call__(self, envelope: EventEnvelope) -> None:
        t = threading.Thread(
            target=self._handler,
            args=(envelope,),
            daemon=True,
            name=f"async-handler-{envelope.event_id[:8]}",
        )
        t.start()
