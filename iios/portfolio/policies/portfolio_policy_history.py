"""
portfolio_policy_history.py — iios.portfolio.policies
======================================================
Thread-safe bounded history for the Portfolio Policy Engine.

Stores events, requests, responses, and audit reports in bounded
deques.  Provides typed query helpers.

C10 Portfolio Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Any, Callable, Dict, List, Optional

from .constants import DEFAULT_MAX_HISTORY, PolicyEventType
from .portfolio_policy_events import PolicyEngineEvent


class PortfolioPolicyHistory:
    """
    Thread-safe bounded history for the Portfolio Policy Engine.

    Parameters
    ----------
    max_entries : Maximum entries per collection (events, requests,
                  responses, audit reports).  Oldest entries are
                  evicted when the bound is reached.
    """

    def __init__(self, max_entries: int = DEFAULT_MAX_HISTORY) -> None:
        self._lock     = threading.Lock()
        self._maxlen   = max_entries
        self._events:   deque = deque(maxlen=max_entries)
        self._requests: deque = deque(maxlen=max_entries)
        self._responses: deque = deque(maxlen=max_entries)
        self._audits:   deque = deque(maxlen=max_entries)

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def record_event(self, event: PolicyEngineEvent) -> None:
        with self._lock:
            self._events.append(event)

    def events(self, limit: Optional[int] = None) -> List[PolicyEngineEvent]:
        with self._lock:
            data = list(self._events)
        return data[-limit:] if limit else data

    def latest_event(self) -> Optional[PolicyEngineEvent]:
        with self._lock:
            return self._events[-1] if self._events else None

    def events_by_type(self, event_type: PolicyEventType) -> List[PolicyEngineEvent]:
        with self._lock:
            return [e for e in self._events if e.event_type == event_type]

    def events_for_portfolio(self, portfolio_id: str) -> List[PolicyEngineEvent]:
        with self._lock:
            return [e for e in self._events if e.portfolio_id == portfolio_id]

    def events_for_evaluation(self, evaluation_id: str) -> List[PolicyEngineEvent]:
        with self._lock:
            return [e for e in self._events if e.evaluation_id == evaluation_id]

    def event_count(self) -> int:
        with self._lock:
            return len(self._events)

    # ------------------------------------------------------------------
    # Requests
    # ------------------------------------------------------------------

    def record_request(self, request: Any) -> None:
        with self._lock:
            self._requests.append(request)

    def requests(self, limit: Optional[int] = None) -> List[Any]:
        with self._lock:
            data = list(self._requests)
        return data[-limit:] if limit else data

    def latest_request(self) -> Optional[Any]:
        with self._lock:
            return self._requests[-1] if self._requests else None

    def requests_for_portfolio(self, portfolio_id: str) -> List[Any]:
        with self._lock:
            return [r for r in self._requests if getattr(r, "portfolio_id", None) == portfolio_id]

    def request_count(self) -> int:
        with self._lock:
            return len(self._requests)

    # ------------------------------------------------------------------
    # Responses
    # ------------------------------------------------------------------

    def record_response(self, response: Any) -> None:
        with self._lock:
            self._responses.append(response)

    def responses(self, limit: Optional[int] = None) -> List[Any]:
        with self._lock:
            data = list(self._responses)
        return data[-limit:] if limit else data

    def latest_response(self) -> Optional[Any]:
        with self._lock:
            return self._responses[-1] if self._responses else None

    def response_count(self) -> int:
        with self._lock:
            return len(self._responses)

    # ------------------------------------------------------------------
    # Audit reports
    # ------------------------------------------------------------------

    def record_audit(self, audit: Any) -> None:
        with self._lock:
            self._audits.append(audit)

    def audits(self, limit: Optional[int] = None) -> List[Any]:
        with self._lock:
            data = list(self._audits)
        return data[-limit:] if limit else data

    def latest_audit(self) -> Optional[Any]:
        with self._lock:
            return self._audits[-1] if self._audits else None

    def audit_count(self) -> int:
        with self._lock:
            return len(self._audits)

    # ------------------------------------------------------------------
    # Bulk operations
    # ------------------------------------------------------------------

    def clear(self) -> None:
        with self._lock:
            self._events.clear()
            self._requests.clear()
            self._responses.clear()
            self._audits.clear()

    def summary(self) -> Dict[str, int]:
        with self._lock:
            return {
                "events":    len(self._events),
                "requests":  len(self._requests),
                "responses": len(self._responses),
                "audits":    len(self._audits),
            }
