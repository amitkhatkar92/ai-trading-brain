"""
decision_policy_history.py — iios.decision.policies
=====================================================
Thread-safe bounded history of policy events and responses.

C9 Decision Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Deque, List, Optional

from .constants import DEFAULT_MAX_HISTORY, PolicyEventType
from .decision_policy_events   import DecisionPolicyEvent
from .decision_policy_response import DecisionPolicyResponse


class DecisionPolicyHistory:
    """
    Thread-safe bounded history for :class:`DecisionPolicyEvent` and
    :class:`DecisionPolicyResponse` objects.

    Parameters
    ----------
    max_events :    Maximum number of events retained (FIFO eviction).
    max_responses : Maximum number of responses retained (FIFO eviction).
    """

    def __init__(
        self,
        max_events:    int = DEFAULT_MAX_HISTORY,
        max_responses: int = DEFAULT_MAX_HISTORY,
    ) -> None:
        self._lock            = threading.Lock()
        self._events:    Deque[DecisionPolicyEvent]    = deque(maxlen=max_events)
        self._responses: Deque[DecisionPolicyResponse] = deque(maxlen=max_responses)

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def record_event(self, event: DecisionPolicyEvent) -> None:
        with self._lock:
            self._events.append(event)

    def events(self) -> List[DecisionPolicyEvent]:
        with self._lock:
            return list(self._events)

    def latest_event(self) -> Optional[DecisionPolicyEvent]:
        with self._lock:
            return self._events[-1] if self._events else None

    def event_count(self) -> int:
        with self._lock:
            return len(self._events)

    def events_for_decision(self, decision_id: str) -> List[DecisionPolicyEvent]:
        with self._lock:
            return [e for e in self._events if e.decision_id == decision_id]

    def events_by_type(self, event_type: PolicyEventType) -> List[DecisionPolicyEvent]:
        with self._lock:
            return [e for e in self._events if e.event_type == event_type]

    # ------------------------------------------------------------------
    # Responses
    # ------------------------------------------------------------------

    def record_response(self, response: DecisionPolicyResponse) -> None:
        with self._lock:
            self._responses.append(response)

    def responses(self) -> List[DecisionPolicyResponse]:
        with self._lock:
            return list(self._responses)

    def latest_response(self) -> Optional[DecisionPolicyResponse]:
        with self._lock:
            return self._responses[-1] if self._responses else None

    def response_count(self) -> int:
        with self._lock:
            return len(self._responses)

    def responses_for_decision(self, decision_id: str) -> List[DecisionPolicyResponse]:
        with self._lock:
            return [r for r in self._responses if r.decision_id == decision_id]

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def clear(self) -> None:
        with self._lock:
            self._events.clear()
            self._responses.clear()
