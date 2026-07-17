"""iios/execution/risk/engine/execution_risk_state.py
==================================================
EngineOpStateRecord — immutable record of one operation-phase occupancy
within the Execution Risk Engine.

Each engine operation transitions through a sequence of EngineOpState
values (IDLE → VALIDATING → EVALUATING → AGGREGATING → FINALIZING →
COMPLETED/FAILED).  Each phase occupancy is recorded here for audit.

C6 Execution Intelligence — Phase 4, Module 2
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

from .constants import EngineOpState, OperationType, TERMINAL_OP_STATES


@dataclass(frozen=True)
class EngineOpStateRecord:
    """
    Immutable snapshot of one engine operation-phase occupancy.

    ``entered_at`` is always populated.
    ``exited_at`` is None while the engine is in this phase; set once
    the engine moves to the next phase or completes the operation.
    """

    state:          EngineOpState
    operation_id:   str
    operation_type: OperationType
    entered_at:     float
    exited_at:      Optional[float] = None

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def duration_ms(self) -> Optional[float]:
        """Phase duration in milliseconds, or None if still active."""
        if self.exited_at is None:
            return None
        return (self.exited_at - self.entered_at) * 1_000.0

    @property
    def is_current(self) -> bool:
        """True if this record represents the current phase (no exit recorded)."""
        return self.exited_at is None

    @property
    def is_terminal(self) -> bool:
        """True if this phase is a terminal state (COMPLETED or FAILED)."""
        return self.state in TERMINAL_OP_STATES

    # ── Mutation helper ───────────────────────────────────────────────────────

    def with_exit(self, exited_at: Optional[float] = None) -> "EngineOpStateRecord":
        """Return a new record with ``exited_at`` stamped."""
        return EngineOpStateRecord(
            state=self.state,
            operation_id=self.operation_id,
            operation_type=self.operation_type,
            entered_at=self.entered_at,
            exited_at=exited_at if exited_at is not None else time.time(),
        )

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "state":          self.state.value,
            "operation_id":   self.operation_id,
            "operation_type": self.operation_type.value,
            "entered_at":     self.entered_at,
            "exited_at":      self.exited_at,
            "duration_ms":    self.duration_ms,
            "is_current":     self.is_current,
            "is_terminal":    self.is_terminal,
        }
