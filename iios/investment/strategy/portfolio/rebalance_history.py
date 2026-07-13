"""iios/investment/strategy/portfolio/rebalance_history.py
RebalanceHistory — append-only ring buffer of rebalance records per portfolio.
"""
from __future__ import annotations

import threading
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Deque, Dict, List, Optional


class RebalanceStatus(str, Enum):
    RECOMMENDED = "recommended"
    EXECUTED    = "executed"
    SKIPPED     = "skipped"


@dataclass(frozen=True)
class RebalanceRecord:
    record_id:     str
    portfolio_id:  str
    trigger:       str              # RebalanceTrigger.value
    status:        RebalanceStatus
    weight_before: Dict[str, float]
    weight_after:  Dict[str, float]
    max_drift:     float
    reason:        str
    created_at:    datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id":    self.record_id,
            "portfolio_id": self.portfolio_id,
            "trigger":      self.trigger,
            "status":       self.status.value,
            "max_drift":    round(self.max_drift, 6),
            "reason":       self.reason,
            "created_at":   self.created_at.isoformat(),
        }


class RebalanceHistory:
    """Append-only ring buffer of RebalanceRecord objects, one deque per portfolio."""

    def __init__(self, max_per_portfolio: int = 500) -> None:
        self._max   = max_per_portfolio
        self._store: Dict[str, Deque[RebalanceRecord]] = {}
        self._lock  = threading.RLock()

    def record(
        self,
        portfolio_id:  str,
        trigger:       str,
        weight_before: Dict[str, float],
        weight_after:  Dict[str, float],
        max_drift:     float,
        reason:        str = "",
        status:        RebalanceStatus = RebalanceStatus.EXECUTED,
    ) -> RebalanceRecord:
        rec = RebalanceRecord(
            record_id=str(uuid.uuid4()),
            portfolio_id=portfolio_id,
            trigger=trigger,
            status=status,
            weight_before=dict(weight_before),
            weight_after=dict(weight_after),
            max_drift=max_drift,
            reason=reason,
        )
        with self._lock:
            if portfolio_id not in self._store:
                self._store[portfolio_id] = deque(maxlen=self._max)
            self._store[portfolio_id].append(rec)
        return rec

    def history(self, portfolio_id: str, n: int = 20) -> List[RebalanceRecord]:
        with self._lock:
            return list(self._store.get(portfolio_id, []))[-n:]

    def latest(self, portfolio_id: str) -> Optional[RebalanceRecord]:
        with self._lock:
            buf = self._store.get(portfolio_id)
            return buf[-1] if buf else None

    def count(self, portfolio_id: str) -> int:
        with self._lock:
            return len(self._store.get(portfolio_id, []))
