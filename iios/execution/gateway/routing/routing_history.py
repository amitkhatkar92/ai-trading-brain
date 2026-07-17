"""iios/execution/gateway/routing/routing_history.py
==================================================
RoutingHistory — thread-safe bounded deque of RoutingDecision
and RoutingEvent objects.

C6 Execution Intelligence — Phase 5, Module 4
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Callable, List, Optional

from .constants import DEFAULT_MAX_HISTORY
from .routing_events import RoutingEvent
from .routing_response import RoutingDecision


class RoutingHistory:
    """
    Thread-safe bounded history of routing decisions and events.

    When max_decisions or max_events is reached, the oldest entry
    is discarded.
    """

    def __init__(
        self,
        max_decisions: int = DEFAULT_MAX_HISTORY,
        max_events:    int = DEFAULT_MAX_HISTORY,
    ) -> None:
        self._max_decisions = max(1, max_decisions)
        self._max_events    = max(1, max_events)
        self._decisions: deque[RoutingDecision] = deque(maxlen=self._max_decisions)
        self._events:    deque[RoutingEvent]    = deque(maxlen=self._max_events)
        self._lock       = threading.Lock()

    # ── Writers ───────────────────────────────────────────────────────────────

    def append_decision(self, decision: RoutingDecision) -> None:
        with self._lock:
            self._decisions.append(decision)

    def append_event(self, event: RoutingEvent) -> None:
        with self._lock:
            self._events.append(event)

    # ── Readers ───────────────────────────────────────────────────────────────

    def decisions(self) -> List[RoutingDecision]:
        with self._lock:
            return list(self._decisions)

    def events(self) -> List[RoutingEvent]:
        with self._lock:
            return list(self._events)

    def decisions_for_broker(self, broker_id: str) -> List[RoutingDecision]:
        with self._lock:
            return [
                d for d in self._decisions
                if d.selected_broker_id == broker_id
            ]

    def successful_decisions(self) -> List[RoutingDecision]:
        with self._lock:
            return [d for d in self._decisions if d.is_routed]

    def failed_decisions(self) -> List[RoutingDecision]:
        with self._lock:
            return [d for d in self._decisions if d.is_failed]

    def failover_decisions(self) -> List[RoutingDecision]:
        with self._lock:
            return [d for d in self._decisions if d.is_failover]

    def latest_decision(self) -> Optional[RoutingDecision]:
        with self._lock:
            return self._decisions[-1] if self._decisions else None

    def latest_event(self) -> Optional[RoutingEvent]:
        with self._lock:
            return self._events[-1] if self._events else None

    def events_by_type(
        self,
        predicate: Callable[[RoutingEvent], bool],
    ) -> List[RoutingEvent]:
        with self._lock:
            return [e for e in self._events if predicate(e)]

    # ── State ─────────────────────────────────────────────────────────────────

    @property
    def decision_count(self) -> int:
        with self._lock:
            return len(self._decisions)

    @property
    def event_count(self) -> int:
        with self._lock:
            return len(self._events)

    def clear(self) -> None:
        with self._lock:
            self._decisions.clear()
            self._events.clear()
