"""
iios/execution/analytics/engine/analytics_history.py
====================================================
EngineAnalyticsHistory — bounded, thread-safe history of analytics
requests, responses, pipelines, and events for the Execution Analytics
Engine.

C8 Execution Analytics & Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import threading
from collections import deque
from typing import List, Optional, TYPE_CHECKING

from .constants import DEFAULT_MAX_HISTORY

if TYPE_CHECKING:
    from .analytics_request import AnalyticsRequest
    from .analytics_response import AnalyticsResponse
    from .analytics_pipeline import AnalyticsPipeline
    from .analytics_events import EngineAnalyticsEvent


class EngineAnalyticsHistory:
    """
    Bounded, thread-safe history of completed analytics workflow items.

    All collections use deque(maxlen=N) for O(1) bounded appends.
    Read operations return list snapshots to avoid holding the lock.
    """

    def __init__(
        self,
        max_requests:   int = DEFAULT_MAX_HISTORY,
        max_responses:  int = DEFAULT_MAX_HISTORY,
        max_pipelines:  int = DEFAULT_MAX_HISTORY,
        max_events:     int = DEFAULT_MAX_HISTORY * 10,
    ) -> None:
        self._lock       = threading.Lock()
        self._requests:  deque["AnalyticsRequest"]  = deque(maxlen=max_requests)
        self._responses: deque["AnalyticsResponse"] = deque(maxlen=max_responses)
        self._pipelines: deque["AnalyticsPipeline"] = deque(maxlen=max_pipelines)
        self._events:    deque["EngineAnalyticsEvent"] = deque(maxlen=max_events)

    # ── Append ────────────────────────────────────────────────────────────────

    def record_request(self, request: "AnalyticsRequest") -> None:
        with self._lock:
            self._requests.append(request)

    def record_response(self, response: "AnalyticsResponse") -> None:
        with self._lock:
            self._responses.append(response)

    def record_pipeline(self, pipeline: "AnalyticsPipeline") -> None:
        with self._lock:
            self._pipelines.append(pipeline)

    def record_event(self, event: "EngineAnalyticsEvent") -> None:
        with self._lock:
            self._events.append(event)

    # ── Read ──────────────────────────────────────────────────────────────────

    def requests(self) -> List["AnalyticsRequest"]:
        with self._lock:
            return list(self._requests)

    def responses(self) -> List["AnalyticsResponse"]:
        with self._lock:
            return list(self._responses)

    def pipelines(self) -> List["AnalyticsPipeline"]:
        with self._lock:
            return list(self._pipelines)

    def events(self) -> List["EngineAnalyticsEvent"]:
        with self._lock:
            return list(self._events)

    def latest_request(self) -> Optional["AnalyticsRequest"]:
        with self._lock:
            return self._requests[-1] if self._requests else None

    def latest_response(self) -> Optional["AnalyticsResponse"]:
        with self._lock:
            return self._responses[-1] if self._responses else None

    def latest_event(self) -> Optional["EngineAnalyticsEvent"]:
        with self._lock:
            return self._events[-1] if self._events else None

    # ── Filtered queries ──────────────────────────────────────────────────────

    def responses_for_request(self, request_id: str) -> List["AnalyticsResponse"]:
        with self._lock:
            return [r for r in self._responses if r.request_id == request_id]

    def pipelines_for_request(self, request_id: str) -> List["AnalyticsPipeline"]:
        with self._lock:
            return [p for p in self._pipelines if p.request_id == request_id]

    def events_for_request(self, request_id: str) -> List["EngineAnalyticsEvent"]:
        with self._lock:
            return [e for e in self._events if e.request_id == request_id]

    # ── Utility ───────────────────────────────────────────────────────────────

    def clear(self) -> None:
        with self._lock:
            self._requests.clear()
            self._responses.clear()
            self._pipelines.clear()
            self._events.clear()

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def request_count(self) -> int:
        with self._lock:
            return len(self._requests)

    @property
    def response_count(self) -> int:
        with self._lock:
            return len(self._responses)

    @property
    def pipeline_count(self) -> int:
        with self._lock:
            return len(self._pipelines)

    @property
    def event_count(self) -> int:
        with self._lock:
            return len(self._events)
