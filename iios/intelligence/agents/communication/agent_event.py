"""
iios/intelligence/agents/communication/agent_event.py
======================================================
AgentEvent — events emitted by the multi-agent system.

Events are distinct from messages:
  - Messages are directed communications between agents.
  - Events are system notifications for logging, monitoring, auditing.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from ..agent_constants import AgentEventType

__all__ = [
    "AgentEvent",
    "AgentEventBus",
    "get_agent_event_bus",
    "reset_agent_event_bus",
]

import threading


@dataclass
class AgentEvent:
    """An event emitted by the multi-agent system."""
    event_id:   str           = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: AgentEventType = AgentEventType.STARTED
    agent_id:   str           = ""
    payload:    dict          = field(default_factory=dict)
    timestamp:  float         = field(default_factory=time.time)
    metadata:   dict          = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "event_id":   self.event_id,
            "event_type": self.event_type.value,
            "agent_id":   self.agent_id,
            "payload":    self.payload,
            "timestamp":  self.timestamp,
        }


class AgentEventBus:
    """
    Lightweight synchronous event bus.

    Subscribers register a callable for one or more event types.
    When an event is emitted, all matching subscribers are called
    synchronously in the emitter's thread.
    """

    def __init__(self) -> None:
        self._lock:        threading.RLock = threading.RLock()
        self._handlers:    dict[AgentEventType, list[Callable]] = {}
        self._event_count: int = 0

    def subscribe(
        self,
        event_type: AgentEventType,
        handler:    Callable[[AgentEvent], None],
    ) -> None:
        with self._lock:
            self._handlers.setdefault(event_type, []).append(handler)

    def unsubscribe(
        self,
        event_type: AgentEventType,
        handler:    Callable[[AgentEvent], None],
    ) -> None:
        with self._lock:
            subs = self._handlers.get(event_type, [])
            try:
                subs.remove(handler)
            except ValueError:
                pass

    def emit(self, event: AgentEvent) -> int:
        """Emit an event. Returns number of handlers called."""
        with self._lock:
            handlers = list(self._handlers.get(event.event_type, []))
            self._event_count += 1

        called = 0
        for h in handlers:
            try:
                h(event)
                called += 1
            except Exception:
                pass  # never let a subscriber crash the emitter
        return called

    def emit_simple(
        self,
        event_type: AgentEventType,
        agent_id:   str = "",
        payload:    Optional[dict] = None,
    ) -> int:
        return self.emit(AgentEvent(
            event_type = event_type,
            agent_id   = agent_id,
            payload    = payload or {},
        ))

    @property
    def event_count(self) -> int:
        return self._event_count

    def stats(self) -> dict:
        with self._lock:
            return {
                "event_count":       self._event_count,
                "subscriber_count":  sum(len(v) for v in self._handlers.values()),
                "subscribed_types":  [et.value for et in self._handlers],
            }

    def clear(self) -> None:
        with self._lock:
            self._handlers.clear()


# ── Singleton ─────────────────────────────────────────────────────────────────

_bus_lock = threading.Lock()
_bus_inst: Optional[AgentEventBus] = None


def get_agent_event_bus() -> AgentEventBus:
    global _bus_inst
    if _bus_inst is None:
        with _bus_lock:
            if _bus_inst is None:
                _bus_inst = AgentEventBus()
    return _bus_inst


def reset_agent_event_bus() -> None:
    global _bus_inst
    with _bus_lock:
        _bus_inst = None
