"""iios/execution/risk/lifecycle/execution_risk_state.py
==================================================
RiskStateRecord — immutable record of a single lifecycle state
occupancy for an execution risk evaluation.

C6 Execution Intelligence — Phase 4, Module 1
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

from .constants import RiskState


@dataclass(frozen=True)
class RiskStateRecord:
    """
    Immutable snapshot of one state-occupancy period for a risk evaluation.

    ``entered_at`` is always set.
    ``exited_at`` is None while the evaluation is in this state;
    once it transitions away, it is set to the exit timestamp.
    """

    state:      RiskState
    entered_at: float
    exited_at:  Optional[float] = None

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def duration_ms(self) -> Optional[float]:
        """Duration in milliseconds, or None if the state is still active."""
        if self.exited_at is None:
            return None
        return (self.exited_at - self.entered_at) * 1_000.0

    @property
    def is_current(self) -> bool:
        """True if this record represents the current state (no exit recorded)."""
        return self.exited_at is None

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "state":       self.state.value,
            "entered_at":  self.entered_at,
            "exited_at":   self.exited_at,
            "duration_ms": self.duration_ms,
            "is_current":  self.is_current,
        }

    def with_exit(self, exited_at: Optional[float] = None) -> "RiskStateRecord":
        """Return a new record with ``exited_at`` stamped."""
        return RiskStateRecord(
            state=self.state,
            entered_at=self.entered_at,
            exited_at=exited_at if exited_at is not None else time.time(),
        )
