"""iios/investment/decision/core/decision_events.py
DecisionEvent — immutable event record + EventDispatcher + EventHistory.
Covers Tasks 4 and 7 (decision lifecycle events + event bus).
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from iios.investment.decision.core.decision_constants import DecisionEventType


# ---------------------------------------------------------------------------
# Event record
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DecisionEvent:
    event_id:    str
    event_type:  DecisionEventType
    decision_id: str
    payload:     Dict[str, Any]
    occurred_at: datetime
    source:      str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":    self.event_id,
            "event_type":  self.event_type.value,
            "decision_id": self.decision_id,
            "payload":     self.payload,
            "occurred_at": self.occurred_at.isoformat(),
            "source":      self.source,
        }


def make_event(
    event_type:  DecisionEventType,
    decision_id: str,
    payload:     Optional[Dict[str, Any]] = None,
    source:      str                      = "framework",
) -> DecisionEvent:
    return DecisionEvent(
        event_id=str(uuid.uuid4()),
        event_type=event_type,
        decision_id=decision_id,
        payload=payload or {},
        occurred_at=datetime.now(timezone.utc),
        source=source,
    )


# ---------------------------------------------------------------------------
# Event dispatcher
# ---------------------------------------------------------------------------

class EventDispatcher:
    """
    Thread-safe publish/subscribe event bus.
    Subscribers receive all events unless filtered by event_type.
    Ring buffer of max_history events is kept for replay/audit.
    """

    def __init__(self, max_history: int = 10_000) -> None:
        self._lock:       threading.RLock                           = threading.RLock()
        self._handlers:   Dict[str, Callable[[DecisionEvent], None]] = {}  # handle_id → callable
        self._type_filter: Dict[str, Optional[DecisionEventType]]    = {}  # handle_id → filter
        self._history:    List[DecisionEvent]                        = []
        self._max         = max_history

    def subscribe(
        self,
        handler:    Callable[[DecisionEvent], None],
        event_type: Optional[DecisionEventType] = None,
    ) -> str:
        """Register a handler. Returns a handle_id for unsubscription."""
        handle_id = str(uuid.uuid4())
        with self._lock:
            self._handlers[handle_id]    = handler
            self._type_filter[handle_id] = event_type
        return handle_id

    def unsubscribe(self, handle_id: str) -> None:
        with self._lock:
            self._handlers.pop(handle_id, None)
            self._type_filter.pop(handle_id, None)

    def dispatch(self, event: DecisionEvent) -> None:
        with self._lock:
            if len(self._history) >= self._max:
                self._history.pop(0)
            self._history.append(event)
            handlers = list(self._handlers.items())
            filters  = dict(self._type_filter)

        for hid, handler in handlers:
            filt = filters.get(hid)
            if filt is None or filt == event.event_type:
                try:
                    handler(event)
                except Exception:
                    pass  # never crash the caller due to a bad subscriber

    def dispatch_simple(
        self,
        event_type:  DecisionEventType,
        decision_id: str,
        payload:     Optional[Dict[str, Any]] = None,
        source:      str                      = "framework",
    ) -> None:
        self.dispatch(make_event(event_type, decision_id, payload, source))

    def history(
        self,
        decision_id: Optional[str]              = None,
        event_type:  Optional[DecisionEventType] = None,
        limit:       int                         = 100,
    ) -> List[DecisionEvent]:
        with self._lock:
            results = list(self._history)
        if decision_id:
            results = [e for e in results if e.decision_id == decision_id]
        if event_type:
            results = [e for e in results if e.event_type == event_type]
        return results[-limit:]

    def count(self) -> int:
        with self._lock:
            return len(self._history)


# ---------------------------------------------------------------------------
# Dedicated EventHistory store (append-only, thread-safe)
# ---------------------------------------------------------------------------

class EventHistory:
    """Append-only ring store — separate from the dispatcher's in-memory ring."""

    def __init__(self, max_size: int = 100_000) -> None:
        self._lock:  threading.RLock     = threading.RLock()
        self._store: List[DecisionEvent] = []
        self._max    = max_size

    def record(self, event: DecisionEvent) -> None:
        with self._lock:
            if len(self._store) >= self._max:
                self._store.pop(0)
            self._store.append(event)

    def for_decision(self, decision_id: str) -> List[DecisionEvent]:
        with self._lock:
            return [e for e in self._store if e.decision_id == decision_id]

    def by_type(self, event_type: DecisionEventType) -> List[DecisionEvent]:
        with self._lock:
            return [e for e in self._store if e.event_type == event_type]

    def recent(self, n: int = 100) -> List[DecisionEvent]:
        with self._lock:
            return self._store[-n:]

    def count(self) -> int:
        with self._lock:
            return len(self._store)
