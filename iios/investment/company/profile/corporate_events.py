"""iios/investment/company/profile/corporate_events.py
Corporate event management: IPO, mergers, acquisitions, restructurings, etc.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from iios.investment.company.profile.models import CorporateEvent, CorporateEventType


class CorporateEventStore:
    """Stores and queries corporate events for one company."""

    def __init__(self) -> None:
        self._events: List[CorporateEvent] = []

    def add(self, event: CorporateEvent) -> None:
        if not any(e.event_id == event.event_id for e in self._events):
            self._events.append(event)
            self._events.sort(key=lambda e: e.date)

    def remove(self, event_id: str) -> bool:
        before = len(self._events)
        self._events = [e for e in self._events if e.event_id != event_id]
        return len(self._events) < before

    def all(self) -> List[CorporateEvent]:
        return list(self._events)

    def by_type(self, event_type: CorporateEventType) -> List[CorporateEvent]:
        return [e for e in self._events if e.event_type is event_type]

    def between(self, from_date: str, to_date: str) -> List[CorporateEvent]:
        return [e for e in self._events if from_date <= e.date <= to_date]

    def latest(self, n: int = 5) -> List[CorporateEvent]:
        return list(reversed(self._events))[:n]

    def earliest(self) -> Optional[CorporateEvent]:
        return self._events[0] if self._events else None

    def most_recent(self) -> Optional[CorporateEvent]:
        return self._events[-1] if self._events else None

    def founding_event(self) -> Optional[CorporateEvent]:
        events = self.by_type(CorporateEventType.FOUNDING)
        return events[0] if events else None

    def ipo_event(self) -> Optional[CorporateEvent]:
        events = self.by_type(CorporateEventType.IPO)
        return events[0] if events else None

    def by_year(self) -> Dict[int, List[CorporateEvent]]:
        result: Dict[int, List[CorporateEvent]] = {}
        for e in self._events:
            try:
                year = int(e.date[:4])
                result.setdefault(year, []).append(e)
            except (ValueError, IndexError):
                pass
        return result

    def has_merger_or_acquisition(self) -> bool:
        return any(
            e.event_type in (CorporateEventType.MERGER, CorporateEventType.ACQUISITION)
            for e in self._events
        )

    def __len__(self) -> int:
        return len(self._events)
