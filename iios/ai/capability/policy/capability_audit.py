"""
capability_audit.py -- iios.ai.capability.policy
==================================================
:class:`CapabilityAuditRecord`  — immutable audit entry.
:class:`CapabilityAuditReport`  — per-principal summary.
:class:`CapabilityAuditManager` — thread-safe audit store.

A9 Enterprise Capability Platform — Phase 3, Module 9
"""
from __future__ import annotations

import time
import uuid
from collections import Counter
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional


class CapabilityAuditEventType(str, Enum):
    EXECUTE_SUCCESS  = "execute_success"
    EXECUTE_FAILURE  = "execute_failure"
    EXECUTE_TIMEOUT  = "execute_timeout"
    AUTH_GRANTED     = "auth_granted"
    AUTH_DENIED      = "auth_denied"
    QUOTA_EXCEEDED   = "quota_exceeded"
    REGISTER         = "register"
    DEREGISTER       = "deregister"
    ENABLE           = "enable"
    DISABLE          = "disable"


@dataclass(frozen=True)
class CapabilityAuditRecord:
    """Immutable audit record for a single capability operation."""

    audit_id:      str
    event_type:    CapabilityAuditEventType
    principal_id:  str
    capability_id: str
    outcome:       str
    timestamp:     float
    duration_ms:   float
    notes:         str

    @classmethod
    def create(
        cls,
        event_type:    CapabilityAuditEventType,
        principal_id:  str,
        capability_id: str,
        outcome:       str,
        duration_ms:   float = 0.0,
        notes:         str   = "",
    ) -> "CapabilityAuditRecord":
        return cls(
            audit_id      = str(uuid.uuid4()),
            event_type    = event_type,
            principal_id  = principal_id,
            capability_id = capability_id,
            outcome       = outcome,
            timestamp     = time.time(),
            duration_ms   = duration_ms,
            notes         = notes,
        )


@dataclass(frozen=True)
class CapabilityAuditReport:
    """Summary report for a principal's capability audit history."""

    principal_id:    str
    total_records:   int
    success_count:   int
    failure_count:   int
    denied_count:    int
    top_capabilities: tuple   # (capability_id, count) pairs

    @classmethod
    def build(
        cls,
        principal_id: str,
        records:      List[CapabilityAuditRecord],
    ) -> "CapabilityAuditReport":
        success  = sum(1 for r in records if r.event_type == CapabilityAuditEventType.EXECUTE_SUCCESS)
        failure  = sum(1 for r in records if r.event_type == CapabilityAuditEventType.EXECUTE_FAILURE)
        denied   = sum(1 for r in records if r.event_type == CapabilityAuditEventType.AUTH_DENIED)
        cap_ctr  = Counter(r.capability_id for r in records)
        top_caps = tuple(cap_ctr.most_common(10))
        return cls(
            principal_id     = principal_id,
            total_records    = len(records),
            success_count    = success,
            failure_count    = failure,
            denied_count     = denied,
            top_capabilities = top_caps,
        )


class CapabilityAuditManager:
    """
    Thread-safe append-only store for :class:`CapabilityAuditRecord` entries.
    Max 100 000 records retained (oldest discarded).
    """

    MAX_RECORDS = 100_000

    def __init__(self) -> None:
        import threading
        self._lock:    threading.Lock                 = threading.Lock()
        self._records: List[CapabilityAuditRecord]    = []
        self._index:   Dict[str, CapabilityAuditRecord] = {}  # audit_id -> record

    def record(
        self,
        event_type:    CapabilityAuditEventType,
        principal_id:  str,
        capability_id: str,
        outcome:       str,
        duration_ms:   float = 0.0,
        notes:         str   = "",
    ) -> CapabilityAuditRecord:
        r = CapabilityAuditRecord.create(event_type, principal_id, capability_id,
                                          outcome, duration_ms, notes)
        with self._lock:
            self._records.append(r)
            self._index[r.audit_id] = r
            if len(self._records) > self.MAX_RECORDS:
                oldest = self._records.pop(0)
                self._index.pop(oldest.audit_id, None)
        return r

    def query(
        self,
        principal_id:  Optional[str]                           = None,
        capability_id: Optional[str]                           = None,
        event_type:    Optional[CapabilityAuditEventType]      = None,
        since:         Optional[float]                         = None,
        limit:         int                                     = 500,
    ) -> List[CapabilityAuditRecord]:
        with self._lock:
            records = list(self._records)
        if principal_id  is not None:
            records = [r for r in records if r.principal_id  == principal_id]
        if capability_id is not None:
            records = [r for r in records if r.capability_id == capability_id]
        if event_type    is not None:
            records = [r for r in records if r.event_type    == event_type]
        if since         is not None:
            records = [r for r in records if r.timestamp     >= since]
        return records[-limit:]

    def generate_report(self, principal_id: str) -> CapabilityAuditReport:
        records = self.query(principal_id=principal_id)
        return CapabilityAuditReport.build(principal_id, records)

    def total_count(self) -> int:
        with self._lock:
            return len(self._records)
