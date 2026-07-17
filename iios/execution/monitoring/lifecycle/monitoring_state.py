"""iios/execution/monitoring/lifecycle/monitoring_state.py
==================================================
MonitoringStateRecord — immutable snapshot of a single lifecycle
state occupancy for a monitoring session.

C6 Execution Intelligence — Phase 6, Module 1
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

from .constants import MonitoringState


@dataclass(frozen=True)
class MonitoringStateRecord:
    """
    Immutable record of one state-occupancy period.

    ``entered_at`` is always set.
    ``exited_at`` is None while the session is in this state.
    """

    state:      MonitoringState
    entered_at: float
    exited_at:  Optional[float] = None

    @property
    def duration_ms(self) -> Optional[float]:
        if self.exited_at is None:
            return None
        return (self.exited_at - self.entered_at) * 1_000.0

    @property
    def is_current(self) -> bool:
        return self.exited_at is None

    def to_dict(self) -> dict:
        return {
            "state":       self.state.value,
            "entered_at":  self.entered_at,
            "exited_at":   self.exited_at,
            "duration_ms": self.duration_ms,
            "is_current":  self.is_current,
        }

    def with_exit(self, exited_at: Optional[float] = None) -> "MonitoringStateRecord":
        return MonitoringStateRecord(
            state=self.state,
            entered_at=self.entered_at,
            exited_at=exited_at if exited_at is not None else time.time(),
        )
