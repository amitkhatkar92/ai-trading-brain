"""
iios/knowledge/search/models/index_definition.py
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from ..search_constants import SearchIndexType

__all__ = ["IndexDefinition", "IndexStatistics"]


@dataclass
class IndexDefinition:
    """Describes a single named index in the search engine."""

    index_id:    str
    name:        str
    index_type:  SearchIndexType
    item_types:  list[str]      # ItemType values this index covers
    fields:      list[str]      # document fields indexed
    is_enabled:  bool           = True
    is_lazy:     bool           = False   # defer indexing until first search
    priority:    int            = 0       # build order (lower = earlier)
    created_at:  float          = field(default_factory=time.time)
    updated_at:  float          = field(default_factory=time.time)
    item_count:  int            = 0
    last_rebuilt: Optional[float] = None

    @classmethod
    def new(
        cls,
        name:       str,
        index_type: SearchIndexType,
        item_types: list[str],
        fields:     list[str],
        **kwargs:   Any,
    ) -> "IndexDefinition":
        return cls(
            index_id   = f"idx:{str(uuid.uuid4())}",
            name       = name,
            index_type = index_type,
            item_types = item_types,
            fields     = fields,
            **kwargs,
        )

    def touch(self) -> None:
        self.updated_at = time.time()

    def mark_rebuilt(self, count: int) -> None:
        self.item_count  = count
        self.last_rebuilt = time.time()
        self.touch()

    def to_dict(self) -> dict[str, Any]:
        return {
            "index_id":    self.index_id,
            "name":        self.name,
            "index_type":  self.index_type.value,
            "item_types":  self.item_types,
            "fields":      self.fields,
            "is_enabled":  self.is_enabled,
            "is_lazy":     self.is_lazy,
            "priority":    self.priority,
            "item_count":  self.item_count,
            "last_rebuilt": self.last_rebuilt,
            "created_at":  self.created_at,
            "updated_at":  self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "IndexDefinition":
        return cls(
            index_id    = data["index_id"],
            name        = data["name"],
            index_type  = SearchIndexType(data["index_type"]),
            item_types  = data.get("item_types", []),
            fields      = data.get("fields", []),
            is_enabled  = data.get("is_enabled", True),
            is_lazy     = data.get("is_lazy", False),
            priority    = data.get("priority", 0),
            created_at  = data.get("created_at", time.time()),
            updated_at  = data.get("updated_at", time.time()),
            item_count  = data.get("item_count", 0),
            last_rebuilt = data.get("last_rebuilt"),
        )


@dataclass
class IndexStatistics:
    """Runtime statistics for a named index."""

    index_id:          str
    name:              str
    item_count:        int   = 0
    token_count:       int   = 0
    build_time_ms:     float = 0.0
    last_query_time_ms: float = 0.0
    total_queries:     int   = 0
    cache_hits:        int   = 0
    cache_misses:      int   = 0
    last_rebuilt:      Optional[float] = None
    computed_at:       float = field(default_factory=time.time)

    @property
    def cache_hit_ratio(self) -> float:
        total = self.cache_hits + self.cache_misses
        return self.cache_hits / total if total > 0 else 0.0

    def record_query(self, time_ms: float, cache_hit: bool) -> None:
        self.total_queries += 1
        self.last_query_time_ms = time_ms
        if cache_hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "index_id":            self.index_id,
            "name":                self.name,
            "item_count":          self.item_count,
            "token_count":         self.token_count,
            "build_time_ms":       round(self.build_time_ms, 3),
            "last_query_time_ms":  round(self.last_query_time_ms, 3),
            "total_queries":       self.total_queries,
            "cache_hits":          self.cache_hits,
            "cache_misses":        self.cache_misses,
            "cache_hit_ratio":     round(self.cache_hit_ratio, 4),
            "last_rebuilt":        self.last_rebuilt,
            "computed_at":         self.computed_at,
        }
