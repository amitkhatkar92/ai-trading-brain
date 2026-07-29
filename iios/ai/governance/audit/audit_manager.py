"""
audit_manager.py -- iios.ai.governance.audit
=============================================
:class:`AuditHistory` — ordered, queryable log of AuditRecord objects.
:class:`AuditReport`  — point-in-time audit summary.
:class:`AuditManager` — thread-safe audit log management.

A8 AI Governance Platform — Phase 3, Module 8
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, FrozenSet, List, Optional, Tuple

from ..exceptions.governance_exceptions import AIAuditRecordNotFoundError
from .audit_record import AuditEventType, AuditRecord


class AuditHistory:
    """Thread-safe ordered log of :class:`AuditRecord` objects."""

    def __init__(self, max_records: int = 100_000) -> None:
        self._lock:    threading.Lock       = threading.Lock()
        self._records: List[AuditRecord]    = []
        self._index:   Dict[str, AuditRecord] = {}
        self._max:     int                  = max_records

    def append(self, record: AuditRecord) -> None:
        with self._lock:
            self._records.append(record)
            self._index[record.record_id] = record
            if len(self._records) > self._max:
                oldest = self._records.pop(0)
                self._index.pop(oldest.record_id, None)

    def get(self, record_id: str) -> AuditRecord:
        with self._lock:
            r = self._index.get(record_id)
        if r is None:
            raise AIAuditRecordNotFoundError(f"Audit record {record_id!r} not found")
        return r

    def query(
        self,
        subject_id:  Optional[str]           = None,
        event_type:  Optional[AuditEventType] = None,
        since:       Optional[float]          = None,
        limit:       int                      = 500,
    ) -> List[AuditRecord]:
        with self._lock:
            records = list(self._records)
        if subject_id:
            records = [r for r in records if r.subject_id == subject_id]
        if event_type:
            records = [r for r in records if r.event_type == event_type]
        if since:
            records = [r for r in records if r.occurred_at >= since]
        return records[-limit:]

    def total_count(self) -> int:
        with self._lock:
            return len(self._records)

    def last_hash(self) -> str:
        with self._lock:
            return self._records[-1].record_hash if self._records else ""


@dataclass(frozen=True)
class AuditReport:
    """Immutable point-in-time audit summary."""

    report_id:       str
    subject_id:      str
    total_records:   int
    denied_count:    int
    escalated_count: int
    allowed_count:   int
    period_start:    float
    period_end:      float
    generated_at:    float
    top_actions:     FrozenSet[Tuple[str, int]]   # (action, count)
    notes:           str

    @classmethod
    def build(
        cls,
        subject_id: str,
        records:    List[AuditRecord],
        notes:      str = "",
    ) -> "AuditReport":
        from collections import Counter
        denied   = sum(1 for r in records if r.outcome == "denied")
        escalated = sum(1 for r in records if r.outcome == "escalated")
        allowed  = sum(1 for r in records if r.outcome == "allowed")
        action_counts = Counter(r.action for r in records)
        top = frozenset(action_counts.most_common(10))
        start = min((r.occurred_at for r in records), default=time.time())
        end   = max((r.occurred_at for r in records), default=time.time())
        return cls(
            report_id       = str(uuid.uuid4()),
            subject_id      = subject_id,
            total_records   = len(records),
            denied_count    = denied,
            escalated_count = escalated,
            allowed_count   = allowed,
            period_start    = start,
            period_end      = end,
            generated_at    = time.time(),
            top_actions     = top,
            notes           = notes,
        )


class AuditManager:
    """
    Thread-safe audit log management.

    Provides chain-linked record creation and reporting.
    """

    def __init__(self, max_records: int = 100_000) -> None:
        self._history = AuditHistory(max_records=max_records)

    def record(
        self,
        event_type:   AuditEventType,
        subject_id:   str,
        principal_id: str,
        action:       str,
        resource:     str,
        outcome:      str,
        notes:        str = "",
        **context: Any,
    ) -> AuditRecord:
        """Create and store an audit record chained to the previous one."""
        previous_hash = self._history.last_hash()
        rec = AuditRecord.create(
            event_type    = event_type,
            subject_id    = subject_id,
            principal_id  = principal_id,
            action        = action,
            resource      = resource,
            outcome       = outcome,
            previous_hash = previous_hash,
            notes         = notes,
            **context,
        )
        self._history.append(rec)
        return rec

    def get(self, record_id: str) -> AuditRecord:
        return self._history.get(record_id)

    def query(
        self,
        subject_id:  Optional[str]            = None,
        event_type:  Optional[AuditEventType]  = None,
        since:       Optional[float]           = None,
        limit:       int                       = 500,
    ) -> List[AuditRecord]:
        return self._history.query(subject_id, event_type, since, limit)

    def generate_report(self, subject_id: str) -> AuditReport:
        records = self._history.query(subject_id=subject_id, limit=10_000)
        return AuditReport.build(subject_id, records)

    def total_count(self) -> int:
        return self._history.total_count()

    def verify_chain_integrity(self, limit: int = 1000) -> bool:
        """Verify hash integrity of the most recent ``limit`` records."""
        records = self._history.query(limit=limit)
        return all(r.verify_integrity() for r in records)
