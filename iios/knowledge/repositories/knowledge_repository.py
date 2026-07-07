"""
iios/knowledge/repositories/knowledge_repository.py
====================================================
Main repository: unified CRUD + search + pagination over the
storage backend with transparent caching and index maintenance.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable, Optional

from ..knowledge_constants import (
    KnowledgeDomain,
    KnowledgeStatus,
    KnowledgeType,
    QueryOperator,
    SortOrder,
    DEFAULT_PAGE_SIZE,
)
from ..knowledge_exceptions import (
    KnowledgeNotFoundError,
    KnowledgeAlreadyExistsError,
    KnowledgeStorageError,
    KnowledgeArchivedError,
)
from ..models.knowledge_record import KnowledgeRecord
from ..models.knowledge_query import (
    KnowledgeFilter,
    KnowledgeQuery,
    PageRequest,
    PageResult,
)
from ..models.knowledge_statistics import KnowledgeRepositoryStats
from ..storage.knowledge_storage import KnowledgeStorage, get_knowledge_storage
from ..storage.knowledge_cache import KnowledgeCache, get_knowledge_cache
from ..indexing.knowledge_index import KnowledgeIndex, get_knowledge_index

__all__ = [
    "KnowledgeRepository",
    "get_knowledge_repository",
    "reset_knowledge_repository",
]

_LOG = logging.getLogger("iios.knowledge.repository")
_lock = threading.Lock()
_repository: Optional["KnowledgeRepository"] = None


class KnowledgeRepository:
    """Unified CRUD + query interface for knowledge records.

    Orchestrates:
    - ``KnowledgeStorage``  — primary data store
    - ``KnowledgeCache``    — read-through cache
    - ``KnowledgeIndex``    — fast multi-field index

    Usage::

        repo = get_knowledge_repository()
        repo.add(record)
        record = repo.get("iios.knowledge/uuid")
        result = repo.query(KnowledgeQuery())
        repo.delete("iios.knowledge/uuid")
    """

    def __init__(
        self,
        storage: Optional[KnowledgeStorage] = None,
        cache: Optional[KnowledgeCache] = None,
        index: Optional[KnowledgeIndex] = None,
    ) -> None:
        self._lock = threading.RLock()
        self._storage = storage or get_knowledge_storage()
        self._cache   = cache   or get_knowledge_cache()
        self._index   = index   or get_knowledge_index()
        self._stats   = KnowledgeRepositoryStats()
        # Re-index any records already in storage
        self._rebuild_index()

    def _rebuild_index(self) -> None:
        for rec in self._storage.all(include_deleted=False):
            self._index.index(rec)
        _LOG.debug("Index rebuilt with %d records", self._index.count())

    # ── Write operations ──────────────────────────────────────────────────────

    def add(self, record: KnowledgeRecord) -> KnowledgeRecord:
        """Store a new record. Raises KnowledgeAlreadyExistsError if it already exists."""
        if self._storage.exists(record.id):
            raise KnowledgeAlreadyExistsError(
                f"Record '{record.id}' already exists",
                code="KR-001",
                context={"knowledge_id": record.id},
            )
        self._storage.put(record, allow_overwrite=False)
        self._index.index(record)
        self._cache.set(record)
        self._update_stats_on_write(record)
        _LOG.debug("Added record '%s' type=%s", record.id, record.knowledge_type.value)
        return record

    def update(self, record: KnowledgeRecord) -> KnowledgeRecord:
        """Update an existing record. Raises KnowledgeNotFoundError if absent."""
        if not self._storage.exists(record.id):
            raise KnowledgeNotFoundError(
                f"Record '{record.id}' not found",
                code="KR-002",
            )
        existing = self._storage.get(record.id)
        if existing.is_deleted:
            raise KnowledgeNotFoundError(
                f"Record '{record.id}' is soft-deleted",
                code="KR-002b",
            )
        self._storage.put(record, allow_overwrite=True)
        self._index.index(record)
        self._cache.set(record)
        self._stats.last_write = time.time()
        _LOG.debug("Updated record '%s'", record.id)
        return record

    def upsert(self, record: KnowledgeRecord) -> KnowledgeRecord:
        """Insert or update a record."""
        if self._storage.exists(record.id):
            return self.update(record)
        return self.add(record)

    def delete(self, knowledge_id: str, hard: bool = False) -> bool:
        """Soft-delete (default) or hard-delete a record."""
        deleted = self._storage.delete(knowledge_id, hard=hard)
        if deleted:
            self._cache.delete(knowledge_id)
            if hard:
                self._index.deindex(knowledge_id)
            self._stats.deleted_items += 1
            self._stats.total_items = max(0, self._stats.total_items - 1)
        return deleted

    def restore(self, knowledge_id: str) -> bool:
        """Undo a soft-delete."""
        ok = self._storage.restore(knowledge_id)
        if ok:
            rec = self._storage.get(knowledge_id)
            self._index.index(rec)
            self._cache.set(rec)
        return ok

    def bulk_add(self, records: list[KnowledgeRecord]) -> int:
        """Add multiple records; skips duplicates. Returns count added."""
        n = 0
        for rec in records:
            try:
                self.add(rec)
                n += 1
            except KnowledgeAlreadyExistsError:
                pass
        return n

    # ── Read operations ───────────────────────────────────────────────────────

    def get(self, knowledge_id: str) -> KnowledgeRecord:
        """Return a record. Raises KnowledgeNotFoundError if absent."""
        # Cache hit
        rec = self._cache.get(knowledge_id)
        if rec is not None and not rec.is_deleted:
            self._stats.cache_hits += 1
            self._stats.last_read = time.time()
            return rec
        self._stats.cache_misses += 1
        rec = self._storage.get(knowledge_id)
        if rec.is_deleted:
            raise KnowledgeNotFoundError(
                f"Record '{knowledge_id}' is deleted",
                code="KR-003",
            )
        self._cache.set(rec)
        self._stats.last_read = time.time()
        return rec

    def get_optional(self, knowledge_id: str) -> Optional[KnowledgeRecord]:
        try:
            return self.get(knowledge_id)
        except KnowledgeNotFoundError:
            return None

    def exists(self, knowledge_id: str) -> bool:
        rec = self._cache.get(knowledge_id)
        if rec is not None:
            return not rec.is_deleted
        return self._storage.exists(knowledge_id)

    # ── Query ─────────────────────────────────────────────────────────────────

    def query(self, query: Optional[KnowledgeQuery] = None) -> PageResult:
        """Execute a structured query. Returns a paginated PageResult."""
        q = query or KnowledgeQuery()
        filt = q.filter
        page = q.pagination

        # Start from index or full scan
        candidate_ids = self._apply_index_filters(filt)
        # Materialise candidates
        candidates = [
            r for r in (self._storage.get_optional(rid) for rid in candidate_ids)
            if r is not None and (filt.include_deleted or not r.is_deleted)
        ]
        # Fine-grained filter
        candidates = [r for r in candidates if self._match_filter(r, filt)]
        # Sort
        candidates = self._sort(candidates, page.sort_by, page.sort_order)
        # Paginate
        total = len(candidates)
        start = page.offset
        end = start + page.page_size
        page_items = candidates[start:end]
        self._stats.total_searches += 1
        return PageResult.build(page_items, total, page)

    def _apply_index_filters(self, filt: KnowledgeFilter) -> set[str]:
        """Use indexes where possible to reduce candidate set."""
        if filt.knowledge_types:
            ids: set[str] = set()
            for kt in filt.knowledge_types:
                ids |= self._index.by_type(kt)
        elif filt.statuses:
            ids = set()
            for st in filt.statuses:
                ids |= self._index.by_status(st)
        elif filt.domains:
            ids = set()
            for d in filt.domains:
                ids |= self._index.by_domain(d)
        elif filt.tags:
            ids = self._index.by_tags(filt.tags, match_all=False)
        elif filt.owner_ids:
            ids = set()
            for oid in filt.owner_ids:
                ids |= self._index.by_owner(oid)
        else:
            ids = self._index.all_ids()
        return ids

    def _match_filter(self, rec: KnowledgeRecord, filt: KnowledgeFilter) -> bool:
        if filt.knowledge_types and rec.knowledge_type not in filt.knowledge_types:
            return False
        if filt.statuses and rec.status not in filt.statuses:
            return False
        if filt.domains and rec.metadata.domain not in filt.domains:
            return False
        if filt.owner_ids and rec.metadata.owner_id not in filt.owner_ids:
            return False
        if filt.tags:
            if not any(rec.metadata.has_tag(t) for t in filt.tags):
                return False
        if filt.created_after and rec.created_at < filt.created_after:
            return False
        if filt.created_before and rec.created_at > filt.created_before:
            return False
        if filt.updated_after and rec.updated_at < filt.updated_after:
            return False
        if filt.min_confidence is not None and rec.metadata.confidence < filt.min_confidence:
            return False
        if filt.max_confidence is not None and rec.metadata.confidence > filt.max_confidence:
            return False
        if not filt.include_expired and rec.is_expired:
            return False
        # Evaluate custom conditions
        for cond in filt.conditions:
            val = self._resolve_field(rec, cond.field)
            if not self._evaluate_condition(val, cond.operator, cond.value):
                return False
        return True

    def _resolve_field(self, rec: KnowledgeRecord, field_path: str) -> Any:
        obj: Any = rec
        for part in field_path.split("."):
            if isinstance(obj, dict):
                obj = obj.get(part)
            else:
                obj = getattr(obj, part, None)
            if obj is None:
                return None
        return obj

    def _evaluate_condition(self, val: Any, op: QueryOperator, expected: Any) -> bool:
        try:
            if op == QueryOperator.EQ:       return val == expected
            if op == QueryOperator.NEQ:      return val != expected
            if op == QueryOperator.GT:       return val > expected
            if op == QueryOperator.GTE:      return val >= expected
            if op == QueryOperator.LT:       return val < expected
            if op == QueryOperator.LTE:      return val <= expected
            if op == QueryOperator.IN:       return val in expected
            if op == QueryOperator.NOT_IN:   return val not in expected
            if op == QueryOperator.CONTAINS: return expected in str(val)
            if op == QueryOperator.STARTS_WITH: return str(val).startswith(str(expected))
            if op == QueryOperator.ENDS_WITH:   return str(val).endswith(str(expected))
            if op == QueryOperator.EXISTS:   return val is not None
            if op == QueryOperator.BETWEEN:
                lo, hi = expected
                return lo <= val <= hi
        except (TypeError, ValueError):
            pass
        return False

    def _sort(self, items: list[KnowledgeRecord], sort_by: str, order: SortOrder) -> list[KnowledgeRecord]:
        def key_fn(r: KnowledgeRecord) -> Any:
            val = self._resolve_field(r, sort_by)
            return (0, "") if val is None else (1, val)
        return sorted(items, key=key_fn, reverse=(order == SortOrder.DESC))

    # ── Statistics ─────────────────────────────────────────────────────────────

    def _update_stats_on_write(self, record: KnowledgeRecord) -> None:
        self._stats.total_items += 1
        self._stats.last_write = time.time()
        k = record.knowledge_type.value
        d = record.metadata.domain.value
        s = record.status.value
        self._stats.items_by_type[k] = self._stats.items_by_type.get(k, 0) + 1
        self._stats.items_by_domain[d] = self._stats.items_by_domain.get(d, 0) + 1
        self._stats.items_by_status[s] = self._stats.items_by_status.get(s, 0) + 1
        if record.status == KnowledgeStatus.ACTIVE:
            self._stats.active_items += 1
        elif record.status == KnowledgeStatus.ARCHIVED:
            self._stats.archived_items += 1

    def stats(self) -> KnowledgeRepositoryStats:
        self._stats.total_items = self._storage.count()
        return self._stats

    def count(self) -> int:
        return self._storage.count()

    def reset(self) -> None:
        self._storage.clear()
        self._index.reset()
        self._cache.clear()
        self._stats = KnowledgeRepositoryStats()


# ── Singleton ─────────────────────────────────────────────────────────────────

def get_knowledge_repository() -> KnowledgeRepository:
    global _repository
    with _lock:
        if _repository is None:
            _repository = KnowledgeRepository()
        return _repository


def reset_knowledge_repository() -> None:
    global _repository
    with _lock:
        if _repository is not None:
            _repository.reset()
        _repository = None
