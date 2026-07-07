"""
iios/knowledge/versioning/provenance_tracker.py
================================================
ProvenanceTracker — records and retrieves the origin and transformation
history of every knowledge item.

Multiple provenance records may exist per item (creation + derivation +
validation + merge, etc.).  Records are ordered by ``created_at``
(oldest first).
"""

from __future__ import annotations

import logging
import threading
from collections import defaultdict
from typing import Any, Optional

from .version_constants import ProvenanceType, SYSTEM_VERSIONING_ACTOR
from .version_exceptions import ProvenanceError
from .models.provenance_record import ProvenanceRecord

__all__ = ["ProvenanceTracker", "get_provenance_tracker", "reset_provenance_tracker"]

_LOG = logging.getLogger("iios.knowledge.versioning.provenance")
_lock = threading.Lock()
_tracker: Optional["ProvenanceTracker"] = None


class ProvenanceTracker:
    """Thread-safe store for knowledge provenance records."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        # knowledge_id → [ProvenanceRecord, ...] (oldest first)
        self._store: dict[str, list[ProvenanceRecord]] = defaultdict(list)
        # provenance_id → knowledge_id (reverse index)
        self._index: dict[str, str] = {}

    # ── Recording ─────────────────────────────────────────────────────────────

    def record(
        self,
        knowledge_id:      str,
        provenance_type:   ProvenanceType,
        actor:             str = SYSTEM_VERSIONING_ACTOR,
        description:       str = "",
        source_id:         Optional[str] = None,
        source_version_id: Optional[str] = None,
        transformation:    str = "",
        attributes:        Optional[dict[str, Any]] = None,
    ) -> ProvenanceRecord:
        pr = ProvenanceRecord(
            knowledge_id      = knowledge_id,
            provenance_type   = provenance_type,
            source_id         = source_id,
            source_version_id = source_version_id,
            actor             = actor,
            description       = description,
            transformation    = transformation,
            attributes        = dict(attributes or {}),
        )
        with self._lock:
            self._store[knowledge_id].append(pr)
            self._index[pr.provenance_id] = knowledge_id

        _LOG.debug(
            "Provenance: %s on '%s' (type=%s)",
            pr.provenance_id[:8], knowledge_id[:16], provenance_type.value,
        )
        return pr

    def record_creation(
        self,
        knowledge_id: str,
        actor:        str = SYSTEM_VERSIONING_ACTOR,
        description:  str = "",
    ) -> ProvenanceRecord:
        return self.record(knowledge_id, ProvenanceType.CREATED,
                           actor=actor, description=description)

    def record_derivation(
        self,
        knowledge_id:      str,
        source_id:         str,
        transformation:    str,
        actor:             str = SYSTEM_VERSIONING_ACTOR,
        source_version_id: Optional[str] = None,
        description:       str = "",
    ) -> ProvenanceRecord:
        return self.record(
            knowledge_id,
            ProvenanceType.DERIVED_FROM,
            actor             = actor,
            description       = description,
            source_id         = source_id,
            source_version_id = source_version_id,
            transformation    = transformation,
        )

    def record_merge(
        self,
        knowledge_id: str,
        source_ids:   list[str],
        actor:        str = SYSTEM_VERSIONING_ACTOR,
    ) -> list[ProvenanceRecord]:
        return [
            self.record(
                knowledge_id,
                ProvenanceType.MERGED_FROM,
                actor       = actor,
                source_id   = sid,
                description = f"Merged from {sid}",
            )
            for sid in source_ids
        ]

    # ── Retrieval ─────────────────────────────────────────────────────────────

    def get_provenance(
        self,
        knowledge_id:    str,
        provenance_type: Optional[ProvenanceType] = None,
    ) -> list[ProvenanceRecord]:
        with self._lock:
            raw = list(self._store.get(knowledge_id, []))
        if provenance_type is not None:
            raw = [p for p in raw if p.provenance_type == provenance_type]
        return raw

    def get_origin(self, knowledge_id: str) -> Optional[ProvenanceRecord]:
        """Return the earliest CREATED provenance record, if any."""
        for p in self.get_provenance(knowledge_id):
            if p.provenance_type == ProvenanceType.CREATED:
                return p
        return None

    def get_sources(self, knowledge_id: str) -> list[str]:
        """Return unique source_ids this item was derived / merged from."""
        seen: set[str] = set()
        result: list[str] = []
        for p in self.get_provenance(knowledge_id):
            if p.source_id and p.source_id not in seen:
                seen.add(p.source_id)
                result.append(p.source_id)
        return result

    def get_record(self, provenance_id: str) -> ProvenanceRecord:
        with self._lock:
            kid = self._index.get(provenance_id)
            if kid is None:
                raise ProvenanceError(
                    f"Provenance record '{provenance_id}' not found.",
                    code="PT-001",
                )
            for p in self._store[kid]:
                if p.provenance_id == provenance_id:
                    return p
        raise ProvenanceError(
            f"Provenance record '{provenance_id}' not found.", code="PT-002"
        )

    def has_provenance(self, knowledge_id: str) -> bool:
        with self._lock:
            return bool(self._store.get(knowledge_id))

    def record_count(self, knowledge_id: str) -> int:
        with self._lock:
            return len(self._store.get(knowledge_id, []))

    # ── Statistics ────────────────────────────────────────────────────────────

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            total = sum(len(v) for v in self._store.values())
            by_type: dict[str, int] = {}
            for records in self._store.values():
                for p in records:
                    k = p.provenance_type.value
                    by_type[k] = by_type.get(k, 0) + 1
            return {
                "total_records":  total,
                "tracked_items":  len(self._store),
                "by_type":        by_type,
            }


# ── Singleton helpers ─────────────────────────────────────────────────────────

def get_provenance_tracker() -> ProvenanceTracker:
    global _tracker
    if _tracker is None:
        with _lock:
            if _tracker is None:
                _tracker = ProvenanceTracker()
    return _tracker


def reset_provenance_tracker() -> None:
    global _tracker
    with _lock:
        _tracker = None
