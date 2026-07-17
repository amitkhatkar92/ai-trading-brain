"""iios/execution/gateway/engine/gateway_state_manager.py
==================================================
GatewayStateManager — thread-safe tracker for the engine's
current operational state.

C6 Execution Intelligence — Phase 5, Module 2
"""
from __future__ import annotations

import threading
import time
from typing import Any, Dict, List, Tuple

from .constants import ACTIVE_ENGINE_STATES, TERMINAL_ENGINE_STATES, EngineState


class GatewayStateManager:
    """
    Thread-safe manager for the Gateway Engine's operational state.

    Transitions are recorded with a timestamp and optional reason.
    The full transition history is retained for observability.
    """

    def __init__(self) -> None:
        self._state:   EngineState = EngineState.STOPPED
        # history entries: (state, entered_at, reason)
        self._history: List[Tuple[EngineState, float, str]] = []
        self._lock     = threading.RLock()
        self._record(EngineState.STOPPED, "initial")

    # ── Transitions ───────────────────────────────────────────────────────────

    def transition(self, new_state: EngineState, *, reason: str = "") -> None:
        """Transition to ``new_state`` and record the change."""
        with self._lock:
            self._state = new_state
            self._record(new_state, reason)

    def _record(self, state: EngineState, reason: str) -> None:
        self._history.append((state, time.time(), reason))

    # ── Query ─────────────────────────────────────────────────────────────────

    def current(self) -> EngineState:
        with self._lock:
            return self._state

    def is_idle(self) -> bool:
        with self._lock:
            return self._state == EngineState.IDLE

    def is_stopped(self) -> bool:
        with self._lock:
            return self._state == EngineState.STOPPED

    def is_failed(self) -> bool:
        with self._lock:
            return self._state == EngineState.FAILED

    def is_active(self) -> bool:
        with self._lock:
            return self._state in ACTIVE_ENGINE_STATES

    def is_terminal(self) -> bool:
        with self._lock:
            return self._state in TERMINAL_ENGINE_STATES

    # ── History ───────────────────────────────────────────────────────────────

    @property
    def history(self) -> List[Tuple[EngineState, float, str]]:
        """Return a copy of the state transition history."""
        with self._lock:
            return list(self._history)

    @property
    def transition_count(self) -> int:
        with self._lock:
            return len(self._history)

    # ── Recovery ──────────────────────────────────────────────────────────────

    def reset_to_idle(self, reason: str = "reset") -> None:
        """Reset engine state to IDLE (for recovery after a transient FAILED)."""
        with self._lock:
            self._state = EngineState.IDLE
            self._record(EngineState.IDLE, reason)

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "current_state":    self._state.value,
                "is_active":        self._state in ACTIVE_ENGINE_STATES,
                "is_terminal":      self._state in TERMINAL_ENGINE_STATES,
                "transition_count": len(self._history),
                "history": [
                    {"state": s.value, "entered_at": t, "reason": r}
                    for s, t, r in self._history[-20:]    # last 20 entries
                ],
            }
