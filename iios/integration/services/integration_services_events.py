"""
integration_services_events.py — iios.integration.services
------------------------------------------------------------
IntegrationServicesEventBus — publishes 10 typed lifecycle events
for the Integration Services layer.

C15 Enterprise Integration & Connectivity — Phase 1, Module 4
"""
from __future__ import annotations

import threading
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Deque, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import ServiceEventType

_log = get_logger(__name__)

EventHandler = Callable[["ServiceEvent"], None]


@dataclass(frozen=True)
class ServiceEvent:
    """An immutable service lifecycle event."""
    event_id:    str
    event_type:  ServiceEventType
    source:      str
    payload:     Dict[str, Any]
    created_at:  str

    @classmethod
    def create(
        cls,
        event_type: ServiceEventType,
        source:     str,
        payload:    Optional[Dict[str, Any]] = None,
    ) -> "ServiceEvent":
        return cls(
            event_id   = f"sevnt-{uuid.uuid4().hex[:12]}",
            event_type = event_type,
            source     = source,
            payload    = payload or {},
            created_at = datetime.now(timezone.utc).isoformat(),
        )


class IntegrationServicesEventBus:
    """
    Thread-safe event bus for all 10 ServiceEventType events.

    Maintains a bounded audit deque. Handler exceptions are caught and
    logged — they never propagate to the publisher.
    """

    def __init__(self, max_history: int = 1_000) -> None:
        self._lock        = threading.Lock()
        self._handlers:   Dict[ServiceEventType, List[EventHandler]] = defaultdict(list)
        self._history:    Deque[ServiceEvent] = deque(maxlen=max_history)
        self._published   = 0
        self._errors      = 0

    # ── Subscribe ────────────────────────────────────────────────────────

    def subscribe(
        self,
        event_type: ServiceEventType,
        handler:    EventHandler,
    ) -> None:
        with self._lock:
            self._handlers[event_type].append(handler)

    def unsubscribe(
        self,
        event_type: ServiceEventType,
        handler:    EventHandler,
    ) -> bool:
        with self._lock:
            lst = self._handlers.get(event_type, [])
            if handler in lst:
                lst.remove(handler)
                return True
        return False

    # ── Publish ──────────────────────────────────────────────────────────

    def publish(self, event: ServiceEvent) -> int:
        """
        Publish a ServiceEvent. Returns delivered handler count.
        Exceptions in handlers are caught and not re-raised.
        """
        with self._lock:
            handlers = list(self._handlers.get(event.event_type, []))
            self._history.append(event)
            self._published += 1

        delivered = 0
        for h in handlers:
            try:
                h(event)
                delivered += 1
            except Exception as exc:
                _log.debug(
                    f"services-event-bus handler error "
                    f"event_type={event.event_type.value!r}: {exc}"
                )
                with self._lock:
                    self._errors += 1

        return delivered

    def emit(
        self,
        event_type: ServiceEventType,
        source:     str,
        payload:    Optional[Dict[str, Any]] = None,
    ) -> int:
        """Convenience: create a ServiceEvent and publish it."""
        return self.publish(ServiceEvent.create(event_type, source, payload))

    # ── Query ─────────────────────────────────────────────────────────────

    def history(self, n: int = 50) -> List[ServiceEvent]:
        with self._lock:
            items = list(self._history)
        return items[-n:]

    def history_by_type(
        self, event_type: ServiceEventType
    ) -> List[ServiceEvent]:
        with self._lock:
            return [e for e in self._history if e.event_type == event_type]

    @property
    def stats(self) -> Dict[str, int]:
        with self._lock:
            return {
                "published":   self._published,
                "errors":      self._errors,
                "subscribers": sum(len(v) for v in self._handlers.values()),
                "history_size": len(self._history),
            }
