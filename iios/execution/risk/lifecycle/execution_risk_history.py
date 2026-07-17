"""iios/execution/risk/lifecycle/execution_risk_history.py
==================================================
RiskHistory — thread-safe, bounded, append-only record of all
state transitions and state occupancy records for a single risk evaluation.

C6 Execution Intelligence — Phase 4, Module 1
"""
from __future__ import annotations

import threading
from typing import List

from .constants import DEFAULT_MAX_HISTORY, RiskState
from .execution_risk_state import RiskStateRecord
from .execution_risk_transition import RiskTransition


class RiskHistory:
    """
    Thread-safe, bounded, append-only history for a single risk evaluation.

    Stores both ``RiskTransition`` (each state change) and
    ``RiskStateRecord`` (time spent in each state).

    When capacity is reached, the oldest entry of each type is evicted.
    Eviction counts are tracked for audit purposes.
    """

    def __init__(self, max_size: int = DEFAULT_MAX_HISTORY) -> None:
        self._max          = max(1, max_size)
        self._transitions: list[RiskTransition]  = []
        self._states:      list[RiskStateRecord] = []
        self._evicted_t    = 0
        self._evicted_s    = 0
        self._lock         = threading.Lock()

    # ── Write ─────────────────────────────────────────────────────────────────

    def append_transition(self, transition: RiskTransition) -> None:
        """Append a transition record; evict oldest if at capacity."""
        with self._lock:
            if len(self._transitions) >= self._max:
                self._transitions.pop(0)
                self._evicted_t += 1
            self._transitions.append(transition)

    def append_state(self, record: RiskStateRecord) -> None:
        """Append a state-occupancy record; evict oldest if at capacity."""
        with self._lock:
            if len(self._states) >= self._max:
                self._states.pop(0)
                self._evicted_s += 1
            self._states.append(record)

    def update_last_state_exit(self, exited_at: float) -> None:
        """Stamp the exit time on the most recent RiskStateRecord."""
        with self._lock:
            if self._states:
                last = self._states[-1]
                self._states[-1] = last.with_exit(exited_at)

    # ── Read ──────────────────────────────────────────────────────────────────

    def transitions(self) -> List[RiskTransition]:
        """All recorded transitions, oldest first."""
        with self._lock:
            return list(self._transitions)

    def states(self) -> List[RiskStateRecord]:
        """All recorded state-occupancy records, oldest first."""
        with self._lock:
            return list(self._states)

    def latest_transition(self, n: int = 1) -> List[RiskTransition]:
        """Return the most recent *n* transitions, newest first."""
        with self._lock:
            return list(reversed(self._transitions[-n:]))

    def transitions_to(self, state: RiskState) -> List[RiskTransition]:
        """All transitions whose ``to_state`` matches *state*."""
        with self._lock:
            return [t for t in self._transitions if t.to_state == state]

    def transitions_from(self, state: RiskState) -> List[RiskTransition]:
        """All transitions whose ``from_state`` matches *state*."""
        with self._lock:
            return [t for t in self._transitions if t.from_state == state]

    # ── Counts ────────────────────────────────────────────────────────────────

    @property
    def total_transitions(self) -> int:
        """Total transitions appended (including evicted)."""
        with self._lock:
            return len(self._transitions) + self._evicted_t

    @property
    def override_count(self) -> int:
        """Number of override transitions recorded."""
        with self._lock:
            return sum(1 for t in self._transitions if t.is_override)

    @property
    def evicted_transitions(self) -> int:
        """Number of transitions evicted due to capacity."""
        with self._lock:
            return self._evicted_t

    @property
    def evicted_states(self) -> int:
        """Number of state records evicted due to capacity."""
        with self._lock:
            return self._evicted_s

    def __len__(self) -> int:
        with self._lock:
            return len(self._transitions)

    def is_empty(self) -> bool:
        """True if no transitions have been recorded."""
        with self._lock:
            return len(self._transitions) == 0
