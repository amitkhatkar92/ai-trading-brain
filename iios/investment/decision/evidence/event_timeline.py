"""iios/investment/decision/evidence/event_timeline.py
EventTimeline — ordered, immutable timeline of evidence events for a decision.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.decision.evidence.evidence_constants import EvidenceEventType


@dataclass(frozen=True)
class TimelineEvent:
    event_id:   str
    event_type: EvidenceEventType
    decision_id: str
    occurred_at: datetime
    details:    Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":   self.event_id,
            "event_type": self.event_type.value,
            "decision_id": self.decision_id,
            "occurred_at": self.occurred_at.isoformat(),
            "details":    self.details,
        }


class EventTimeline:
    """Thread-safe ordered timeline of evidence events."""

    def __init__(self, max_size: int = 10_000) -> None:
        self._lock:   threading.RLock       = threading.RLock()
        self._events: List[TimelineEvent]   = []
        self._max     = max_size

    def record(self, event: TimelineEvent) -> None:
        with self._lock:
            if len(self._events) >= self._max:
                self._events.pop(0)
            self._events.append(event)

    def record_simple(
        self,
        event_type:  EvidenceEventType,
        decision_id: str,
        details:     Optional[Dict[str, Any]] = None,
    ) -> TimelineEvent:
        import uuid
        event = TimelineEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            decision_id=decision_id,
            occurred_at=datetime.now(timezone.utc),
            details=details or {},
        )
        self.record(event)
        return event

    def for_decision(self, decision_id: str) -> List[TimelineEvent]:
        with self._lock:
            return [e for e in self._events if e.decision_id == decision_id]

    def by_type(self, event_type: EvidenceEventType) -> List[TimelineEvent]:
        with self._lock:
            return [e for e in self._events if e.event_type == event_type]

    def recent(self, n: int = 50) -> List[TimelineEvent]:
        with self._lock:
            return self._events[-n:]

    def count(self) -> int:
        with self._lock:
            return len(self._events)

    def all_events(self) -> List[TimelineEvent]:
        with self._lock:
            return list(self._events)
