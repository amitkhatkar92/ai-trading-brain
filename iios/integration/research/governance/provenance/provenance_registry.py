"""provenance/provenance_registry.py — Thread-safe in-memory provenance store."""
from __future__ import annotations

import threading
from typing import Any, Optional

from iios.integration.research.governance.governance_constants import (
    DEFAULT_MAX_PROVENANCE_RECORDS,
    ProvenanceType,
)
from iios.integration.research.governance.governance_exceptions import (
    ProvenanceNotFoundError,
    LineageCapacityError,
)
from iios.integration.research.governance.provenance.provenance_record import ProvenanceRecord


class ProvenanceRegistry:
    """Thread-safe store for ProvenanceRecord instances."""

    def __init__(self, max_records: int = DEFAULT_MAX_PROVENANCE_RECORDS) -> None:
        self._records: dict[str, ProvenanceRecord] = {}
        self._by_entity: dict[str, list[str]]      = {}   # entity_id → [record_id, ...]
        self._max    = max_records
        self._lock   = threading.RLock()

    def register(self, record: ProvenanceRecord) -> None:
        with self._lock:
            if len(self._records) >= self._max:
                raise LineageCapacityError(f"Provenance registry capacity ({self._max}) reached")
            self._records[record.record_id] = record
            self._by_entity.setdefault(record.entity_id, []).append(record.record_id)

    def get(self, record_id: str) -> ProvenanceRecord:
        with self._lock:
            rec = self._records.get(record_id)
        if rec is None:
            raise ProvenanceNotFoundError(f"Provenance record '{record_id}' not found")
        return rec

    def get_for_entity(self, entity_id: str) -> list[ProvenanceRecord]:
        with self._lock:
            ids = list(self._by_entity.get(entity_id, []))
            return [self._records[i] for i in ids if i in self._records]

    def latest_for_entity(self, entity_id: str) -> Optional[ProvenanceRecord]:
        records = self.get_for_entity(entity_id)
        if not records:
            return None
        return max(records, key=lambda r: r.created_at)

    def has(self, record_id: str) -> bool:
        with self._lock:
            return record_id in self._records

    def all_records(self) -> list[ProvenanceRecord]:
        with self._lock:
            return list(self._records.values())

    def count(self) -> int:
        with self._lock:
            return len(self._records)

    def stats(self) -> dict[str, Any]:
        with self._lock:
            by_type: dict[str, int] = {}
            for rec in self._records.values():
                k = rec.entity_type.value
                by_type[k] = by_type.get(k, 0) + 1
            return {
                "total":    len(self._records),
                "by_type":  by_type,
                "capacity": self._max,
            }
