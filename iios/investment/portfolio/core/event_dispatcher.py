"""iios/investment/portfolio/core/event_dispatcher.py

Thread-safe publish-subscribe event dispatcher for the Institutional
Portfolio Framework.  Supports priority-ordered, type-filtered dispatch
with per-handler error isolation.
"""
from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Callable, Optional, Set, Type

from iios.investment.portfolio.core.portfolio_events import (
    EventPriority,
    PortfolioEvent,
    PortfolioEventType,
)
from iios.investment.portfolio.core.event_history import EventHistory

log = logging.getLogger(__name__)

# Handler signature: (event) → None
EventHandler = Callable[[PortfolioEvent], None]

_PRIORITY_ORDER: dict[EventPriority, int] = {
    EventPriority.CRITICAL: 0,
    EventPriority.NORMAL:   1,
    EventPriority.LOW:      2,
}


@dataclass
class _HandlerRegistration:
    """Internal registration entry for one event handler."""

    handler_id:   str
    handler:      EventHandler
    event_types:  frozenset           # frozenset[PortfolioEventType] | empty = all
    portfolio_ids:frozenset           # frozenset[str] | empty = all
    priority:     EventPriority
    name:         str


class EventDispatcher:
    """
    Central dispatcher for all portfolio framework events.

    Features:
    - Subscribe with optional type and portfolio_id filters
    - Priority-ordered dispatch (CRITICAL before NORMAL before LOW)
    - Per-handler error isolation (one failure never blocks others)
    - Integrated EventHistory for audit
    - Thread-safe
    """

    def __init__(self, history: Optional[EventHistory] = None) -> None:
        self._lock:     threading.RLock                          = threading.RLock()
        self._handlers: dict[str, _HandlerRegistration]          = {}
        self._history:  EventHistory                             = history or EventHistory()

    # ------------------------------------------------------------------
    # Subscription management
    # ------------------------------------------------------------------

    def subscribe(
        self,
        handler:       EventHandler,
        *,
        event_types:   Optional[Set[PortfolioEventType]] = None,
        portfolio_ids: Optional[Set[str]]                = None,
        priority:      EventPriority                     = EventPriority.NORMAL,
        name:          str                               = "",
    ) -> str:
        """
        Register a handler.  Returns the handler_id.

        Args:
            handler:       Callable that receives a PortfolioEvent.
            event_types:   If provided, only receives these event types.
            portfolio_ids: If provided, only receives events for these portfolios.
            priority:      Dispatch order (CRITICAL first).
            name:          Human-readable label for diagnostics.
        """
        handler_id = str(uuid.uuid4())
        reg = _HandlerRegistration(
            handler_id    = handler_id,
            handler       = handler,
            event_types   = frozenset(event_types)   if event_types   else frozenset(),
            portfolio_ids = frozenset(portfolio_ids) if portfolio_ids else frozenset(),
            priority      = priority,
            name          = name or handler.__name__ if hasattr(handler, "__name__") else "anonymous",
        )
        with self._lock:
            self._handlers[handler_id] = reg
        return handler_id

    def unsubscribe(self, handler_id: str) -> bool:
        """Remove a handler by its handler_id. Returns True if found."""
        with self._lock:
            if handler_id in self._handlers:
                del self._handlers[handler_id]
                return True
            return False

    def subscription_count(self) -> int:
        with self._lock:
            return len(self._handlers)

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def dispatch(self, event: PortfolioEvent) -> int:
        """
        Dispatch an event to all matching handlers.
        Returns the count of handlers that received the event.
        Errors in individual handlers are caught and logged.
        """
        t0 = time.time()

        # Snapshot handlers to avoid holding lock during dispatch
        with self._lock:
            handlers = sorted(
                self._handlers.values(),
                key=lambda r: _PRIORITY_ORDER.get(r.priority, 99),
            )

        called_count  = 0
        failed_count  = 0

        for reg in handlers:
            if not self._matches(reg, event):
                continue
            try:
                reg.handler(event)
                called_count += 1
            except Exception as exc:
                failed_count += 1
                log.error(
                    "Handler %s (%s) failed for event %s: %s",
                    reg.handler_id[:8], reg.name, event.event_type.value, exc,
                )

        duration_ms = (time.time() - t0) * 1_000
        self._history.record(
            event,
            handler_count = called_count,
            failed_count  = failed_count,
            duration_ms   = duration_ms,
        )
        return called_count

    def dispatch_many(self, events: list[PortfolioEvent]) -> int:
        """Dispatch a list of events; returns total handler calls."""
        return sum(self.dispatch(e) for e in events)

    # ------------------------------------------------------------------
    # History access
    # ------------------------------------------------------------------

    @property
    def history(self) -> EventHistory:
        return self._history

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _matches(reg: _HandlerRegistration, event: PortfolioEvent) -> bool:
        if reg.event_types and event.event_type not in reg.event_types:
            return False
        if reg.portfolio_ids and event.portfolio_id not in reg.portfolio_ids:
            return False
        return True
