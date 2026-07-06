"""
iios/events/event_metadata.py
================================
EventMetadata and base Event dataclasses.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from .event_priority import EventPriority

__all__ = ["EventMetadata", "Event", "make_event_id", "make_correlation_id"]


def make_event_id() -> str:
    return str(uuid.uuid4())


def make_correlation_id() -> str:
    return str(uuid.uuid4())


@dataclass
class EventMetadata:
    """Carries identity, routing, and delivery metadata for every event."""

    event_id: str = field(default_factory=make_event_id)
    event_type: str = ""
    source: str = "iios"
    timestamp: float = field(default_factory=time.time)
    correlation_id: str = field(default_factory=make_correlation_id)
    causation_id: str = ""           # id of the event that caused this one
    priority: EventPriority = EventPriority.NORMAL
    tags: dict[str, str] = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 3
    sticky: bool = False             # replay to new subscribers
    one_time: bool = False           # auto-unsubscribe after first delivery
    persistent: bool = False         # persist to store and replay
    ttl: Optional[float] = None      # seconds until expiry
    scheduled_at: Optional[float] = None  # delivery timestamp (Unix)
    schema_version: str = "1"

    @property
    def is_expired(self) -> bool:
        if self.ttl is None:
            return False
        return time.time() - self.timestamp >= self.ttl

    @property
    def is_due(self) -> bool:
        if self.scheduled_at is None:
            return True
        return time.time() >= self.scheduled_at

    def child(self, event_type: str = "") -> "EventMetadata":
        """Create metadata for a child event (same correlation, different causation)."""
        return EventMetadata(
            event_type=event_type or self.event_type,
            source=self.source,
            correlation_id=self.correlation_id,
            causation_id=self.event_id,
            priority=self.priority,
            tags=dict(self.tags),
        )


@dataclass
class Event:
    """Base event class. All IIOS events subclass or wrap this.

    Usage::

        from iios.events import Event, EventMetadata, EventPriority

        event = Event(
            metadata=EventMetadata(
                event_type="trade.executed",
                source="execution_engine",
                priority=EventPriority.HIGH,
            ),
            payload={"symbol": "RELIANCE", "qty": 100},
        )
    """

    metadata: EventMetadata = field(default_factory=EventMetadata)
    payload: dict[str, Any] = field(default_factory=dict)

    @property
    def event_id(self) -> str:
        return self.metadata.event_id

    @property
    def event_type(self) -> str:
        return self.metadata.event_type

    @property
    def correlation_id(self) -> str:
        return self.metadata.correlation_id

    @property
    def priority(self) -> EventPriority:
        return self.metadata.priority

    @property
    def is_expired(self) -> bool:
        return self.metadata.is_expired

    @property
    def is_due(self) -> bool:
        return self.metadata.is_due

    def __lt__(self, other: "Event") -> bool:
        # Used by priority queues (lower value = higher priority)
        return self.priority < other.priority
