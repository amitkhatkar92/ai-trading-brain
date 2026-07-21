"""
decision_optimization_history.py — iios.decision.optimization
==============================================================
Thread-safe bounded history of optimization events and responses.

C9 Decision Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Deque, List, Optional

from .constants import DEFAULT_MAX_HISTORY, OptimizationEventType
from .decision_optimization_events import DecisionOptimizationEvent


class DecisionOptimizationHistory:
    """
    Thread-safe bounded history for :class:`DecisionOptimizationEvent` and
    optimization response dicts.

    Parameters
    ----------
    max_events :    Maximum events retained (FIFO eviction).
    max_responses : Maximum response dicts retained.
    """

    def __init__(
        self,
        max_events:    int = DEFAULT_MAX_HISTORY,
        max_responses: int = DEFAULT_MAX_HISTORY,
    ) -> None:
        self._lock              = threading.Lock()
        self._events: Deque[DecisionOptimizationEvent] = deque(maxlen=max_events)
        self._responses: Deque[dict]                   = deque(maxlen=max_responses)

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def record_event(self, event: DecisionOptimizationEvent) -> None:
        with self._lock:
            self._events.append(event)

    def events(self) -> List[DecisionOptimizationEvent]:
        with self._lock:
            return list(self._events)

    def latest_event(self) -> Optional[DecisionOptimizationEvent]:
        with self._lock:
            return self._events[-1] if self._events else None

    def event_count(self) -> int:
        with self._lock:
            return len(self._events)

    def events_for_decision(self, decision_id: str) -> List[DecisionOptimizationEvent]:
        with self._lock:
            return [e for e in self._events if e.decision_id == decision_id]

    def events_by_type(self, event_type: OptimizationEventType) -> List[DecisionOptimizationEvent]:
        with self._lock:
            return [e for e in self._events if e.event_type == event_type]

    # ------------------------------------------------------------------
    # Responses (stored as dicts for flexibility)
    # ------------------------------------------------------------------

    def record_response(self, response: dict) -> None:
        with self._lock:
            self._responses.append(response)

    def responses(self) -> List[dict]:
        with self._lock:
            return list(self._responses)

    def latest_response(self) -> Optional[dict]:
        with self._lock:
            return self._responses[-1] if self._responses else None

    def response_count(self) -> int:
        with self._lock:
            return len(self._responses)

    def responses_for_decision(self, decision_id: str) -> List[dict]:
        with self._lock:
            return [
                r for r in self._responses
                if r.get("decision_id") == decision_id
            ]

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def clear(self) -> None:
        with self._lock:
            self._events.clear()
            self._responses.clear()
