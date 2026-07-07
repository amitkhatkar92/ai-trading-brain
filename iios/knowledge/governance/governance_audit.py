"""
iios/knowledge/governance/governance_audit.py
==============================================
GovernanceAuditLog — append-only, per-item audit trail for every
governance lifecycle event.

Identical in spirit to the versioning AuditLog but records
GovernanceAuditEntry objects and is keyed by GovernanceAction.
"""

from __future__ import annotations

import logging
import threading
from collections import defaultdict, deque
from typing import Any, Optional

from .governance_constants import (
    GovernanceAction,
    MAX_AUDIT_ENTRIES,
    SYSTEM_GOVERNANCE_ACTOR,
)
from .governance_exceptions import GovernanceAuditError
from .models.governance_audit import GovernanceAuditEntry

__all__ = ["GovernanceAuditLog", "get_governance_audit_log",
           "reset_governance_audit_log"]

_LOG = logging.getLogger("iios.knowledge.governance.audit")
_lock = threading.Lock()
_log_instance: Optional["GovernanceAuditLog"] = None


class GovernanceAuditLog:
    """Thread-safe append-only governance audit trail."""

    def __init__(self, max_entries: int = MAX_AUDIT_ENTRIES) -> None:
        self._lock  = threading.RLock()
        self._max   = max_entries
        # knowledge_id → deque[GovernanceAuditEntry] (oldest first)
        self._store: dict[str, deque[GovernanceAuditEntry]] = defaultdict(
            lambda: deque(maxlen=self._max)
        )
        # audit_id → knowledge_id (reverse index)
        self._index: dict[str, str] = {}

    # ── Write ─────────────────────────────────────────────────────────────────

    def log(
        self,
        knowledge_id:  str,
        action:        GovernanceAction,
        actor:         str            = SYSTEM_GOVERNANCE_ACTOR,
        reason:        str            = "",
        gov_record_id: Optional[str]  = None,
        cert_id:       Optional[str]  = None,
        kqi_before:    Optional[float]= None,
        kqi_after:     Optional[float]= None,
        details:       Optional[dict[str, Any]] = None,
    ) -> GovernanceAuditEntry:
        entry = GovernanceAuditEntry(
            knowledge_id  = knowledge_id,
            action        = action,
            actor         = actor,
            reason        = reason,
            gov_record_id = gov_record_id,
            cert_id       = cert_id,
            kqi_before    = kqi_before,
            kqi_after     = kqi_after,
            details       = dict(details or {}),
        )
        with self._lock:
            bucket = self._store[knowledge_id]
            if len(bucket) == self._max:
                evicted = bucket[0]
                self._index.pop(evicted.audit_id, None)
            bucket.append(entry)
            self._index[entry.audit_id] = knowledge_id

        _LOG.debug(
            "GovAudit: [%s] on '%s' by '%s'",
            action.value, knowledge_id[:16], actor,
        )
        return entry

    # ── Read ──────────────────────────────────────────────────────────────────

    def get_trail(
        self,
        knowledge_id: str,
        action:       Optional[GovernanceAction] = None,
        actor:        Optional[str]              = None,
        limit:        Optional[int]              = None,
    ) -> list[GovernanceAuditEntry]:
        """Return audit entries for *knowledge_id*, newest first."""
        with self._lock:
            raw: list[GovernanceAuditEntry] = list(
                reversed(self._store.get(knowledge_id, []))
            )
        if action is not None:
            raw = [e for e in raw if e.action == action]
        if actor is not None:
            raw = [e for e in raw if e.actor == actor]
        if limit is not None:
            raw = raw[:limit]
        return raw

    def get_entry(self, audit_id: str) -> GovernanceAuditEntry:
        with self._lock:
            kid = self._index.get(audit_id)
            if kid is None:
                raise GovernanceAuditError(
                    f"Audit entry '{audit_id}' not found.", code="GE-400"
                )
            for e in self._store[kid]:
                if e.audit_id == audit_id:
                    return e
        raise GovernanceAuditError(
            f"Audit entry '{audit_id}' not found.", code="GE-401"
        )

    def entry_count(self, knowledge_id: str) -> int:
        with self._lock:
            return len(self._store.get(knowledge_id, []))

    def total_entries(self) -> int:
        with self._lock:
            return sum(len(v) for v in self._store.values())

    # ── Statistics ────────────────────────────────────────────────────────────

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            total = self.total_entries()
            by_action: dict[str, int] = {}
            for bucket in self._store.values():
                for e in bucket:
                    k = e.action.value
                    by_action[k] = by_action.get(k, 0) + 1
            return {
                "total_entries":  total,
                "tracked_items":  len(self._store),
                "by_action":      by_action,
            }


# ── Singleton helpers ─────────────────────────────────────────────────────────

def get_governance_audit_log() -> GovernanceAuditLog:
    global _log_instance
    if _log_instance is None:
        with _lock:
            if _log_instance is None:
                _log_instance = GovernanceAuditLog()
    return _log_instance


def reset_governance_audit_log() -> None:
    global _log_instance
    with _lock:
        _log_instance = None
