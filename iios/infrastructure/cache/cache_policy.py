"""
iios/infrastructure/cache/cache_policy.py
==========================================
Eviction policy implementations for the IIOS Distributed Caching Framework.
Each policy implements the ``select_victims(entries, count)`` interface,
selecting the *count* entries that should be evicted from the provided list.

Separate from the legacy ``cache_policies.py`` which uses the key-tracking
(on_access/on_insert) interface. These policies work directly with CacheEntry
objects and are used by the new multi-level cache providers.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any

from .cache_entry import CacheEntry
from .cache_constants import EvictionPolicy

__all__ = [
    "BaseEvictionPolicy",
    "LRUEvictionPolicy",
    "LFUEvictionPolicy",
    "FIFOEvictionPolicy",
    "TTLEvictionPolicy",
    "SizeEvictionPolicy",
    "PriorityEvictionPolicy",
    "NullEvictionPolicy",
    "make_eviction_policy",
]


class BaseEvictionPolicy(ABC):
    """Abstract base for entry-based eviction policies."""

    @abstractmethod
    def select_victims(self, entries: list[CacheEntry], count: int) -> list[str]:
        """Return *count* keys to evict from *entries* (sorted worst → best)."""

    def name(self) -> str:
        return type(self).__name__


class LRUEvictionPolicy(BaseEvictionPolicy):
    """Evict entries with the oldest ``last_accessed`` timestamp."""

    def select_victims(self, entries: list[CacheEntry], count: int) -> list[str]:
        sorted_entries = sorted(entries, key=lambda e: e.last_accessed)
        return [e.key for e in sorted_entries[:count]]


class LFUEvictionPolicy(BaseEvictionPolicy):
    """Evict entries with the fewest accesses (ties broken by last_accessed)."""

    def select_victims(self, entries: list[CacheEntry], count: int) -> list[str]:
        sorted_entries = sorted(entries, key=lambda e: (e.access_count, e.last_accessed))
        return [e.key for e in sorted_entries[:count]]


class FIFOEvictionPolicy(BaseEvictionPolicy):
    """Evict entries that were inserted first (oldest ``created_at``)."""

    def select_victims(self, entries: list[CacheEntry], count: int) -> list[str]:
        sorted_entries = sorted(entries, key=lambda e: e.created_at)
        return [e.key for e in sorted_entries[:count]]


class TTLEvictionPolicy(BaseEvictionPolicy):
    """Evict expired entries first, then those closest to expiry."""

    def select_victims(self, entries: list[CacheEntry], count: int) -> list[str]:
        now = time.time()

        def _sort_key(e: CacheEntry) -> tuple[int, float]:
            if e.is_expired:
                return (0, 0.0)   # expired — evict first
            if e.expires_at is None:
                return (2, float("inf"))  # immortal — evict last
            return (1, e.expires_at)      # soonest-to-expire first

        sorted_entries = sorted(entries, key=_sort_key)
        return [e.key for e in sorted_entries[:count]]


class SizeEvictionPolicy(BaseEvictionPolicy):
    """Evict the largest entries first to free maximum memory."""

    def select_victims(self, entries: list[CacheEntry], count: int) -> list[str]:
        sorted_entries = sorted(entries, key=lambda e: e.size_bytes, reverse=True)
        return [e.key for e in sorted_entries[:count]]


class PriorityEvictionPolicy(BaseEvictionPolicy):
    """Evict lowest-priority entries first (highest priority int value)."""

    def select_victims(self, entries: list[CacheEntry], count: int) -> list[str]:
        # Higher priority int = lower importance = evicted first
        # Ties broken by LRU (oldest last_accessed)
        sorted_entries = sorted(entries, key=lambda e: (-e.priority, e.last_accessed))
        return [e.key for e in sorted_entries[:count]]


class NullEvictionPolicy(BaseEvictionPolicy):
    """No eviction — returns empty list (cache silently stops accepting writes when full)."""

    def select_victims(self, entries: list[CacheEntry], count: int) -> list[str]:
        return []


def make_eviction_policy(policy: EvictionPolicy) -> BaseEvictionPolicy:
    """Factory function — returns the appropriate policy implementation."""
    mapping: dict[EvictionPolicy, BaseEvictionPolicy] = {
        EvictionPolicy.LRU: LRUEvictionPolicy(),
        EvictionPolicy.LFU: LFUEvictionPolicy(),
        EvictionPolicy.FIFO: FIFOEvictionPolicy(),
        EvictionPolicy.TTL: TTLEvictionPolicy(),
        EvictionPolicy.SIZE: SizeEvictionPolicy(),
        EvictionPolicy.PRIORITY: PriorityEvictionPolicy(),
        EvictionPolicy.NONE: NullEvictionPolicy(),
    }
    return mapping.get(policy, LRUEvictionPolicy())
