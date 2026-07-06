"""
iios/events/event_factory.py
================================
Factory for creating typed Event instances.
"""

from __future__ import annotations

import time
from typing import Any, Optional

from .event_metadata import Event, EventMetadata, make_event_id
from .event_priority import EventPriority

__all__ = ["EventFactory"]


class EventFactory:
    """Creates Event instances with validated metadata.

    Usage::

        factory = EventFactory(source="execution_engine")

        event = factory.create(
            event_type="trade.executed",
            payload={"symbol": "RELIANCE", "qty": 100},
            priority=EventPriority.HIGH,
        )

        # Sticky event — new subscribers receive this immediately
        sticky = factory.sticky("market.regime", payload={"regime": "BULL"})

        # One-time event — handler auto-removed after first delivery
        once = factory.once("session.started")

        # Delayed event — delivered after delay seconds
        delayed = factory.delayed("cache.flush", delay=60.0)

        # Child event — same correlation chain
        child = factory.child_of(event, "trade.settled")
    """

    def __init__(self, source: str = "iios") -> None:
        self._source = source

    def create(
        self,
        event_type: str,
        payload: Optional[dict[str, Any]] = None,
        *,
        priority: EventPriority = EventPriority.NORMAL,
        correlation_id: Optional[str] = None,
        causation_id: str = "",
        tags: Optional[dict[str, str]] = None,
        ttl: Optional[float] = None,
        sticky: bool = False,
        one_time: bool = False,
        persistent: bool = False,
        schema_version: str = "1",
        source: Optional[str] = None,
    ) -> Event:
        meta = EventMetadata(
            event_type=event_type,
            source=source or self._source,
            priority=priority,
            causation_id=causation_id,
            tags=tags or {},
            sticky=sticky,
            one_time=one_time,
            persistent=persistent,
            ttl=ttl,
            schema_version=schema_version,
        )
        if correlation_id:
            meta.correlation_id = correlation_id
        return Event(metadata=meta, payload=dict(payload or {}))

    def sticky(
        self,
        event_type: str,
        payload: Optional[dict[str, Any]] = None,
        **kw: Any,
    ) -> Event:
        return self.create(event_type, payload, sticky=True, **kw)

    def once(
        self,
        event_type: str,
        payload: Optional[dict[str, Any]] = None,
        **kw: Any,
    ) -> Event:
        return self.create(event_type, payload, one_time=True, **kw)

    def persistent(
        self,
        event_type: str,
        payload: Optional[dict[str, Any]] = None,
        **kw: Any,
    ) -> Event:
        return self.create(event_type, payload, persistent=True, **kw)

    def delayed(
        self,
        event_type: str,
        delay: float,
        payload: Optional[dict[str, Any]] = None,
        **kw: Any,
    ) -> Event:
        meta_kw = dict(kw)
        event = self.create(event_type, payload, **meta_kw)
        event.metadata.scheduled_at = time.time() + delay
        return event

    def scheduled(
        self,
        event_type: str,
        at: float,
        payload: Optional[dict[str, Any]] = None,
        **kw: Any,
    ) -> Event:
        event = self.create(event_type, payload, **kw)
        event.metadata.scheduled_at = at
        return event

    def child_of(self, parent: Event, event_type: str = "", payload: Optional[dict[str, Any]] = None) -> Event:
        meta = parent.metadata.child(event_type)
        return Event(metadata=meta, payload=dict(payload or {}))

    def with_ttl(self, event_type: str, ttl: float, payload: Optional[dict[str, Any]] = None, **kw: Any) -> Event:
        return self.create(event_type, payload, ttl=ttl, **kw)

    # ── Convenience class methods ─────────────────────────────────────────────

    @classmethod
    def make(
        cls,
        event_type: str,
        payload: Optional[dict[str, Any]] = None,
        source: str = "iios",
        **kw: Any,
    ) -> Event:
        return cls(source=source).create(event_type, payload, **kw)
