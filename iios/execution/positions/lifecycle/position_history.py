"""iios/execution/positions/lifecycle/position_history.py
==================================================
PositionHistory — thread-safe, bounded, append-only record of all
state transitions and state occupancy records for a single position.

C6 Execution Intelligence — Phase 3, Module 1
"""
from __future__ import annotations

import threading
from typing import Iterator, Sequence

from .constants import DEFAULT_MAX_HISTORY, PositionState
from .position_state import PositionStateRecord
from .position_transition import PositionTransition


class PositionHistory:
    """
    Thread-safe, bounded, append-only history for a single position.

    Stores both ``PositionTransition`` (each state change) and
    ``PositionStateRecord`` (time spent in each state).

    When capacity is reached, the oldest entry of each type is evicted.
    Eviction counts are tracked for audit purposes.
    """

    def __init__(self, max_size: int = DEFAULT_MAX_HISTORY) -> None:
        self._max          = max(1, max_size)
        self._transitions: list[PositionTransition] = []
        self._states:      list[PositionStateRecord] = []
        self._evicted_t    = 0  # evicted transitions
        self._evicted_s    = 0  # evicted state records
        self._lock         = threading.Lock()

    # ── Write ─────────────────────────────────────────────────────────────────

    def append_transition(self, transition: PositionTransition) -> None:
        """Append a transition record; evict oldest if at capacity."""
        with self._lock:
            if len(self._transitions) >= self._max:
                self._transitions.pop(0)
                self._evicted_t += 1
            self._transitions.append(transition)

    def append_state(self, record: PositionStateRecord) -> None:
        """Append a state-occupancy record; evict oldest if at capacity."""
        with self._lock:
            if len(self._states) >= self._max:
                self._states.pop(0)
                self._evicted_s += 1
            self._states.append(record)

    def update_last_state_exit(self, exited_at: float) -> None:
        """
        Stamp the exit time on the most recent PositionStateRecord.

        Called when the position transitions away from its current state.
        """
        with self._lock:
            if self._states:
                last = self._states[-1]
                self._states[-1] = last.with_exit(exited_at)

    # ── Read ──────────────────────────────────────────────────────────────────

    def transitions(self) -> list[PositionTransition]:
        """All recorded transitions, oldest first."""
        with self._lock:
            return list(self._transitions)

    def states(self) -> list[PositionStateRecord]:
        """All recorded state-occupancy records, oldest first."""
        with self._lock:
            return list(self._states)

    def latest_transition(self, n: int = 1) -> list[PositionTransition]:
        """Return the most recent *n* transitions, newest first."""
        with self._lock:
            return list(reversed(self._transitions[-n:]))

    def transitions_to(self, state: PositionState) -> list[PositionTransition]:
        """All transitions whose ``to_state`` matches *state*."""
        with self._lock:
            return [t for t in self._transitions if t.to_state == state]

    def transitions_from(self, state: PositionState) -> list[PositionTransition]:
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
    def recovery_count(self) -> int:
        """Number of recovery-related transitions recorded."""
        with self._lock:
            return sum(1 for t in self._transitions if t.is_recovery)

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

    def __iter__(self) -> Iterator[PositionTransition]:
        with self._lock:
            return iter(list(self._transitions))
