"""iios/execution/monitoring/alerts/alert_history.py
==================================================
AlertHistory — thread-safe bounded deque for Alert, AlertSnapshot,
and AlertEvent objects.

C6 Execution Intelligence — Phase 6, Module 4
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Callable, List, Optional

from .constants import DEFAULT_MAX_HISTORY


class AlertHistory:
    """
    Thread-safe, bounded history store for alert framework objects.

    Separate bounded deques for alerts, snapshots, and events allow
    independent capacity control.
    """

    def __init__(
        self,
        max_alerts:    int = DEFAULT_MAX_HISTORY,
        max_snapshots: int = DEFAULT_MAX_HISTORY,
        max_events:    int = DEFAULT_MAX_HISTORY,
    ) -> None:
        self._alerts:    deque = deque(maxlen=max(1, max_alerts))
        self._snapshots: deque = deque(maxlen=max(1, max_snapshots))
        self._events:    deque = deque(maxlen=max(1, max_events))
        self._lock = threading.Lock()

    # ── Writers ───────────────────────────────────────────────────────────────

    def append_alert(self, alert) -> None:
        with self._lock:
            self._alerts.append(alert)

    def append_snapshot(self, snapshot) -> None:
        with self._lock:
            self._snapshots.append(snapshot)

    def append_event(self, event) -> None:
        with self._lock:
            self._events.append(event)

    def clear(self) -> None:
        with self._lock:
            self._alerts.clear()
            self._snapshots.clear()
            self._events.clear()

    # ── Alert queries ─────────────────────────────────────────────────────────

    def alerts(self) -> List:
        with self._lock:
            return list(self._alerts)

    def latest_alert(self) -> Optional[object]:
        with self._lock:
            return self._alerts[-1] if self._alerts else None

    def alerts_for_session(self, session_id: str) -> List:
        with self._lock:
            return [a for a in self._alerts if a.session_id == session_id]

    def alerts_by_type(self, alert_type) -> List:
        with self._lock:
            return [a for a in self._alerts if a.alert_type == alert_type]

    def alerts_by_severity(self, severity) -> List:
        with self._lock:
            return [a for a in self._alerts if a.severity == severity]

    # ── Snapshot queries ──────────────────────────────────────────────────────

    def snapshots(self) -> List:
        with self._lock:
            return list(self._snapshots)

    def latest_snapshot(self) -> Optional[object]:
        with self._lock:
            return self._snapshots[-1] if self._snapshots else None

    def snapshots_for_session(self, session_id: str) -> List:
        with self._lock:
            return [s for s in self._snapshots if s.session_id == session_id]

    # ── Event queries ─────────────────────────────────────────────────────────

    def events(self) -> List:
        with self._lock:
            return list(self._events)

    def latest_event(self) -> Optional[object]:
        with self._lock:
            return self._events[-1] if self._events else None

    def events_for_session(self, session_id: str) -> List:
        with self._lock:
            return [e for e in self._events if e.session_id == session_id]

    def events_for_alert(self, alert_id: str) -> List:
        with self._lock:
            return [e for e in self._events if e.alert_id == alert_id]

    def events_matching(self, predicate: Callable) -> List:
        with self._lock:
            return [e for e in self._events if predicate(e)]

    # ── Counts ────────────────────────────────────────────────────────────────

    @property
    def alert_count(self) -> int:
        with self._lock:
            return len(self._alerts)

    @property
    def snapshot_count(self) -> int:
        with self._lock:
            return len(self._snapshots)

    @property
    def event_count(self) -> int:
        with self._lock:
            return len(self._events)
