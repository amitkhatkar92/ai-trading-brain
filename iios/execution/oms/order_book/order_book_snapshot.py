"""iios/execution/oms/order_book/order_book_snapshot.py
==================================================
OrderBookSnapshot — immutable point-in-time view of the Order Book.

Three snapshot types:
  OrderBookSnapshot      — full book summary
  FilteredSnapshot       — entries matching a filter
  HistoricalSnapshot     — entries from a time window

C6 Execution Intelligence — Phase 2, Module 2
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from iios.execution.oms.order_book.constants import BookEntryStatus, VERSION
from iios.execution.oms.order_book.order_book_entry import OrderBookEntry


@dataclass(frozen=True)
class OrderBookSnapshot:
    """
    Immutable summary of the entire Order Book at a point in time.
    """
    snapshot_id:    str   = field(default_factory=lambda: str(uuid.uuid4()))
    schema_version: str   = VERSION
    captured_at:    float = field(default_factory=time.time)

    # Counts per status
    total_entries:  int = 0
    active_count:   int = 0
    completed_count: int = 0
    cancelled_count: int = 0
    rejected_count:  int = 0
    expired_count:   int = 0
    failed_count:    int = 0

    # Index cardinalities
    unique_instruments: int = 0
    unique_strategies:  int = 0
    unique_portfolios:  int = 0
    unique_brokers:     int = 0

    metadata:       dict[str, Any] = field(default_factory=dict)

    @property
    def terminal_count(self) -> int:
        return (
            self.completed_count
            + self.cancelled_count
            + self.rejected_count
            + self.expired_count
            + self.failed_count
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id":      self.snapshot_id,
            "schema_version":   self.schema_version,
            "captured_at":      self.captured_at,
            "total_entries":    self.total_entries,
            "active_count":     self.active_count,
            "completed_count":  self.completed_count,
            "cancelled_count":  self.cancelled_count,
            "rejected_count":   self.rejected_count,
            "expired_count":    self.expired_count,
            "failed_count":     self.failed_count,
            "terminal_count":   self.terminal_count,
            "unique_instruments": self.unique_instruments,
            "unique_strategies":  self.unique_strategies,
            "unique_portfolios":  self.unique_portfolios,
            "unique_brokers":     self.unique_brokers,
        }


@dataclass(frozen=True)
class FilteredSnapshot:
    """
    Immutable snapshot of entries matching a specific filter.
    """
    snapshot_id:    str = field(default_factory=lambda: str(uuid.uuid4()))
    captured_at:    float = field(default_factory=time.time)
    filter_summary: dict[str, Any] = field(default_factory=dict)
    entries:        tuple[dict[str, Any], ...] = field(default_factory=tuple)
    total_matched:  int = 0
    query_time_ms:  float = 0.0

    @property
    def count(self) -> int:
        return len(self.entries)

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id":    self.snapshot_id,
            "captured_at":    self.captured_at,
            "count":          self.count,
            "total_matched":  self.total_matched,
            "query_time_ms":  round(self.query_time_ms, 3),
            "filter_summary": self.filter_summary,
        }


@dataclass(frozen=True)
class HistoricalSnapshot:
    """
    Immutable snapshot of entries within a historical time window.
    """
    snapshot_id:  str   = field(default_factory=lambda: str(uuid.uuid4()))
    captured_at:  float = field(default_factory=time.time)
    window_start: float = 0.0
    window_end:   float = field(default_factory=time.time)
    entries:      tuple[dict[str, Any], ...] = field(default_factory=tuple)

    @property
    def count(self) -> int:
        return len(self.entries)

    @property
    def window_sec(self) -> float:
        return self.window_end - self.window_start

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id":  self.snapshot_id,
            "captured_at":  self.captured_at,
            "window_start": self.window_start,
            "window_end":   self.window_end,
            "window_sec":   round(self.window_sec, 1),
            "count":        self.count,
        }
