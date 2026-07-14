"""iios/investment/strategy/integration/integration_events.py
Event bus for the Strategy Intelligence Integration Engine.
"""
from __future__ import annotations

import threading
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from iios.investment.strategy.integration.integration_constants import IntegrationEventType


@dataclass(frozen=True)
class IntegrationEvent:
    event_id:    str
    event_type:  IntegrationEventType
    strategy_id: str
    payload:     Dict[str, Any]
    occurred_at: datetime
    source:      str = "system"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":    self.event_id,
            "event_type":  self.event_type.value,
            "strategy_id": self.strategy_id,
            "payload":     self.payload,
            "occurred_at": self.occurred_at.isoformat(),
            "source":      self.source,
        }


def _make_event(
    event_type:  IntegrationEventType,
    strategy_id: str,
    payload:     Optional[Dict[str, Any]] = None,
    source:      str = "system",
) -> IntegrationEvent:
    return IntegrationEvent(
        event_id=str(uuid.uuid4()),
        event_type=event_type,
        strategy_id=strategy_id,
        payload=payload or {},
        occurred_at=datetime.now(timezone.utc),
        source=source,
    )


_Handler = Callable[[IntegrationEvent], None]


class IntegrationEventBus:
    """Thread-safe event bus with a 10 000-event ring buffer."""

    _RING_SIZE = 10_000

    def __init__(self) -> None:
        self._lock:     threading.Lock                              = threading.Lock()
        self._handlers: Dict[Optional[IntegrationEventType], List[_Handler]] = {}
        self._history:  deque[IntegrationEvent]                    = deque(maxlen=self._RING_SIZE)

    def subscribe(
        self,
        handler:    _Handler,
        event_type: Optional[IntegrationEventType] = None,
    ) -> None:
        with self._lock:
            bucket = self._handlers.setdefault(event_type, [])
            if handler not in bucket:
                bucket.append(handler)

    def unsubscribe(
        self,
        handler:    _Handler,
        event_type: Optional[IntegrationEventType] = None,
    ) -> None:
        with self._lock:
            bucket = self._handlers.get(event_type, [])
            if handler in bucket:
                bucket.remove(handler)

    def emit(self, event: IntegrationEvent) -> None:
        with self._lock:
            self._history.append(event)
            handlers = (
                list(self._handlers.get(event.event_type, []))
                + list(self._handlers.get(None, []))
            )
        for h in handlers:
            try:
                h(event)
            except Exception:
                pass

    def emit_simple(
        self,
        event_type:  IntegrationEventType,
        strategy_id: str,
        payload:     Optional[Dict[str, Any]] = None,
        source:      str = "system",
    ) -> IntegrationEvent:
        event = _make_event(event_type, strategy_id, payload, source)
        self.emit(event)
        return event

    def history(
        self,
        strategy_id: Optional[str] = None,
        event_type:  Optional[IntegrationEventType] = None,
    ) -> List[IntegrationEvent]:
        with self._lock:
            events = list(self._history)
        if strategy_id:
            events = [e for e in events if e.strategy_id == strategy_id]
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return events

    def count(self) -> int:
        with self._lock:
            return len(self._history)
