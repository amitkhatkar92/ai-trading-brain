"""iios/execution/monitoring/lifecycle/monitoring_session.py
==================================================
MonitoringSession — core domain object for an execution monitoring session.

Mutable; holds current state, history of state records, and transitions.
NOT a LifecycleAwareMixin — it is managed by MonitoringLifecycle.

C6 Execution Intelligence — Phase 6, Module 1
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

from .constants import (
    ACTOR_LIFECYCLE,
    ENDED_STATES,
    RUNNING_STATES,
    TERMINAL_STATES,
    VALID_TRANSITIONS,
    MonitoringState,
)
from .exceptions import (
    InvalidMonitoringTransitionError,
    MonitoringSessionTerminalError,
)
from .monitoring_state import MonitoringStateRecord
from .monitoring_transition import make_monitoring_transition


class MonitoringSession:
    """
    Core domain object for a single execution monitoring session.

    State transitions are validated against VALID_TRANSITIONS and
    enforce the full state machine.  ``start_time`` is set when the
    session first enters ACTIVE; ``end_time`` is set when the session
    enters STOPPED or FAILED.
    """

    def __init__(
        self,
        *,
        session_id:           Optional[str]  = None,
        execution_session_id: str,
        portfolio_id:         str,
        gateway_id:           Optional[str]  = None,
        workflow_id:          Optional[str]  = None,
        strategy_id:          Optional[str]  = None,
        order_id:             Optional[str]  = None,
        monitoring_version:   int             = 1,
        metadata:             Optional[Dict[str, Any]] = None,
    ) -> None:
        self._session_id           = session_id or str(uuid.uuid4())
        self._execution_session_id = execution_session_id
        self._portfolio_id         = portfolio_id
        self._gateway_id           = gateway_id
        self._workflow_id          = workflow_id
        self._strategy_id          = strategy_id
        self._order_id             = order_id
        self._monitoring_version   = monitoring_version
        self._metadata             = dict(metadata or {})

        now = time.time()
        self._state                = MonitoringState.CREATED
        self._start_time: Optional[float] = None
        self._end_time:   Optional[float] = None
        self._failure_reason: str  = ""
        self._created_at           = now
        self._updated_at           = now

        self._state_history: List[MonitoringStateRecord] = [
            MonitoringStateRecord(state=MonitoringState.CREATED, entered_at=now)
        ]
        self._transitions: List[Any] = []

    # ── Identity ──────────────────────────────────────────────────────────────

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def execution_session_id(self) -> str:
        return self._execution_session_id

    @property
    def portfolio_id(self) -> str:
        return self._portfolio_id

    @property
    def gateway_id(self) -> Optional[str]:
        return self._gateway_id

    @property
    def workflow_id(self) -> Optional[str]:
        return self._workflow_id

    @property
    def strategy_id(self) -> Optional[str]:
        return self._strategy_id

    @property
    def order_id(self) -> Optional[str]:
        return self._order_id

    @property
    def monitoring_version(self) -> int:
        return self._monitoring_version

    # ── State ─────────────────────────────────────────────────────────────────

    @property
    def state(self) -> MonitoringState:
        return self._state

    @property
    def start_time(self) -> Optional[float]:
        return self._start_time

    @property
    def end_time(self) -> Optional[float]:
        return self._end_time

    @property
    def failure_reason(self) -> str:
        return self._failure_reason

    @property
    def created_at(self) -> float:
        return self._created_at

    @property
    def updated_at(self) -> float:
        return self._updated_at

    @property
    def metadata(self) -> Dict[str, Any]:
        return dict(self._metadata)

    # ── Derived predicates ────────────────────────────────────────────────────

    @property
    def is_active(self) -> bool:
        return self._state == MonitoringState.ACTIVE

    @property
    def is_running(self) -> bool:
        return self._state in RUNNING_STATES

    @property
    def is_terminal(self) -> bool:
        return self._state in TERMINAL_STATES

    @property
    def is_failed(self) -> bool:
        return self._state == MonitoringState.FAILED

    @property
    def is_stopped(self) -> bool:
        return self._state == MonitoringState.STOPPED

    @property
    def is_ended(self) -> bool:
        return self._state in ENDED_STATES

    @property
    def duration_ms(self) -> Optional[float]:
        if self._start_time is None:
            return None
        end = self._end_time or time.time()
        return (end - self._start_time) * 1_000.0

    # ── History ───────────────────────────────────────────────────────────────

    @property
    def state_history(self) -> List[MonitoringStateRecord]:
        return list(self._state_history)

    @property
    def transitions(self):
        return list(self._transitions)

    # ── State machine ─────────────────────────────────────────────────────────

    def transition_to(
        self,
        new_state: MonitoringState,
        *,
        actor:  str = ACTOR_LIFECYCLE,
        reason: str = "",
    ) -> None:
        """
        Transition to ``new_state``.  Validates against VALID_TRANSITIONS.

        Raises:
            MonitoringSessionTerminalError: if the session is already terminal.
            InvalidMonitoringTransitionError: if the transition is not allowed.
        """
        allowed = VALID_TRANSITIONS.get(self._state, frozenset())
        if new_state not in allowed:
            if not allowed:
                # No valid transitions from this state — it is truly terminal
                raise MonitoringSessionTerminalError(
                    self._session_id, self._state.value
                )
            raise InvalidMonitoringTransitionError(
                self._session_id, self._state.value, new_state.value
            )

        now = time.time()

        # Close current state record
        if self._state_history:
            closed = self._state_history[-1].with_exit(now)
            self._state_history[-1] = closed

        # Transition
        transition = make_monitoring_transition(
            self._session_id,
            self._state,
            new_state,
            actor=actor,
            reason=reason,
        )
        self._transitions.append(transition)
        self._state = new_state
        self._updated_at = now

        # Open new state record
        self._state_history.append(
            MonitoringStateRecord(state=new_state, entered_at=now)
        )

        # Side-effects
        if new_state == MonitoringState.ACTIVE and self._start_time is None:
            self._start_time = now
        if new_state in (MonitoringState.STOPPED, MonitoringState.FAILED):
            self._end_time = now
        if new_state == MonitoringState.FAILED:
            self._failure_reason = reason

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id":           self._session_id,
            "execution_session_id": self._execution_session_id,
            "portfolio_id":         self._portfolio_id,
            "gateway_id":           self._gateway_id,
            "workflow_id":          self._workflow_id,
            "strategy_id":          self._strategy_id,
            "order_id":             self._order_id,
            "monitoring_version":   self._monitoring_version,
            "state":                self._state.value,
            "start_time":           self._start_time,
            "end_time":             self._end_time,
            "failure_reason":       self._failure_reason,
            "duration_ms":          self.duration_ms,
            "created_at":           self._created_at,
            "updated_at":           self._updated_at,
            "transition_count":     len(self._transitions),
        }

    def __repr__(self) -> str:
        return (
            f"MonitoringSession(session_id={self._session_id!r}, "
            f"state={self._state.value!r}, "
            f"portfolio_id={self._portfolio_id!r})"
        )
