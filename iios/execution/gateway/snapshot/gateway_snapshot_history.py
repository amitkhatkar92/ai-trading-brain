"""iios/execution/gateway/snapshot/gateway_snapshot_history.py
==================================================
GatewaySnapshotHistory — thread-safe bounded deque of
ExecutionGatewaySnapshot and SnapshotEvent objects.

C6 Execution Intelligence — Phase 5, Module 5
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Callable, List, Optional

from .constants import DEFAULT_MAX_HISTORY
from .execution_gateway_snapshot import ExecutionGatewaySnapshot
from .gateway_snapshot_events import SnapshotEvent


class GatewaySnapshotHistory:
    """
    Thread-safe bounded history of gateway snapshots and events.

    When the deque is full, the oldest entry is discarded.
    """

    def __init__(
        self,
        max_snapshots: int = DEFAULT_MAX_HISTORY,
        max_events:    int = DEFAULT_MAX_HISTORY,
    ) -> None:
        self._max_snapshots = max(1, max_snapshots)
        self._max_events    = max(1, max_events)
        self._snapshots: deque[ExecutionGatewaySnapshot] = deque(
            maxlen=self._max_snapshots
        )
        self._events: deque[SnapshotEvent] = deque(maxlen=self._max_events)
        self._lock = threading.Lock()

    # ── Writers ───────────────────────────────────────────────────────────────

    def append(self, snapshot: ExecutionGatewaySnapshot) -> None:
        with self._lock:
            self._snapshots.append(snapshot)

    def append_event(self, event: SnapshotEvent) -> None:
        with self._lock:
            self._events.append(event)

    # ── Readers ───────────────────────────────────────────────────────────────

    def all(self) -> List[ExecutionGatewaySnapshot]:
        with self._lock:
            return list(self._snapshots)

    def events(self) -> List[SnapshotEvent]:
        with self._lock:
            return list(self._events)

    def latest(self) -> Optional[ExecutionGatewaySnapshot]:
        with self._lock:
            return self._snapshots[-1] if self._snapshots else None

    def latest_event(self) -> Optional[SnapshotEvent]:
        with self._lock:
            return self._events[-1] if self._events else None

    def by_execution_id(self, execution_id: str) -> List[ExecutionGatewaySnapshot]:
        with self._lock:
            return [s for s in self._snapshots if s.execution_id == execution_id]

    def by_gateway_id(self, gateway_id: str) -> List[ExecutionGatewaySnapshot]:
        with self._lock:
            return [s for s in self._snapshots if s.gateway_id == gateway_id]

    def by_order_id(self, order_id: str) -> List[ExecutionGatewaySnapshot]:
        with self._lock:
            return [s for s in self._snapshots if s.order_id == order_id]

    def by_portfolio_id(self, portfolio_id: str) -> List[ExecutionGatewaySnapshot]:
        with self._lock:
            return [s for s in self._snapshots if s.portfolio_id == portfolio_id]

    def completed(self) -> List[ExecutionGatewaySnapshot]:
        with self._lock:
            return [s for s in self._snapshots if s.is_completed]

    def failed(self) -> List[ExecutionGatewaySnapshot]:
        with self._lock:
            return [s for s in self._snapshots if s.is_failed]

    def events_matching(
        self, predicate: Callable[[SnapshotEvent], bool]
    ) -> List[SnapshotEvent]:
        with self._lock:
            return [e for e in self._events if predicate(e)]

    # ── State ─────────────────────────────────────────────────────────────────

    @property
    def snapshot_count(self) -> int:
        with self._lock:
            return len(self._snapshots)

    @property
    def event_count(self) -> int:
        with self._lock:
            return len(self._events)

    def clear(self) -> None:
        with self._lock:
            self._snapshots.clear()
            self._events.clear()
