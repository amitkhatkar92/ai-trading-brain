"""iios/execution/gateway/lifecycle/gateway_history.py
==================================================
GatewayHistory — thread-safe, bounded, append-only record of all
state transitions and state occupancy records for a single gateway request.

C6 Execution Intelligence — Phase 5, Module 1
"""
from __future__ import annotations

import threading
from typing import List

from .constants import DEFAULT_MAX_HISTORY, GatewayState
from .gateway_state import GatewayStateRecord
from .gateway_transition import GatewayTransition


class GatewayHistory:
    """
    Thread-safe, bounded, append-only history for a single gateway request.

    Stores both ``GatewayTransition`` (each state change) and
    ``GatewayStateRecord`` (time spent in each state).

    When capacity is reached, the oldest entry of each type is evicted.
    Eviction counts are tracked for audit purposes.
    """

    def __init__(self, max_size: int = DEFAULT_MAX_HISTORY) -> None:
        self._max         = max(1, max_size)
        self._transitions: list[GatewayTransition]  = []
        self._states:      list[GatewayStateRecord] = []
        self._evicted_t   = 0
        self._evicted_s   = 0
        self._lock        = threading.Lock()

    # ── Write ─────────────────────────────────────────────────────────────────

    def append_transition(self, transition: GatewayTransition) -> None:
        """Append a transition record; evict oldest if at capacity."""
        with self._lock:
            if len(self._transitions) >= self._max:
                self._transitions.pop(0)
                self._evicted_t += 1
            self._transitions.append(transition)

    def append_state(self, record: GatewayStateRecord) -> None:
        """Append a state-occupancy record; evict oldest if at capacity."""
        with self._lock:
            if len(self._states) >= self._max:
                self._states.pop(0)
                self._evicted_s += 1
            self._states.append(record)

    def update_last_state_exit(self, exited_at: float) -> None:
        """Stamp the exit time on the most recent GatewayStateRecord."""
        with self._lock:
            if self._states:
                last = self._states[-1]
                self._states[-1] = last.with_exit(exited_at)

    # ── Read ──────────────────────────────────────────────────────────────────

    def transitions(self) -> List[GatewayTransition]:
        """All recorded transitions, oldest first."""
        with self._lock:
            return list(self._transitions)

    def states(self) -> List[GatewayStateRecord]:
        """All recorded state-occupancy records, oldest first."""
        with self._lock:
            return list(self._states)

    def latest_transition(self, n: int = 1) -> List[GatewayTransition]:
        """Return the most recent *n* transitions, newest first."""
        with self._lock:
            return list(reversed(self._transitions[-n:]))

    def transitions_to(self, state: GatewayState) -> List[GatewayTransition]:
        """All transitions whose ``to_state`` matches *state*."""
        with self._lock:
            return [t for t in self._transitions if t.to_state == state]

    def transitions_from(self, state: GatewayState) -> List[GatewayTransition]:
        """All transitions whose ``from_state`` matches *state*."""
        with self._lock:
            return [t for t in self._transitions if t.from_state == state]

    def state_records_for(self, state: GatewayState) -> List[GatewayStateRecord]:
        """All state-occupancy records for *state*."""
        with self._lock:
            return [r for r in self._states if r.state == state]

    def current_state_record(self) -> GatewayStateRecord | None:
        """The active (non-exited) state record, if any."""
        with self._lock:
            if self._states and self._states[-1].is_current:
                return self._states[-1]
            return None

    # ── Counters ──────────────────────────────────────────────────────────────

    @property
    def transition_count(self) -> int:
        with self._lock:
            return len(self._transitions)

    @property
    def state_count(self) -> int:
        with self._lock:
            return len(self._states)

    @property
    def evicted_transitions(self) -> int:
        with self._lock:
            return self._evicted_t

    @property
    def evicted_states(self) -> int:
        with self._lock:
            return self._evicted_s

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "transitions":         [t.to_dict() for t in self.transitions()],
            "states":              [s.to_dict() for s in self.states()],
            "transition_count":    self.transition_count,
            "state_count":         self.state_count,
            "evicted_transitions": self.evicted_transitions,
            "evicted_states":      self.evicted_states,
        }
