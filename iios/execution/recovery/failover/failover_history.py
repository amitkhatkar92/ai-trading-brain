"""
iios/execution/recovery/failover/failover_history.py
====================================================
FailoverHistory — bounded append-only store for all failover records.

C7 Execution Recovery & Resilience — Phase 1, Module 4
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Deque, List, Optional

from .constants import DEFAULT_MAX_HISTORY, DEFAULT_MAX_EVENTS


class FailoverHistory:
    """Thread-safe bounded deque store for failover framework entities."""

    def __init__(
        self,
        max_requests:   int = DEFAULT_MAX_HISTORY,
        max_responses:  int = DEFAULT_MAX_HISTORY,
        max_events:     int = DEFAULT_MAX_EVENTS,
        max_results:    int = DEFAULT_MAX_HISTORY,
    ) -> None:
        self._lock = threading.Lock()
        self._requests:  Deque = deque(maxlen=max_requests)
        self._responses: Deque = deque(maxlen=max_responses)
        self._events:    Deque = deque(maxlen=max_events)
        self._results:   Deque = deque(maxlen=max_results)

    # ── Append ────────────────────────────────────────────────────────────────

    def append_request(self, request: object) -> None:
        with self._lock:
            self._requests.append(request)

    def append_response(self, response: object) -> None:
        with self._lock:
            self._responses.append(response)

    def append_event(self, event: object) -> None:
        with self._lock:
            self._events.append(event)

    def append_result(self, result: object) -> None:
        with self._lock:
            self._results.append(result)

    # ── Read ──────────────────────────────────────────────────────────────────

    def requests(self) -> List[object]:
        with self._lock:
            return list(self._requests)

    def responses(self) -> List[object]:
        with self._lock:
            return list(self._responses)

    def events(self) -> List[object]:
        with self._lock:
            return list(self._events)

    def results(self) -> List[object]:
        with self._lock:
            return list(self._results)

    def latest_request(self) -> Optional[object]:
        with self._lock:
            return self._requests[-1] if self._requests else None

    def latest_response(self) -> Optional[object]:
        with self._lock:
            return self._responses[-1] if self._responses else None

    def latest_event(self) -> Optional[object]:
        with self._lock:
            return self._events[-1] if self._events else None

    def latest_result(self) -> Optional[object]:
        with self._lock:
            return self._results[-1] if self._results else None

    # ── Filtered reads ────────────────────────────────────────────────────────

    def for_session(self, failover_session_id: str) -> List[object]:
        """All responses for a failover session (most recent first)."""
        with self._lock:
            return [
                r for r in reversed(self._responses)
                if getattr(r, "failover_session_id", "") == failover_session_id
            ]

    def for_decision(self, source_decision_id: str) -> List[object]:
        """All responses for a source M3 decision (most recent first)."""
        with self._lock:
            return [
                r for r in reversed(self._responses)
                if getattr(r, "source_decision_id", "") == source_decision_id
            ]

    def for_execution_session(self, execution_session_id: str) -> List[object]:
        """All responses for an execution session (most recent first)."""
        with self._lock:
            return [
                r for r in reversed(self._responses)
                if getattr(r, "result", None) is not None
                and getattr(
                    getattr(r, "result"),
                    "failover_session_id", ""
                ) == execution_session_id
            ]

    # ── Counts ────────────────────────────────────────────────────────────────

    @property
    def request_count(self) -> int:
        with self._lock:
            return len(self._requests)

    @property
    def response_count(self) -> int:
        with self._lock:
            return len(self._responses)

    @property
    def event_count(self) -> int:
        with self._lock:
            return len(self._events)

    @property
    def result_count(self) -> int:
        with self._lock:
            return len(self._results)

    # ── Utility ───────────────────────────────────────────────────────────────

    def clear(self) -> None:
        with self._lock:
            self._requests.clear()
            self._responses.clear()
            self._events.clear()
            self._results.clear()
