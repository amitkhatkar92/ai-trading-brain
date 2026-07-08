"""
iios/decisions/registry/decision_registry.py
=============================================
Thread-safe registry for Decision objects.
Supports lookup, history, lineage, and lifecycle management.
"""
from __future__ import annotations

import threading
import time
from typing import Any

from ..decision_constants import DecisionStatus, DecisionType, MAX_DECISION_RECORDS
from ..decision_exceptions import (
    DecisionAlreadyExistsError,
    DecisionNotFoundError,
    RegistryOverflowError,
)
from ..models.decision import Decision
from ..models.decision_history import DecisionHistory
from ..models.decision_statistics import DecisionStatistics, build_statistics


class DecisionRegistry:
    """
    Append-only thread-safe store for Decision objects.

    Supports:
    - Lookup by decision_id
    - Lookup by source_id (list)
    - Lookup by request_id
    - Lookup by type
    - History per source
    - Lineage chain (request → decision → children)
    - Lifecycle state changes (cancel, expire)
    """

    def __init__(self, max_records: int = MAX_DECISION_RECORDS) -> None:
        self._records:    dict[str, Decision]       = {}
        self._ordered:    list[str]                 = []
        self._by_source:  dict[str, list[str]]      = {}
        self._by_request: dict[str, list[str]]      = {}
        self._by_type:    dict[str, list[str]]      = {}
        self._history:    dict[str, DecisionHistory] = {}   # source_id → history
        self._max:        int                       = max_records
        self._lock:       threading.RLock           = threading.RLock()

    # -- Write ─────────────────────────────────────────────────────────────────

    def register(self, decision: Decision) -> None:
        with self._lock:
            if decision.decision_id in self._records:
                raise DecisionAlreadyExistsError(decision.decision_id)
            if len(self._ordered) >= self._max:
                # Evict oldest
                oldest = self._ordered.pop(0)
                self._records.pop(oldest, None)
            self._records[decision.decision_id] = decision
            self._ordered.append(decision.decision_id)
            # Index by source
            src = decision.metadata.source_id or "unknown"
            self._by_source.setdefault(src, []).append(decision.decision_id)
            # Index by request
            self._by_request.setdefault(decision.request_id, []).append(decision.decision_id)
            # Index by type
            self._by_type.setdefault(decision.decision_type.value, []).append(decision.decision_id)
            # Append to source history
            if src not in self._history:
                self._history[src] = DecisionHistory(source_id=src)
            self._history[src].append(decision)

    def update(self, decision: Decision) -> None:
        """Replace an existing decision in-place."""
        with self._lock:
            if decision.decision_id not in self._records:
                raise DecisionNotFoundError(decision.decision_id)
            self._records[decision.decision_id] = decision

    # -- Read ──────────────────────────────────────────────────────────────────

    def get(self, decision_id: str) -> Decision:
        with self._lock:
            d = self._records.get(decision_id)
        if d is None:
            raise DecisionNotFoundError(decision_id)
        return d

    def has(self, decision_id: str) -> bool:
        with self._lock:
            return decision_id in self._records

    def for_source(self, source_id: str) -> list[Decision]:
        with self._lock:
            ids = list(self._by_source.get(source_id, []))
            return [self._records[i] for i in ids if i in self._records]

    def for_request(self, request_id: str) -> list[Decision]:
        with self._lock:
            ids = list(self._by_request.get(request_id, []))
            return [self._records[i] for i in ids if i in self._records]

    def for_type(self, decision_type: DecisionType) -> list[Decision]:
        with self._lock:
            ids = list(self._by_type.get(decision_type.value, []))
            return [self._records[i] for i in ids if i in self._records]

    def recent(self, n: int = 100) -> list[Decision]:
        with self._lock:
            ids = list(self._ordered[-n:])
            return [self._records[i] for i in reversed(ids) if i in self._records]

    def all(self) -> list[Decision]:
        with self._lock:
            return [self._records[i] for i in self._ordered if i in self._records]

    def history_for_source(self, source_id: str) -> DecisionHistory | None:
        with self._lock:
            return self._history.get(source_id)

    # -- Lifecycle ─────────────────────────────────────────────────────────────

    def cancel(self, decision_id: str) -> None:
        d = self.get(decision_id)
        d.status = DecisionStatus.CANCELLED
        self.update(d)

    def expire(self, decision_id: str) -> None:
        d = self.get(decision_id)
        d.status = DecisionStatus.EXPIRED
        self.update(d)

    def expire_stale(self, ttl_s: float) -> list[str]:
        """Mark all PENDING/IN_PROGRESS decisions older than ttl_s as EXPIRED."""
        now     = time.time()
        expired = []
        with self._lock:
            ids = list(self._ordered)
        for did in ids:
            with self._lock:
                d = self._records.get(did)
            if d and d.status in (DecisionStatus.PENDING, DecisionStatus.IN_PROGRESS):
                if (now - d.created_at) > ttl_s:
                    d.status = DecisionStatus.EXPIRED
                    self.update(d)
                    expired.append(did)
        return expired

    # -- Stats ─────────────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        with self._lock:
            all_d = [self._records[i] for i in self._ordered if i in self._records]
        return {
            "total":    len(all_d),
            "sources":  len(self._by_source),
            "types":    len(self._by_type),
            "completed": sum(1 for d in all_d if d.status == DecisionStatus.COMPLETED),
            "failed":    sum(1 for d in all_d if d.status == DecisionStatus.FAILED),
        }

    def statistics(self, source_id: str | None = None) -> DecisionStatistics:
        with self._lock:
            if source_id:
                ids  = list(self._by_source.get(source_id, []))
                decs = [self._records[i] for i in ids if i in self._records]
            else:
                decs = [self._records[i] for i in self._ordered if i in self._records]
        return build_statistics(decs, source_id=source_id or "*")


# ── Singleton ──────────────────────────────────────────────────────────────────

_LOCK:     threading.Lock           = threading.Lock()
_REGISTRY: DecisionRegistry | None = None


def get_decision_registry() -> DecisionRegistry:
    global _REGISTRY
    if _REGISTRY is None:
        with _LOCK:
            if _REGISTRY is None:
                _REGISTRY = DecisionRegistry()
    return _REGISTRY


def reset_decision_registry() -> None:
    global _REGISTRY
    with _LOCK:
        _REGISTRY = None
