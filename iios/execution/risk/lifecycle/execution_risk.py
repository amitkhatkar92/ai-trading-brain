"""iios/execution/risk/lifecycle/execution_risk.py
==================================================
ExecutionRisk — the core domain object for the IIOS Execution Risk Lifecycle.

Tracks all lifecycle state for a single execution risk evaluation.
Exposes a controlled ``transition_to()`` method that enforces the state
machine and appends immutable history records.

This class is NOT a LifecycleAwareMixin; it is a pure domain object.
Thread-safety is provided via an internal RLock.

C6 Execution Intelligence — Phase 4, Module 1
"""
from __future__ import annotations

import threading
import time
from typing import Any, Callable, Dict, List, Optional

from .constants import (
    ACTOR_LIFECYCLE,
    ACTIVE_STATES,
    BLOCKING_STATES,
    OUTCOME_STATES,
    PASS_STATES,
    TERMINAL_STATES,
    VALID_TRANSITIONS,
    RiskCategory,
    RiskState,
)
from .exceptions import InvalidRiskTransitionError
from .execution_risk_event import (
    RiskEvent,
    make_risk_archived,
    make_risk_blocked,
    make_risk_evaluation_started,
    make_risk_expired,
    make_risk_overridden,
    make_risk_passed,
    make_risk_warning,
)
from .execution_risk_history import RiskHistory
from .execution_risk_metadata import RiskMetadata
from .execution_risk_state import RiskStateRecord
from .execution_risk_transition import RiskTransition, make_risk_transition


# ── Event type → factory mapping ──────────────────────────────────────────────

_STATE_EVENT_FACTORY: Dict[RiskState, Callable[..., RiskEvent]] = {
    RiskState.EVALUATING: make_risk_evaluation_started,
    RiskState.PASSED:     make_risk_passed,
    RiskState.WARNING:    make_risk_warning,
    RiskState.BLOCKED:    make_risk_blocked,
    RiskState.OVERRIDDEN: make_risk_overridden,
    RiskState.EXPIRED:    make_risk_expired,
    RiskState.ARCHIVED:   make_risk_archived,
}


class ExecutionRisk:
    """
    Core domain object representing a single institutional execution risk evaluation.

    Responsibilities
    ----------------
    * Hold all risk identity and lifecycle fields.
    * Enforce the state machine via ``transition_to()``.
    * Maintain an immutable, ordered transition and state history.
    * Emit domain events on lifecycle milestones.

    Non-responsibilities
    --------------------
    * No risk score calculations.
    * No broker communication.
    * No order execution.
    * No portfolio optimisation.
    """

    __slots__ = (
        # identity
        "_risk_id", "_execution_id", "_workflow_id", "_order_id",
        "_position_id", "_portfolio_id", "_strategy_id", "_decision_id",
        "_correlation_id",
        # category
        "_risk_category",
        # state
        "_state",
        # timing
        "_evaluation_time_ms", "_expiry_time",
        # timestamps
        "_created_at", "_updated_at",
        # internals
        "_history", "_metadata", "_lock",
        "_event_listeners",
    )

    def __init__(
        self,
        risk_id:       str,
        execution_id:  str,
        workflow_id:   str,
        order_id:      str,
        position_id:   str,
        portfolio_id:  str,
        strategy_id:   str,
        decision_id:   str,
        risk_category: RiskCategory,
        *,
        correlation_id: str            = "",
        expiry_time:    Optional[float] = None,
        max_history:    int            = 500,
    ) -> None:
        now = time.time()

        self._risk_id       = risk_id
        self._execution_id  = execution_id
        self._workflow_id   = workflow_id
        self._order_id      = order_id
        self._position_id   = position_id
        self._portfolio_id  = portfolio_id
        self._strategy_id   = strategy_id
        self._decision_id   = decision_id
        self._correlation_id = correlation_id

        self._risk_category = risk_category

        self._state              = RiskState.CREATED
        self._evaluation_time_ms = 0.0
        self._expiry_time        = expiry_time

        self._created_at = now
        self._updated_at = now

        self._history          = RiskHistory(max_history)
        self._metadata         = RiskMetadata()
        self._lock             = threading.RLock()
        self._event_listeners: List[Callable[[RiskEvent], None]] = []

        # Seed initial state record
        self._history.append_state(RiskStateRecord(state=RiskState.CREATED, entered_at=now))

    # ── Identity ──────────────────────────────────────────────────────────────

    @property
    def risk_id(self) -> str:
        return self._risk_id

    @property
    def execution_id(self) -> str:
        return self._execution_id

    @property
    def workflow_id(self) -> str:
        return self._workflow_id

    @property
    def order_id(self) -> str:
        return self._order_id

    @property
    def position_id(self) -> str:
        return self._position_id

    @property
    def portfolio_id(self) -> str:
        return self._portfolio_id

    @property
    def strategy_id(self) -> str:
        return self._strategy_id

    @property
    def decision_id(self) -> str:
        return self._decision_id

    @property
    def correlation_id(self) -> str:
        return self._correlation_id

    # ── Category & State ──────────────────────────────────────────────────────

    @property
    def risk_category(self) -> RiskCategory:
        return self._risk_category

    @property
    def state(self) -> RiskState:
        with self._lock:
            return self._state

    # ── Timing ────────────────────────────────────────────────────────────────

    @property
    def evaluation_time_ms(self) -> float:
        """Time recorded for the evaluation step (ms), or 0 if not set."""
        with self._lock:
            return self._evaluation_time_ms

    @property
    def expiry_time(self) -> Optional[float]:
        """Unix timestamp when this evaluation expires, or None."""
        with self._lock:
            return self._expiry_time

    # ── Timestamps ────────────────────────────────────────────────────────────

    @property
    def created_at(self) -> float:
        return self._created_at

    @property
    def updated_at(self) -> float:
        with self._lock:
            return self._updated_at

    # ── Derived status ────────────────────────────────────────────────────────

    @property
    def is_active(self) -> bool:
        """True if the evaluation is in PENDING_EVALUATION or EVALUATING."""
        with self._lock:
            return self._state in ACTIVE_STATES

    @property
    def is_passed(self) -> bool:
        """True if the evaluation outcome allows execution (PASSED/WARNING/OVERRIDDEN)."""
        with self._lock:
            return self._state in PASS_STATES

    @property
    def is_blocked(self) -> bool:
        """True if the evaluation is in BLOCKED state."""
        with self._lock:
            return self._state in BLOCKING_STATES

    @property
    def is_archived(self) -> bool:
        """True if the evaluation is in the terminal ARCHIVED state."""
        with self._lock:
            return self._state in TERMINAL_STATES

    @property
    def is_expired(self) -> bool:
        """True if the evaluation has expired by state or by wall-clock."""
        with self._lock:
            if self._state == RiskState.EXPIRED:
                return True
            if self._expiry_time is not None and time.time() >= self._expiry_time:
                return True
            return False

    # ── State machine ─────────────────────────────────────────────────────────

    def transition_to(
        self,
        new_state:          RiskState,
        *,
        actor:              str = ACTOR_LIFECYCLE,
        reason:             str = "",
        evaluation_time_ms: float = 0.0,
        metadata:           Dict[str, Any] | None = None,
    ) -> RiskTransition:
        """
        Transition to *new_state*, enforcing the state machine.

        Parameters
        ----------
        new_state:          Target state.
        actor:              Label of the requesting actor.
        reason:             Human-readable reason for the transition.
        evaluation_time_ms: Duration of evaluation to record on this transition.
        metadata:           Arbitrary key/value metadata for the transition.

        Returns
        -------
        RiskTransition
            The immutable transition record appended to history.

        Raises
        ------
        InvalidRiskTransitionError
            If the transition is not permitted by the state machine.
        """
        with self._lock:
            current = self._state
            allowed = VALID_TRANSITIONS.get(current, frozenset())

            if new_state not in allowed:
                raise InvalidRiskTransitionError(
                    self._risk_id, current, new_state,
                    correlation_id=self._correlation_id,
                )

            now        = time.time()
            transition = make_risk_transition(
                risk_id=self._risk_id,
                from_state=current,
                to_state=new_state,
                actor=actor,
                reason=reason,
                metadata=metadata or {},
            )

            self._history.update_last_state_exit(now)
            self._history.append_state(RiskStateRecord(state=new_state, entered_at=now))
            self._history.append_transition(transition)

            if evaluation_time_ms > 0.0:
                self._evaluation_time_ms = evaluation_time_ms

            self._state      = new_state
            self._updated_at = now

        # Emit event outside the lock
        factory = _STATE_EVENT_FACTORY.get(new_state)
        if factory is not None:
            event = factory(
                risk_id=self._risk_id,
                execution_id=self._execution_id,
                portfolio_id=self._portfolio_id,
                strategy_id=self._strategy_id,
                actor=actor,
            )
            self._emit_state_event(event)

        return transition

    # ── Events ────────────────────────────────────────────────────────────────

    def add_event_listener(self, listener: Callable[[RiskEvent], None]) -> None:
        """Register a callable to receive lifecycle events."""
        with self._lock:
            self._event_listeners.append(listener)

    def remove_event_listener(self, listener: Callable[[RiskEvent], None]) -> None:
        """Deregister a previously registered listener."""
        with self._lock:
            try:
                self._event_listeners.remove(listener)
            except ValueError:
                pass

    def _emit_state_event(self, event: RiskEvent) -> None:
        with self._lock:
            listeners = list(self._event_listeners)
        for listener in listeners:
            try:
                listener(event)
            except Exception:
                pass

    # ── History & metadata ────────────────────────────────────────────────────

    @property
    def history(self) -> RiskHistory:
        return self._history

    @property
    def metadata(self) -> RiskMetadata:
        return self._metadata

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        with self._lock:
            return {
                "risk_id":             self._risk_id,
                "execution_id":        self._execution_id,
                "workflow_id":         self._workflow_id,
                "order_id":            self._order_id,
                "position_id":         self._position_id,
                "portfolio_id":        self._portfolio_id,
                "strategy_id":         self._strategy_id,
                "decision_id":         self._decision_id,
                "correlation_id":      self._correlation_id,
                "risk_category":       self._risk_category.value,
                "state":               self._state.value,
                "evaluation_time_ms":  self._evaluation_time_ms,
                "expiry_time":         self._expiry_time,
                "created_at":          self._created_at,
                "updated_at":          self._updated_at,
                "is_active":           self._state in ACTIVE_STATES,
                "is_passed":           self._state in PASS_STATES,
                "is_blocked":          self._state in BLOCKING_STATES,
                "is_archived":         self._state in TERMINAL_STATES,
                "metadata":            self._metadata.to_dict(),
            }
