"""
knowledge_collection.py -- iios.ai.memory_knowledge.knowledge
=============================================================
:class:`KnowledgeCollection` — a named, typed group of knowledge items.
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass
from typing import Dict, FrozenSet, List, Optional

from ..core.knowledge_item     import KnowledgeItem
from ..core.knowledge_category import KnowledgeCategory


@dataclass(frozen=True)
class CollectionMetadata:
    """Immutable metadata describing a knowledge collection."""
    collection_id: str
    name:          str
    description:   str
    category:      KnowledgeCategory
    tags:          FrozenSet[str]
    created_at:    float

    @classmethod
    def create(
        cls,
        name:          str,
        category:      KnowledgeCategory,
        description:   str              = "",
        tags:          FrozenSet[str]   = frozenset(),
        *,
        collection_id: Optional[str]    = None,
    ) -> "CollectionMetadata":
        return cls(
            collection_id = collection_id or str(uuid.uuid4()),
            name          = name,
            description   = description,
            category      = category,
            tags          = tags,
            created_at    = time.time(),
        )


class KnowledgeCollection:
    """
    Mutable, thread-safe container of :class:`KnowledgeItem` objects.
    """

    def __init__(self, metadata: CollectionMetadata) -> None:
        self._meta:  CollectionMetadata              = metadata
        self._items: Dict[str, KnowledgeItem]        = {}
        self._lock:  threading.RLock                 = threading.RLock()

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def collection_id(self) -> str:
        return self._meta.collection_id

    @property
    def name(self) -> str:
        return self._meta.name

    @property
    def metadata(self) -> CollectionMetadata:
        return self._meta

    # ── Mutation ──────────────────────────────────────────────────────────────

    def add(self, item: KnowledgeItem) -> None:
        with self._lock:
            self._items[item.item_id] = item

    def remove(self, item_id: str) -> bool:
        with self._lock:
            return self._items.pop(item_id, None) is not None

    # ── Query ─────────────────────────────────────────────────────────────────

    def get(self, item_id: str) -> Optional[KnowledgeItem]:
        with self._lock:
            return self._items.get(item_id)

    def list_all(self) -> List[KnowledgeItem]:
        with self._lock:
            return list(self._items.values())

    def find_by_tags(self, tags: FrozenSet[str]) -> List[KnowledgeItem]:
        with self._lock:
            return [i for i in self._items.values() if tags.issubset(i.tags)]

    def __len__(self) -> int:
        with self._lock:
            return len(self._items)
