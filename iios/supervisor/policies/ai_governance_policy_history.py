"""
ai_governance_policy_history.py — iios.supervisor.policies
------------------------------------------------------------
Bounded history of AI governance policy evaluation artefacts.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 3
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Deque, List

from .constants import DEFAULT_MAX_HISTORY


class AIGovernancePolicyHistory:
    """
    Thread-safe bounded history of governance evaluation requests, responses,
    events, and audit reports.

    Parameters
    ----------
    max_requests :   Maximum evaluation requests to retain.
    max_responses :  Maximum evaluation responses to retain.
    max_events :     Maximum events to retain.
    max_audits :     Maximum audit reports to retain.
    """

    def __init__(
        self,
        max_requests:  int = DEFAULT_MAX_HISTORY,
        max_responses: int = DEFAULT_MAX_HISTORY,
        max_events:    int = DEFAULT_MAX_HISTORY,
        max_audits:    int = DEFAULT_MAX_HISTORY,
    ) -> None:
        self._lock:      threading.Lock = threading.Lock()
        self._requests:  Deque          = deque(maxlen=max_requests)
        self._responses: Deque          = deque(maxlen=max_responses)
        self._events:    Deque          = deque(maxlen=max_events)
        self._audits:    Deque          = deque(maxlen=max_audits)

    # ------------------------------------------------------------------
    # Requests
    # ------------------------------------------------------------------

    def record_request(self, request: object) -> None:
        with self._lock:
            self._requests.append(request)

    def recent_requests(self, n: int = 20) -> List:
        with self._lock:
            items = list(self._requests)
        return items[-n:] if n < len(items) else items

    def request_count(self) -> int:
        with self._lock:
            return len(self._requests)

    # ------------------------------------------------------------------
    # Responses
    # ------------------------------------------------------------------

    def record_response(self, response: object) -> None:
        with self._lock:
            self._responses.append(response)

    def recent_responses(self, n: int = 20) -> List:
        with self._lock:
            items = list(self._responses)
        return items[-n:] if n < len(items) else items

    def response_count(self) -> int:
        with self._lock:
            return len(self._responses)

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def record_event(self, event: object) -> None:
        with self._lock:
            self._events.append(event)

    def recent_events(self, n: int = 20) -> List:
        with self._lock:
            items = list(self._events)
        return items[-n:] if n < len(items) else items

    def event_count(self) -> int:
        with self._lock:
            return len(self._events)

    # ------------------------------------------------------------------
    # Audit reports
    # ------------------------------------------------------------------

    def record_audit(self, report: object) -> None:
        with self._lock:
            self._audits.append(report)

    def recent_audits(self, n: int = 20) -> List:
        with self._lock:
            items = list(self._audits)
        return items[-n:] if n < len(items) else items

    def audit_count(self) -> int:
        with self._lock:
            return len(self._audits)

    # ------------------------------------------------------------------
    # Aggregate
    # ------------------------------------------------------------------

    def counts(self) -> dict:
        with self._lock:
            return {
                "requests":  len(self._requests),
                "responses": len(self._responses),
                "events":    len(self._events),
                "audits":    len(self._audits),
            }

    def clear(self) -> None:
        with self._lock:
            self._requests.clear()
            self._responses.clear()
            self._events.clear()
            self._audits.clear()
