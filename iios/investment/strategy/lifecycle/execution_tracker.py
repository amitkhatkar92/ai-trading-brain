"""iios/investment/strategy/lifecycle/execution_tracker.py
Per-execution record keeping — ring-buffered execution history.
"""
from __future__ import annotations

import threading
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Deque, Dict, List, Optional


class ExecutionStatus(str, Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    SUCCESS   = "success"
    FAILED    = "failed"
    TIMEOUT   = "timeout"
    CANCELLED = "cancelled"
    RETRYING  = "retrying"


@dataclass
class ExecutionRecord:
    """Complete record of a single strategy execution attempt."""

    record_id: str = field(
        default_factory=lambda: f"rec-{uuid.uuid4().hex[:10]}"
    )
    strategy_id: str = ""
    session_id: str = ""
    cycle_id: str = ""
    status: ExecutionStatus = ExecutionStatus.PENDING
    started_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    completed_at: Optional[datetime] = None
    duration_ms: float = 0.0
    retry_count: int = 0
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Dict = field(default_factory=dict)

    def complete(
        self,
        status: ExecutionStatus,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Mark this record as complete and compute duration."""
        self.completed_at = datetime.now(timezone.utc)
        self.status = status
        self.duration_ms = (
            self.completed_at - self.started_at
        ).total_seconds() * 1_000
        self.error_type = error_type
        self.error_message = error_message

    @property
    def is_complete(self) -> bool:
        return self.status not in (
            ExecutionStatus.PENDING,
            ExecutionStatus.RUNNING,
            ExecutionStatus.RETRYING,
        )

    @property
    def succeeded(self) -> bool:
        return self.status == ExecutionStatus.SUCCESS

    @property
    def failed(self) -> bool:
        return self.status in (ExecutionStatus.FAILED, ExecutionStatus.TIMEOUT)

    def to_dict(self) -> dict:
        return {
            "record_id": self.record_id,
            "strategy_id": self.strategy_id,
            "session_id": self.session_id,
            "cycle_id": self.cycle_id,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "duration_ms": round(self.duration_ms, 2),
            "retry_count": self.retry_count,
            "error_type": self.error_type,
            "error_message": self.error_message,
        }


class ExecutionTracker:
    """
    Thread-safe ring buffer of recent execution records.

    Maintains:
    - A global ring (ordered by time, maxlen=max_records)
    - Per-strategy rings (maxlen=per_strategy_limit)

    All query methods return copies — callers can freely iterate without
    holding any lock.
    """

    _PER_STRATEGY_LIMIT = 200

    def __init__(self, max_records: int = 5_000) -> None:
        self._lock = threading.RLock()
        self._max = max_records
        self._global: Deque[ExecutionRecord] = deque(maxlen=max_records)
        self._by_strategy: Dict[str, Deque[ExecutionRecord]] = {}

    def start_record(
        self,
        strategy_id: str,
        session_id: str = "",
        cycle_id: str = "",
    ) -> ExecutionRecord:
        """Create, store, and return a new RUNNING record."""
        record = ExecutionRecord(
            strategy_id=strategy_id,
            session_id=session_id,
            cycle_id=cycle_id,
            status=ExecutionStatus.RUNNING,
        )
        with self._lock:
            self._global.append(record)
            if strategy_id not in self._by_strategy:
                self._by_strategy[strategy_id] = deque(
                    maxlen=self._PER_STRATEGY_LIMIT
                )
            self._by_strategy[strategy_id].append(record)
        return record

    def get_recent(self, n: int = 50) -> List[ExecutionRecord]:
        """Return the n most recent global records."""
        with self._lock:
            return list(self._global)[-n:]

    def get_for_strategy(
        self, strategy_id: str, n: int = 50
    ) -> List[ExecutionRecord]:
        """Return the n most recent records for a specific strategy."""
        with self._lock:
            deq = self._by_strategy.get(strategy_id, deque())
            return list(deq)[-n:]

    def get_failures(
        self, strategy_id: Optional[str] = None
    ) -> List[ExecutionRecord]:
        """Return all failed records (global or per-strategy)."""
        if strategy_id:
            records = self.get_for_strategy(strategy_id, 200)
        else:
            with self._lock:
                records = list(self._global)
        return [r for r in records if r.failed]

    def count_by_status(
        self, strategy_id: Optional[str] = None
    ) -> Dict[str, int]:
        """Return counts grouped by ExecutionStatus value."""
        records = (
            self.get_for_strategy(strategy_id, 200)
            if strategy_id
            else self.get_recent(1_000)
        )
        counts: Dict[str, int] = {}
        for r in records:
            counts[r.status.value] = counts.get(r.status.value, 0) + 1
        return counts

    def last_execution(self, strategy_id: str) -> Optional[ExecutionRecord]:
        """Return the most recent record for a strategy, or None."""
        records = self.get_for_strategy(strategy_id, 1)
        return records[0] if records else None

    def known_strategy_ids(self) -> List[str]:
        with self._lock:
            return list(self._by_strategy.keys())
