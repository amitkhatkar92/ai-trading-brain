"""
market_analytics_history.py — iios.market.analytics
=====================================================
Bounded in-memory history store for the Market Analytics Framework.

C12 Market Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Any, Deque, Dict, List

from .constants import DEFAULT_MAX_HISTORY


class MarketAnalyticsHistory:
    """Bounded ring-buffer of analytics artefacts. Thread-safe."""

    def __init__(self, max_events: int = DEFAULT_MAX_HISTORY) -> None:
        self._max = max_events
        self._lock = threading.RLock()
        self._events:    Deque[Any] = deque(maxlen=max_events)
        self._requests:  Deque[Any] = deque(maxlen=max_events)
        self._reports:   Deque[Any] = deque(maxlen=max_events)

    def record_event(self, event: Any) -> None:
        with self._lock:
            self._events.append(event)

    def record_request(self, request: Any) -> None:
        with self._lock:
            self._requests.append(request)

    def record_report(self, report: Any) -> None:
        with self._lock:
            self._reports.append(report)

    def recent_events(self, n: int = 10) -> List[Any]:
        with self._lock:
            items = list(self._events)
        return items[-n:] if n < len(items) else items

    def recent_requests(self, n: int = 10) -> List[Any]:
        with self._lock:
            items = list(self._requests)
        return items[-n:] if n < len(items) else items

    def recent_reports(self, n: int = 10) -> List[Any]:
        with self._lock:
            items = list(self._reports)
        return items[-n:] if n < len(items) else items

    def counts(self) -> Dict[str, int]:
        with self._lock:
            return {
                "events":   len(self._events),
                "requests": len(self._requests),
                "reports":  len(self._reports),
            }

    def clear(self) -> None:
        with self._lock:
            self._events.clear()
            self._requests.clear()
            self._reports.clear()
