"""
decision_integration_registry.py — iios.decision.integration
=============================================================
Tracks in-flight and completed integration requests.  Used by the
``query()`` public API to look up prior results.

C9 Decision Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from .constants import DEFAULT_MAX_IN_FLIGHT, DEFAULT_MAX_HISTORY
from .exceptions import DuplicateIntegrationError, IntegrationWorkflowError


class DecisionIntegrationRegistry:
    """
    Thread-safe registry of integration records.

    Tracks two collections:
    * **in-flight** — requests currently being processed.
    * **completed** — bounded history of finished responses.

    Usage
    -----
    ::

        registry = DecisionIntegrationRegistry()
        registry.register_in_flight(request)
        ...
        registry.complete(request_id, response)
        response = registry.find_completed(request_id)

    Parameters
    ----------
    max_in_flight : Maximum simultaneous in-flight requests.
    max_completed : Maximum retained completed responses.
    """

    def __init__(
        self,
        max_in_flight: int = DEFAULT_MAX_IN_FLIGHT,
        max_completed: int = DEFAULT_MAX_HISTORY,
    ) -> None:
        self._lock:        threading.RLock            = threading.RLock()
        self._in_flight:   Dict[str, object]           = {}
        self._completed:   Dict[str, object]           = {}
        self._by_decision: Dict[str, List[str]]        = {}
        self._by_session:  Dict[str, str]              = {}
        self._max_in_flight = max_in_flight
        self._max_completed = max_completed
        self._completed_order: List[str]               = []

    # ------------------------------------------------------------------
    # In-flight
    # ------------------------------------------------------------------

    def register_in_flight(self, request: object) -> None:
        """
        Register a new in-flight request.

        Raises
        ------
        DuplicateIntegrationError
            When a request with the same ID is already in flight.
        IntegrationWorkflowError
            When the in-flight capacity is exhausted.
        """
        rid = getattr(request, "request_id", "")
        did = getattr(request, "decision_id", "")
        with self._lock:
            if rid in self._in_flight:
                raise DuplicateIntegrationError(rid)
            if len(self._in_flight) >= self._max_in_flight:
                raise IntegrationWorkflowError(
                    f"In-flight capacity exhausted ({self._max_in_flight})"
                )
            self._in_flight[rid] = request

    def deregister_in_flight(self, request_id: str) -> bool:
        """Remove a request from in-flight.  Returns True if it existed."""
        with self._lock:
            if request_id in self._in_flight:
                del self._in_flight[request_id]
                return True
            return False

    def is_in_flight(self, request_id: str) -> bool:
        with self._lock:
            return request_id in self._in_flight

    def in_flight_count(self) -> int:
        with self._lock:
            return len(self._in_flight)

    def all_in_flight(self) -> List[object]:
        with self._lock:
            return list(self._in_flight.values())

    # ------------------------------------------------------------------
    # Completion
    # ------------------------------------------------------------------

    def complete(
        self,
        request_id: str,
        response:   object,
    ) -> None:
        """
        Move a request from in-flight to completed.

        Evicts the oldest completed record when capacity is exceeded.
        """
        session_id  = getattr(response, "session_id",  "")
        decision_id = getattr(response, "decision_id", "")

        with self._lock:
            self._in_flight.pop(request_id, None)

            # Evict oldest if over capacity
            while len(self._completed_order) >= self._max_completed:
                oldest = self._completed_order.pop(0)
                evicted = self._completed.pop(oldest, None)
                if evicted is not None:
                    eid = getattr(evicted, "session_id", "")
                    if eid in self._by_session:
                        del self._by_session[eid]

            self._completed[request_id]    = response
            self._completed_order.append(request_id)

            if session_id:
                self._by_session[session_id] = request_id

            if decision_id:
                self._by_decision.setdefault(decision_id, []).append(request_id)

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def find_completed(self, request_id: str) -> Optional[object]:
        """Return a completed response by request_id, or None."""
        with self._lock:
            return self._completed.get(request_id)

    def find_by_session(self, session_id: str) -> Optional[object]:
        """Return the completed response for a given session_id, or None."""
        with self._lock:
            rid = self._by_session.get(session_id)
            if rid is None:
                return None
            return self._completed.get(rid)

    def find_by_decision(self, decision_id: str) -> List[object]:
        """Return all completed responses for a decision_id."""
        with self._lock:
            rids = self._by_decision.get(decision_id, [])
            return [self._completed[r] for r in rids if r in self._completed]

    def completed_count(self) -> int:
        with self._lock:
            return len(self._completed)

    def all_completed(self) -> List[object]:
        with self._lock:
            return list(self._completed.values())

    # ------------------------------------------------------------------
    # Clear
    # ------------------------------------------------------------------

    def clear(self) -> None:
        with self._lock:
            self._in_flight.clear()
            self._completed.clear()
            self._completed_order.clear()
            self._by_decision.clear()
            self._by_session.clear()
