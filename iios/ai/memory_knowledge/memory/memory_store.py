"""
memory_store.py -- iios.ai.memory_knowledge.memory
===================================================
:class:`MemoryStore` — storage-independent ABC for memory persistence.

Concrete backends (Redis, SQLite, in-process dict, cloud KV) implement
this interface.  A4 ships with :class:`InMemoryStore` as the default.
"""
from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from ..core.memory_entry  import MemoryEntry
from ..core.memory_scope  import MemoryScope


class MemoryStore(ABC):
    """Abstract storage backend for memory entries."""

    @abstractmethod
    def put(self, entry: MemoryEntry) -> None:
        """Persist (insert or replace) an entry."""

    @abstractmethod
    def get(self, entry_id: str) -> Optional[MemoryEntry]:
        """Return entry by ID, or None if absent."""

    @abstractmethod
    def delete(self, entry_id: str) -> bool:
        """Delete entry; return True if it existed."""

    @abstractmethod
    def list_by_scope(self, scope: MemoryScope) -> List[MemoryEntry]:
        """Return all entries with the given scope."""

    @abstractmethod
    def list_by_owner(self, owner_id: str) -> List[MemoryEntry]:
        """Return all entries owned by ``owner_id``."""

    @abstractmethod
    def list_all(self) -> List[MemoryEntry]:
        """Return every entry in the store."""

    @abstractmethod
    def clear(self) -> int:
        """Delete all entries; return count deleted."""

    @abstractmethod
    def count(self) -> int:
        """Return the total number of stored entries."""


# ─────────────────────────────────────────────────────────────────────────────
# Default implementation: in-process dictionary
# ─────────────────────────────────────────────────────────────────────────────

class InMemoryStore(MemoryStore):
    """Thread-safe in-process memory store (default implementation)."""

    def __init__(self) -> None:
        self._lock:  threading.RLock                    = threading.RLock()
        self._store: Dict[str, MemoryEntry]             = {}

    def put(self, entry: MemoryEntry) -> None:
        with self._lock:
            self._store[entry.entry_id] = entry

    def get(self, entry_id: str) -> Optional[MemoryEntry]:
        with self._lock:
            return self._store.get(entry_id)

    def delete(self, entry_id: str) -> bool:
        with self._lock:
            return self._store.pop(entry_id, None) is not None

    def list_by_scope(self, scope: MemoryScope) -> List[MemoryEntry]:
        with self._lock:
            return [e for e in self._store.values() if e.scope == scope]

    def list_by_owner(self, owner_id: str) -> List[MemoryEntry]:
        with self._lock:
            return [e for e in self._store.values() if e.owner_id == owner_id]

    def list_all(self) -> List[MemoryEntry]:
        with self._lock:
            return list(self._store.values())

    def clear(self) -> int:
        with self._lock:
            count = len(self._store)
            self._store.clear()
            return count

    def count(self) -> int:
        with self._lock:
            return len(self._store)
