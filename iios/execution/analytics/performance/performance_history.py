"""
iios/execution/analytics/performance/performance_history.py
===========================================================
PerformanceAnalyticsHistory — bounded history store for the
Performance Analytics Framework.

Stores recent reports, KPI reports, trends, benchmarks, scorecards,
and events using bounded deques.

C8 Execution Analytics & Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import collections
import threading
from typing import Any, Deque, List, Optional

from .constants import DEFAULT_MAX_HISTORY


class PerformanceAnalyticsHistory:
    """
    Bounded event and artefact history for the Performance Analytics Framework.

    Thread-safe.  All collections bounded at DEFAULT_MAX_HISTORY entries.
    """

    def __init__(self, maxlen: int = DEFAULT_MAX_HISTORY) -> None:
        self._maxlen = maxlen
        self._lock   = threading.Lock()
        self.reports:    Deque[Any] = collections.deque(maxlen=maxlen)
        self.kpi_reports: Deque[Any] = collections.deque(maxlen=maxlen)
        self.trends:     Deque[Any] = collections.deque(maxlen=maxlen)
        self.benchmarks: Deque[Any] = collections.deque(maxlen=maxlen)
        self.scorecards: Deque[Any] = collections.deque(maxlen=maxlen)
        self.events:     Deque[Any] = collections.deque(maxlen=maxlen)

    # ── Append methods ────────────────────────────────────────────────────────

    def add_report(self, report: Any) -> None:
        with self._lock:
            self.reports.append(report)

    def add_kpi_report(self, kpi_report: Any) -> None:
        with self._lock:
            self.kpi_reports.append(kpi_report)

    def add_trend(self, trend: Any) -> None:
        with self._lock:
            self.trends.append(trend)

    def add_benchmark(self, benchmark: Any) -> None:
        with self._lock:
            self.benchmarks.append(benchmark)

    def add_scorecard(self, scorecard: Any) -> None:
        with self._lock:
            self.scorecards.append(scorecard)

    def add_event(self, event: Any) -> None:
        with self._lock:
            self.events.append(event)

    # ── Snapshot methods (copies) ─────────────────────────────────────────────

    def recent_reports(self, n: int = 10) -> List[Any]:
        with self._lock:
            items = list(self.reports)
        return items[-n:] if n > 0 else items

    def recent_kpi_reports(self, n: int = 10) -> List[Any]:
        with self._lock:
            items = list(self.kpi_reports)
        return items[-n:] if n > 0 else items

    def recent_trends(self, n: int = 10) -> List[Any]:
        with self._lock:
            items = list(self.trends)
        return items[-n:] if n > 0 else items

    def recent_benchmarks(self, n: int = 10) -> List[Any]:
        with self._lock:
            items = list(self.benchmarks)
        return items[-n:] if n > 0 else items

    def recent_scorecards(self, n: int = 10) -> List[Any]:
        with self._lock:
            items = list(self.scorecards)
        return items[-n:] if n > 0 else items

    def recent_events(self, n: int = 10) -> List[Any]:
        with self._lock:
            items = list(self.events)
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
            self.reports.clear()
            self.kpi_reports.clear()
            self.trends.clear()
            self.benchmarks.clear()
            self.scorecards.clear()
            self.events.clear()
