"""iios/investment/company/profile/timeline.py
Ordered corporate event timeline — higher-level view over CorporateEventStore.
"""
from __future__ import annotations

from typing import List, Optional

from iios.investment.company.profile.corporate_events import CorporateEventStore
from iios.investment.company.profile.models import CorporateEvent, CorporateEventType


class Timeline:
    """Chronological corporate event timeline for one company."""

    def __init__(self) -> None:
        self._store = CorporateEventStore()

    def add_event(self, event: CorporateEvent) -> None:
        self._store.add(event)

    def add(
        self,
        event_type:  CorporateEventType,
        date:        str,
        description: str,
        **details,
    ) -> CorporateEvent:
        event = CorporateEvent.new(event_type, date, description, details or None)
        self._store.add(event)
        return event

    def events(self) -> List[CorporateEvent]:
        return self._store.all()

    def founding_year(self) -> Optional[int]:
        ev = self._store.founding_event()
        if ev:
            try:
                return int(ev.date[:4])
            except (ValueError, IndexError):
                pass
        return None

    def ipo_year(self) -> Optional[int]:
        ev = self._store.ipo_event()
        if ev:
            try:
                return int(ev.date[:4])
            except (ValueError, IndexError):
                pass
        return None

    def age_years(self, reference_year: int) -> Optional[int]:
        fy = self.founding_year()
        if fy:
            return reference_year - fy
        return None

    def milestones(self) -> List[CorporateEvent]:
        return self._store.by_type(CorporateEventType.MILESTONE)

    def acquisitions(self) -> List[CorporateEvent]:
        return self._store.by_type(CorporateEventType.ACQUISITION)

    def spinoffs(self) -> List[CorporateEvent]:
        return self._store.by_type(CorporateEventType.SPINOFF)

    def name_changes(self) -> List[CorporateEvent]:
        return self._store.by_type(CorporateEventType.NAME_CHANGE)

    def __len__(self) -> int:
        return len(self._store)

    def summary(self) -> str:
        total     = len(self._store)
        fy        = self.founding_year()
        ipo_y     = self.ipo_year()
        acq_count = len(self.acquisitions())
        parts     = [f"{total} events"]
        if fy:
            parts.append(f"founded {fy}")
        if ipo_y:
            parts.append(f"IPO {ipo_y}")
        if acq_count:
            parts.append(f"{acq_count} acquisitions")
        return " | ".join(parts)
