"""
market_integration_history.py — iios.market.integration
=========================================================
Bounded ring-buffer history for the Market Integration subsystem.

C12 Market Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

from collections import deque
from typing import Any, Deque, Dict, List, Optional

from .constants import DEFAULT_MAX_HISTORY


class MarketIntegrationHistory:
    """
    Bounded in-memory history of integration activity.

    Stores recent requests, responses, events, and errors in
    separate bounded deques.  Thread-safe via the caller (engine)
    holding its own lock before calling history methods.

    Parameters
    ----------
    max_entries : Maximum entries kept per deque (FIFO eviction).
    """

    def __init__(self, max_entries: int = DEFAULT_MAX_HISTORY) -> None:
        self._max     = max_entries
        self._requests:  Deque[Any] = deque(maxlen=max_entries)
        self._responses: Deque[Any] = deque(maxlen=max_entries)
        self._events:    Deque[Any] = deque(maxlen=max_entries)
        self._errors:    Deque[Any] = deque(maxlen=max_entries)

    # ------------------------------------------------------------------
    # Record
    # ------------------------------------------------------------------

    def record_request(self, request: Any) -> None:
        self._requests.append(request)

    def record_response(self, response: Any) -> None:
        self._responses.append(response)

    def record_event(self, event: Any) -> None:
        self._events.append(event)

    def record_error(self, error: Any) -> None:
        self._errors.append(error)

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def recent_requests(self, n: Optional[int] = None) -> List[Any]:
        items = list(self._requests)
        return items[-n:] if n is not None and n < len(items) else items

    def recent_responses(self, n: Optional[int] = None) -> List[Any]:
        items = list(self._responses)
        return items[-n:] if n is not None and n < len(items) else items

    def recent_events(self, n: Optional[int] = None) -> List[Any]:
        items = list(self._events)
        return items[-n:] if n is not None and n < len(items) else items

    def recent_errors(self, n: Optional[int] = None) -> List[Any]:
        items = list(self._errors)
        return items[-n:] if n is not None and n < len(items) else items

    def counts(self) -> Dict[str, int]:
        return {
            "requests":  len(self._requests),
            "responses": len(self._responses),
            "events":    len(self._events),
            "errors":    len(self._errors),
        }

    def clear(self) -> None:
        self._requests.clear()
        self._responses.clear()
        self._events.clear()
        self._errors.clear()
