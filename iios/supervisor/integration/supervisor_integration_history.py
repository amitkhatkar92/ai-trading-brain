"""
supervisor_integration_history.py — iios.supervisor.integration
----------------------------------------------------------------
Bounded in-memory history of integration requests, responses, and events.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 6
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Any, Deque, Dict, List

from .constants import DEFAULT_MAX_HISTORY


class SupervisorIntegrationHistory:
    """
    Thread-safe bounded record of integration activity.

    Maintains three independent deques:
    - ``_requests``  : most-recent integration requests (dicts)
    - ``_responses`` : most-recent integration responses (dicts)
    - ``_events``    : most-recent domain events (dicts)

    Each deque is bounded to ``max_records`` entries (oldest dropped first).
    """

    def __init__(self, max_records: int = DEFAULT_MAX_HISTORY) -> None:
        self._max        = max(1, max_records)
        self._lock       = threading.Lock()
        self._requests:  Deque[Dict[str, Any]] = deque(maxlen=self._max)
        self._responses: Deque[Dict[str, Any]] = deque(maxlen=self._max)
        self._events:    Deque[Dict[str, Any]] = deque(maxlen=self._max)

    # ------------------------------------------------------------------
    # Record
    # ------------------------------------------------------------------

    def record_request(self, request: Any) -> None:
        """Append a request (or plain dict) to the request history."""
        entry = request if isinstance(request, dict) else (
            request.to_dict() if hasattr(request, "to_dict") else {"raw": str(request)}
        )
        with self._lock:
            self._requests.append(entry)

    def record_response(self, response: Any) -> None:
        """Append a response (or plain dict) to the response history."""
        entry = response if isinstance(response, dict) else (
            response.to_dict() if hasattr(response, "to_dict") else {"raw": str(response)}
        )
        with self._lock:
            self._responses.append(entry)

    def record_event(self, event: Any) -> None:
        """Append a domain event (or plain dict) to the event history."""
        entry = event if isinstance(event, dict) else (
            event.to_dict() if hasattr(event, "to_dict") else {"raw": str(event)}
        )
        with self._lock:
            self._events.append(entry)

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def recent_requests(self, n: int = 10) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._requests)[-n:]

    def recent_responses(self, n: int = 10) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._responses)[-n:]

    def recent_events(self, n: int = 10) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._events)[-n:]

    def counts(self) -> Dict[str, int]:
        with self._lock:
            return {
                "requests":  len(self._requests),
                "responses": len(self._responses),
                "events":    len(self._events),
            }

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def clear(self) -> None:
        with self._lock:
            self._requests.clear()
            self._responses.clear()
            self._events.clear()
