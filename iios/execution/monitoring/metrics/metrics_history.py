"""iios/execution/monitoring/metrics/metrics_history.py
==================================================
MetricsHistory — thread-safe bounded history of snapshots, responses,
and domain events.

C6 Execution Intelligence — Phase 6, Module 3
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Callable, List, Optional

from .constants import DEFAULT_MAX_HISTORY


class MetricsHistory:
    """
    Thread-safe bounded deque for MetricsSnapshot, MetricsResponse,
    and MetricsEvent objects.
    """

    def __init__(
        self,
        max_snapshots:  int = DEFAULT_MAX_HISTORY,
        max_responses:  int = DEFAULT_MAX_HISTORY,
        max_events:     int = DEFAULT_MAX_HISTORY,
    ) -> None:
        self._max_snapshots = max(1, max_snapshots)
        self._max_responses = max(1, max_responses)
        self._max_events    = max(1, max_events)

        self._snapshots: deque = deque(maxlen=self._max_snapshots)
        self._responses: deque = deque(maxlen=self._max_responses)
        self._events:    deque = deque(maxlen=self._max_events)
        self._lock = threading.Lock()

    # ── Writers ───────────────────────────────────────────────────────────────

    def append_snapshot(self, snapshot) -> None:
        with self._lock:
            self._snapshots.append(snapshot)

    def append_response(self, response) -> None:
        with self._lock:
            self._responses.append(response)

    def append_event(self, event) -> None:
        with self._lock:
            self._events.append(event)

    def clear(self) -> None:
        with self._lock:
            self._snapshots.clear()
            self._responses.clear()
            self._events.clear()

    # ── Snapshot queries ──────────────────────────────────────────────────────

    def snapshots(self) -> list:
        with self._lock:
            return list(self._snapshots)

    def latest_snapshot(self) -> Optional[object]:
        with self._lock:
            return self._snapshots[-1] if self._snapshots else None

    def snapshots_for_session(self, session_id: str) -> list:
        with self._lock:
            return [s for s in self._snapshots if s.session_id == session_id]

    def snapshots_for_portfolio(self, portfolio_id: str) -> list:
        with self._lock:
            return [s for s in self._snapshots if s.portfolio_id == portfolio_id]

    def latest_snapshot_for_session(self, session_id: str) -> Optional[object]:
        with self._lock:
            matching = [s for s in self._snapshots if s.session_id == session_id]
            return matching[-1] if matching else None

    # ── Response queries ──────────────────────────────────────────────────────

    def responses(self) -> list:
        with self._lock:
            return list(self._responses)

    def latest_response(self) -> Optional[object]:
        with self._lock:
            return self._responses[-1] if self._responses else None

    def responses_for_session(self, session_id: str) -> list:
        with self._lock:
            return [r for r in self._responses if r.session_id == session_id]

    # ── Event queries ─────────────────────────────────────────────────────────

    def events(self) -> list:
        with self._lock:
            return list(self._events)

    def latest_event(self) -> Optional[object]:
        with self._lock:
            return self._events[-1] if self._events else None

    def events_for_session(self, session_id: str) -> list:
        with self._lock:
            return [e for e in self._events if e.session_id == session_id]

    def events_matching(self, predicate: Callable) -> list:
        with self._lock:
            return [e for e in self._events if predicate(e)]

    # ── Counts ────────────────────────────────────────────────────────────────

    @property
    def snapshot_count(self) -> int:
        with self._lock:
            return len(self._snapshots)

    @property
    def response_count(self) -> int:
        with self._lock:
            return len(self._responses)

    @property
    def event_count(self) -> int:
        with self._lock:
            return len(self._events)
