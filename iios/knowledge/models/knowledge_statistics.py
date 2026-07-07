"""
iios/knowledge/models/knowledge_statistics.py
==============================================
Aggregated statistics about a knowledge item or the entire repository.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional

__all__ = ["KnowledgeItemStats", "KnowledgeRepositoryStats"]


@dataclass
class KnowledgeItemStats:
    """Statistics for a single knowledge item."""
    knowledge_id:    str   = ""
    access_count:    int   = 0
    update_count:    int   = 0
    validation_runs: int   = 0
    failures:        int   = 0
    version_count:   int   = 1
    link_count:      int   = 0
    last_accessed:   Optional[float] = None
    last_updated:    Optional[float] = None

    def record_access(self) -> None:
        self.access_count += 1
        self.last_accessed = time.time()

    def record_update(self) -> None:
        self.update_count += 1
        self.last_updated = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "knowledge_id":    self.knowledge_id,
            "access_count":    self.access_count,
            "update_count":    self.update_count,
            "validation_runs": self.validation_runs,
            "failures":        self.failures,
            "version_count":   self.version_count,
            "link_count":      self.link_count,
            "last_accessed":   self.last_accessed,
            "last_updated":    self.last_updated,
        }


@dataclass
class KnowledgeRepositoryStats:
    """Aggregate statistics for the whole repository."""
    total_items:      int   = 0
    active_items:     int   = 0
    archived_items:   int   = 0
    deleted_items:    int   = 0
    total_versions:   int   = 0
    total_references: int   = 0
    total_searches:   int   = 0
    cache_hits:       int   = 0
    cache_misses:     int   = 0
    last_write:       Optional[float] = None
    last_read:        Optional[float] = None
    items_by_type:    dict[str, int]  = field(default_factory=dict)
    items_by_domain:  dict[str, int]  = field(default_factory=dict)
    items_by_status:  dict[str, int]  = field(default_factory=dict)

    @property
    def cache_hit_ratio(self) -> float:
        total = self.cache_hits + self.cache_misses
        return self.cache_hits / total if total > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_items":      self.total_items,
            "active_items":     self.active_items,
            "archived_items":   self.archived_items,
            "deleted_items":    self.deleted_items,
            "total_versions":   self.total_versions,
            "total_references": self.total_references,
            "total_searches":   self.total_searches,
            "cache_hits":       self.cache_hits,
            "cache_misses":     self.cache_misses,
            "last_write":       self.last_write,
            "last_read":        self.last_read,
            "items_by_type":    dict(self.items_by_type),
            "items_by_domain":  dict(self.items_by_domain),
            "items_by_status":  dict(self.items_by_status),
            "cache_hit_ratio":  self.cache_hit_ratio,
        }
