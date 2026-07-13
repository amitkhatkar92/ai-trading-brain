"""iios/investment/company/financials/restatement_tracker.py
Tracks financial statement restatements and revisions per company.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RestatementEvent:
    ticker:       str
    period_label: str
    version_from: int
    version_to:   int
    reason:       str
    detected_at:  float = field(default_factory=time.time)
    fields_changed: List[str] = field(default_factory=list)
    magnitude_pct:  Optional[float] = None   # max % change across restated fields

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker":          self.ticker,
            "period_label":    self.period_label,
            "version_from":    self.version_from,
            "version_to":      self.version_to,
            "reason":          self.reason,
            "detected_at":     self.detected_at,
            "fields_changed":  self.fields_changed,
            "magnitude_pct":   self.magnitude_pct,
        }


class RestatementTracker:
    """Thread-safe log of restatement events per company."""

    def __init__(self, max_events_per_ticker: int = 50) -> None:
        self._lock:  threading.RLock = threading.RLock()
        self._events: Dict[str, List[RestatementEvent]] = defaultdict(list)
        self._max    = max_events_per_ticker

    def record(self, event: RestatementEvent) -> None:
        with self._lock:
            history = self._events[event.ticker]
            history.append(event)
            if len(history) > self._max:
                history.pop(0)

    def get_events(self, ticker: str) -> List[RestatementEvent]:
        with self._lock:
            return list(self._events.get(ticker, []))

    def restatement_count(self, ticker: str) -> int:
        with self._lock:
            return len(self._events.get(ticker, []))

    def was_restated(self, ticker: str, period_label: str) -> bool:
        with self._lock:
            return any(
                e.period_label == period_label
                for e in self._events.get(ticker, [])
            )

    def detect_and_record(
        self,
        ticker:       str,
        period_label: str,
        old_values:   Dict[str, Optional[float]],
        new_values:   Dict[str, Optional[float]],
        version_from: int,
        version_to:   int,
        reason:       str = "data_revision",
    ) -> Optional[RestatementEvent]:
        """Compare old vs new values and record if material change detected (>1% on any key field)."""
        changed:    List[str]   = []
        max_change: float       = 0.0
        for k, old in old_values.items():
            new = new_values.get(k)
            if old is None or new is None:
                continue
            if old == 0:
                continue
            change = abs(new - old) / abs(old) * 100.0
            if change > 1.0:
                changed.append(k)
                max_change = max(max_change, change)

        if not changed:
            return None

        event = RestatementEvent(
            ticker=ticker,
            period_label=period_label,
            version_from=version_from,
            version_to=version_to,
            reason=reason,
            fields_changed=changed,
            magnitude_pct=round(max_change, 2),
        )
        self.record(event)
        return event

    def summary(self, ticker: str) -> Dict[str, Any]:
        events = self.get_events(ticker)
        return {
            "ticker":             ticker,
            "total_restatements": len(events),
            "periods_restated":   list({e.period_label for e in events}),
            "events":             [e.to_dict() for e in events[-10:]],  # last 10
        }
