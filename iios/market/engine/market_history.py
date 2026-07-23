"""
market_history.py — iios.market.engine
=========================================
Bounded in-memory history store for market engine events, requests,
responses, and pipeline records.

C12 Market Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Any, Deque, Dict, List, TYPE_CHECKING

from .constants import DEFAULT_MAX_HISTORY

if TYPE_CHECKING:
    from .market_events import MarketEngineEvent
    from .market_pipeline import MarketPipeline
    from .market_request import MarketRequest
    from .market_response import MarketResponse


class MarketEngineHistory:
    """
    Thread-safe, bounded history store for the Market Engine.

    Each category has its own bounded deque that discards the oldest entry
    when full.

    Parameters
    ----------
    max_events    : Capacity for events.
    max_requests  : Capacity for requests.
    max_responses : Capacity for responses.
    max_pipelines : Capacity for pipelines.
    """

    def __init__(
        self,
        max_events:    int = DEFAULT_MAX_HISTORY,
        max_requests:  int = DEFAULT_MAX_HISTORY,
        max_responses: int = DEFAULT_MAX_HISTORY,
        max_pipelines: int = DEFAULT_MAX_HISTORY,
    ) -> None:
        self._lock      = threading.Lock()
        self._events:    Deque = deque(maxlen=max_events)
        self._requests:  Deque = deque(maxlen=max_requests)
        self._responses: Deque = deque(maxlen=max_responses)
        self._pipelines: Deque = deque(maxlen=max_pipelines)

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def record_event(self, event: "MarketEngineEvent") -> None:
        with self._lock:
            self._events.append(event)

    def recent_events(self, n: int = 20) -> List["MarketEngineEvent"]:
        with self._lock:
            items = list(self._events)
        return items[-n:] if n < len(items) else items

    # ------------------------------------------------------------------
    # Requests
    # ------------------------------------------------------------------

    def record_request(self, request: "MarketRequest") -> None:
        with self._lock:
            self._requests.append(request)

    def recent_requests(self, n: int = 20) -> List["MarketRequest"]:
        with self._lock:
            items = list(self._requests)
        return items[-n:] if n < len(items) else items

    # ------------------------------------------------------------------
    # Responses
    # ------------------------------------------------------------------

    def record_response(self, response: "MarketResponse") -> None:
        with self._lock:
            self._responses.append(response)

    def recent_responses(self, n: int = 20) -> List["MarketResponse"]:
        with self._lock:
            items = list(self._responses)
        return items[-n:] if n < len(items) else items

    # ------------------------------------------------------------------
    # Pipelines
    # ------------------------------------------------------------------

    def record_pipeline(self, pipeline: "MarketPipeline") -> None:
        with self._lock:
            self._pipelines.append(pipeline)

    def recent_pipelines(self, n: int = 20) -> List["MarketPipeline"]:
        with self._lock:
            items = list(self._pipelines)
        return items[-n:] if n < len(items) else items

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def counts(self) -> Dict[str, int]:
        with self._lock:
            return {
                "events":    len(self._events),
                "requests":  len(self._requests),
                "responses": len(self._responses),
                "pipelines": len(self._pipelines),
            }

    def clear(self) -> None:
        with self._lock:
            self._events.clear()
            self._requests.clear()
            self._responses.clear()
            self._pipelines.clear()
