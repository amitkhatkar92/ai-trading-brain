"""
iios/execution/analytics/predictive/predictive_history.py
=========================================================
PredictiveIntelligenceHistory — bounded history store for the
Predictive Intelligence Framework.

C8 Execution Analytics & Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import collections
import threading
from typing import Any, Deque, List

from .constants import DEFAULT_MAX_HISTORY


class PredictiveIntelligenceHistory:
    """
    Bounded history store for prediction reports, forecasts, and events.

    Thread-safe.  All collections bounded at DEFAULT_MAX_HISTORY entries.
    """

    def __init__(self, maxlen: int = DEFAULT_MAX_HISTORY) -> None:
        self._maxlen  = maxlen
        self._lock    = threading.Lock()
        self.reports:            Deque[Any] = collections.deque(maxlen=maxlen)
        self.forecasts:          Deque[Any] = collections.deque(maxlen=maxlen)
        self.probability_reports:Deque[Any] = collections.deque(maxlen=maxlen)
        self.capacity_forecasts: Deque[Any] = collections.deque(maxlen=maxlen)
        self.risk_forecasts:     Deque[Any] = collections.deque(maxlen=maxlen)
        self.operational_forecasts: Deque[Any] = collections.deque(maxlen=maxlen)
        self.events:             Deque[Any] = collections.deque(maxlen=maxlen)

    # ── Append methods ────────────────────────────────────────────────────────

    def add_report(self, report: Any) -> None:
        with self._lock:
            self.reports.append(report)

    def add_forecast(self, forecast: Any) -> None:
        with self._lock:
            self.forecasts.append(forecast)

    def add_probability_report(self, report: Any) -> None:
        with self._lock:
            self.probability_reports.append(report)

    def add_capacity_forecast(self, cf: Any) -> None:
        with self._lock:
            self.capacity_forecasts.append(cf)

    def add_risk_forecast(self, rf: Any) -> None:
        with self._lock:
            self.risk_forecasts.append(rf)

    def add_operational_forecast(self, of: Any) -> None:
        with self._lock:
            self.operational_forecasts.append(of)

    def add_event(self, event: Any) -> None:
        with self._lock:
            self.events.append(event)

    # ── Snapshot methods (copies) ─────────────────────────────────────────────

    def recent_reports(self, n: int = 10) -> List[Any]:
        with self._lock:
            items = list(self.reports)
        return items[-n:] if n > 0 else items

    def recent_forecasts(self, n: int = 10) -> List[Any]:
        with self._lock:
            items = list(self.forecasts)
        return items[-n:] if n > 0 else items

    def recent_events(self, n: int = 10) -> List[Any]:
        with self._lock:
            items = list(self.events)
        return items[-n:] if n > 0 else items

    def recent_risk_forecasts(self, n: int = 10) -> List[Any]:
        with self._lock:
            items = list(self.risk_forecasts)
        return items[-n:] if n > 0 else items

    def recent_capacity_forecasts(self, n: int = 10) -> List[Any]:
        with self._lock:
            items = list(self.capacity_forecasts)
        return items[-n:] if n > 0 else items

    # ── Inspection ────────────────────────────────────────────────────────────

    @property
    def report_count(self) -> int:
        with self._lock:
            return len(self.reports)

    @property
    def event_count(self) -> int:
        with self._lock:
            return len(self.events)

    @property
    def maxlen(self) -> int:
        return self._maxlen

    def clear(self) -> None:
        with self._lock:
            for deq in (
                self.reports, self.forecasts, self.probability_reports,
                self.capacity_forecasts, self.risk_forecasts,
                self.operational_forecasts, self.events,
            ):
                deq.clear()
