"""iios/investment/strategy/debate/debate_events.py
Event bus for streaming debate lifecycle events.
"""
from __future__ import annotations

import threading
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from iios.investment.strategy.debate.debate_constants import DebateEventType


@dataclass(frozen=True)
class DebateEvent:
    event_id:    str
    event_type:  DebateEventType
    session_id:  str
    payload:     Dict[str, Any]
    occurred_at: datetime
    source:      str = "system"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":    self.event_id,
            "event_type":  self.event_type.value,
            "session_id":  self.session_id,
            "payload":     self.payload,
            "occurred_at": self.occurred_at.isoformat(),
            "source":      self.source,
        }


def _make_event(
    event_type: DebateEventType,
    session_id: str,
    payload:    Optional[Dict[str, Any]] = None,
    source:     str = "system",
) -> DebateEvent:
    return DebateEvent(
        event_id=str(uuid.uuid4()),
        event_type=event_type,
        session_id=session_id,
        payload=payload or {},
        occurred_at=datetime.now(timezone.utc),
        source=source,
    )


_Handler = Callable[[DebateEvent], None]


class DebateEventBus:
    """Thread-safe pub/sub event bus with a rolling ring buffer of 10 000 events."""

    _RING_SIZE = 10_000

    def __init__(self) -> None:
        self._lock:      threading.Lock              = threading.Lock()
        self._handlers:  Dict[Optional[DebateEventType], List[_Handler]] = {}
        self._history:   deque[DebateEvent]          = deque(maxlen=self._RING_SIZE)

    def subscribe(
        self,
        handler:    _Handler,
        event_type: Optional[DebateEventType] = None,
    ) -> None:
        with self._lock:
            bucket = self._handlers.setdefault(event_type, [])
            if handler not in bucket:
                bucket.append(handler)

    def unsubscribe(
        self,
        handler:    _Handler,
        event_type: Optional[DebateEventType] = None,
    ) -> None:
        with self._lock:
            bucket = self._handlers.get(event_type, [])
            if handler in bucket:
                bucket.remove(handler)

    def emit(self, event: DebateEvent) -> None:
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
        event_type: DebateEventType,
        session_id: str,
        payload:    Optional[Dict[str, Any]] = None,
        source:     str = "system",
    ) -> DebateEvent:
        event = _make_event(event_type, session_id, payload, source)
        self.emit(event)
        return event

    def history(
        self,
        session_id: Optional[str] = None,
        event_type: Optional[DebateEventType] = None,
    ) -> List[DebateEvent]:
        with self._lock:
            events = list(self._history)
        if session_id:
            events = [e for e in events if e.session_id == session_id]
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return events

    def count(self) -> int:
        with self._lock:
            return len(self._history)
