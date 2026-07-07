"""
iios/knowledge/search/index_optimizer.py
==========================================
Provides optimization hints and compaction operations for the index store.

Responsibilities:
- Identify large/stale indexes
- Suggest rebuild when fragmentation > threshold
- Remove empty token entries
- Report optimization opportunities
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any, Optional

from .index_manager import IndexManager, get_index_manager
from .index_registry import IndexRegistry, get_index_registry

__all__ = ["IndexOptimizer", "get_index_optimizer", "reset_index_optimizer"]

_LOG   = logging.getLogger("iios.knowledge.search.optimizer")
_lock  = threading.Lock()
_opt:  Optional["IndexOptimizer"] = None

_FRAGMENTATION_THRESHOLD = 0.20   # 20% empty entries → recommend rebuild
_MIN_TOKEN_COUNT         = 1      # remove tokens with fewer docs


class IndexOptimizer:
    """
    Analyzes and compacts the in-memory search indexes.

    Usage::

        opt = get_index_optimizer()
        report = opt.analyze()
        if report["should_compact"]:
            opt.compact()
    """

    def __init__(
        self,
        index_manager: Optional[IndexManager] = None,
        index_registry: Optional[IndexRegistry] = None,
    ) -> None:
        self._mgr  = index_manager  or get_index_manager()
        self._reg  = index_registry or get_index_registry()
        self._lock = threading.RLock()

    def analyze(self) -> dict[str, Any]:
        """
        Return an analysis report with optimization suggestions.

        Keys: item_count, keyword_count, tag_count, empty_keyword_entries,
        fragmentation_ratio, should_compact, recommendations.
        """
        stats = self._mgr.statistics()
        keyword_count = stats.get("keyword_count", 0)

        empty_keyword = 0
        with self._mgr._lock:
            for tok, ids in list(self._mgr._keyword.items()):
                if len(ids) == 0:
                    empty_keyword += 1

        frag = empty_keyword / max(keyword_count, 1)
        should_compact = frag > _FRAGMENTATION_THRESHOLD

        recommendations = []
        if should_compact:
            recommendations.append(
                f"Compact keyword index ({empty_keyword} empty entries, "
                f"{frag:.1%} fragmentation)"
            )
        if stats.get("item_count", 0) == 0:
            recommendations.append("Index is empty; consider running a full rebuild")

        return {
            "item_count":          stats.get("item_count", 0),
            "keyword_count":       keyword_count,
            "tag_count":           stats.get("tag_count", 0),
            "empty_keyword_entries": empty_keyword,
            "fragmentation_ratio": round(frag, 4),
            "should_compact":      should_compact,
            "recommendations":     recommendations,
        }

    def compact(self) -> dict[str, Any]:
        """
        Remove empty token buckets from the keyword index.
        Returns stats: removed_tokens, elapsed_ms.
        """
        start   = time.perf_counter()
        removed = 0
        with self._mgr._lock:
            stale_tokens = [tok for tok, ids in self._mgr._keyword.items() if len(ids) == 0]
            for tok in stale_tokens:
                del self._mgr._keyword[tok]
                removed += 1
        elapsed_ms = (time.perf_counter() - start) * 1000
        _LOG.info("Index compact: removed %d empty keyword entries in %.1f ms", removed, elapsed_ms)
        return {"removed_tokens": removed, "elapsed_ms": round(elapsed_ms, 3)}

    def optimize(self) -> dict[str, Any]:
        """Run analyze + compact if needed."""
        report = self.analyze()
        compact_result: dict[str, Any] = {"removed_tokens": 0, "elapsed_ms": 0.0}
        if report["should_compact"]:
            compact_result = self.compact()
        return {**report, "compact": compact_result}


def get_index_optimizer() -> IndexOptimizer:
    global _opt
    with _lock:
        if _opt is None:
            _opt = IndexOptimizer()
        return _opt


def reset_index_optimizer() -> None:
    global _opt
    with _lock:
        _opt = None
