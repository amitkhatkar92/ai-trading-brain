"""
risk_integration_history.py — iios.risk.integration
=====================================================
Bounded ring-buffer history for integration requests, responses, and events.

C11 Risk Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Any, Deque, Dict, List, Optional

from .constants import DEFAULT_MAX_HISTORY
from .risk_integration_request import RiskIntegrationRequest
from .risk_integration_response import RiskIntegrationResponse


class RiskIntegrationHistory:
    """
    Thread-safe bounded ring-buffer history for integration artefacts.

    Four independent buffers:
    - Requests
    - Responses
    - Events
    - Errors

    Parameters
    ----------
    max_items :
        Maximum items per buffer.
    """

    def __init__(self, max_items: int = DEFAULT_MAX_HISTORY) -> None:
        self._max       = max_items
        self._lock      = threading.RLock()
        self._requests:  Deque[RiskIntegrationRequest]  = deque(maxlen=max_items)
        self._responses: Deque[RiskIntegrationResponse] = deque(maxlen=max_items)
        self._events:    Deque[Any]                     = deque(maxlen=max_items)
        self._errors:    Deque[Any]                     = deque(maxlen=max_items)

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record_request(self, request: RiskIntegrationRequest) -> None:
        with self._lock:
            self._requests.append(request)

    def record_response(self, response: RiskIntegrationResponse) -> None:
        with self._lock:
            self._responses.append(response)

    def record_event(self, event: Any) -> None:
        with self._lock:
            self._events.append(event)

    def record_error(self, error: Any) -> None:
        with self._lock:
            self._errors.append(error)

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def recent_requests(self, n: int = 10) -> List[RiskIntegrationRequest]:
        with self._lock:
            items = list(self._requests)
        return items[-n:] if n < len(items) else items

    def recent_responses(self, n: int = 10) -> List[RiskIntegrationResponse]:
        with self._lock:
            items = list(self._responses)
        return items[-n:] if n < len(items) else items

    def recent_events(self, n: int = 10) -> List[Any]:
        with self._lock:
            items = list(self._events)
        return items[-n:] if n < len(items) else items

    def recent_errors(self, n: int = 10) -> List[Any]:
        with self._lock:
            items = list(self._errors)
        return items[-n:] if n < len(items) else items

    def find_response(self, request_id: str) -> Optional[RiskIntegrationResponse]:
        with self._lock:
            for r in reversed(list(self._responses)):
                if r.request_id == request_id:
                    return r
        return None

    def find_request(self, request_id: str) -> Optional[RiskIntegrationRequest]:
        with self._lock:
            for r in reversed(list(self._requests)):
                if r.request_id == request_id:
                    return r
        return None

    def responses_for_portfolio(
        self, portfolio_id: str
    ) -> List[RiskIntegrationResponse]:
        with self._lock:
            return [r for r in self._responses if r.portfolio_id == portfolio_id]

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def counts(self) -> Dict[str, int]:
        with self._lock:
            return {
                "requests":  len(self._requests),
                "responses": len(self._responses),
                "events":    len(self._events),
                "errors":    len(self._errors),
            }

    def clear(self) -> None:
        with self._lock:
            self._requests.clear()
            self._responses.clear()
            self._events.clear()
            self._errors.clear()
