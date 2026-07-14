"""iios/investment/portfolio/construction/selection_history.py

Thread-safe history of SecuritySelector selection runs.
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class SelectionRecord:
    """Audit record for a single SecuritySelector.select() invocation."""

    record_id:          str             = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:       str             = ""
    request_id:         str             = ""

    recommendations_in: int             = 0
    recommendations_out:int             = 0
    filters_applied:    Tuple[str, ...] = field(default_factory=tuple)
    rejected_count:     int             = 0
    selected_symbols:   Tuple[str, ...] = field(default_factory=tuple)

    policy_name:        str             = ""
    selection_criterion:str             = ""

    duration_ms:        float           = 0.0
    selected_at:        float           = field(default_factory=time.time)

    @property
    def pass_rate(self) -> float:
        return (
            self.recommendations_out / self.recommendations_in
            if self.recommendations_in > 0
            else 0.0
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id":           self.record_id,
            "portfolio_id":        self.portfolio_id,
            "request_id":          self.request_id,
            "recommendations_in":  self.recommendations_in,
            "recommendations_out": self.recommendations_out,
            "filters_applied":     list(self.filters_applied),
            "rejected_count":      self.rejected_count,
            "selected_symbols":    list(self.selected_symbols),
            "policy_name":         self.policy_name,
            "selection_criterion": self.selection_criterion,
            "pass_rate":           round(self.pass_rate, 4),
            "duration_ms":         round(self.duration_ms, 2),
            "selected_at":         self.selected_at,
        }


class SelectionHistory:
    """
    Thread-safe bounded history of SelectionRecords.

    cap default of 500 gives ~2 years of daily records at 1 run / day.
    """

    __slots__ = ("_max_size", "_records", "_lock")

    def __init__(self, max_size: int = 500) -> None:
        if max_size < 1:
            raise ValueError("max_size must be >= 1")
        self._max_size = max_size
        self._records: List[SelectionRecord] = []
        self._lock = threading.RLock()

    def add(self, record: SelectionRecord) -> None:
        with self._lock:
            self._records.append(record)
            if len(self._records) > self._max_size:
                self._records.pop(0)

    def all(self) -> List[SelectionRecord]:
        with self._lock:
            return list(self._records)

    def recent(self, n: int) -> List[SelectionRecord]:
        with self._lock:
            return list(self._records[-n:])

    def for_portfolio(self, portfolio_id: str) -> List[SelectionRecord]:
        with self._lock:
            return [r for r in self._records if r.portfolio_id == portfolio_id]

    def latest(self) -> Optional[SelectionRecord]:
        with self._lock:
            return self._records[-1] if self._records else None

    def count(self) -> int:
        with self._lock:
            return len(self._records)

    def avg_pass_rate(self) -> float:
        with self._lock:
            if not self._records:
                return 0.0
            return sum(r.pass_rate for r in self._records) / len(self._records)

    def reset(self) -> None:
        with self._lock:
            self._records.clear()
