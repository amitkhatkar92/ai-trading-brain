"""iios/investment/strategy/core/strategy_lifecycle.py
Per-strategy lifecycle manager: enforces state transitions and
emits lifecycle events for each change.
"""
from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from .event_dispatcher import EventDispatcher
from .strategy_events import StrategyEvent, StrategyEventType
from .strategy_state import StrategyState, validate_transition

logger = logging.getLogger(__name__)

# State → event type mapping
_TRANSITION_EVENTS: Dict[StrategyState, StrategyEventType] = {
    StrategyState.REGISTERED:  StrategyEventType.STRATEGY_REGISTERED,
    StrategyState.LOADED:      StrategyEventType.STRATEGY_LOADED,
    StrategyState.INITIALIZED: StrategyEventType.STRATEGY_INITIALIZED,
    StrategyState.READY:       StrategyEventType.STRATEGY_READY,
    StrategyState.RUNNING:     StrategyEventType.STRATEGY_STARTED,
    StrategyState.PAUSED:      StrategyEventType.STRATEGY_PAUSED,
    StrategyState.COMPLETED:   StrategyEventType.STRATEGY_COMPLETED,
    StrategyState.FAILED:      StrategyEventType.STRATEGY_FAILED,
    StrategyState.ARCHIVED:    StrategyEventType.STRATEGY_ARCHIVED,
}


class LifecycleError(Exception):
    """Raised for illegal lifecycle state transitions."""


class StrategyLifecycle:
    """
    Per-strategy lifecycle tracker owned by StrategyFramework.
    Enforces valid transitions and publishes events for each change.
    """

    def __init__(
        self,
        strategy_id: str,
        dispatcher: EventDispatcher,
        initial_state: StrategyState = StrategyState.REGISTERED,
    ) -> None:
        self._strategy_id = strategy_id
        self._dispatcher = dispatcher
        self._lock = threading.RLock()
        self._state = initial_state
        self._entered_at: datetime = datetime.now(timezone.utc)
        self._history: List[Tuple[StrategyState, datetime]] = [
            (initial_state, self._entered_at)
        ]
        self._transition_count: int = 0
        self._emit(initial_state)

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def state(self) -> StrategyState:
        with self._lock:
            return self._state

    @property
    def entered_at(self) -> datetime:
        with self._lock:
            return self._entered_at

    @property
    def age_seconds(self) -> float:
        return (datetime.now(timezone.utc) - self.entered_at).total_seconds()

    @property
    def transition_count(self) -> int:
        with self._lock:
            return self._transition_count

    # ── Transition ────────────────────────────────────────────────────────────

    def transition(self, target: StrategyState, reason: str = "") -> None:
        """Attempt a state transition; raises LifecycleError on invalid move."""
        with self._lock:
            if not validate_transition(self._state, target):
                raise LifecycleError(
                    f"[{self._strategy_id}] Cannot transition "
                    f"{self._state.value} → {target.value}"
                )
            self._state = target
            self._entered_at = datetime.now(timezone.utc)
            self._history.append((target, self._entered_at))
            self._transition_count += 1
        self._emit(target, reason=reason)

    def _emit(self, state: StrategyState, reason: str = "") -> None:
        event_type = _TRANSITION_EVENTS.get(state)
        if event_type:
            self._dispatcher.emit(
                event_type,
                strategy_id=self._strategy_id,
                payload={"state": state.value, "reason": reason},
            )

    # ── History ───────────────────────────────────────────────────────────────

    def state_history(self) -> List[Tuple[StrategyState, datetime]]:
        with self._lock:
            return list(self._history)

    def to_dict(self) -> dict:
        with self._lock:
            return {
                "strategy_id": self._strategy_id,
                "state": self._state.value,
                "entered_at": self._entered_at.isoformat(),
                "transition_count": self._transition_count,
                "age_seconds": self.age_seconds,
            }
