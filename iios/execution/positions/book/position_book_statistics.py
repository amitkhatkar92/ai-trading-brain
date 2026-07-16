"""iios/execution/positions/book/position_book_statistics.py
==================================================
BookStatistics — aggregated counters and derived metrics for the
IIOS Position Book.

C6 Execution Intelligence — Phase 3, Module 3
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict

from .constants import IndexType


@dataclass
class BookStatistics:
    """
    Mutable statistics accumulator for the Position Book.

    Counters are incremented by ``PositionBook`` as operations complete.
    Thread safety is the caller's responsibility — PositionBook wraps
    mutating calls under its own lock.

    Live position counts (active, closed, archived, suspended) are updated
    by ``PositionBook.notify_state_changed()`` and recalculated on ``snapshot()``.
    """

    # ── Operation counters ────────────────────────────────────────────────────
    positions_added:   int = 0
    positions_removed: int = 0

    # ── Live state counts ─────────────────────────────────────────────────────
    active_positions:    int = 0
    closed_positions:    int = 0
    archived_positions:  int = 0
    suspended_positions: int = 0

    # ── Query / snapshot counters ─────────────────────────────────────────────
    total_queries:    int = 0
    total_snapshots:  int = 0
    failed_queries:   int = 0

    # ── Timing accumulation ───────────────────────────────────────────────────
    total_query_time_ms: float = 0.0

    # ── Timestamp ─────────────────────────────────────────────────────────────
    last_updated_at: float = field(default_factory=time.time)

    # ── Index utilization ─────────────────────────────────────────────────────
    index_utilization: Dict[str, int] = field(default_factory=dict)

    # ── Derived properties ────────────────────────────────────────────────────

    @property
    def query_count(self) -> int:
        return self.total_queries

    @property
    def snapshot_count(self) -> int:
        return self.total_snapshots

    @property
    def average_lookup_time_ms(self) -> float:
        """Mean query elapsed time in milliseconds."""
        successful = self.total_queries - self.failed_queries
        if successful <= 0:
            return 0.0
        return self.total_query_time_ms / successful

    @property
    def positions_in_book(self) -> int:
        """Current estimated count of positions in the book."""
        return max(0, self.positions_added - self.positions_removed)

    # ── Mutation helpers ──────────────────────────────────────────────────────

    def record_added(self) -> None:
        self.positions_added += 1
        self.last_updated_at  = time.time()

    def record_removed(self) -> None:
        self.positions_removed += 1
        self.last_updated_at   = time.time()

    def record_query(self, elapsed_ms: float = 0.0) -> None:
        self.total_queries      += 1
        self.total_query_time_ms += elapsed_ms
        self.last_updated_at     = time.time()

    def record_failed_query(self) -> None:
        self.failed_queries  += 1
        self.total_queries   += 1
        self.last_updated_at  = time.time()

    def record_snapshot(self) -> None:
        self.total_snapshots += 1
        self.last_updated_at  = time.time()

    def update_live_counts(
        self,
        active:    int,
        closed:    int,
        archived:  int,
        suspended: int,
    ) -> None:
        """Set the live state partition counts directly from the index."""
        self.active_positions    = active
        self.closed_positions    = closed
        self.archived_positions  = archived
        self.suspended_positions = suspended
        self.last_updated_at     = time.time()

    def update_index_utilization(self, utilization: Dict[IndexType, int]) -> None:
        """Copy the current index utilization snapshot into statistics."""
        self.index_utilization = {k.value: v for k, v in utilization.items()}
        self.last_updated_at   = time.time()

    def touch(self) -> None:
        self.last_updated_at = time.time()

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "positions_added":       self.positions_added,
            "positions_removed":     self.positions_removed,
            "positions_in_book":     self.positions_in_book,
            "active_positions":      self.active_positions,
            "closed_positions":      self.closed_positions,
            "archived_positions":    self.archived_positions,
            "suspended_positions":   self.suspended_positions,
            "total_queries":         self.total_queries,
            "total_snapshots":       self.total_snapshots,
            "failed_queries":        self.failed_queries,
            "average_lookup_time_ms": self.average_lookup_time_ms,
            "index_utilization":     dict(self.index_utilization),
            "last_updated_at":       self.last_updated_at,
        }
