"""iios/execution/positions/engine/position_state.py
==================================================
EngineStateRecord — immutable record of one operation-phase occupancy
within the Position Engine.

Each engine operation transitions through a sequence of EngineState values
(IDLE → VALIDATING → CREATING → COMPLETED, etc.).  Each phase occupancy
is recorded here for audit purposes.

C6 Execution Intelligence — Phase 3, Module 2
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from .constants import EngineState, OperationType, TERMINAL_ENGINE_STATES


@dataclass(frozen=True)
class EngineStateRecord:
    """
    Immutable snapshot of one engine-state occupancy during an operation.

    ``entered_at`` is always populated.
    ``exited_at`` is None while the engine is in this phase; set once
    the engine moves to the next phase.
    """

    state:          EngineState
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
        return self.exited_at is None

    @property
    def is_terminal(self) -> bool:
        return self.state in TERMINAL_ENGINE_STATES

    # ── Mutation helper ───────────────────────────────────────────────────────

    def with_exit(self, exited_at: Optional[float] = None) -> "EngineStateRecord":
        """Return a new record with ``exited_at`` stamped."""
        return EngineStateRecord(
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
