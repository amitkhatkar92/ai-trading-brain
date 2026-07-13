"""iios/investment/strategy/risk/risk_events.py
Risk event types and event bus for the risk engine subsystems.
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class RiskEventType(str, Enum):
    RISK_EVALUATED     = "risk_evaluated"
    RISK_SCORE_CHANGED = "risk_score_changed"
    LIMIT_BREACHED     = "limit_breached"
    EMERGENCY_STOP     = "emergency_stop"
    STRESS_TEST_FAILED = "stress_test_failed"
    DRAWDOWN_ALERT     = "drawdown_alert"
    REGIME_MISMATCH    = "regime_mismatch"
    RISK_CLEARED       = "risk_cleared"
    PROFILE_UPDATED    = "risk_profile_updated"


@dataclass(frozen=True)
class RiskEvent:
    event_id:    str
    event_type:  RiskEventType
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


RiskEventHandler = Callable[[RiskEvent], None]


class RiskEventBus:
    """
    Lightweight in-process event bus for risk events.
    Thread-safe.  Handlers called synchronously on emitter's thread.
    """

    def __init__(self) -> None:
        self._handlers: Dict[RiskEventType, List[RiskEventHandler]] = {}
        self._global:   List[RiskEventHandler] = []
        self._lock = threading.RLock()

    def subscribe(
        self,
        handler:    RiskEventHandler,
        event_type: Optional[RiskEventType] = None,
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
        handler:    RiskEventHandler,
        event_type: Optional[RiskEventType] = None,
    ) -> None:
        with self._lock:
            if event_type is None:
                self._global = [h for h in self._global if h != handler]
            elif event_type in self._handlers:
                self._handlers[event_type] = [
                    h for h in self._handlers[event_type] if h != handler
                ]

    def emit(self, event: RiskEvent) -> None:
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
        event_type:  RiskEventType,
        strategy_id: str,
        payload:     Optional[Dict[str, Any]] = None,
    ) -> None:
        self.emit(RiskEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            strategy_id=strategy_id,
            payload=payload or {},
        ))
