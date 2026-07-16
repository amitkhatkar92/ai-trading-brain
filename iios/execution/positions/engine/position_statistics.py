"""iios/execution/positions/engine/position_statistics.py
==================================================
EngineStatistics — aggregated operation counters and averages for the
Position Engine.

C6 Execution Intelligence — Phase 3, Module 2
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class EngineStatistics:
    """
    Mutable statistics accumulator for PositionManager and PositionEngine.

    Counters are incremented by the manager as operations complete.
    Thread safety is the caller's responsibility.
    """

    # ── Operation counters ────────────────────────────────────────────────────
    positions_created:      int = 0
    positions_updated:      int = 0
    positions_closed:       int = 0
    positions_synchronized: int = 0
    positions_archived:     int = 0
    positions_queried:      int = 0

    # ── Totals ────────────────────────────────────────────────────────────────
    total_operations:  int   = 0
    failed_operations: int   = 0

    # ── Timing accumulation ───────────────────────────────────────────────────
    total_update_time_ms: float = 0.0

    # ── Timestamp ─────────────────────────────────────────────────────────────
    last_updated_at: float = field(default_factory=time.time)

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def average_update_time_ms(self) -> float:
        """Mean operation elapsed time in milliseconds."""
        successful = self.total_operations - self.failed_operations
        if successful == 0:
            return 0.0
        return self.total_update_time_ms / successful

    @property
    def success_rate(self) -> float:
        """Fraction of operations that succeeded (0–1)."""
        if self.total_operations == 0:
            return 1.0
        return (self.total_operations - self.failed_operations) / self.total_operations

    @property
    def failure_count(self) -> int:
        return self.failed_operations

    # ── Mutation helpers ──────────────────────────────────────────────────────

    def _record(self, elapsed_ms: float) -> None:
        self.total_operations  += 1
        self.total_update_time_ms += elapsed_ms
        self.last_updated_at    = time.time()

    def record_created(self, elapsed_ms: float = 0.0) -> None:
        self.positions_created += 1
        self._record(elapsed_ms)

    def record_updated(self, elapsed_ms: float = 0.0) -> None:
        self.positions_updated += 1
        self._record(elapsed_ms)

    def record_closed(self, elapsed_ms: float = 0.0) -> None:
        self.positions_closed += 1
        self._record(elapsed_ms)

    def record_synchronized(self, elapsed_ms: float = 0.0) -> None:
        self.positions_synchronized += 1
        self._record(elapsed_ms)

    def record_archived(self, elapsed_ms: float = 0.0) -> None:
        self.positions_archived += 1
        self._record(elapsed_ms)

    def record_queried(self, elapsed_ms: float = 0.0) -> None:
        self.positions_queried += 1
        self._record(elapsed_ms)

    def record_failed(self, elapsed_ms: float = 0.0) -> None:
        self.failed_operations += 1
        self.total_operations  += 1
        self.last_updated_at    = time.time()

    def touch(self) -> None:
        self.last_updated_at = time.time()

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "positions_created":      self.positions_created,
            "positions_updated":      self.positions_updated,
            "positions_closed":       self.positions_closed,
            "positions_synchronized": self.positions_synchronized,
            "positions_archived":     self.positions_archived,
            "positions_queried":      self.positions_queried,
            "total_operations":       self.total_operations,
            "failed_operations":      self.failed_operations,
            "failure_count":          self.failure_count,
            "total_update_time_ms":   self.total_update_time_ms,
            "average_update_time_ms": self.average_update_time_ms,
            "success_rate":           self.success_rate,
            "last_updated_at":        self.last_updated_at,
        }
