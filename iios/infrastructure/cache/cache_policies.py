"""
iios/infrastructure/cache/cache_policies.py
============================================
Eviction policy implementations: LRU, LFU, FIFO.
"""

from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from collections import OrderedDict, defaultdict
from typing import Any, Hashable, Optional

__all__ = ["CachePolicy", "LRUPolicy", "LFUPolicy", "FIFOPolicy"]


class CachePolicy(ABC):
    """Abstract base for eviction policies."""

    @abstractmethod
    def on_access(self, key: Hashable) -> None:
        """Called when a key is accessed (hit)."""

    @abstractmethod
    def on_insert(self, key: Hashable) -> None:
        """Called when a new key is inserted."""

    @abstractmethod
    def on_delete(self, key: Hashable) -> None:
        """Called when a key is explicitly deleted."""

    @abstractmethod
    def evict_key(self) -> Optional[Hashable]:
        """Return the key to evict (or None if nothing tracked)."""


class LRUPolicy(CachePolicy):
    """Least Recently Used eviction."""

    def __init__(self) -> None:
        self._order: OrderedDict[Hashable, None] = OrderedDict()
        self._lock = threading.Lock()

    def on_access(self, key: Hashable) -> None:
        with self._lock:
            if key in self._order:
                self._order.move_to_end(key)

    def on_insert(self, key: Hashable) -> None:
        with self._lock:
            self._order[key] = None
            self._order.move_to_end(key)

    def on_delete(self, key: Hashable) -> None:
        with self._lock:
            self._order.pop(key, None)

    def evict_key(self) -> Optional[Hashable]:
        with self._lock:
            if not self._order:
                return None
            return next(iter(self._order))

    def __len__(self) -> int:
        return len(self._order)


class LFUPolicy(CachePolicy):
    """Least Frequently Used eviction."""

    def __init__(self) -> None:
        self._freq: dict[Hashable, int] = {}
        self._lock = threading.Lock()

    def on_access(self, key: Hashable) -> None:
        with self._lock:
            if key in self._freq:
                self._freq[key] += 1

    def on_insert(self, key: Hashable) -> None:
        with self._lock:
            self._freq[key] = 1

    def on_delete(self, key: Hashable) -> None:
        with self._lock:
            self._freq.pop(key, None)

    def evict_key(self) -> Optional[Hashable]:
        with self._lock:
            if not self._freq:
                return None
            return min(self._freq, key=lambda k: self._freq[k])

    def __len__(self) -> int:
        return len(self._freq)


class FIFOPolicy(CachePolicy):
    """First In First Out eviction."""

    def __init__(self) -> None:
        self._order: list[Hashable] = []
        self._lock = threading.Lock()

    def on_access(self, key: Hashable) -> None:
        pass  # FIFO does not change order on access

    def on_insert(self, key: Hashable) -> None:
        with self._lock:
            self._order.append(key)

    def on_delete(self, key: Hashable) -> None:
        with self._lock:
            try:
                self._order.remove(key)
            except ValueError:
                pass

    def evict_key(self) -> Optional[Hashable]:
        with self._lock:
            if not self._order:
                return None
            return self._order[0]

    def __len__(self) -> int:
        return len(self._order)
