"""iios/investment/portfolio/construction/constraint_history.py

Thread-safe history of constraint evaluation runs.
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.portfolio.construction.construction_types import (
    ConstraintOutcome,
    ConstraintSeverity,
)


@dataclass(frozen=True)
class ConstraintCheckRecord:
    """Outcome of evaluating one constraint against one blueprint."""

    check_id:        str               = field(default_factory=lambda: str(uuid.uuid4()))
    constraint_name: str               = ""
    constraint_type: str               = ""
    severity:        ConstraintSeverity= ConstraintSeverity.HARD
    outcome:         ConstraintOutcome = ConstraintOutcome.NOT_CHECKED
    message:         str               = ""
    blueprint_id:    str               = ""
    portfolio_id:    str               = ""
    checked_at:      float             = field(default_factory=time.time)
    details:         Dict[str, Any]    = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.outcome == ConstraintOutcome.PASSED

    @property
    def violated(self) -> bool:
        return self.outcome == ConstraintOutcome.VIOLATED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "check_id":        self.check_id,
            "constraint_name": self.constraint_name,
            "constraint_type": self.constraint_type,
            "severity":        self.severity.value,
            "outcome":         self.outcome.value,
            "message":         self.message,
            "blueprint_id":    self.blueprint_id,
            "portfolio_id":    self.portfolio_id,
            "checked_at":      self.checked_at,
            "details":         dict(self.details),
        }


class ConstraintHistory:
    """Thread-safe bounded store of constraint check records."""

    __slots__ = ("_max_size", "_records", "_lock")

    def __init__(self, max_size: int = 2000) -> None:
        self._max_size = max_size
        self._records: List[ConstraintCheckRecord] = []
        self._lock = threading.RLock()

    def add(self, record: ConstraintCheckRecord) -> None:
        with self._lock:
            self._records.append(record)
            if len(self._records) > self._max_size:
                self._records.pop(0)

    def add_many(self, records: List[ConstraintCheckRecord]) -> None:
        for r in records:
            self.add(r)

    def all(self) -> List[ConstraintCheckRecord]:
        with self._lock:
            return list(self._records)

    def recent(self, n: int) -> List[ConstraintCheckRecord]:
        with self._lock:
            return list(self._records[-n:])

    def for_blueprint(self, blueprint_id: str) -> List[ConstraintCheckRecord]:
        with self._lock:
            return [r for r in self._records if r.blueprint_id == blueprint_id]

    def for_portfolio(self, portfolio_id: str) -> List[ConstraintCheckRecord]:
        with self._lock:
            return [r for r in self._records if r.portfolio_id == portfolio_id]

    def violations(self) -> List[ConstraintCheckRecord]:
        with self._lock:
            return [r for r in self._records if r.violated]

    def count(self) -> int:
        with self._lock:
            return len(self._records)

    def violation_rate(self) -> float:
        with self._lock:
            if not self._records:
                return 0.0
            return sum(1 for r in self._records if r.violated) / len(self._records)

    def latest_for_portfolio(self, portfolio_id: str) -> Optional[ConstraintCheckRecord]:
        with self._lock:
            matches = [r for r in self._records if r.portfolio_id == portfolio_id]
            return matches[-1] if matches else None

    def reset(self) -> None:
        with self._lock:
            self._records.clear()
