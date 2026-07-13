"""iios/investment/strategy/opportunity/opportunity_event.py
OpportunityEvent — immutable event published by the Opportunity Engine.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List


class EventType(str, Enum):
    OPPORTUNITY_DISCOVERED    = "opportunity_discovered"
    OPPORTUNITY_MATCHED       = "opportunity_matched"
    OPPORTUNITY_RANKED        = "opportunity_ranked"
    RECOMMENDATION_GENERATED  = "recommendation_generated"
    STATE_CHANGED             = "state_changed"
    OPPORTUNITY_EXPIRED       = "opportunity_expired"
    OPPORTUNITY_ARCHIVED      = "opportunity_archived"
    ALERT_RAISED              = "alert_raised"
    MONITORING_TRIGGERED      = "monitoring_triggered"
    CHANGE_DETECTED           = "change_detected"


@dataclass(frozen=True)
class OpportunityEvent:
    """Published whenever a significant event occurs in the Opportunity Engine."""
    event_id:       str
    event_type:     EventType
    opportunity_id: str
    strategy_id:    str
    occurred_at:    datetime
    payload:        Dict[str, Any] = field(default_factory=dict)
    source:         str = "opportunity_engine"

    @classmethod
    def create(
        cls,
        event_type: EventType,
        opportunity_id: str,
        strategy_id: str,
        payload: Dict[str, Any] | None = None,
    ) -> "OpportunityEvent":
        return cls(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            opportunity_id=opportunity_id,
            strategy_id=strategy_id,
            occurred_at=datetime.now(timezone.utc),
            payload=payload or {},
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":       self.event_id,
            "event_type":     self.event_type.value,
            "opportunity_id": self.opportunity_id,
            "strategy_id":    self.strategy_id,
            "occurred_at":    self.occurred_at.isoformat(),
            "payload":        self.payload,
            "source":         self.source,
        }


EventListener = Callable[[OpportunityEvent], None]


class EventBus:
    """Lightweight synchronous in-process event bus for the Opportunity Engine."""

    def __init__(self) -> None:
        self._listeners: Dict[EventType | None, List[EventListener]] = {}

    def subscribe(
        self,
        listener: EventListener,
        event_type: EventType | None = None,
    ) -> None:
        """Subscribe to a specific event type, or None to receive all events."""
        self._listeners.setdefault(event_type, []).append(listener)

    def publish(self, event: OpportunityEvent) -> None:
        for listener in self._listeners.get(event.event_type, []):
            try:
                listener(event)
            except Exception:
                pass
        for listener in self._listeners.get(None, []):
            try:
                listener(event)
            except Exception:
                pass
