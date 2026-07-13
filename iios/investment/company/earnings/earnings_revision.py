"""iios/investment/company/earnings/earnings_revision.py
Tracks revisions to REPORTED earnings (restatements), not analyst estimates.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class EarningsRevisionEvent:
    ticker:        str
    period_label:  str
    field:         str            # e.g. "diluted_eps", "net_income"
    old_value:     Optional[float]
    new_value:     Optional[float]
    revision_pct:  Optional[float]  # % change (None if sign flip)
    direction:     str            # "upward" | "downward" | "sign_change"
    detected_at:   float = field(default_factory=time.time)
    note:          str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker":        self.ticker,
            "period_label":  self.period_label,
            "field":         self.field,
            "old_value":     self.old_value,
            "new_value":     self.new_value,
            "revision_pct":  self.revision_pct,
            "direction":     self.direction,
            "detected_at":   self.detected_at,
            "note":          self.note,
        }


class EarningsRevisionTracker:
    """Detects and records revisions when reported earnings are restated."""

    _MATERIALITY_THRESHOLD = 1.0   # % change that qualifies as a revision

    def __init__(self, max_events: int = 100) -> None:
        self._lock:   threading.RLock = threading.RLock()
        self._events: Dict[str, List[EarningsRevisionEvent]] = defaultdict(list)
        self._max    = max_events

    def detect(
        self,
        ticker:       str,
        period_label: str,
        old_report,   # EarningsReport
        new_report,   # EarningsReport
        tracked_fields: Optional[List[str]] = None,
    ) -> List[EarningsRevisionEvent]:
        """Compare old vs new EarningsReport; record material differences."""
        fields = tracked_fields or [
            "basic_eps", "diluted_eps", "net_income",
            "net_income_to_common", "revenue", "ebit", "ebitda",
        ]
        recorded: List[EarningsRevisionEvent] = []
        for f in fields:
            old = getattr(old_report, f, None)
            new = getattr(new_report, f, None)
            if old is None or new is None:
                continue
            if old == new:
                continue

            # Determine direction and magnitude
            if old == 0:
                rev_pct   = None
                direction = "sign_change" if new < 0 else "upward"
            else:
                rev_pct   = (new - old) / abs(old) * 100
                if abs(rev_pct) < self._MATERIALITY_THRESHOLD:
                    continue
                direction = "upward" if rev_pct > 0 else "downward"
                if (old > 0) != (new > 0):
                    direction = "sign_change"

            event = EarningsRevisionEvent(
                ticker=ticker,
                period_label=period_label,
                field=f,
                old_value=old,
                new_value=new,
                revision_pct=rev_pct,
                direction=direction,
            )
            self._record(event)
            recorded.append(event)
        return recorded

    def get_events(self, ticker: str, n: int = 20) -> List[EarningsRevisionEvent]:
        with self._lock:
            return list(self._events.get(ticker, []))[-n:]

    def revision_count(self, ticker: str) -> int:
        with self._lock:
            return len(self._events.get(ticker, []))

    def upward_revisions(self, ticker: str) -> int:
        with self._lock:
            return sum(1 for e in self._events.get(ticker, []) if e.direction == "upward")

    def downward_revisions(self, ticker: str) -> int:
        with self._lock:
            return sum(1 for e in self._events.get(ticker, []) if e.direction == "downward")

    def revision_bias(self, ticker: str) -> Optional[float]:
        """Positive = more upward revisions; negative = more downward. Range -1 to 1."""
        up   = self.upward_revisions(ticker)
        down = self.downward_revisions(ticker)
        total = up + down
        if total == 0:
            return None
        return (up - down) / total

    def summary(self, ticker: str) -> Dict[str, Any]:
        events = self.get_events(ticker)
        return {
            "ticker":              ticker,
            "total_revisions":     len(events),
            "upward_revisions":    sum(1 for e in events if e.direction == "upward"),
            "downward_revisions":  sum(1 for e in events if e.direction == "downward"),
            "sign_changes":        sum(1 for e in events if e.direction == "sign_change"),
            "revision_bias":       self.revision_bias(ticker),
            "recent_events":       [e.to_dict() for e in events[-5:]],
        }

    def _record(self, event: EarningsRevisionEvent) -> None:
        with self._lock:
            history = self._events[event.ticker]
            history.append(event)
            if len(history) > self._max:
                history.pop(0)
