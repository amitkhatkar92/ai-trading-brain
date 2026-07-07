"""
iios/knowledge/storage/knowledge_storage.py
============================================
Thread-safe in-memory storage backend for knowledge records.
Supports an optional write-through JSON file persistence layer.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, Iterator, Optional

from ..knowledge_constants import KnowledgeStatus
from ..knowledge_exceptions import (
    KnowledgeNotFoundError,
    KnowledgeAlreadyExistsError,
    KnowledgeStorageError,
    KnowledgeSerializationError,
)
from ..models.knowledge_record import KnowledgeRecord

__all__ = [
    "KnowledgeStorage",
    "get_knowledge_storage",
    "reset_knowledge_storage",
]

_LOG = logging.getLogger("iios.knowledge.storage")
_lock = threading.Lock()
_storage: Optional["KnowledgeStorage"] = None


class KnowledgeStorage:
    """Primary in-memory store for KnowledgeRecord objects.

    Optionally persists to a JSON file when *persist_path* is provided.
    All reads/writes are protected by an RLock.

    Usage::

        store = get_knowledge_storage()
        store.put(record)
        record = store.get("iios.knowledge/some-uuid")
        store.delete("iios.knowledge/some-uuid")
    """

    def __init__(self, persist_path: Optional[str] = None) -> None:
        self._lock = threading.RLock()
        self._store: dict[str, KnowledgeRecord] = {}
        self._persist_path = persist_path
        self._dirty = False
        if persist_path and Path(persist_path).exists():
            self._load_from_file(persist_path)

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def put(self, record: KnowledgeRecord, allow_overwrite: bool = True) -> None:
        """Insert or replace a record."""
        with self._lock:
            if not allow_overwrite and record.id in self._store:
                raise KnowledgeAlreadyExistsError(
                    f"Record '{record.id}' already exists",
                    code="KS-001",
                    context={"knowledge_id": record.id},
                )
            self._store[record.id] = record
            self._dirty = True

    def get(self, knowledge_id: str) -> KnowledgeRecord:
        """Return a record by ID. Raises KnowledgeNotFoundError if absent."""
        with self._lock:
            rec = self._store.get(knowledge_id)
        if rec is None:
            raise KnowledgeNotFoundError(
                f"Knowledge record '{knowledge_id}' not found",
                code="KS-002",
                context={"knowledge_id": knowledge_id},
            )
        return rec

    def get_optional(self, knowledge_id: str) -> Optional[KnowledgeRecord]:
        with self._lock:
            return self._store.get(knowledge_id)

    def exists(self, knowledge_id: str) -> bool:
        with self._lock:
            return knowledge_id in self._store

    def delete(self, knowledge_id: str, hard: bool = False) -> bool:
        """Soft-delete (mark is_deleted=True) or hard-delete from storage."""
        with self._lock:
            rec = self._store.get(knowledge_id)
            if rec is None:
                return False
            if hard:
                del self._store[knowledge_id]
            else:
                rec.is_deleted = True
                rec.touch()
            self._dirty = True
        return True

    def restore(self, knowledge_id: str) -> bool:
        """Undo a soft-delete."""
        with self._lock:
            rec = self._store.get(knowledge_id)
            if rec is None:
                return False
            rec.is_deleted = False
            rec.touch()
            self._dirty = True
        return True

    # ── Bulk / iteration ──────────────────────────────────────────────────────

    def all(self, include_deleted: bool = False) -> list[KnowledgeRecord]:
        with self._lock:
            recs = list(self._store.values())
        if include_deleted:
            return recs
        return [r for r in recs if not r.is_deleted]

    def count(self, include_deleted: bool = False) -> int:
        return len(self.all(include_deleted))

    def ids(self) -> list[str]:
        with self._lock:
            return list(self._store.keys())

    def bulk_put(self, records: list[KnowledgeRecord], allow_overwrite: bool = True) -> int:
        n = 0
        for rec in records:
            try:
                self.put(rec, allow_overwrite)
                n += 1
            except KnowledgeAlreadyExistsError:
                pass
        return n

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self._dirty = True

    # ── Persistence ───────────────────────────────────────────────────────────

    def flush(self) -> None:
        """Write dirty records to the persist_path (if configured)."""
        if not self._persist_path:
            return
        with self._lock:
            if not self._dirty:
                return
            data = {k: v.to_dict() for k, v in self._store.items()}
            self._dirty = False

        try:
            tmp = self._persist_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
            os.replace(tmp, self._persist_path)
            _LOG.debug("Flushed %d records to %s", len(data), self._persist_path)
        except OSError as exc:
            raise KnowledgeStorageError(f"Failed to flush: {exc}", code="KS-003") from exc

    def _load_from_file(self, path: str) -> None:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for raw in data.values():
                rec = KnowledgeRecord.from_dict(raw)
                self._store[rec.id] = rec
            _LOG.info("Loaded %d records from %s", len(data), path)
        except Exception as exc:
            _LOG.warning("Failed to load from %s: %s", path, exc)


# ── Singleton ─────────────────────────────────────────────────────────────────

def get_knowledge_storage(persist_path: Optional[str] = None) -> KnowledgeStorage:
    global _storage
    with _lock:
        if _storage is None:
            _storage = KnowledgeStorage(persist_path)
        return _storage


def reset_knowledge_storage() -> None:
    global _storage
    with _lock:
        if _storage is not None:
            _storage.clear()
        _storage = None
