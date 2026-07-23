"""
supervisor_history.py — iios.supervisor.engine
-----------------------------------------------
Bounded history stores for supervisor engine audit trail.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 2
"""
from __future__ import annotations

import collections
import threading
from typing import Any, List

from .constants import DEFAULT_MAX_HISTORY


class SupervisorEngineHistory:
    """
    Thread-safe bounded history for the supervisor engine audit trail.

    Maintains separate deques for:
    - Events (SupervisorEngineEvent)
    - Requests (SupervisorRequest)
    - Responses (SupervisorResponse)
    - Pipelines (SupervisorPipeline)

    Each deque discards oldest entries when the maximum capacity is
    reached (FIFO eviction).

    Parameters
    ----------
    max_history : Maximum entries per history deque.
    """

    def __init__(self, max_history: int = DEFAULT_MAX_HISTORY) -> None:
        self._lock             = threading.Lock()
        self._max              = max_history
        self._events:    collections.deque = collections.deque(maxlen=max_history)
        self._requests:  collections.deque = collections.deque(maxlen=max_history)
        self._responses: collections.deque = collections.deque(maxlen=max_history)
        self._pipelines: collections.deque = collections.deque(maxlen=max_history)

    # ------------------------------------------------------------------
    # Record helpers
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

    def record_pipeline(self, pipeline: Any) -> None:
        with self._lock:
            self._pipelines.append(pipeline)

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------

    def recent_events(self, n: int = 20) -> List[Any]:
        with self._lock:
            items = list(self._events)
        return items[-n:] if n < len(items) else items

    def recent_requests(self, n: int = 20) -> List[Any]:
        with self._lock:
            items = list(self._requests)
        return items[-n:] if n < len(items) else items

    def recent_responses(self, n: int = 20) -> List[Any]:
        with self._lock:
            items = list(self._responses)
        return items[-n:] if n < len(items) else items

    def recent_pipelines(self, n: int = 20) -> List[Any]:
        with self._lock:
            items = list(self._pipelines)
        return items[-n:] if n < len(items) else items

    # ------------------------------------------------------------------

    def clear(self) -> None:
        with self._lock:
            self._events.clear()
            self._requests.clear()
            self._responses.clear()
            self._pipelines.clear()
