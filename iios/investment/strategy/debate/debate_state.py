"""iios/investment/strategy/debate/debate_state.py
Debate state machine.
"""
from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import List, Optional

from iios.investment.strategy.debate.debate_constants import DebatePhase, DebateStatus


_VALID_TRANSITIONS: dict[DebatePhase, List[DebatePhase]] = {
    DebatePhase.INITIALIZATION:      [DebatePhase.OPENING_STATEMENTS],
    DebatePhase.OPENING_STATEMENTS:  [DebatePhase.EVIDENCE_COLLECTION],
    DebatePhase.EVIDENCE_COLLECTION: [DebatePhase.ARGUMENTS],
    DebatePhase.ARGUMENTS:           [DebatePhase.REBUTTALS],
    DebatePhase.REBUTTALS:           [DebatePhase.COUNTER_ARGUMENTS],
    DebatePhase.COUNTER_ARGUMENTS:   [DebatePhase.CONSENSUS_BUILDING],
    DebatePhase.CONSENSUS_BUILDING:  [DebatePhase.FINAL_OPINIONS],
    DebatePhase.FINAL_OPINIONS:      [DebatePhase.CLOSED],
    DebatePhase.CLOSED:              [],
}


class DebateStateError(RuntimeError):
    pass


class DebateState:
    """
    Thread-safe state machine for a debate session.
    Tracks phase transitions, status, and timestamps.
    """

    def __init__(self) -> None:
        self._lock           = threading.RLock()
        self._phase          = DebatePhase.INITIALIZATION
        self._status         = DebateStatus.PENDING
        self._phase_history: List[tuple[DebatePhase, datetime]] = [
            (DebatePhase.INITIALIZATION, datetime.now(timezone.utc))
        ]
        self._error:         Optional[str]    = None

    @property
    def phase(self) -> DebatePhase:
        with self._lock:
            return self._phase

    @property
    def status(self) -> DebateStatus:
        with self._lock:
            return self._status

    @property
    def error(self) -> Optional[str]:
        with self._lock:
            return self._error

    def advance(self, target: DebatePhase) -> None:
        with self._lock:
            allowed = _VALID_TRANSITIONS.get(self._phase, [])
            if target not in allowed:
                raise DebateStateError(
                    f"Cannot transition from {self._phase.value} to {target.value}. "
                    f"Allowed: {[p.value for p in allowed]}"
                )
            self._phase = target
            self._phase_history.append((target, datetime.now(timezone.utc)))
            if target == DebatePhase.CLOSED:
                self._status = DebateStatus.COMPLETED

    def start(self) -> None:
        with self._lock:
            if self._status != DebateStatus.PENDING:
                raise DebateStateError("Debate already started")
            self._status = DebateStatus.RUNNING

    def fail(self, reason: str) -> None:
        with self._lock:
            self._status = DebateStatus.FAILED
            self._error  = reason

    def cancel(self) -> None:
        with self._lock:
            self._status = DebateStatus.CANCELLED

    def phase_history(self) -> List[dict]:
        with self._lock:
            return [
                {"phase": p.value, "entered_at": t.isoformat()}
                for p, t in self._phase_history
            ]

    def phase_duration_ms(self, phase: DebatePhase) -> Optional[float]:
        """Return how long the given phase lasted (ms). None if not reached."""
        history = [e for e in self._phase_history if e[0] == phase]
        if not history:
            return None
        idx = self._phase_history.index(history[0])
        if idx + 1 < len(self._phase_history):
            delta = self._phase_history[idx + 1][1] - history[0][1]
            return round(delta.total_seconds() * 1000, 2)
        return None

    @property
    def is_terminal(self) -> bool:
        return self._status.is_terminal

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._status == DebateStatus.RUNNING
