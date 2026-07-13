"""iios/investment/strategy/portfolio/portfolio_events.py
Portfolio event types and event bus for the lifecycle and monitor subsystems.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class PortfolioEventType(str, Enum):
    CREATED      = "portfolio_created"
    OPTIMIZED    = "portfolio_optimized"
    APPROVED     = "portfolio_approved"
    ACTIVATED    = "portfolio_activated"
    REBALANCED   = "portfolio_rebalanced"
    PAUSED       = "portfolio_paused"
    ARCHIVED     = "portfolio_archived"
    STRATEGY_ADDED   = "strategy_added"
    STRATEGY_REMOVED = "strategy_removed"
    WEIGHT_UPDATED   = "weight_updated"
    HEALTH_ALERT     = "health_alert"
    REBALANCE_DUE    = "rebalance_due"
    SCORE_CHANGED    = "score_changed"


@dataclass(frozen=True)
class PortfolioEvent:
    event_id:     str
    event_type:   PortfolioEventType
    portfolio_id: str
    payload:      Dict[str, Any]
    emitted_at:   datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":     self.event_id,
            "event_type":   self.event_type.value,
            "portfolio_id": self.portfolio_id,
            "payload":      self.payload,
            "emitted_at":   self.emitted_at.isoformat(),
        }


PortfolioEventHandler = Callable[[PortfolioEvent], None]


class PortfolioEventBus:
    """
    Lightweight in-process event bus for portfolio events.
    Thread-safe.  Handlers are called synchronously on the emitter's thread.
    """

    def __init__(self) -> None:
        self._handlers: Dict[PortfolioEventType, List[PortfolioEventHandler]] = {}
        self._global:   List[PortfolioEventHandler] = []
        self._lock = threading.RLock()

    def subscribe(
        self,
        handler:    PortfolioEventHandler,
        event_type: Optional[PortfolioEventType] = None,
    ) -> None:
        with self._lock:
            if event_type is None:
                if handler not in self._global:
                    self._global.append(handler)
            else:
                self._handlers.setdefault(event_type, [])
                if handler not in self._handlers[event_type]:
                    self._handlers[event_type].append(handler)

    def unsubscribe(
        self,
        handler:    PortfolioEventHandler,
        event_type: Optional[PortfolioEventType] = None,
    ) -> None:
        with self._lock:
            if event_type is None:
                self._global = [h for h in self._global if h != handler]
            elif event_type in self._handlers:
                self._handlers[event_type] = [
                    h for h in self._handlers[event_type] if h != handler
                ]

    def emit(self, event: PortfolioEvent) -> None:
        with self._lock:
            handlers = list(self._global) + list(
                self._handlers.get(event.event_type, [])
            )
        for h in handlers:
            try:
                h(event)
            except Exception:
                pass
