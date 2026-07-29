"""
memory_manager.py -- iios.ai.memory_knowledge.memory
=====================================================
:class:`MemoryManager` — M2 engine for all memory operations.

Responsibilities
----------------
* CRUD on :class:`MemoryEntry` objects via a :class:`MemoryStore`.
* Scope-aware retrieval (working / session / long-term / shared).
* Expired-entry detection and eviction.
* Event publishing via :class:`MemoryEventBus`.
* Policy evaluation via :class:`RetentionPolicy` and :class:`PrivacyPolicy`.
"""
from __future__ import annotations

import threading
import time
from typing import Any, FrozenSet, List, Optional

from ..core.memory_entry    import MemoryEntry
from ..core.memory_scope    import MemoryScope
from ..events.event_bus     import MemoryEventBus
from ..events.memory_events import (
    MemoryCreatedEvent,
    MemoryDeletedEvent,
    MemoryExpiredEvent,
    MemoryUpdatedEvent,
)
from ..exceptions           import AIMemoryNotFoundError, AIMemoryExpiredError
from .memory_store           import InMemoryStore, MemoryStore

SYSTEM_ID = "iios:ai:memory_knowledge:memory_manager"


class MemoryManager:
    """
    Engine layer for memory lifecycle management.

    Usage::

        manager = MemoryManager()
        entry = manager.store(content="hello", scope=MemoryScope.SESSION)
        retrieved = manager.retrieve(entry.entry_id)
    """

    def __init__(
        self,
        store:     Optional[MemoryStore]     = None,
        event_bus: Optional[MemoryEventBus]  = None,
    ) -> None:
        self._store:     MemoryStore     = store or InMemoryStore()
        self._event_bus: MemoryEventBus  = event_bus or MemoryEventBus()
        self._lock:      threading.RLock = threading.RLock()

    # ── Write ─────────────────────────────────────────────────────────────────

    def store(
        self,
        content:    Any,
        scope:      MemoryScope         = MemoryScope.SESSION,
        owner_id:   str                 = "system",
        tags:       FrozenSet[str]      = frozenset(),
        expires_at: Optional[float]     = None,
        source:     str                 = "",
        *,
        entry_id:   Optional[str]       = None,
    ) -> MemoryEntry:
        """Create and persist a new memory entry; return the entry."""
        entry = MemoryEntry.create(
            content    = content,
            scope      = scope,
            owner_id   = owner_id,
            tags       = tags,
            expires_at = expires_at,
            source     = source,
            entry_id   = entry_id,
        )
        self._store.put(entry)
        self._event_bus.publish(
            MemoryCreatedEvent.create(entry.entry_id, scope.value, owner_id)
        )
        return entry

    def update(self, entry_id: str, new_content: Any) -> MemoryEntry:
        """Replace content of an existing entry; raise if not found or expired."""
        existing = self._get_or_raise(entry_id)
        updated  = existing.with_content(new_content)
        self._store.put(updated)
        self._event_bus.publish(
            MemoryUpdatedEvent.create(entry_id, updated.metadata.version)
        )
        return updated

    def delete(self, entry_id: str) -> None:
        """Delete an entry by ID; raise :class:`AIMemoryNotFoundError` if absent."""
        if not self._store.delete(entry_id):
            raise AIMemoryNotFoundError(entry_id)
        self._event_bus.publish(MemoryDeletedEvent.create(entry_id))

    # ── Read ──────────────────────────────────────────────────────────────────

    def retrieve(self, entry_id: str) -> MemoryEntry:
        """Return an entry; raise on missing or expired."""
        return self._get_or_raise(entry_id)

    def retrieve_by_scope(self, scope: MemoryScope) -> List[MemoryEntry]:
        """Return all non-expired entries in a scope."""
        return self._filter_live(self._store.list_by_scope(scope))

    def retrieve_by_owner(self, owner_id: str) -> List[MemoryEntry]:
        """Return all non-expired entries owned by ``owner_id``."""
        return self._filter_live(self._store.list_by_owner(owner_id))

    def retrieve_by_tags(self, tags: FrozenSet[str]) -> List[MemoryEntry]:
        """Return all non-expired entries that carry ALL of the given tags."""
        return [
            e for e in self._filter_live(self._store.list_all())
            if tags.issubset(e.tags)
        ]

    def list_all(self) -> List[MemoryEntry]:
        """Return every non-expired entry."""
        return self._filter_live(self._store.list_all())

    # ── Maintenance ───────────────────────────────────────────────────────────

    def evict_expired(self) -> int:
        """Purge all expired entries; return count evicted."""
        expired = [e for e in self._store.list_all() if e.is_expired()]
        for e in expired:
            self._store.delete(e.entry_id)
            self._event_bus.publish(MemoryExpiredEvent.create(e.entry_id))
        return len(expired)

    def count(self) -> int:
        return self._store.count()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _get_or_raise(self, entry_id: str) -> MemoryEntry:
        entry = self._store.get(entry_id)
        if entry is None:
            raise AIMemoryNotFoundError(entry_id)
        if entry.is_expired():
            self._store.delete(entry_id)
            self._event_bus.publish(MemoryExpiredEvent.create(entry_id))
            raise AIMemoryExpiredError(entry_id)
        return entry

    def _filter_live(self, entries: List[MemoryEntry]) -> List[MemoryEntry]:
        live, expired = [], []
        for e in entries:
            if e.is_expired():
                expired.append(e)
            else:
                live.append(e)
        for e in expired:
            self._store.delete(e.entry_id)
            self._event_bus.publish(MemoryExpiredEvent.create(e.entry_id))
        return live
