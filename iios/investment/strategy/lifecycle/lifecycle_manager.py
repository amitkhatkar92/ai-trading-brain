"""iios/investment/strategy/lifecycle/lifecycle_manager.py
State machine for strategy lifecycle transitions.
"""
from __future__ import annotations

import threading
import time
from typing import Any

from iios.investment.strategy.strategy_constants import (
    LIFECYCLE_TRANSITIONS,
    LifecycleEvent,
    StrategyStatus,
)
from iios.investment.strategy.strategy_exceptions import (
    StrategyLifecycleInvalidTransitionError,
    StrategyNotFoundError,
)
from iios.investment.strategy.core.strategy_profile import StrategyProfile
from iios.investment.strategy.lifecycle.lifecycle_history import (
    LifecycleHistory,
    LifecycleHistoryEntry,
)

# Map (from, to) pair → LifecycleEvent
_EVENT_MAP: dict[tuple[str, str], LifecycleEvent] = {
    (StrategyStatus.DRAFT.value,          StrategyStatus.TESTING.value):       LifecycleEvent.STARTED_TESTING,
    (StrategyStatus.TESTING.value,        StrategyStatus.PAPER_TRADING.value): LifecycleEvent.STARTED_PAPER,
    (StrategyStatus.TESTING.value,        StrategyStatus.DRAFT.value):         LifecycleEvent.CREATED,
    (StrategyStatus.PAPER_TRADING.value,  StrategyStatus.VALIDATION.value):    LifecycleEvent.STARTED_VALIDATION,
    (StrategyStatus.PAPER_TRADING.value,  StrategyStatus.TESTING.value):       LifecycleEvent.STARTED_TESTING,
    (StrategyStatus.VALIDATION.value,     StrategyStatus.APPROVED.value):      LifecycleEvent.APPROVED,
    (StrategyStatus.VALIDATION.value,     StrategyStatus.PAPER_TRADING.value): LifecycleEvent.STARTED_PAPER,
    (StrategyStatus.APPROVED.value,       StrategyStatus.PRODUCTION.value):    LifecycleEvent.PROMOTED_PRODUCTION,
    (StrategyStatus.APPROVED.value,       StrategyStatus.VALIDATION.value):    LifecycleEvent.STARTED_VALIDATION,
    (StrategyStatus.PRODUCTION.value,     StrategyStatus.SUSPENDED.value):     LifecycleEvent.SUSPENDED,
    (StrategyStatus.PRODUCTION.value,     StrategyStatus.DEPRECATED.value):    LifecycleEvent.DEPRECATED,
    (StrategyStatus.SUSPENDED.value,      StrategyStatus.PRODUCTION.value):    LifecycleEvent.RESUMED,
    (StrategyStatus.SUSPENDED.value,      StrategyStatus.DEPRECATED.value):    LifecycleEvent.DEPRECATED,
    (StrategyStatus.DEPRECATED.value,     StrategyStatus.ARCHIVED.value):      LifecycleEvent.ARCHIVED,
    (StrategyStatus.DEPRECATED.value,     StrategyStatus.RETIRED.value):       LifecycleEvent.RETIRED,
    (StrategyStatus.ARCHIVED.value,       StrategyStatus.RETIRED.value):       LifecycleEvent.RETIRED,
}


class LifecycleManager:
    """
    Validates and applies lifecycle transitions for registered strategies.

    The state machine is driven by LIFECYCLE_TRANSITIONS from constants.
    Every transition is recorded in LifecycleHistory.
    """

    def __init__(
        self,
        profiles: dict[str, StrategyProfile] | None = None,
        history:  LifecycleHistory            | None = None,
    ) -> None:
        self._lock     = threading.RLock()
        self._profiles = profiles if profiles is not None else {}
        self._history  = history  or LifecycleHistory()

    def register_profile(self, profile: StrategyProfile) -> None:
        with self._lock:
            self._profiles[profile.strategy_id] = profile

    def transition(
        self,
        strategy_id: str,
        to_status:   StrategyStatus,
        reason:      str            = "",
        actor:       str            = "system",
        metadata:    dict[str, Any] | None = None,
    ) -> bool:
        """
        Apply the transition if valid.

        Returns True on success.
        Raises StrategyLifecycleInvalidTransitionError on invalid transition.
        Raises StrategyNotFoundError if strategy_id is not registered.
        """
        with self._lock:
            if strategy_id not in self._profiles:
                raise StrategyNotFoundError(
                    f"Strategy not found for lifecycle transition: {strategy_id}",
                    strategy_id=strategy_id,
                )

            profile     = self._profiles[strategy_id]
            from_status = profile.lifecycle_status

            # Guard retired strategies — no further transitions
            if from_status == StrategyStatus.RETIRED:
                raise StrategyLifecycleInvalidTransitionError(
                    from_status=from_status.value,
                    to_status=to_status.value,
                )

            allowed = LIFECYCLE_TRANSITIONS.get(from_status.value, frozenset())
            if to_status.value not in allowed:
                raise StrategyLifecycleInvalidTransitionError(
                    from_status=from_status.value,
                    to_status=to_status.value,
                )

            # Apply
            profile.set_status(to_status)

            # Record
            event = _EVENT_MAP.get(
                (from_status.value, to_status.value),
                LifecycleEvent.CREATED,
            )
            self._history.record(LifecycleHistoryEntry(
                strategy_id = strategy_id,
                from_status = from_status,
                to_status   = to_status,
                event       = event,
                reason      = reason,
                actor       = actor,
                metadata    = metadata or {},
            ))

        return True

    def is_valid_transition(
        self,
        from_status: StrategyStatus,
        to_status:   StrategyStatus,
    ) -> bool:
        allowed = LIFECYCLE_TRANSITIONS.get(from_status.value, frozenset())
        return to_status.value in allowed

    def get_history(self, strategy_id: str, n: int = 20) -> list[LifecycleHistoryEntry]:
        return self._history.get(strategy_id, n)

    def statistics(self) -> dict[str, Any]:
        return self._history.statistics()
