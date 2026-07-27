"""
ai_event_bus.py — iios.ai.foundation.adapters
=============================================
:class:`AIEventBus` — intra-platform event publishing interface.

All inter-module communication within the AI Platform flows through the
event bus — this is the mechanism that prevents circular imports between
A2 (Model Management) and A7 (Execution Routing).  See Review
Observation O-001.

A1 AI Foundation — Phase 3, Module 4
"""
from __future__ import annotations

import abc
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .constants import SCHEMA_VERSION, VERSION


# ---------------------------------------------------------------------------
# AI event
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AIEvent:
    """
    Immutable event published on the AI event bus.

    Fields
    ------
    event_type :  Domain event type string (e.g. ``"ai.model.selected"``).
    source_id :   Module identifier that published this event.
    payload :     Arbitrary event data (must be JSON-serialisable).
    event_id :    Unique event identifier (auto-generated).
    timestamp :   Wall-clock time of event creation.
    correlation : Optional correlation identifier (links related events).
    version :     Schema version string.
    """
    event_type:  str
    source_id:   str
    payload:     Dict[str, Any]
    event_id:    str   = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp:   float = field(default_factory=time.time)
    correlation: str   = ""
    version:     str   = VERSION
    schema:      str   = SCHEMA_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":    self.event_id,
            "event_type":  self.event_type,
            "source_id":   self.source_id,
            "timestamp":   self.timestamp,
            "correlation": self.correlation,
            "payload":     self.payload,
        }


# Handler type
AIEventHandler = Callable[[AIEvent], None]


# ---------------------------------------------------------------------------
# Abstract event bus interface
# ---------------------------------------------------------------------------

class AIEventBus(abc.ABC):
    """
    Abstract AI Platform event bus.

    All inter-module communication uses this interface.  No AI module
    holds a direct reference to another AI module — only the event bus.

    Design note
    -----------
    This prevents the circular dependency between A2 (Model Management)
    and A7 (Execution Routing) identified in Review Observation O-001.
    A2 publishes ``"ai.model.selected"``; A7 subscribes.  A7 publishes
    ``"ai.routing.feedback"``; A2 subscribes.  Neither holds a reference
    to the other.

    Implementations
    ---------------
    :class:`LocalAIEventBus` — in-process synchronous bus (default).
    Future: async bus, distributed bus (Kafka, Redis Streams).
    """

    @abc.abstractmethod
    def publish(self, event: AIEvent) -> None:
        """Publish ``event`` to all subscribers of its ``event_type``."""

    @abc.abstractmethod
    def subscribe(self, event_type: str, handler: AIEventHandler) -> str:
        """
        Subscribe ``handler`` to events of ``event_type``.

        Returns
        -------
        str
            Subscription ID — pass to :meth:`unsubscribe` to remove.
        """

    @abc.abstractmethod
    def unsubscribe(self, subscription_id: str) -> None:
        """Remove the subscription identified by ``subscription_id``."""

    def emit(
        self,
        event_type:  str,
        source_id:   str,
        payload:     Dict[str, Any],
        correlation: str = "",
    ) -> AIEvent:
        """
        Convenience factory — create an :class:`AIEvent` and publish it.

        Returns the published event.
        """
        event = AIEvent(
            event_type  = event_type,
            source_id   = source_id,
            payload     = payload,
            correlation = correlation,
        )
        self.publish(event)
        return event


# ---------------------------------------------------------------------------
# Local synchronous implementation (default, always available)
# ---------------------------------------------------------------------------

class LocalAIEventBus(AIEventBus):
    """
    In-process synchronous event bus.

    Handlers are called in subscription order on the publisher's thread.
    Exceptions in handlers are caught and logged — a faulty handler never
    breaks event delivery to other subscribers.

    Suitable for single-process deployment and testing.
    """

    def __init__(self) -> None:
        self._lock:          threading.Lock              = threading.Lock()
        self._handlers:      Dict[str, List[tuple[str, AIEventHandler]]] = {}
        # subscription_id → event_type
        self._sub_map:       Dict[str, str]              = {}

    def publish(self, event: AIEvent) -> None:
        with self._lock:
            handlers = list(self._handlers.get(event.event_type, []))
        for sub_id, handler in handlers:
            try:
                handler(event)
            except Exception:
                # swallow — faulty handlers must not break the bus
                pass

    def subscribe(self, event_type: str, handler: AIEventHandler) -> str:
        sub_id = str(uuid.uuid4())
        with self._lock:
            self._handlers.setdefault(event_type, []).append((sub_id, handler))
            self._sub_map[sub_id] = event_type
        return sub_id

    def unsubscribe(self, subscription_id: str) -> None:
        with self._lock:
            event_type = self._sub_map.pop(subscription_id, None)
            if event_type and event_type in self._handlers:
                self._handlers[event_type] = [
                    (sid, h)
                    for sid, h in self._handlers[event_type]
                    if sid != subscription_id
                ]

    def subscriber_count(self, event_type: Optional[str] = None) -> int:
        """Return subscriber count for ``event_type``, or total across all types."""
        with self._lock:
            if event_type:
                return len(self._handlers.get(event_type, []))
            return sum(len(v) for v in self._handlers.values())

    def __repr__(self) -> str:
        return f"<LocalAIEventBus subscriptions={len(self._sub_map)}>"
