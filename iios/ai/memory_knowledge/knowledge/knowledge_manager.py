"""
knowledge_manager.py -- iios.ai.memory_knowledge.knowledge
===========================================================
:class:`KnowledgeManager` — M2 engine for knowledge CRUD and search.
"""
from __future__ import annotations

import threading
from typing import Any, Dict, FrozenSet, List, Optional

from ..core.knowledge_category  import KnowledgeCategory
from ..core.knowledge_item      import KnowledgeItem
from ..events.event_bus         import MemoryEventBus
from ..events.memory_events     import (
    KnowledgeAddedEvent,
    KnowledgeRemovedEvent,
    KnowledgeUpdatedEvent,
)
from ..exceptions                import (
    AIKnowledgeNotFoundError,
    AIKnowledgeAlreadyExistsError,
    AIKnowledgeValidationError,
)
from .knowledge_collection       import CollectionMetadata, KnowledgeCollection

SYSTEM_ID = "iios:ai:memory_knowledge:knowledge_manager"


class KnowledgeManager:
    """
    Engine layer for knowledge lifecycle: add, remove, update, search.

    Items are stored in a flat catalogue and optionally grouped into
    :class:`KnowledgeCollection` objects.
    """

    def __init__(self, event_bus: Optional[MemoryEventBus] = None) -> None:
        self._event_bus:   MemoryEventBus                         = event_bus or MemoryEventBus()
        self._items:       Dict[str, KnowledgeItem]               = {}
        self._collections: Dict[str, KnowledgeCollection]         = {}
        self._lock:        threading.RLock                        = threading.RLock()

    # ── Item CRUD ─────────────────────────────────────────────────────────────

    def add(
        self,
        title:         str,
        content:       Any,
        category:      KnowledgeCategory   = KnowledgeCategory.DOCUMENT,
        tags:          FrozenSet[str]       = frozenset(),
        author:        str                  = "system",
        source:        str                  = "",
        language:      str                  = "en",
        collection_id: Optional[str]        = None,
        *,
        item_id:       Optional[str]        = None,
    ) -> KnowledgeItem:
        """Create and register a new knowledge item."""
        if not title.strip():
            raise AIKnowledgeValidationError("Knowledge item title must not be blank")
        item = KnowledgeItem.create(
            title         = title,
            content       = content,
            category      = category,
            tags          = tags,
            author        = author,
            source        = source,
            language      = language,
            collection_id = collection_id,
            item_id       = item_id,
        )
        with self._lock:
            if item.item_id in self._items:
                raise AIKnowledgeAlreadyExistsError(item.item_id)
            self._items[item.item_id] = item
            if collection_id and collection_id in self._collections:
                self._collections[collection_id].add(item)
        self._event_bus.publish(
            KnowledgeAddedEvent.create(item.item_id, category.value, title)
        )
        return item

    def remove(self, item_id: str) -> None:
        """Remove a knowledge item; raise if not found."""
        with self._lock:
            if item_id not in self._items:
                raise AIKnowledgeNotFoundError(item_id)
            item = self._items.pop(item_id)
            if item.collection_id and item.collection_id in self._collections:
                self._collections[item.collection_id].remove(item_id)
        self._event_bus.publish(KnowledgeRemovedEvent.create(item_id))

    def update(self, item_id: str, new_content: Any) -> KnowledgeItem:
        """Replace item content; raise if not found."""
        with self._lock:
            if item_id not in self._items:
                raise AIKnowledgeNotFoundError(item_id)
            updated = self._items[item_id].with_content(new_content)
            self._items[item_id] = updated
            cid = updated.collection_id
            if cid and cid in self._collections:
                self._collections[cid].add(updated)
        self._event_bus.publish(
            KnowledgeUpdatedEvent.create(item_id, updated.metadata.version)
        )
        return updated

    def get(self, item_id: str) -> KnowledgeItem:
        """Return item by ID; raise if not found."""
        with self._lock:
            item = self._items.get(item_id)
        if item is None:
            raise AIKnowledgeNotFoundError(item_id)
        return item

    def find_by_title(self, title: str) -> Optional[KnowledgeItem]:
        with self._lock:
            for item in self._items.values():
                if item.title.lower() == title.lower():
                    return item
        return None

    def search(
        self,
        *,
        category: Optional[KnowledgeCategory] = None,
        tags:     Optional[FrozenSet[str]]     = None,
        keyword:  Optional[str]                = None,
    ) -> List[KnowledgeItem]:
        """Filter catalogue by category, tags, and/or keyword in title."""
        with self._lock:
            results = list(self._items.values())
        if category:
            results = [i for i in results if i.category == category]
        if tags:
            results = [i for i in results if tags.issubset(i.tags)]
        if keyword:
            kw = keyword.lower()
            results = [i for i in results if kw in i.title.lower()]
        return results

    def list_all(self) -> List[KnowledgeItem]:
        with self._lock:
            return list(self._items.values())

    def count(self) -> int:
        with self._lock:
            return len(self._items)

    # ── Collection management ─────────────────────────────────────────────────

    def create_collection(
        self,
        name:          str,
        category:      KnowledgeCategory,
        description:   str              = "",
        tags:          FrozenSet[str]   = frozenset(),
        *,
        collection_id: Optional[str]    = None,
    ) -> KnowledgeCollection:
        meta = CollectionMetadata.create(
            name          = name,
            category      = category,
            description   = description,
            tags          = tags,
            collection_id = collection_id,
        )
        col = KnowledgeCollection(meta)
        with self._lock:
            self._collections[col.collection_id] = col
        return col

    def get_collection(self, collection_id: str) -> Optional[KnowledgeCollection]:
        with self._lock:
            return self._collections.get(collection_id)

    def list_collections(self) -> List[KnowledgeCollection]:
        with self._lock:
            return list(self._collections.values())
