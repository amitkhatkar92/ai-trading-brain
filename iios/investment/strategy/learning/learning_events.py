"""iios/investment/strategy/learning/learning_events.py
Learning event bus — typed events published by the Learning Engine.
Pattern mirrors risk_events.py for consistency.
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class LearningEventType(str, Enum):
    OBSERVATION_RECORDED     = "observation_recorded"
    PATTERN_DETECTED         = "pattern_detected"
    DEGRADATION_DETECTED     = "degradation_detected"
    DEGRADATION_CLEARED      = "degradation_cleared"
    DRIFT_DETECTED           = "drift_detected"
    RECOMMENDATION_GENERATED = "recommendation_generated"
    KNOWLEDGE_UPDATED        = "knowledge_updated"
    MATURITY_LEVEL_CHANGED   = "maturity_level_changed"
    BASELINE_ESTABLISHED     = "baseline_established"
    LEARNING_SCORE_UPDATED   = "learning_score_updated"


@dataclass(frozen=True)
class LearningEvent:
    event_id:    str
    event_type:  LearningEventType
    strategy_id: str
    payload:     Dict[str, Any]
    emitted_at:  datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":    self.event_id,
            "event_type":  self.event_type.value,
            "strategy_id": self.strategy_id,
            "payload":     self.payload,
            "emitted_at":  self.emitted_at.isoformat(),
        }


LearningEventHandler = Callable[[LearningEvent], None]


class LearningEventBus:
    """Thread-safe in-process event bus for learning events."""

    def __init__(self) -> None:
        self._handlers: Dict[LearningEventType, List[LearningEventHandler]] = {}
        self._global:   List[LearningEventHandler] = []
        self._lock = threading.RLock()

    def subscribe(
        self,
        handler:    LearningEventHandler,
        event_type: Optional[LearningEventType] = None,
    ) -> None:
        with self._lock:
            if event_type is None:
                if handler not in self._global:
                    self._global.append(handler)
            else:
                self._handlers.setdefault(event_type, [])
                if handler not in self._handlers[event_type]:
                    self._handlers[event_type].append(handler)

    def unsubscribe(
        self,
        handler:    LearningEventHandler,
        event_type: Optional[LearningEventType] = None,
    ) -> None:
        with self._lock:
            if event_type is None:
                self._global = [h for h in self._global if h != handler]
            elif event_type in self._handlers:
                self._handlers[event_type] = [
                    h for h in self._handlers[event_type] if h != handler
                ]

    def emit(self, event: LearningEvent) -> None:
        with self._lock:
            handlers = list(self._global) + list(
                self._handlers.get(event.event_type, [])
            )
        for h in handlers:
            try:
                h(event)
            except Exception:
                pass

    def emit_simple(
        self,
        event_type:  LearningEventType,
        strategy_id: str,
        payload:     Optional[Dict[str, Any]] = None,
    ) -> None:
        self.emit(LearningEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            strategy_id=strategy_id,
            payload=payload or {},
        ))
