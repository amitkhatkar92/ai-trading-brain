"""
integration_gateway_events.py — iios.integration.gateway
----------------------------------------------------------
GatewayEvent and IntegrationGatewayEventBus.

Thread-safe publish/subscribe event bus with bounded history.

C15 Enterprise Integration & Connectivity — Phase 1, Module 6
"""
from __future__ import annotations

import threading
import uuid
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import (
    DEFAULT_MAX_HISTORY,
    EVENT_ID_PREFIX,
    GatewayEventType,
)

_log = get_logger(__name__)


@dataclass(frozen=True)
class GatewayEvent:
    """Immutable event emitted by the Enterprise Integration Gateway."""

    event_id:   str
    event_type: GatewayEventType
    gateway_id: str
    request_id: str
    source:     str
    payload:    Dict[str, Any]
    occurred_at: str

    @classmethod
    def create(
        cls,
        event_type: GatewayEventType,
        gateway_id: str,
        request_id: str,
        source:     str,
        payload:    Optional[Dict[str, Any]] = None,
        *,
        event_id:   Optional[str]            = None,
    ) -> "GatewayEvent":
        return cls(
            event_id    = event_id or f"{EVENT_ID_PREFIX}{uuid.uuid4().hex[:12]}",
            event_type  = event_type,
            gateway_id  = gateway_id,
            request_id  = request_id,
            source      = source,
            payload     = dict(payload or {}),
            occurred_at = datetime.now(timezone.utc).isoformat(),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":    self.event_id,
            "event_type":  self.event_type.value,
            "gateway_id":  self.gateway_id,
            "request_id":  self.request_id,
            "source":      self.source,
            "payload":     dict(self.payload),
            "occurred_at": self.occurred_at,
        }


# ─── type alias ──────────────────────────────────────────────────────────────
_Handler = Callable[[GatewayEvent], None]


class IntegrationGatewayEventBus:
    """
    Thread-safe publish/subscribe event bus for gateway events.

    Supports per-event-type subscription, history with configurable
    bound, and silent handler exception suppression.
    """

    def __init__(self, max_history: int = DEFAULT_MAX_HISTORY) -> None:
        self._handlers: Dict[GatewayEventType, List[_Handler]] = {
            et: [] for et in GatewayEventType
        }
        self._history: deque[GatewayEvent] = deque(maxlen=max_history)
        self._stats:   Dict[str, int]       = {
            "published":        0,
            "failed_handlers":  0,
            "history_size":     0,
        }
        self._lock = threading.Lock()

    # ─── subscription ─────────────────────────────────────────────────

    def subscribe(self, event_type: GatewayEventType, handler: _Handler) -> bool:
        """Register *handler* for *event_type*. Returns True if newly added."""
        with self._lock:
            if handler not in self._handlers[event_type]:
                self._handlers[event_type].append(handler)
                return True
            return False

    def unsubscribe(self, event_type: GatewayEventType, handler: _Handler) -> bool:
        """Remove *handler* for *event_type*. Returns True if removed."""
        with self._lock:
            try:
                self._handlers[event_type].remove(handler)
                return True
            except ValueError:
                return False

    # ─── publication ──────────────────────────────────────────────────

    def publish(self, event: GatewayEvent) -> int:
        """
        Deliver *event* to all subscribers for its type.

        Returns the number of handlers successfully invoked.
        Handler exceptions are suppressed and counted.
        """
        with self._lock:
            handlers = list(self._handlers[event.event_type])
            self._history.append(event)
            self._stats["published"] += 1
            self._stats["history_size"] = len(self._history)

        invoked = 0
        for handler in handlers:
            try:
                handler(event)
                invoked += 1
            except Exception as exc:
                with self._lock:
                    self._stats["failed_handlers"] += 1
                _log.info(
                    f"GatewayEventBus: handler error "
                    f"type={event.event_type.value!r} exc={exc!r}"
                )
        return invoked

    def emit(
        self,
        event_type: GatewayEventType,
        gateway_id: str,
        request_id: str,
        source:     str,
        payload:    Optional[Dict[str, Any]] = None,
    ) -> int:
        """Create and publish a typed event. Returns handler count."""
        event = GatewayEvent.create(event_type, gateway_id, request_id, source, payload)
        return self.publish(event)

    # ─── history ──────────────────────────────────────────────────────

    def history(self, n: Optional[int] = None) -> List[GatewayEvent]:
        """Return the most recent *n* events (or all if None)."""
        with self._lock:
            items = list(self._history)
        return items[-n:] if n is not None else items

    def history_by_type(self, event_type: GatewayEventType) -> List[GatewayEvent]:
        """Return all history events of the given type."""
        with self._lock:
            return [e for e in self._history if e.event_type == event_type]

    # ─── statistics ───────────────────────────────────────────────────

    @property
    def stats(self) -> Dict[str, int]:
        with self._lock:
            return dict(self._stats)

    def subscriber_count(self, event_type: GatewayEventType) -> int:
        with self._lock:
            return len(self._handlers[event_type])

    def clear_history(self) -> int:
        with self._lock:
            n = len(self._history)
            self._history.clear()
            self._stats["history_size"] = 0
            return n
