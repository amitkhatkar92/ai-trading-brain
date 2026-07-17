"""iios/execution/gateway/brokers/broker_history.py
==================================================
BrokerHistory — bounded, thread-safe history store for
BrokerEvent and BrokerResponse objects.

C6 Execution Intelligence — Phase 5, Module 3
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Any, Callable, Dict, List, Optional

from .constants import DEFAULT_MAX_HISTORY
from .broker_events import BrokerEvent
from .broker_response import BrokerResponse


class BrokerHistory:
    """
    Bounded, thread-safe history store for BrokerEvent and BrokerResponse.

    When the store reaches ``max_size``, the oldest entry of the
    relevant type is evicted (FIFO eviction).
    """

    def __init__(self, max_size: int = DEFAULT_MAX_HISTORY) -> None:
        self._max_size  = max(1, max_size)
        self._events:   deque[BrokerEvent]    = deque()
        self._responses: deque[BrokerResponse] = deque()
        self._evicted_events    = 0
        self._evicted_responses = 0
        self._lock              = threading.Lock()

    # ── Append ────────────────────────────────────────────────────────────────

    def append_event(self, event: BrokerEvent) -> None:
        with self._lock:
            if len(self._events) >= self._max_size:
                self._events.popleft()
                self._evicted_events += 1
            self._events.append(event)

    def append_response(self, response: BrokerResponse) -> None:
        with self._lock:
            if len(self._responses) >= self._max_size:
                self._responses.popleft()
                self._evicted_responses += 1
            self._responses.append(response)

    # ── Query — events ────────────────────────────────────────────────────────

    def events(self) -> List[BrokerEvent]:
        with self._lock:
            return list(self._events)

    def latest_event(self) -> Optional[BrokerEvent]:
        with self._lock:
            return self._events[-1] if self._events else None

    def events_for_broker(self, broker_id: str) -> List[BrokerEvent]:
        with self._lock:
            return [e for e in self._events if e.broker_id == broker_id]

    def events_by_type(
        self,
        predicate: Callable[[BrokerEvent], bool],
    ) -> List[BrokerEvent]:
        with self._lock:
            return [e for e in self._events if predicate(e)]

    # ── Query — responses ─────────────────────────────────────────────────────

    def responses(self) -> List[BrokerResponse]:
        with self._lock:
            return list(self._responses)

    def latest_response(self) -> Optional[BrokerResponse]:
        with self._lock:
            return self._responses[-1] if self._responses else None

    def responses_for_broker(self, broker_id: str) -> List[BrokerResponse]:
        with self._lock:
            return [r for r in self._responses if r.broker_id == broker_id]

    def responses_for_request(self, request_id: str) -> List[BrokerResponse]:
        with self._lock:
            return [r for r in self._responses if r.request_id == request_id]

    def successful_responses(self) -> List[BrokerResponse]:
        with self._lock:
            return [r for r in self._responses if r.is_success]

    def failed_responses(self) -> List[BrokerResponse]:
        with self._lock:
            return [r for r in self._responses if r.is_failure or r.is_error]

    # ── Counts ────────────────────────────────────────────────────────────────

    @property
    def event_count(self) -> int:
        with self._lock:
            return len(self._events)

    @property
    def response_count(self) -> int:
        with self._lock:
            return len(self._responses)

    @property
    def evicted_events(self) -> int:
        with self._lock:
            return self._evicted_events

    @property
    def evicted_responses(self) -> int:
        with self._lock:
            return self._evicted_responses

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "max_size":         self._max_size,
                "event_count":      len(self._events),
                "response_count":   len(self._responses),
                "evicted_events":   self._evicted_events,
                "evicted_responses": self._evicted_responses,
            }
