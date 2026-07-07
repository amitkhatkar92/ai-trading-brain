"""
iios/knowledge/search/search_factory.py
==========================================
Factory for constructing search-layer objects (queries and results).
"""
from __future__ import annotations

import threading
from typing import Any, Optional

from .search_constants import (
    SearchType, RankingStrategy, SearchSortOrder,
    DEFAULT_SEARCH_PAGE_SIZE, SYSTEM_SEARCH_ACTOR,
)
from .query_builder import QueryBuilder, get_query_builder
from .models.unified_query  import UnifiedSearchQuery
from .models.unified_result import UnifiedSearchResult

__all__ = ["SearchFactory", "get_search_factory", "reset_search_factory"]

_lock:    threading.Lock              = threading.Lock()
_factory: Optional["SearchFactory"]  = None


class SearchFactory:
    """
    Convenience factory for the most common query construction patterns.

    Usage::

        sf = get_search_factory()
        q  = sf.quick_search("NIFTY 50 trend")
        q  = sf.page_query("equity signals", page=2, page_size=20)
        q  = sf.strict_confidence_query("TATASTEEL", min_confidence=0.9)
    """

    def __init__(self, actor: str = SYSTEM_SEARCH_ACTOR) -> None:
        self._actor   = actor
        self._builder = get_query_builder()

    # ── Query factories ───────────────────────────────────────────────────────

    def quick_search(self, text: str, **kwargs: Any) -> UnifiedSearchQuery:
        """Single-text HYBRID search with default settings."""
        return UnifiedSearchQuery(
            search_type      = SearchType.HYBRID,
            text             = text,
            ranking_strategy = RankingStrategy.HYBRID,
            actor            = self._actor,
            **kwargs,
        )

    def page_query(
        self,
        text:      str,
        page:      int = 1,
        page_size: int = DEFAULT_SEARCH_PAGE_SIZE,
        **kwargs:  Any,
    ) -> UnifiedSearchQuery:
        return UnifiedSearchQuery(
            search_type = SearchType.KEYWORD,
            text        = text,
            page        = page,
            page_size   = page_size,
            actor       = self._actor,
            **kwargs,
        )

    def strict_confidence_query(
        self,
        text:           str,
        min_confidence: float = 0.9,
        **kwargs:       Any,
    ) -> UnifiedSearchQuery:
        return UnifiedSearchQuery(
            search_type    = SearchType.HYBRID,
            text           = text,
            min_confidence = min_confidence,
            ranking_strategy = RankingStrategy.CONFIDENCE,
            actor          = self._actor,
            **kwargs,
        )

    def recent_items_query(
        self,
        text:      str = "",
        page_size: int = 20,
        **kwargs:  Any,
    ) -> UnifiedSearchQuery:
        return UnifiedSearchQuery(
            search_type      = SearchType.HYBRID,
            text             = text,
            ranking_strategy = RankingStrategy.RECENCY,
            page_size        = page_size,
            actor            = self._actor,
            **kwargs,
        )

    def domain_query(
        self,
        domain:    str,
        text:      str  = "",
        **kwargs:  Any,
    ) -> UnifiedSearchQuery:
        return UnifiedSearchQuery(
            search_type  = SearchType.HYBRID,
            text         = text,
            filters      = {"domain": domain},
            actor        = self._actor,
            **kwargs,
        )

    def type_query(
        self,
        knowledge_type: str,
        text:           str = "",
        **kwargs:       Any,
    ) -> UnifiedSearchQuery:
        return UnifiedSearchQuery(
            search_type      = SearchType.ONTOLOGY,
            text             = text,
            knowledge_types  = [f"knowledge_type:{knowledge_type.lower()}"],
            actor            = self._actor,
            **kwargs,
        )

    def fuzzy_search(
        self,
        text:            str,
        threshold:       float = 0.75,
        **kwargs:        Any,
    ) -> UnifiedSearchQuery:
        return UnifiedSearchQuery(
            search_type     = SearchType.KEYWORD,
            text            = text,
            fuzzy           = True,
            fuzzy_threshold = threshold,
            actor           = self._actor,
            **kwargs,
        )

    # ── Result factories ──────────────────────────────────────────────────────

    def from_knowledge_record(self, record: Any, score: float = 0.0) -> UnifiedSearchResult:
        return UnifiedSearchResult.from_knowledge_record(record, score=score)

    def from_graph_node(self, node: Any, score: float = 0.0) -> UnifiedSearchResult:
        return UnifiedSearchResult.from_graph_node(node, score=score)


def get_search_factory(actor: str = SYSTEM_SEARCH_ACTOR) -> SearchFactory:
    global _factory
    with _lock:
        if _factory is None:
            _factory = SearchFactory(actor=actor)
        return _factory


def reset_search_factory() -> None:
    global _factory
    with _lock:
        _factory = None
