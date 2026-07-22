"""
portfolio_optimization_history.py — iios.portfolio.optimization
================================================================
Bounded deques for optimization events, requests, and responses.

C10 Portfolio Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Any, Dict, List

from .constants import DEFAULT_MAX_HISTORY
from .portfolio_optimization_events import OptimizationEngineEvent
from .portfolio_optimization_request import PortfolioOptimizationRequest
from .portfolio_optimization_response import PortfolioOptimizationResponse


class PortfolioOptimizationHistory:
    """
    Thread-safe, bounded history store for the optimization engine.

    Maintains three separate FIFO queues — events, requests,
    responses — each with an independent maximum size.

    Parameters
    ----------
    max_events :    Maximum events to retain.
    max_requests :  Maximum requests to retain.
    max_responses : Maximum responses to retain.
    """

    def __init__(
        self,
        max_events:    int = DEFAULT_MAX_HISTORY,
        max_requests:  int = DEFAULT_MAX_HISTORY,
        max_responses: int = DEFAULT_MAX_HISTORY,
    ) -> None:
        self._lock      = threading.Lock()
        self._events:    deque = deque(maxlen=max_events)
        self._requests:  deque = deque(maxlen=max_requests)
        self._responses: deque = deque(maxlen=max_responses)

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def record_event(self, event: OptimizationEngineEvent) -> None:
        with self._lock:
            self._events.append(event)

    def record_request(self, request: PortfolioOptimizationRequest) -> None:
        with self._lock:
            self._requests.append(request)

    def record_response(self, response: PortfolioOptimizationResponse) -> None:
        with self._lock:
            self._responses.append(response)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def recent_events(self, n: int = 10) -> List[OptimizationEngineEvent]:
        with self._lock:
            events = list(self._events)
        return events[-n:]

    def recent_requests(self, n: int = 10) -> List[PortfolioOptimizationRequest]:
        with self._lock:
            requests = list(self._requests)
        return requests[-n:]

    def recent_responses(self, n: int = 10) -> List[PortfolioOptimizationResponse]:
        with self._lock:
            responses = list(self._responses)
        return responses[-n:]

    def summary(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "event_count":    len(self._events),
                "request_count":  len(self._requests),
                "response_count": len(self._responses),
            }

    def clear(self) -> None:
        with self._lock:
            self._events.clear()
            self._requests.clear()
            self._responses.clear()
