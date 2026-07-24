"""
event_bus_engine.py — iios.integration.services
-------------------------------------------------
EventBusEngine — publish/subscribe in-process event routing for the
Integration Services layer.

This is NOT the governance event bus (M3). It handles application-level
integration events (e.g. trade signals, data feeds, connector state changes).

C15 Enterprise Integration & Connectivity — Phase 1, Module 4
"""
from __future__ import annotations

import threading
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

_log = get_logger(__name__)

Subscriber = Callable[["IntegrationEvent"], None]


@dataclass(frozen=True)
class IntegrationEvent:
    """An application-level integration event published over the event bus."""
    event_id:    str
    topic:       str
    source:      str
    payload:     Dict[str, Any]
    created_at:  str

    @classmethod
    def create(
        cls,
        topic:   str,
        source:  str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> "IntegrationEvent":
        return cls(
            event_id   = f"ievt-{uuid.uuid4().hex[:12]}",
            topic      = topic,
            source     = source,
            payload    = payload or {},
            created_at = datetime.now(timezone.utc).isoformat(),
        )


class EventBusEngine:
    """
    Thread-safe in-process publish/subscribe event bus for integration events.

    Subscribers register by topic pattern. Published events are delivered
    synchronously to all matching subscribers. Exceptions in handlers are
    caught and logged — they never propagate to the publisher.
    """

    def __init__(self) -> None:
        self._lock        = threading.Lock()
        self._subscribers: Dict[str, List[Subscriber]] = defaultdict(list)
        self._published   = 0
        self._delivered   = 0
        self._errors      = 0

    # ── public ──────────────────────────────────────────────────────────

    def subscribe(self, topic: str, handler: Subscriber) -> None:
        """Register a subscriber for a topic."""
        with self._lock:
            self._subscribers[topic].append(handler)

    def unsubscribe(self, topic: str, handler: Subscriber) -> bool:
        """Remove a subscriber. Returns True if found and removed."""
        with self._lock:
            handlers = self._subscribers.get(topic, [])
            if handler in handlers:
                handlers.remove(handler)
                return True
        return False

    def publish(self, event: IntegrationEvent) -> int:
        """
        Publish an event to all subscribers on ``event.topic``.
        Returns the number of handlers that received the event.
        """
        with self._lock:
            handlers = list(self._subscribers.get(event.topic, []))
            self._published += 1

        delivered = 0
        for handler in handlers:
            try:
                handler(event)
                delivered += 1
            except Exception as exc:
                _log.debug(f"event-bus handler error on topic {event.topic!r}: {exc}")
                with self._lock:
                    self._errors += 1

        with self._lock:
            self._delivered += delivered

        return delivered

    def publish_to(
        self,
        topic:   str,
        source:  str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Convenience: create an IntegrationEvent and publish it."""
        event = IntegrationEvent.create(topic=topic, source=source, payload=payload)
        return self.publish(event)

    @property
    def stats(self) -> Dict[str, int]:
        with self._lock:
            return {
                "published":    self._published,
                "delivered":    self._delivered,
                "errors":       self._errors,
                "subscribers":  sum(len(v) for v in self._subscribers.values()),
            }

    def topics(self) -> List[str]:
        with self._lock:
            return [t for t, subs in self._subscribers.items() if subs]

    def subscriber_count(self, topic: str) -> int:
        with self._lock:
            return len(self._subscribers.get(topic, []))
