"""
learning_evaluation_event_bus.py -- iios.ai.learning_evaluation.events
========================================================================
Thread-safe pub/sub event bus for the A7 Learning & Evaluation Platform.

A7 Learning & Evaluation Platform — Phase 3, Module 7
"""
from __future__ import annotations

import threading
from typing import Callable, Dict, List, Type

from .learning_evaluation_events import (
    LearningEvaluationEvent,
    LearningEvaluationEventType,
)


class LearningEvaluationEventBus:
    """
    Thread-safe synchronous event bus.

    Subscribers register a callback for a specific event type.
    Events are dispatched synchronously in the calling thread.
    Exceptions in subscriber callbacks are silently swallowed to ensure
    that a misbehaving subscriber cannot block the emitter.
    """

    def __init__(self) -> None:
        self._lock: threading.Lock = threading.Lock()
        self._handlers: Dict[LearningEvaluationEventType, List[Callable]] = {}
        self._history: List[LearningEvaluationEvent] = []
        self._max_history: int = 1000

    # ── subscription ──────────────────────────────────────────────────────────

    def subscribe(
        self,
        event_type: LearningEvaluationEventType,
        handler:    Callable[[LearningEvaluationEvent], None],
    ) -> None:
        with self._lock:
            self._handlers.setdefault(event_type, []).append(handler)

    def unsubscribe(
        self,
        event_type: LearningEvaluationEventType,
        handler:    Callable[[LearningEvaluationEvent], None],
    ) -> None:
        with self._lock:
            handlers = self._handlers.get(event_type, [])
            if handler in handlers:
                handlers.remove(handler)

    def subscribe_all(self, handler: Callable[[LearningEvaluationEvent], None]) -> None:
        """Subscribe to every event type."""
        for et in LearningEvaluationEventType:
            self.subscribe(et, handler)

    # ── publication ───────────────────────────────────────────────────────────

    def publish(self, event: LearningEvaluationEvent) -> None:
        """Dispatch event to all registered handlers and record in history."""
        with self._lock:
            handlers = list(self._handlers.get(event.event_type, []))
            # Trim history
            if len(self._history) >= self._max_history:
                self._history = self._history[-(self._max_history - 1):]
            self._history.append(event)

        for handler in handlers:
            try:
                handler(event)
            except Exception:
                pass  # isolate subscriber failures

    # ── introspection ─────────────────────────────────────────────────────────

    def history(
        self,
        event_type: LearningEvaluationEventType | None = None,
        limit: int = 100,
    ) -> List[LearningEvaluationEvent]:
        with self._lock:
            events = list(self._history)
        if event_type is not None:
            events = [e for e in events if e.event_type == event_type]
        return events[-limit:]

    def subscriber_count(self, event_type: LearningEvaluationEventType) -> int:
        with self._lock:
            return len(self._handlers.get(event_type, []))

    def clear_history(self) -> None:
        with self._lock:
            self._history.clear()
