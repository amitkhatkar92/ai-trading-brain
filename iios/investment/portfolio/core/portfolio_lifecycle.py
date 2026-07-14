"""iios/investment/portfolio/core/portfolio_lifecycle.py

Lifecycle state machine for the Institutional Portfolio Framework.
Enforces valid transitions and maintains a per-portfolio lifecycle history.
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Optional, Tuple

from iios.investment.portfolio.core.portfolio_types import PortfolioLifecycleState


class LifecycleError(RuntimeError):
    """Raised when an invalid lifecycle transition is attempted."""

    def __init__(
        self,
        message: str = "",
        *,
        portfolio_id:  str                   = "",
        from_state:    PortfolioLifecycleState = PortfolioLifecycleState.REGISTERED,
        to_state:      PortfolioLifecycleState = PortfolioLifecycleState.REGISTERED,
    ) -> None:
        self.portfolio_id = portfolio_id
        self.from_state   = from_state
        self.to_state     = to_state
        super().__init__(
            message or
            f"Invalid transition: {from_state.value!r} → {to_state.value!r} "
            f"for portfolio {portfolio_id!r}"
        )


@dataclass(frozen=True)
class LifecycleTransition:
    """Record of a single lifecycle state transition."""

    transition_id: str                    = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:  str                    = ""
    from_state:    PortfolioLifecycleState= PortfolioLifecycleState.REGISTERED
    to_state:      PortfolioLifecycleState= PortfolioLifecycleState.INITIALIZED
    triggered_by:  str                    = "framework"
    reason:        str                    = ""
    transitioned_at: float                = field(default_factory=time.time)
    duration_ms:   float                  = 0.0

    def to_dict(self) -> dict:
        return {
            "transition_id":   self.transition_id,
            "portfolio_id":    self.portfolio_id,
            "from_state":      self.from_state.value,
            "to_state":        self.to_state.value,
            "triggered_by":    self.triggered_by,
            "reason":          self.reason,
            "transitioned_at": self.transitioned_at,
            "duration_ms":     self.duration_ms,
        }


# ---------------------------------------------------------------------------
# Valid transition matrix
# ---------------------------------------------------------------------------
#
# REGISTERED → INITIALIZED → READY → CONSTRUCTED → ACTIVE ↔ MONITORING
#                                                  ↕            ↕
#                                               PAUSED ─────────┘
#                                                  ↓
#                                              ARCHIVED  (terminal)
# Any state → FAILED (terminal) via error path
# REBALANCED is a transient checkpoint that collapses back to ACTIVE

S = PortfolioLifecycleState

_VALID_TRANSITIONS: Dict[PortfolioLifecycleState, FrozenSet[PortfolioLifecycleState]] = {
    S.REGISTERED:  frozenset({S.INITIALIZED, S.FAILED}),
    S.INITIALIZED: frozenset({S.READY, S.FAILED}),
    S.READY:       frozenset({S.CONSTRUCTED, S.FAILED}),
    S.CONSTRUCTED: frozenset({S.ACTIVE, S.FAILED}),
    S.ACTIVE:      frozenset({S.MONITORING, S.REBALANCED, S.PAUSED, S.ARCHIVED, S.FAILED}),
    S.MONITORING:  frozenset({S.ACTIVE, S.REBALANCED, S.PAUSED, S.ARCHIVED, S.FAILED}),
    S.REBALANCED:  frozenset({S.ACTIVE, S.MONITORING, S.PAUSED, S.ARCHIVED, S.FAILED}),
    S.PAUSED:      frozenset({S.ACTIVE, S.ARCHIVED, S.FAILED}),
    S.ARCHIVED:    frozenset(),       # terminal
    S.FAILED:      frozenset(),       # terminal
}


class PortfolioLifecycle:
    """
    Thread-safe lifecycle state machine for a single portfolio.

    Tracks the current state, validates transitions, and maintains
    an ordered history of all transitions.
    """

    def __init__(self, portfolio_id: str) -> None:
        self._lock         = threading.RLock()
        self._portfolio_id = portfolio_id
        self._state        = S.REGISTERED
        self._history:     List[LifecycleTransition] = []
        self._entered_at   = time.time()

    # ------------------------------------------------------------------
    # State inspection
    # ------------------------------------------------------------------

    @property
    def current_state(self) -> PortfolioLifecycleState:
        with self._lock:
            return self._state

    @property
    def is_terminal(self) -> bool:
        with self._lock:
            return self._state.is_terminal

    @property
    def is_operational(self) -> bool:
        with self._lock:
            return self._state.is_operational

    def can_transition_to(self, target: PortfolioLifecycleState) -> bool:
        with self._lock:
            return target in _VALID_TRANSITIONS.get(self._state, frozenset())

    # ------------------------------------------------------------------
    # Transition
    # ------------------------------------------------------------------

    def transition(
        self,
        target:       PortfolioLifecycleState,
        *,
        triggered_by: str = "framework",
        reason:       str = "",
    ) -> LifecycleTransition:
        """
        Advance to *target* state.  Raises LifecycleError if invalid.
        Returns the LifecycleTransition record.
        """
        with self._lock:
            allowed = _VALID_TRANSITIONS.get(self._state, frozenset())
            if target not in allowed:
                raise LifecycleError(
                    portfolio_id = self._portfolio_id,
                    from_state   = self._state,
                    to_state     = target,
                )
            t0            = time.time()
            duration_ms   = (t0 - self._entered_at) * 1_000
            rec           = LifecycleTransition(
                portfolio_id    = self._portfolio_id,
                from_state      = self._state,
                to_state        = target,
                triggered_by    = triggered_by,
                reason          = reason,
                duration_ms     = duration_ms,
            )
            self._state     = target
            self._entered_at= t0
            self._history.append(rec)
            return rec

    def force_to(
        self,
        target:       PortfolioLifecycleState,
        *,
        triggered_by: str = "force",
        reason:       str = "administrative override",
    ) -> LifecycleTransition:
        """
        Bypass validation and set state directly.  Administrative use only.
        """
        with self._lock:
            rec = LifecycleTransition(
                portfolio_id  = self._portfolio_id,
                from_state    = self._state,
                to_state      = target,
                triggered_by  = triggered_by,
                reason        = reason,
            )
            self._state      = target
            self._entered_at = time.time()
            self._history.append(rec)
            return rec

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def history(self) -> List[LifecycleTransition]:
        with self._lock:
            return list(self._history)

    def last_transition(self) -> Optional[LifecycleTransition]:
        with self._lock:
            return self._history[-1] if self._history else None

    def transitions_to(
        self, state: PortfolioLifecycleState
    ) -> List[LifecycleTransition]:
        with self._lock:
            return [t for t in self._history if t.to_state == state]

    def time_in_current_state_seconds(self) -> float:
        with self._lock:
            return time.time() - self._entered_at

    def to_dict(self) -> dict:
        with self._lock:
            return {
                "portfolio_id":  self._portfolio_id,
                "current_state": self._state.value,
                "is_terminal":   self._state.is_terminal,
                "transitions":   len(self._history),
            }
