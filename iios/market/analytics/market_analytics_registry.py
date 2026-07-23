"""
market_analytics_registry.py — iios.market.analytics
======================================================
Thread-safe registry of completed analytics reports.

C12 Market Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import threading
from collections import OrderedDict
from typing import Dict, List, Optional

from .constants import DEFAULT_MAX_ANALYTICS
from .market_analytics_response import MarketAnalyticsReport


class MarketAnalyticsRegistry:
    """
    Thread-safe registry holding the most recent analytics reports.

    Reports are keyed by ``report_id``. When the registry reaches capacity
    the oldest entry is evicted (FIFO).
    """

    def __init__(self, max_reports: int = DEFAULT_MAX_ANALYTICS) -> None:
        self._max   = max_reports
        self._lock  = threading.RLock()
        self._store: OrderedDict[str, MarketAnalyticsReport] = OrderedDict()

    def register(self, report: MarketAnalyticsReport) -> None:
        if not report.report_id:
            from .exceptions import MarketAnalyticsRegistryError
            raise MarketAnalyticsRegistryError("report_id must not be empty")
        with self._lock:
            if report.report_id in self._store:
                # Update in-place (remove-and-reinsert to keep insertion order)
                del self._store[report.report_id]
            elif len(self._store) >= self._max:
                self._store.popitem(last=False)
            self._store[report.report_id] = report

    def get(self, report_id: str) -> Optional[MarketAnalyticsReport]:
        with self._lock:
            return self._store.get(report_id)

    def get_by_analytics_id(self, analytics_id: str) -> List[MarketAnalyticsReport]:
        with self._lock:
            return [r for r in self._store.values() if r.analytics_id == analytics_id]

    def latest_for_exchange(self, exchange: str) -> Optional[MarketAnalyticsReport]:
        with self._lock:
            results = [r for r in self._store.values() if r.exchange == exchange]
            return results[-1] if results else None

    def remove(self, report_id: str) -> bool:
        with self._lock:
            if report_id in self._store:
                del self._store[report_id]
                return True
            return False

    def all_reports(self) -> List[MarketAnalyticsReport]:
        with self._lock:
            return list(self._store.values())

    def count(self) -> int:
        with self._lock:
            return len(self._store)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def is_registered(self, report_id: str) -> bool:
        with self._lock:
            return report_id in self._store
