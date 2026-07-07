"""
iios/knowledge/storage/knowledge_cache.py
==========================================
Read-through / write-behind cache layer for knowledge records.
Wraps the infrastructure CacheManager for LRU eviction and TTL.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Optional

from ..knowledge_constants import DEFAULT_CACHE_TTL
from ..models.knowledge_record import KnowledgeRecord

__all__ = ["KnowledgeCache", "get_knowledge_cache", "reset_knowledge_cache"]

_LOG = logging.getLogger("iios.knowledge.cache")
_lock = threading.Lock()
_cache_instance: Optional["KnowledgeCache"] = None

_CACHE_NAME = "iios_knowledge"
_MAX_SIZE = 5_000


class KnowledgeCache:
    """LRU cache wrapping a MemoryCache for knowledge records.

    Falls back to a plain dict when the infrastructure CacheManager
    is unavailable (for standalone testing).
    """

    def __init__(self, max_size: int = _MAX_SIZE, ttl: float = DEFAULT_CACHE_TTL) -> None:
        self._lock = threading.RLock()
        self._max_size = max_size
        self._ttl = ttl
        self._cache: Optional[Any] = None
        self._fallback: dict[str, KnowledgeRecord] = {}
        self._hits = 0
        self._misses = 0
        self._using_infra = False
        self._init_cache()

    def _init_cache(self) -> None:
        try:
            from iios.infrastructure.cache.cache_manager import get_cache_manager
            mgr = get_cache_manager()
            mgr.create(_CACHE_NAME, max_size=self._max_size, ttl=self._ttl)
            self._cache = mgr.get(_CACHE_NAME)
            self._using_infra = True
            _LOG.debug("KnowledgeCache: using infrastructure MemoryCache")
        except Exception as exc:
            _LOG.debug("KnowledgeCache: infra cache unavailable (%s), using fallback dict", exc)
            self._using_infra = False

    # ── Cache operations ──────────────────────────────────────────────────────

    def get(self, knowledge_id: str) -> Optional[KnowledgeRecord]:
        if self._using_infra and self._cache is not None:
            try:
                val = self._cache.get(knowledge_id)
                if val is not None:
                    self._hits += 1
                    return val
                self._misses += 1
                return None
            except Exception:
                pass
        # Fallback
        rec = self._fallback.get(knowledge_id)
        if rec is not None:
            self._hits += 1
        else:
            self._misses += 1
        return rec

    def set(self, record: KnowledgeRecord, ttl: Optional[float] = None) -> None:
        if self._using_infra and self._cache is not None:
            try:
                self._cache.set(record.id, record, ttl=ttl)
                return
            except Exception:
                pass
        # Fallback with naive size limit
        with self._lock:
            if len(self._fallback) >= self._max_size:
                oldest = next(iter(self._fallback))
                del self._fallback[oldest]
            self._fallback[record.id] = record

    def delete(self, knowledge_id: str) -> bool:
        if self._using_infra and self._cache is not None:
            try:
                self._cache.delete(knowledge_id)
                return True
            except Exception:
                pass
        return self._fallback.pop(knowledge_id, None) is not None

    def clear(self) -> None:
        if self._using_infra and self._cache is not None:
            try:
                self._cache.clear()
            except Exception:
                pass
        with self._lock:
            self._fallback.clear()

    @property
    def hit_ratio(self) -> float:
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0

    def stats(self) -> dict[str, Any]:
        return {
            "hits":       self._hits,
            "misses":     self._misses,
            "hit_ratio":  self.hit_ratio,
            "using_infra": self._using_infra,
        }

    def reset(self) -> None:
        self.clear()
        self._hits = 0
        self._misses = 0


def get_knowledge_cache() -> KnowledgeCache:
    global _cache_instance
    with _lock:
        if _cache_instance is None:
            _cache_instance = KnowledgeCache()
        return _cache_instance


def reset_knowledge_cache() -> None:
    global _cache_instance
    with _lock:
        if _cache_instance is not None:
            _cache_instance.reset()
        _cache_instance = None
