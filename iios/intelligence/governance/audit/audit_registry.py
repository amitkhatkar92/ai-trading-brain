"""
iios/intelligence/governance/audit/audit_registry.py
=====================================================
Thread-safe append-only store for AuditRecord objects.
"""
from __future__ import annotations

import threading
from typing import Any

from .audit_record import AuditRecord
from ..quality_constants import AuditEventType, MAX_AUDIT_RECORDS
from ..quality_exceptions import AuditRecordNotFoundError


class AuditRegistry:
    """
    Append-only thread-safe store for AuditRecord entries.
    Supports lookup by audit_id, product_id, source_id, and event_type.
    """

    def __init__(self, max_records: int = MAX_AUDIT_RECORDS) -> None:
        self._records:    dict[str, AuditRecord]     = {}
        self._ordered:    list[str]                   = []   # insertion order
        self._by_product: dict[str, list[str]]        = {}
        self._by_source:  dict[str, list[str]]        = {}
        self._by_event:   dict[str, list[str]]        = {}
        self._max:        int                          = max_records
        self._lock:       threading.RLock             = threading.RLock()

    # -- Write ─────────────────────────────────────────────────────────────────

    def append(self, record: AuditRecord) -> None:
        with self._lock:
            # Evict oldest if full
            if len(self._ordered) >= self._max:
                oldest_id = self._ordered.pop(0)
                old       = self._records.pop(oldest_id, None)
                if old:
                    self._by_product.get(old.product_id, [])  # no-op — we leave index dirty (acceptable)
            self._records[record.audit_id] = record
            self._ordered.append(record.audit_id)
            self._by_product.setdefault(record.product_id, []).append(record.audit_id)
            self._by_source.setdefault(record.source_id, []).append(record.audit_id)
            self._by_event.setdefault(record.event_type.value, []).append(record.audit_id)

    # -- Read ──────────────────────────────────────────────────────────────────

    def get(self, audit_id: str) -> AuditRecord:
        with self._lock:
            r = self._records.get(audit_id)
        if r is None:
            raise AuditRecordNotFoundError(audit_id)
        return r

    def has(self, audit_id: str) -> bool:
        with self._lock:
            return audit_id in self._records

    def for_product(self, product_id: str) -> list[AuditRecord]:
        with self._lock:
            ids = list(self._by_product.get(product_id, []))
            return [self._records[i] for i in ids if i in self._records]

    def for_source(self, source_id: str) -> list[AuditRecord]:
        with self._lock:
            ids = list(self._by_source.get(source_id, []))
            return [self._records[i] for i in ids if i in self._records]

    def for_event_type(self, event_type: AuditEventType) -> list[AuditRecord]:
        with self._lock:
            ids = list(self._by_event.get(event_type.value, []))
            return [self._records[i] for i in ids if i in self._records]

    def recent(self, n: int = 100) -> list[AuditRecord]:
        with self._lock:
            ids = list(self._ordered[-n:])
            return [self._records[i] for i in reversed(ids) if i in self._records]

    def all(self) -> list[AuditRecord]:
        with self._lock:
            return [self._records[i] for i in self._ordered if i in self._records]

    # -- Stats ─────────────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "total":       len(self._ordered),
                "products":    len(self._by_product),
                "sources":     len(self._by_source),
            }


# ── Singleton ──────────────────────────────────────────────────────────────────

_LOCK:     threading.Lock           = threading.Lock()
_REGISTRY: AuditRegistry | None   = None


def get_audit_registry() -> AuditRegistry:
    global _REGISTRY
    if _REGISTRY is None:
        with _LOCK:
            if _REGISTRY is None:
                _REGISTRY = AuditRegistry()
    return _REGISTRY


def reset_audit_registry() -> None:
    global _REGISTRY
    with _LOCK:
        _REGISTRY = None
