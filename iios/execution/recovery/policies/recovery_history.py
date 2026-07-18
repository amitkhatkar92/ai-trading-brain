"""
iios/execution/recovery/policies/recovery_history.py
====================================================
RecoveryPolicyHistory — bounded append-only store for policy events,
requests, decisions, and evaluation reports.

C7 Execution Recovery & Resilience — Phase 1, Module 3
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Deque, List, Optional, Sequence

from .constants import DEFAULT_MAX_HISTORY, DEFAULT_MAX_EVENTS


class RecoveryPolicyHistory:
    """
    Thread-safe bounded deque store for policy framework entities.

    When a deque reaches its capacity, the oldest entry is discarded
    (left side).
    """

    def __init__(
        self,
        max_requests:  int = DEFAULT_MAX_HISTORY,
        max_decisions: int = DEFAULT_MAX_HISTORY,
        max_events:    int = DEFAULT_MAX_EVENTS,
        max_reports:   int = DEFAULT_MAX_HISTORY,
    ) -> None:
        self._lock = threading.Lock()

        self._requests:  Deque = deque(maxlen=max_requests)
        self._decisions: Deque = deque(maxlen=max_decisions)
        self._events:    Deque = deque(maxlen=max_events)
        self._reports:   Deque = deque(maxlen=max_reports)

    # ── Append ────────────────────────────────────────────────────────────────

    def append_request(self, request: object) -> None:
        with self._lock:
            self._requests.append(request)

    def append_decision(self, decision: object) -> None:
        with self._lock:
            self._decisions.append(decision)

    def append_event(self, event: object) -> None:
        with self._lock:
            self._events.append(event)

    def append_report(self, report: object) -> None:
        with self._lock:
            self._reports.append(report)

    # ── Read ──────────────────────────────────────────────────────────────────

    def requests(self) -> List[object]:
        with self._lock:
            return list(self._requests)

    def decisions(self) -> List[object]:
        with self._lock:
            return list(self._decisions)

    def events(self) -> List[object]:
        with self._lock:
            return list(self._events)

    def reports(self) -> List[object]:
        with self._lock:
            return list(self._reports)

    def latest_request(self) -> Optional[object]:
        with self._lock:
            return self._requests[-1] if self._requests else None

    def latest_decision(self) -> Optional[object]:
        with self._lock:
            return self._decisions[-1] if self._decisions else None

    def latest_event(self) -> Optional[object]:
        with self._lock:
            return self._events[-1] if self._events else None

    def latest_report(self) -> Optional[object]:
        with self._lock:
            return self._reports[-1] if self._reports else None

    # ── Filtered reads ────────────────────────────────────────────────────────

    def for_subsystem(self, subsystem_id: str) -> List[object]:
        """All decisions for a given subsystem_id (most recent first)."""
        with self._lock:
            return [
                d for d in reversed(self._decisions)
                if getattr(d, "subsystem_id", "") == subsystem_id
            ]

    def for_execution_session(self, execution_session_id: str) -> List[object]:
        """All decisions for a given execution_session_id (most recent first)."""
        with self._lock:
            return [
                d for d in reversed(self._decisions)
                if getattr(d, "execution_session_id", "") == execution_session_id
            ]

    # ── Counts ────────────────────────────────────────────────────────────────

    @property
    def request_count(self) -> int:
        with self._lock:
            return len(self._requests)

    @property
    def decision_count(self) -> int:
        with self._lock:
            return len(self._decisions)

    @property
    def event_count(self) -> int:
        with self._lock:
            return len(self._events)

    @property
    def report_count(self) -> int:
        with self._lock:
            return len(self._reports)

    # ── Utility ───────────────────────────────────────────────────────────────

    def clear(self) -> None:
        with self._lock:
            self._requests.clear()
            self._decisions.clear()
            self._events.clear()
            self._reports.clear()
