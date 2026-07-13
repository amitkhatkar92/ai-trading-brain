"""iios/investment/strategy/core/event_dispatcher.py
Synchronous publish-subscribe event dispatcher for institutional strategies.
"""
from __future__ import annotations

import logging
import threading
from typing import Callable, Dict, List, Optional

from .event_history import EventHistory
from .strategy_events import StrategyEvent, StrategyEventType

logger = logging.getLogger(__name__)

Handler = Callable[[StrategyEvent], None]


class EventDispatcher:
    """
    Thread-safe synchronous event bus.
    Handlers are called inline in the publishing thread in registration order.
    Handler exceptions are logged and suppressed to protect the caller.
    """

    def __init__(self, history: Optional[EventHistory] = None) -> None:
        self._lock = threading.RLock()
        self._handlers: Dict[StrategyEventType, List[Handler]] = {}
        self._global_handlers: List[Handler] = []
        self._history = history or EventHistory()

    def subscribe(
        self,
        handler: Handler,
        event_types: Optional[List[StrategyEventType]] = None,
    ) -> None:
        """Subscribe to specific event types, or all events if event_types is None."""
        with self._lock:
            if event_types is None:
                self._global_handlers.append(handler)
            else:
                for et in event_types:
                    self._handlers.setdefault(et, []).append(handler)

    def unsubscribe(
        self,
        handler: Handler,
        event_types: Optional[List[StrategyEventType]] = None,
    ) -> None:
        with self._lock:
            if event_types is None:
                try:
                    self._global_handlers.remove(handler)
                except ValueError:
                    pass
            else:
                for et in event_types:
                    try:
                        self._handlers.get(et, []).remove(handler)
                    except ValueError:
                        pass

    def publish(self, event: StrategyEvent) -> None:
        """Persist event to history and call all matching handlers."""
        self._history.record(event)
        with self._lock:
            specific = list(self._handlers.get(event.event_type, []))
            global_ = list(self._global_handlers)

        for handler in specific + global_:
            try:
                handler(event)
            except Exception:
                logger.exception(
                    "Event handler %s raised on %s", handler, event.event_type.value
                )

    def emit(
        self,
        event_type: StrategyEventType,
        strategy_id: str,
        payload: Optional[dict] = None,
        session_id: Optional[str] = None,
        severity: str = "info",
    ) -> StrategyEvent:
        """Construct a StrategyEvent and publish it. Returns the event."""
        event = StrategyEvent(
            event_type=event_type,
            strategy_id=strategy_id,
            payload=payload or {},
            session_id=session_id,
            severity=severity,
        )
        self.publish(event)
        return event

    @property
    def history(self) -> EventHistory:
        return self._history
