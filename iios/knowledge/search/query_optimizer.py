"""
iios/knowledge/search/query_optimizer.py
==========================================
Pre-execution query optimization: normalization, stop-word removal,
traversal depth capping, and redundancy elimination.
"""
from __future__ import annotations

import re
import threading
from typing import Optional

from .search_constants import SearchType, MAX_SEARCH_PAGE_SIZE
from .models.unified_query import UnifiedSearchQuery

__all__ = ["QueryOptimizer", "get_query_optimizer", "reset_query_optimizer"]

_lock:      threading.Lock              = threading.Lock()
_optimizer: Optional["QueryOptimizer"] = None

# Common stop words to remove from keyword queries
_STOP_WORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "to", "of", "in", "for",
    "on", "with", "at", "by", "from", "up", "about", "into", "through",
    "and", "or", "not", "but", "if", "as", "its", "it", "this", "that",
    "these", "those", "he", "she", "they", "we", "you", "i",
})

_MAX_TRAVERSAL_DEPTH = 10
_WORD_RE = re.compile(r"[a-z0-9_]+")


class QueryOptimizer:
    """
    Rewrites a UnifiedSearchQuery for better execution performance.

    Optimizations applied:
    1. Normalize text (lowercase, strip)
    2. Remove stop words from keyword queries
    3. Cap page_size to MAX_SEARCH_PAGE_SIZE
    4. Cap traversal_depth to _MAX_TRAVERSAL_DEPTH
    5. Deduplicate tags and item_types
    6. Remove empty/whitespace-only filters

    Usage::

        optimizer = get_query_optimizer()
        optimized = optimizer.optimize(query)
    """

    def optimize(self, query: UnifiedSearchQuery) -> UnifiedSearchQuery:
        """Return an optimized copy. Original query is not mutated."""
        from dataclasses import replace
        changes: dict = {}

        # ── Normalize text ────────────────────────────────────────────────────
        normalized = query.text.strip()
        if normalized != query.text:
            changes["text"] = normalized

        # ── Remove stop words for keyword-class searches ──────────────────────
        if query.search_type in (SearchType.KEYWORD, SearchType.HYBRID):
            tokens = _WORD_RE.findall(normalized.lower())
            meaningful = [t for t in tokens if t not in _STOP_WORDS and len(t) >= 2]
            # Only apply if we still have tokens remaining
            if meaningful and len(meaningful) < len(tokens):
                cleaned = " ".join(meaningful)
                changes["text"] = cleaned

        # ── Cap page_size ─────────────────────────────────────────────────────
        if query.page_size > MAX_SEARCH_PAGE_SIZE:
            changes["page_size"] = MAX_SEARCH_PAGE_SIZE

        # ── Cap traversal depth ───────────────────────────────────────────────
        if query.traversal_depth > _MAX_TRAVERSAL_DEPTH:
            changes["traversal_depth"] = _MAX_TRAVERSAL_DEPTH

        # ── Deduplicate tags ──────────────────────────────────────────────────
        dedup_tags = list(dict.fromkeys(t.lower().strip() for t in query.tags if t.strip()))
        if dedup_tags != query.tags:
            changes["tags"] = dedup_tags

        # ── Deduplicate item_types ────────────────────────────────────────────
        dedup_it = list(dict.fromkeys(query.item_types))
        if dedup_it != query.item_types:
            changes["item_types"] = dedup_it

        # ── Remove empty filter values ────────────────────────────────────────
        clean_filters = {
            k: v for k, v in query.filters.items()
            if v is not None and str(v).strip()
        }
        if clean_filters != query.filters:
            changes["filters"] = clean_filters

        if not changes:
            return query  # nothing to change

        return replace(query, **changes)


def get_query_optimizer() -> QueryOptimizer:
    global _optimizer
    with _lock:
        if _optimizer is None:
            _optimizer = QueryOptimizer()
        return _optimizer


def reset_query_optimizer() -> None:
    global _optimizer
    with _lock:
        _optimizer = None
