"""
iios/observation/repositories/observation_cache.py
==================================================
LRU cache layer in front of the observation storage.
"""

from __future__ import annotations

import logging
import threading
from collections import OrderedDict
from typing import Any, Optional

from ..observation_constants import MAX_CACHE_SIZE
from ..models.observation import Observation

__all__ = ["ObservationCache", "get_observation_cache", "reset_observation_cache"]

_LOG  = logging.getLogger("iios.observation.cache")
_lock = threading.Lock()
_cache_instance: Optional["ObservationCache"] = None


class ObservationCache:
    """Thread-safe LRU cache for recently accessed observations."""

    def __init__(self, max_size: int = MAX_CACHE_SIZE) -> None:
        self._lock     = threading.RLock()
        self._max      = max_size
        self._store:   OrderedDict[str, Observation] = OrderedDict()
        self._hits:    int = 0
        self._misses:  int = 0

    def get(self, obs_id: str) -> Optional[Observation]:
        with self._lock:
            if obs_id in self._store:
                self._store.move_to_end(obs_id)
                self._hits += 1
                return self._store[obs_id]
            self._misses += 1
            return None

    def put(self, obs: Observation) -> None:
        with self._lock:
            if obs.id in self._store:
                self._store.move_to_end(obs.id)
                self._store[obs.id] = obs
            else:
                if len(self._store) >= self._max:
                    evicted_id, _ = self._store.popitem(last=False)
                    _LOG.debug("Cache evicted: %s", evicted_id[:24])
                self._store[obs.id] = obs

    def invalidate(self, obs_id: str) -> None:
        with self._lock:
            self._store.pop(obs_id, None)

    def contains(self, obs_id: str) -> bool:
        with self._lock:
            return obs_id in self._store

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self._hits   = 0
            self._misses = 0

    def size(self) -> int:
        with self._lock:
            return len(self._store)

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            total = self._hits + self._misses
            return {
                "size":       len(self._store),
                "max_size":   self._max,
                "hits":       self._hits,
                "misses":     self._misses,
                "hit_rate":   round(self._hits / total, 4) if total > 0 else 0.0,
            }


# ── Singleton helpers ─────────────────────────────────────────────────────────

def get_observation_cache() -> ObservationCache:
    global _cache_instance
    if _cache_instance is None:
        with _lock:
            if _cache_instance is None:
                _cache_instance = ObservationCache()
    return _cache_instance


def reset_observation_cache() -> None:
    global _cache_instance
    with _lock:
        _cache_instance = None
