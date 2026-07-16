"""iios/execution/positions/lifecycle/position_statistics.py
==================================================
PositionStatistics — aggregated counters and averages for the
Position Lifecycle registry.

C6 Execution Intelligence — Phase 3, Module 1
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict


@dataclass
class PositionStatistics:
    """
    Mutable statistics accumulator for a PositionRegistry.

    All numeric fields start at zero and are incremented by the registry
    as positions change state.  Thread safety is the registry's responsibility.
    """

    # ── Position counts ───────────────────────────────────────────────────────
    positions_created:   int = 0
    positions_opened:    int = 0
    positions_closed:    int = 0
    positions_archived:  int = 0
    positions_suspended: int = 0
    positions_recovered: int = 0
    positions_partially_closed: int = 0

    # ── Transition counters ───────────────────────────────────────────────────
    total_transitions:   int = 0
    recovery_count:      int = 0

    # ── Holding time accumulation ─────────────────────────────────────────────
    total_holding_time_ms: float = 0.0   # sum of holding times for closed positions

    # ── Size accumulation ─────────────────────────────────────────────────────
    total_position_size: Decimal = field(default_factory=lambda: Decimal(0))

    # ── Timestamp ─────────────────────────────────────────────────────────────
    last_updated_at: float = field(default_factory=time.time)

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def average_holding_time_ms(self) -> float:
        """Mean holding time in milliseconds for closed positions."""
        denom = self.positions_closed
        if denom == 0:
            return 0.0
        return self.total_holding_time_ms / denom

    @property
    def average_position_size(self) -> Decimal:
        """Mean quantity across all created positions."""
        denom = self.positions_created
        if denom == 0:
            return Decimal(0)
        return self.total_position_size / Decimal(denom)

    @property
    def close_rate(self) -> float:
        """Fraction of opened positions that have been closed (0–1)."""
        if self.positions_opened == 0:
            return 0.0
        return self.positions_closed / self.positions_opened

    # ── Mutation helpers ──────────────────────────────────────────────────────

    def touch(self) -> None:
        """Update the last_updated_at timestamp."""
        self.last_updated_at = time.time()

    def record_created(self, quantity: Decimal) -> None:
        self.positions_created  += 1
        self.total_position_size += quantity
        self.touch()

    def record_opened(self) -> None:
        self.positions_opened += 1
        self.touch()

    def record_partially_closed(self) -> None:
        self.positions_partially_closed += 1
        self.touch()

    def record_closed(self, holding_time_ms: float = 0.0) -> None:
        self.positions_closed      += 1
        self.total_holding_time_ms += holding_time_ms
        self.touch()

    def record_archived(self) -> None:
        self.positions_archived += 1
        self.touch()

    def record_suspended(self) -> None:
        self.positions_suspended += 1
        self.touch()

    def record_recovered(self) -> None:
        self.positions_recovered += 1
        self.touch()

    def record_transition(self, is_recovery: bool = False) -> None:
        self.total_transitions += 1
        if is_recovery:
            self.recovery_count += 1
        self.touch()

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "positions_created":         self.positions_created,
            "positions_opened":          self.positions_opened,
            "positions_closed":          self.positions_closed,
            "positions_archived":        self.positions_archived,
            "positions_suspended":       self.positions_suspended,
            "positions_recovered":       self.positions_recovered,
            "positions_partially_closed": self.positions_partially_closed,
            "total_transitions":         self.total_transitions,
            "recovery_count":            self.recovery_count,
            "total_holding_time_ms":     self.total_holding_time_ms,
            "average_holding_time_ms":   self.average_holding_time_ms,
            "total_position_size":       str(self.total_position_size),
            "average_position_size":     str(self.average_position_size),
            "close_rate":                self.close_rate,
            "last_updated_at":           self.last_updated_at,
        }
