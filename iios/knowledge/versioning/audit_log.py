"""
iios/knowledge/versioning/audit_log.py
=======================================
AuditLog — append-only per-item audit trail for all versioning lifecycle
events.

The log is stored in memory with a configurable maximum per item.  When
the limit is reached the oldest entries are evicted (FIFO) so memory
usage stays bounded.  All writes are serialised through an RLock.
"""

from __future__ import annotations

import logging
import threading
from collections import defaultdict, deque
from typing import Any, Optional

from .version_constants import (
    VersionEventType,
    DEFAULT_BRANCH,
    SYSTEM_VERSIONING_ACTOR,
    MAX_AUDIT_ENTRIES_PER_ITEM,
)
from .version_exceptions import AuditError
from .models.version_audit import AuditEntry

__all__ = ["AuditLog", "get_audit_log", "reset_audit_log"]

_LOG = logging.getLogger("iios.knowledge.versioning.audit")
_lock = threading.Lock()
_log_instance: Optional["AuditLog"] = None


class AuditLog:
    """Append-only, thread-safe audit trail for versioning events."""

    def __init__(self, max_entries_per_item: int = MAX_AUDIT_ENTRIES_PER_ITEM) -> None:
        self._lock = threading.RLock()
        self._max = max_entries_per_item
        # knowledge_id → bounded deque[AuditEntry]  (oldest first)
        self._store: dict[str, deque[AuditEntry]] = defaultdict(
            lambda: deque(maxlen=self._max)
        )
        # audit_id → knowledge_id  (reverse index for get_entry())
        self._index: dict[str, str] = {}

    # ── Write ─────────────────────────────────────────────────────────────────

    def log(
        self,
        knowledge_id: str,
        event_type:   VersionEventType,
        actor:        str  = SYSTEM_VERSIONING_ACTOR,
        reason:       str  = "",
        version_id:   Optional[str]      = None,
        branch_name:  str  = DEFAULT_BRANCH,
        details:      Optional[dict[str, Any]] = None,
    ) -> AuditEntry:
        """Append one audit entry and return it."""
        entry = AuditEntry(
            knowledge_id = knowledge_id,
            event_type   = event_type,
            version_id   = version_id,
            branch_name  = branch_name,
            actor        = actor,
            reason       = reason,
            details      = dict(details or {}),
        )
        with self._lock:
            # If deque is full the oldest entry is automatically evicted by
            # maxlen — remove the corresponding index entry too.
            bucket = self._store[knowledge_id]
            if len(bucket) == self._max:
                evicted = bucket[0]
                self._index.pop(evicted.audit_id, None)
            bucket.append(entry)
            self._index[entry.audit_id] = knowledge_id

        _LOG.debug(
            "Audit: [%s] %s on '%s' by '%s'",
            event_type.value, version_id or "-", knowledge_id[:16], actor,
        )
        return entry

    # ── Read ──────────────────────────────────────────────────────────────────

    def get_trail(
        self,
        knowledge_id: str,
        event_type:   Optional[VersionEventType] = None,
        actor:        Optional[str] = None,
        branch:       Optional[str] = None,
        limit:        Optional[int] = None,
    ) -> list[AuditEntry]:
        """Return audit entries for *knowledge_id*, newest first."""
        with self._lock:
            raw: list[AuditEntry] = list(reversed(self._store.get(knowledge_id, [])))

        if event_type is not None:
            raw = [e for e in raw if e.event_type == event_type]
        if actor is not None:
            raw = [e for e in raw if e.actor == actor]
        if branch is not None:
            raw = [e for e in raw if e.branch_name == branch]
        if limit is not None:
            raw = raw[:limit]
        return raw

    def get_entry(self, audit_id: str) -> AuditEntry:
        with self._lock:
            kid = self._index.get(audit_id)
            if kid is None:
                raise AuditError(
                    f"Audit entry '{audit_id}' not found.", code="AL-001"
                )
            for entry in self._store[kid]:
                if entry.audit_id == audit_id:
                    return entry
        raise AuditError(f"Audit entry '{audit_id}' not found.", code="AL-002")

    def entry_count(self, knowledge_id: str) -> int:
        with self._lock:
            return len(self._store.get(knowledge_id, []))

    def total_entries(self) -> int:
        with self._lock:
            return sum(len(v) for v in self._store.values())

    def clear(self, knowledge_id: str) -> None:
        """Remove all audit entries for *knowledge_id* (for testing)."""
        with self._lock:
            bucket = self._store.pop(knowledge_id, None)
            if bucket:
                for entry in bucket:
                    self._index.pop(entry.audit_id, None)

    # ── Statistics ────────────────────────────────────────────────────────────

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            total = self.total_entries()
            by_event: dict[str, int] = {}
            for bucket in self._store.values():
                for e in bucket:
                    k = e.event_type.value
                    by_event[k] = by_event.get(k, 0) + 1
            return {
                "total_entries":   total,
                "tracked_items":   len(self._store),
                "by_event_type":   by_event,
            }


# ── Singleton helpers ─────────────────────────────────────────────────────────

def get_audit_log() -> AuditLog:
    global _log_instance
    if _log_instance is None:
        with _lock:
            if _log_instance is None:
                _log_instance = AuditLog()
    return _log_instance


def reset_audit_log() -> None:
    global _log_instance
    with _lock:
        _log_instance = None
