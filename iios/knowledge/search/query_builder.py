"""
iios/knowledge/search/query_builder.py
========================================
Fluent builder for constructing UnifiedSearchQuery objects.
"""
from __future__ import annotations

import threading
from typing import Any, Optional

from .search_constants import (
    SearchType, RankingStrategy, SearchSortOrder, SearchQueryOp, ItemType,
    DEFAULT_SEARCH_PAGE_SIZE, SYSTEM_SEARCH_ACTOR,
)
from .models.unified_query import UnifiedSearchQuery

__all__ = ["QueryBuilder", "get_query_builder", "reset_query_builder"]

_lock:    threading.Lock             = threading.Lock()
_builder: Optional["QueryBuilder"]  = None


class QueryBuilder:
    """
    Fluent factory for UnifiedSearchQuery objects.

    Usage::

        qb = get_query_builder()

        q = qb.keyword("NIFTY 50 trend", page_size=20)
        q = qb.tag(["equity", "index"], match_all=True)
        q = qb.hybrid("NIFTY", tags=["equity"], filters={"domain": "equity"})
        q = qb.by_id("iios.knowledge/abc123")
        q = qb.graph_traversal("iios.graph/abc123", depth=4)
    """

    # ── Convenience constructors ──────────────────────────────────────────────

    def keyword(
        self,
        text:             str,
        item_types:       Optional[list[str]]   = None,
        min_confidence:   float                 = 0.0,
        min_score:        float                 = 0.0,
        page:             int                   = 1,
        page_size:        int                   = DEFAULT_SEARCH_PAGE_SIZE,
        ranking_strategy: RankingStrategy       = RankingStrategy.HYBRID,
        fuzzy:            bool                  = False,
        fuzzy_threshold:  float                 = 0.75,
        actor:            str                   = SYSTEM_SEARCH_ACTOR,
        **kwargs:         Any,
    ) -> UnifiedSearchQuery:
        return UnifiedSearchQuery(
            search_type      = SearchType.KEYWORD,
            text             = text,
            item_types       = item_types or [],
            min_confidence   = min_confidence,
            min_score        = min_score,
            page             = page,
            page_size        = page_size,
            ranking_strategy = ranking_strategy,
            fuzzy            = fuzzy,
            fuzzy_threshold  = fuzzy_threshold,
            actor            = actor,
            **kwargs,
        )

    def tag(
        self,
        tags:      list[str],
        match_all: bool      = False,
        **kwargs:  Any,
    ) -> UnifiedSearchQuery:
        return UnifiedSearchQuery(
            search_type    = SearchType.TAG,
            tags           = tags,
            tags_match_all = match_all,
            **kwargs,
        )

    def metadata(
        self,
        filters:  dict[str, Any],
        **kwargs: Any,
    ) -> UnifiedSearchQuery:
        return UnifiedSearchQuery(
            search_type = SearchType.METADATA,
            filters     = filters,
            **kwargs,
        )

    def by_id(
        self,
        item_id:  str,
        **kwargs: Any,
    ) -> UnifiedSearchQuery:
        return UnifiedSearchQuery(
            search_type = SearchType.ID_LOOKUP,
            text        = item_id,
            **kwargs,
        )

    def exact(
        self,
        text:     str,
        **kwargs: Any,
    ) -> UnifiedSearchQuery:
        return UnifiedSearchQuery(
            search_type = SearchType.EXACT_MATCH,
            text        = text,
            **kwargs,
        )

    def ontology(
        self,
        keys:     list[str],
        **kwargs: Any,
    ) -> UnifiedSearchQuery:
        """
        Search by ontology keys.

        Keys should be prefixed: "knowledge_type:fact", "domain:equity", "node_type:signal".
        """
        return UnifiedSearchQuery(
            search_type    = SearchType.ONTOLOGY,
            knowledge_types = keys,
            **kwargs,
        )

    def hybrid(
        self,
        text:      str                   = "",
        tags:      Optional[list[str]]   = None,
        filters:   Optional[dict[str, Any]] = None,
        **kwargs:  Any,
    ) -> UnifiedSearchQuery:
        return UnifiedSearchQuery(
            search_type = SearchType.HYBRID,
            text        = text,
            tags        = tags or [],
            filters     = filters or {},
            **kwargs,
        )

    def graph_traversal(
        self,
        start_node_id:   str,
        depth:           int = 3,
        **kwargs:        Any,
    ) -> UnifiedSearchQuery:
        return UnifiedSearchQuery(
            search_type    = SearchType.GRAPH_TRAVERSAL,
            start_node_id  = start_node_id,
            traversal_depth = depth,
            item_types     = [ItemType.GRAPH_NODE.value],
            **kwargs,
        )

    def relationship(
        self,
        item_id:  str,
        **kwargs: Any,
    ) -> UnifiedSearchQuery:
        return UnifiedSearchQuery(
            search_type = SearchType.RELATIONSHIP,
            text        = item_id,
            **kwargs,
        )

    def from_dict(self, data: dict[str, Any]) -> UnifiedSearchQuery:
        return UnifiedSearchQuery.from_dict(data)


def get_query_builder() -> QueryBuilder:
    global _builder
    with _lock:
        if _builder is None:
            _builder = QueryBuilder()
        return _builder


def reset_query_builder() -> None:
    global _builder
    with _lock:
        _builder = None
