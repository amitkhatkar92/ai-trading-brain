"""
iios/execution/analytics/lifecycle/analytics_session.py
=======================================================
AnalyticsSession — core mutable domain object for an analytics lifecycle
session.

NOT a LifecycleAwareMixin; managed exclusively by AnalyticsLifecycle.

C8 Execution Analytics & Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

from .constants import (
    ACTIVE_STATES,
    ACTOR_LIFECYCLE,
    IMMUTABLE_STATES,
    TERMINAL_STATES,
    VALID_TRANSITIONS,
    VERSION,
    AnalyticsMode,
    AnalyticsScope,
    AnalyticsState,
    AnalyticsTrigger,
)
from .exceptions import AnalyticsInvalidTransitionError, AnalyticsSessionTerminalError
from .analytics_state import AnalyticsStateRecord
from .analytics_transition import AnalyticsTransition, make_analytics_transition


class AnalyticsSession:
    """
    Core domain object representing a single analytics lifecycle.

    State transitions are validated against ``VALID_TRANSITIONS``.
    ``start_time``  is set when entering ACTIVE.
    ``end_time``    is set when entering COMPLETED or FAILED.
    ``failure_reason`` is set when the session transitions to FAILED.
    """

    def __init__(
        self,
        *,
        session_id:            Optional[str]           = None,
        execution_session_id:  str,
        analytics_scope:       AnalyticsScope          = AnalyticsScope.EXECUTION,
        analytics_mode:        AnalyticsMode           = AnalyticsMode.ON_DEMAND,
        analytics_trigger:     AnalyticsTrigger        = AnalyticsTrigger.AUTOMATIC,
        analytics_reason:      str                     = "",
        workflow_id:           str                     = "",
        portfolio_id:          str                     = "",
        strategy_id:           str                     = "",
        analytics_version:     int                     = 1,
        metadata:              Optional[Dict[str, Any]]= None,
    ) -> None:
        self._session_id            = session_id or str(uuid.uuid4())
        self._execution_session_id  = execution_session_id
        self._analytics_scope       = analytics_scope
        self._analytics_mode        = analytics_mode
        self._analytics_trigger     = analytics_trigger
        self._analytics_reason      = analytics_reason
        self._workflow_id           = workflow_id
        self._portfolio_id          = portfolio_id
        self._strategy_id           = strategy_id
        self._analytics_version     = analytics_version
        self._metadata              = dict(metadata or {})

        now                             = time.time()
        self._state                     = AnalyticsState.CREATED
        self._start_time: Optional[float]     = None
        self._end_time:   Optional[float]     = None
        self._failure_reason: str             = ""
        self._created_at                      = now
        self._updated_at                      = now

        self._state_history: List[AnalyticsStateRecord] = [
            AnalyticsStateRecord(
                state      = AnalyticsState.CREATED,
                entered_at = now,
                actor      = ACTOR_LIFECYCLE,
            )
        ]
        self._transitions: List[AnalyticsTransition] = []

    # ── Identity ──────────────────────────────────────────────────────────────

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def execution_session_id(self) -> str:
        return self._execution_session_id

    @property
    def analytics_scope(self) -> AnalyticsScope:
        return self._analytics_scope

    @property
    def analytics_mode(self) -> AnalyticsMode:
        return self._analytics_mode

    @property
    def analytics_trigger(self) -> AnalyticsTrigger:
        return self._analytics_trigger

    @property
    def analytics_reason(self) -> str:
        return self._analytics_reason

    @property
    def workflow_id(self) -> str:
        return self._workflow_id

    @property
    def portfolio_id(self) -> str:
        return self._portfolio_id

    @property
    def strategy_id(self) -> str:
        return self._strategy_id

    @property
    def analytics_version(self) -> int:
        return self._analytics_version

    @property
    def metadata(self) -> Dict[str, Any]:
        return dict(self._metadata)

    # ── State ─────────────────────────────────────────────────────────────────

    @property
    def state(self) -> AnalyticsState:
        return self._state

    @property
    def is_active(self) -> bool:
        return self._state in ACTIVE_STATES

    @property
    def is_terminal(self) -> bool:
        return self._state in TERMINAL_STATES

    @property
    def is_completed(self) -> bool:
        return self._state == AnalyticsState.COMPLETED

    @property
    def is_failed(self) -> bool:
        return self._state == AnalyticsState.FAILED

    @property
    def is_archived(self) -> bool:
        return self._state == AnalyticsState.ARCHIVED

    @property
    def is_paused(self) -> bool:
        return self._state == AnalyticsState.PAUSED

    # ── Timing ────────────────────────────────────────────────────────────────

    @property
    def start_time(self) -> Optional[float]:
        return self._start_time

    @property
    def end_time(self) -> Optional[float]:
        return self._end_time

    @property
    def created_at(self) -> float:
        return self._created_at

    @property
    def updated_at(self) -> float:
        return self._updated_at

    @property
    def duration_seconds(self) -> Optional[float]:
        if self._start_time is not None and self._end_time is not None:
            return self._end_time - self._start_time
        return None

    # ── Failure ───────────────────────────────────────────────────────────────

    @property
    def failure_reason(self) -> str:
        return self._failure_reason

    # ── History ───────────────────────────────────────────────────────────────

    @property
    def state_history(self) -> List[AnalyticsStateRecord]:
        return list(self._state_history)

    @property
    def transitions(self) -> List[AnalyticsTransition]:
        return list(self._transitions)

    @property
    def transition_count(self) -> int:
        return len(self._transitions)

    # ── Mutation ──────────────────────────────────────────────────────────────

    def transition_to(
        self,
        target_state: AnalyticsState,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> AnalyticsTransition:
        """
        Validate and execute a state transition.

        Raises:
            AnalyticsSessionTerminalError     — session is in ARCHIVED state.
            AnalyticsInvalidTransitionError   — transition not allowed.
        """
        if self._state in IMMUTABLE_STATES:
            raise AnalyticsSessionTerminalError(self._session_id, self._state.value)

        allowed = VALID_TRANSITIONS.get(self._state, frozenset())
        if target_state not in allowed:
            raise AnalyticsInvalidTransitionError(
                self._state.value, target_state.value, self._session_id
            )

        from_state = self._state
        now        = time.time()

        transition = make_analytics_transition(
            session_id = self._session_id,
            from_state = from_state,
            to_state   = target_state,
            actor      = actor,
            reason     = reason,
        )

        self._state = target_state
        self._updated_at = now

        self._state_history.append(
            AnalyticsStateRecord(
                state      = target_state,
                entered_at = now,
                actor      = actor,
                reason     = reason,
            )
        )
        self._transitions.append(transition)

        # ── Side-effects ──────────────────────────────────────────────────────
        if target_state == AnalyticsState.ACTIVE and self._start_time is None:
            self._start_time = now
        if target_state in (AnalyticsState.COMPLETED, AnalyticsState.FAILED):
            self._end_time = now

        return transition

    def set_failure_reason(self, reason: str) -> None:
        self._failure_reason = reason

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id":            self._session_id,
            "execution_session_id":  self._execution_session_id,
            "analytics_scope":       self._analytics_scope.value,
            "analytics_mode":        self._analytics_mode.value,
            "analytics_trigger":     self._analytics_trigger.value,
            "analytics_reason":      self._analytics_reason,
            "workflow_id":           self._workflow_id,
            "portfolio_id":          self._portfolio_id,
            "strategy_id":           self._strategy_id,
            "analytics_version":     self._analytics_version,
            "state":                 self._state.value,
            "start_time":            self._start_time,
            "end_time":              self._end_time,
            "failure_reason":        self._failure_reason,
            "created_at":            self._created_at,
            "updated_at":            self._updated_at,
            "transition_count":      len(self._transitions),
            "framework_version":     VERSION,
        }
