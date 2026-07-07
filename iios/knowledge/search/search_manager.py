"""
iios/knowledge/search/search_manager.py
==========================================
High-level façade for the Knowledge Indexing & Search Engine.
Primary public entry-point for all search and indexing operations.
"""
from __future__ import annotations

import logging
import threading
from typing import Any, Optional

from .search_constants import (
    SearchType, RankingStrategy, ItemType, SYSTEM_SEARCH_ACTOR,
    DEFAULT_SEARCH_PAGE_SIZE,
)
from .index_manager    import IndexManager,    get_index_manager
from .index_builder    import IndexBuilder,    get_index_builder
from .index_registry   import IndexRegistry,   get_index_registry
from .index_optimizer  import IndexOptimizer,  get_index_optimizer
from .index_statistics import SearchStats,     get_search_stats
from .query_builder    import QueryBuilder,    get_query_builder
from .search_engine    import SearchEngine,    get_search_engine
from .search_factory   import SearchFactory,   get_search_factory
from .models.unified_query   import UnifiedSearchQuery
from .models.unified_result  import UnifiedSearchResult
from .models.search_response import SearchResponse

__all__ = ["SearchManager", "get_search_manager", "reset_search_manager"]

_LOG  = logging.getLogger("iios.knowledge.search.manager")
_lock = threading.Lock()
_mgr: Optional["SearchManager"] = None


class SearchManager:
    """
    Unified service façade for the Knowledge Indexing & Search Engine.

    Orchestrates IndexManager, IndexBuilder, SearchEngine, QueryBuilder,
    SearchFactory, and SearchStats.

    Usage::

        sm = get_search_manager()

        # Index items
        sm.index_knowledge_record(record)
        sm.index_graph_node(node)

        # Search
        response = sm.search("NIFTY 50 trend")
        response = sm.search_by_tags(["equity", "index"])
        response = sm.hybrid_search("NIFTY", tags=["equity"], filters={"domain": "equity"})

        print(sm.statistics())
    """

    def __init__(
        self,
        index_manager:  Optional[IndexManager]  = None,
        index_builder:  Optional[IndexBuilder]  = None,
        search_engine:  Optional[SearchEngine]  = None,
        query_builder:  Optional[QueryBuilder]  = None,
        search_factory: Optional[SearchFactory] = None,
        stats:          Optional[SearchStats]   = None,
    ) -> None:
        self._lock    = threading.RLock()
        self._idx     = index_manager  or get_index_manager()
        self._builder = index_builder  or get_index_builder()
        self._engine  = search_engine  or get_search_engine()
        self._qb      = query_builder  or get_query_builder()
        self._factory = search_factory or get_search_factory()
        self._stats   = stats          or get_search_stats()

    # ── Indexing operations ───────────────────────────────────────────────────

    def index_knowledge_record(self, record: Any) -> bool:
        """Index a single KnowledgeRecord. Returns True on success."""
        ok = self._builder.index_knowledge_record(record)
        if ok:
            self._engine.invalidate_cache()
        return ok

    def index_graph_node(self, node: Any) -> bool:
        """Index a single GraphNode. Returns True on success."""
        ok = self._builder.index_graph_node(node)
        if ok:
            self._engine.invalidate_cache()
        return ok

    def deindex_item(self, item_id: str) -> bool:
        """Remove an item from all indexes."""
        ok = self._idx.deindex_item(item_id)
        if ok:
            self._engine.invalidate_cache()
        return ok

    def rebuild_indexes(
        self,
        knowledge_repository: Optional[Any] = None,
        graph_repository:     Optional[Any] = None,
    ) -> dict[str, Any]:
        """Full rebuild from both repositories. Clears and re-populates all indexes."""
        self._engine.invalidate_cache()
        return self._builder.full_rebuild(
            knowledge_repository=knowledge_repository,
            graph_repository=graph_repository,
        )

    # ── Search operations ─────────────────────────────────────────────────────

    def search(
        self,
        text:             str,
        search_type:      SearchType       = SearchType.HYBRID,
        page:             int              = 1,
        page_size:        int              = DEFAULT_SEARCH_PAGE_SIZE,
        min_confidence:   float            = 0.0,
        min_score:        float            = 0.0,
        ranking_strategy: RankingStrategy  = RankingStrategy.HYBRID,
        actor:            str              = SYSTEM_SEARCH_ACTOR,
        **kwargs:         Any,
    ) -> SearchResponse:
        q = UnifiedSearchQuery(
            search_type      = search_type,
            text             = text,
            page             = page,
            page_size        = page_size,
            min_confidence   = min_confidence,
            min_score        = min_score,
            ranking_strategy = ranking_strategy,
            actor            = actor,
            **kwargs,
        )
        return self._engine.search(q)

    def search_by_id(self, item_id: str) -> Optional[UnifiedSearchResult]:
        q = self._qb.by_id(item_id)
        response = self._engine.search(q)
        return response.results[0] if response.results else None

    def search_by_tags(
        self,
        tags:      list[str],
        match_all: bool = False,
        **kwargs:  Any,
    ) -> SearchResponse:
        q = self._qb.tag(tags, match_all=match_all, **kwargs)
        return self._engine.search(q)

    def search_by_metadata(
        self,
        filters:  dict[str, Any],
        **kwargs: Any,
    ) -> SearchResponse:
        q = self._qb.metadata(filters, **kwargs)
        return self._engine.search(q)

    def search_by_type(
        self,
        knowledge_type: str,
        **kwargs:       Any,
    ) -> SearchResponse:
        q = self._qb.ontology([f"knowledge_type:{knowledge_type.lower()}"], **kwargs)
        return self._engine.search(q)

    def search_by_node_type(
        self,
        node_type: str,
        **kwargs:  Any,
    ) -> SearchResponse:
        q = UnifiedSearchQuery(
            search_type  = SearchType.ONTOLOGY,
            node_types   = [f"node_type:{node_type.lower()}"],
            **kwargs,
        )
        return self._engine.search(q)

    def graph_traversal_search(
        self,
        start_node_id: str,
        depth:         int = 3,
        **kwargs:      Any,
    ) -> SearchResponse:
        q = self._qb.graph_traversal(start_node_id, depth=depth, **kwargs)
        return self._engine.search(q)

    def hybrid_search(
        self,
        text:    str                     = "",
        tags:    Optional[list[str]]     = None,
        filters: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> SearchResponse:
        q = self._qb.hybrid(text=text, tags=tags, filters=filters, **kwargs)
        return self._engine.search(q)

    def fuzzy_search(
        self,
        text:      str,
        threshold: float = 0.75,
        **kwargs:  Any,
    ) -> SearchResponse:
        q = self._factory.fuzzy_search(text, threshold=threshold, **kwargs)
        return self._engine.search(q)

    def relationship_search(
        self,
        item_id:  str,
        **kwargs: Any,
    ) -> SearchResponse:
        q = self._qb.relationship(item_id, **kwargs)
        return self._engine.search(q)

    # ── Advanced search ───────────────────────────────────────────────────────

    def search_with_query(self, query: UnifiedSearchQuery) -> SearchResponse:
        """Execute a pre-built UnifiedSearchQuery directly."""
        return self._engine.search(query)

    # ── Statistics & health ───────────────────────────────────────────────────

    def item_count(self) -> int:
        return self._idx.item_count()

    def statistics(self) -> dict[str, Any]:
        return self._engine.statistics()

    def optimize_indexes(self) -> dict[str, Any]:
        opt = get_index_optimizer()
        return opt.optimize()

    def status(self) -> dict[str, Any]:
        idx_stats = self._idx.statistics()
        return {
            "status":      "running",
            "item_count":  idx_stats.get("item_count", 0),
            "items_by_type": idx_stats.get("items_by_type", {}),
        }


def get_search_manager() -> SearchManager:
    global _mgr
    with _lock:
        if _mgr is None:
            _mgr = SearchManager()
        return _mgr


def reset_search_manager() -> None:
    global _mgr
    with _lock:
        _mgr = None
