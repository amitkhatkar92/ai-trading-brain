"""
iios/knowledge/search/index_registry.py
========================================
Registry of IndexDefinition entries (index metadata, not the data store itself).
"""
from __future__ import annotations

import threading
from typing import Any, Optional

from .search_constants import SearchIndexType, ItemType
from .search_exceptions import SearchIndexNotFoundError, SearchIndexAlreadyExistsError
from .models.index_definition import IndexDefinition

__all__ = ["IndexRegistry", "get_index_registry", "reset_index_registry"]

_lock:     threading.Lock                  = threading.Lock()
_registry: Optional["IndexRegistry"]       = None


class IndexRegistry:
    """Maintains the catalog of all known IndexDefinitions."""

    def __init__(self) -> None:
        self._lock:    threading.RLock             = threading.RLock()
        self._entries: dict[str, IndexDefinition]  = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        defaults = [
            IndexDefinition.new(
                name       = "primary",
                index_type = SearchIndexType.PRIMARY,
                item_types = [ItemType.KNOWLEDGE.value, ItemType.GRAPH_NODE.value],
                fields     = ["id", "title", "content"],
                priority   = 0,
            ),
            IndexDefinition.new(
                name       = "keyword",
                index_type = SearchIndexType.KEYWORD,
                item_types = [ItemType.KNOWLEDGE.value, ItemType.GRAPH_NODE.value],
                fields     = ["title", "content", "description"],
                priority   = 1,
            ),
            IndexDefinition.new(
                name       = "tag",
                index_type = SearchIndexType.TAG,
                item_types = [ItemType.KNOWLEDGE.value, ItemType.GRAPH_NODE.value],
                fields     = ["tags"],
                priority   = 2,
            ),
            IndexDefinition.new(
                name       = "metadata",
                index_type = SearchIndexType.METADATA,
                item_types = [ItemType.KNOWLEDGE.value, ItemType.GRAPH_NODE.value],
                fields     = ["metadata.*"],
                priority   = 3,
            ),
            IndexDefinition.new(
                name       = "ontology",
                index_type = SearchIndexType.ONTOLOGY,
                item_types = [ItemType.KNOWLEDGE.value, ItemType.GRAPH_NODE.value],
                fields     = ["knowledge_type", "domain", "node_type"],
                priority   = 4,
            ),
            IndexDefinition.new(
                name       = "graph",
                index_type = SearchIndexType.GRAPH,
                item_types = [ItemType.GRAPH_NODE.value],
                fields     = ["node_type", "label", "weight"],
                priority   = 5,
            ),
            IndexDefinition.new(
                name       = "temporal",
                index_type = SearchIndexType.TEMPORAL,
                item_types = [ItemType.KNOWLEDGE.value, ItemType.GRAPH_NODE.value],
                fields     = ["created_at", "updated_at"],
                priority   = 6,
            ),
        ]
        for defn in defaults:
            self._entries[defn.name] = defn

    def register(self, defn: IndexDefinition, override: bool = False) -> None:
        with self._lock:
            if not override and defn.name in self._entries:
                raise SearchIndexAlreadyExistsError(
                    f"Index '{defn.name}' already registered", code="IR-001",
                )
            self._entries[defn.name] = defn

    def get(self, name: str) -> IndexDefinition:
        with self._lock:
            entry = self._entries.get(name)
        if entry is None:
            raise SearchIndexNotFoundError(f"Index '{name}' not found", code="IR-002")
        return entry

    def get_optional(self, name: str) -> Optional[IndexDefinition]:
        with self._lock:
            return self._entries.get(name)

    def has(self, name: str) -> bool:
        with self._lock:
            return name in self._entries

    def all(self) -> list[IndexDefinition]:
        with self._lock:
            return sorted(self._entries.values(), key=lambda d: d.priority)

    def enabled(self) -> list[IndexDefinition]:
        with self._lock:
            return sorted(
                [d for d in self._entries.values() if d.is_enabled],
                key=lambda d: d.priority,
            )

    def list_names(self) -> list[str]:
        with self._lock:
            return sorted(self._entries.keys())

    def mark_rebuilt(self, name: str, count: int) -> None:
        with self._lock:
            entry = self._entries.get(name)
        if entry:
            entry.mark_rebuilt(count)

    def unregister(self, name: str) -> None:
        with self._lock:
            self._entries.pop(name, None)

    def reset(self) -> None:
        with self._lock:
            self._entries.clear()
            self._register_defaults()

    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            return {name: d.to_dict() for name, d in self._entries.items()}


def get_index_registry() -> IndexRegistry:
    global _registry
    with _lock:
        if _registry is None:
            _registry = IndexRegistry()
        return _registry


def reset_index_registry() -> None:
    global _registry
    with _lock:
        _registry = None
