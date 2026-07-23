"""
market_policy_history.py — iios.market.policies
=================================================
Bounded in-memory history store for the Market Policy Framework.

C12 Market Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Any, Deque, Dict, List

from .constants import DEFAULT_MAX_HISTORY


class MarketPolicyHistory:
    """
    Bounded ring-buffer of evaluation artefacts.

    Four independent deques are maintained:
    - Events
    - Requests
    - Responses
    - Audit reports

    All operations are thread-safe.

    Parameters
    ----------
    max_events :
        Maximum number of items to retain per buffer.
        Defaults to :data:`~.constants.DEFAULT_MAX_HISTORY`.
    """

    def __init__(self, max_events: int = DEFAULT_MAX_HISTORY) -> None:
        self._max = max_events
        self._lock = threading.RLock()
        self._events:    Deque[Any] = deque(maxlen=max_events)
        self._requests:  Deque[Any] = deque(maxlen=max_events)
        self._responses: Deque[Any] = deque(maxlen=max_events)
        self._audits:    Deque[Any] = deque(maxlen=max_events)

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record_event(self, event: Any) -> None:
        with self._lock:
            self._events.append(event)

    def record_request(self, request: Any) -> None:
        with self._lock:
            self._requests.append(request)

    def record_response(self, response: Any) -> None:
        with self._lock:
            self._responses.append(response)

    def record_audit(self, report: Any) -> None:
        with self._lock:
            self._audits.append(report)

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def recent_events(self, n: int = 10) -> List[Any]:
        with self._lock:
            items = list(self._events)
        return items[-n:] if n < len(items) else items

    def recent_requests(self, n: int = 10) -> List[Any]:
        with self._lock:
            items = list(self._requests)
        return items[-n:] if n < len(items) else items

    def recent_responses(self, n: int = 10) -> List[Any]:
        with self._lock:
            items = list(self._responses)
        return items[-n:] if n < len(items) else items

    def recent_audits(self, n: int = 10) -> List[Any]:
        with self._lock:
            items = list(self._audits)
        return items[-n:] if n < len(items) else items

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def counts(self) -> Dict[str, int]:
        with self._lock:
            return {
                "events":    len(self._events),
                "requests":  len(self._requests),
                "responses": len(self._responses),
                "audits":    len(self._audits),
            }

    def clear(self) -> None:
        with self._lock:
            self._events.clear()
            self._requests.clear()
            self._responses.clear()
            self._audits.clear()
