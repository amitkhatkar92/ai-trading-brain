"""
portfolio_history.py — iios.portfolio.engine
=============================================
Bounded history of Portfolio Engine events, requests, responses,
and pipeline records.

C10 Portfolio Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Deque, List, Optional

from .constants import DEFAULT_MAX_HISTORY, PortfolioEventType, PortfolioWorkflowType


class PortfolioEngineHistory:
    """
    Thread-safe bounded history for the Portfolio Engine.

    Maintains separate bounded deques for:
    * Events     (:class:`PortfolioEngineEvent`)
    * Requests   (:class:`PortfolioRequest`)
    * Responses  (:class:`PortfolioResponse`)
    * Pipelines  (:class:`PortfolioPipeline` — completed/failed only)

    Usage
    -----
    ::

        history = PortfolioEngineHistory()
        history.record_event(event)
        history.record_request(request)
        history.record_response(response)
        history.record_pipeline(pipeline)
        latest = history.latest_event()

    Parameters
    ----------
    max_entries : Maximum items per collection.
    """

    def __init__(self, max_entries: int = DEFAULT_MAX_HISTORY) -> None:
        self._lock:      threading.Lock = threading.Lock()
        self._events:    Deque          = deque(maxlen=max_entries)
        self._requests:  Deque          = deque(maxlen=max_entries)
        self._responses: Deque          = deque(maxlen=max_entries)
        self._pipelines: Deque          = deque(maxlen=max_entries)

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def record_event(self, event: object) -> None:
        with self._lock:
            self._events.append(event)

    def events(self) -> List:
        with self._lock:
            return list(self._events)

    def latest_event(self) -> Optional[object]:
        with self._lock:
            return self._events[-1] if self._events else None

    def events_by_type(self, event_type: PortfolioEventType) -> List:
        with self._lock:
            return [e for e in self._events
                    if getattr(e, "event_type", None) == event_type]

    def events_for_portfolio(self, portfolio_id: str) -> List:
        with self._lock:
            return [e for e in self._events
                    if getattr(e, "portfolio_id", None) == portfolio_id]

    def event_count(self) -> int:
        with self._lock:
            return len(self._events)

    # ------------------------------------------------------------------
    # Requests
    # ------------------------------------------------------------------

    def record_request(self, request: object) -> None:
        with self._lock:
            self._requests.append(request)

    def requests(self) -> List:
        with self._lock:
            return list(self._requests)

    def latest_request(self) -> Optional[object]:
        with self._lock:
            return self._requests[-1] if self._requests else None

    def requests_for_portfolio(self, portfolio_id: str) -> List:
        with self._lock:
            return [r for r in self._requests
                    if getattr(r, "portfolio_id", None) == portfolio_id]

    def request_count(self) -> int:
        with self._lock:
            return len(self._requests)

    # ------------------------------------------------------------------
    # Responses
    # ------------------------------------------------------------------

    def record_response(self, response: object) -> None:
        with self._lock:
            self._responses.append(response)

    def responses(self) -> List:
        with self._lock:
            return list(self._responses)

    def latest_response(self) -> Optional[object]:
        with self._lock:
            return self._responses[-1] if self._responses else None

    def responses_for_portfolio(self, portfolio_id: str) -> List:
        with self._lock:
            return [r for r in self._responses
                    if getattr(r, "portfolio_id", None) == portfolio_id]

    def response_count(self) -> int:
        with self._lock:
            return len(self._responses)

    # ------------------------------------------------------------------
    # Pipelines
    # ------------------------------------------------------------------

    def record_pipeline(self, pipeline: object) -> None:
        with self._lock:
            self._pipelines.append(pipeline)

    def pipelines(self) -> List:
        with self._lock:
            return list(self._pipelines)

    def latest_pipeline(self) -> Optional[object]:
        with self._lock:
            return self._pipelines[-1] if self._pipelines else None

    def pipeline_count(self) -> int:
        with self._lock:
            return len(self._pipelines)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def summary(self) -> dict:
        with self._lock:
            return {
                "events":    len(self._events),
                "requests":  len(self._requests),
                "responses": len(self._responses),
                "pipelines": len(self._pipelines),
            }

    # ------------------------------------------------------------------
    # Clear
    # ------------------------------------------------------------------

    def clear(self) -> None:
        with self._lock:
            self._events.clear()
            self._requests.clear()
            self._responses.clear()
            self._pipelines.clear()
