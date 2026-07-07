"""
iios/knowledge/search/query_executor.py
==========================================
Routes a UnifiedSearchQuery to the correct index search strategy and
returns a list of UnifiedSearchResult objects (unranked, unfiltered).
"""
from __future__ import annotations

import logging
import threading
from typing import Any, Optional

from .search_constants import SearchType, SearchIndexType, ItemType
from .search_exceptions import SearchExecutionError
from .index_manager import IndexManager, get_index_manager
from .models.unified_query  import UnifiedSearchQuery
from .models.unified_result import UnifiedSearchResult

__all__ = ["QueryExecutor", "get_query_executor", "reset_query_executor"]

_LOG   = logging.getLogger("iios.knowledge.search.executor")
_lock  = threading.Lock()
_exec: Optional["QueryExecutor"] = None


class QueryExecutor:
    """
    Translates a UnifiedSearchQuery into a list of scored UnifiedSearchResult
    objects by delegating to the IndexManager.

    Usage::

        executor = get_query_executor()
        results  = executor.execute(query)
    """

    def __init__(self, index_manager: Optional[IndexManager] = None) -> None:
        self._idx   = index_manager or get_index_manager()
        self._lock  = threading.RLock()

    # ── Main dispatch ─────────────────────────────────────────────────────────

    def execute(self, query: UnifiedSearchQuery) -> tuple[list[UnifiedSearchResult], list[str]]:
        """
        Execute a query and return (results, indexes_used).

        Results are scored but NOT yet ranked by RankingStrategy — that
        step is performed by SearchEngine._rank_results().
        """
        stype = query.search_type
        try:
            if stype == SearchType.ID_LOOKUP:
                return self._id_lookup(query)
            if stype == SearchType.EXACT_MATCH:
                return self._exact_match(query)
            if stype == SearchType.KEYWORD:
                return self._keyword(query)
            if stype == SearchType.TAG:
                return self._tag(query)
            if stype == SearchType.METADATA:
                return self._metadata(query)
            if stype == SearchType.ONTOLOGY:
                return self._ontology(query)
            if stype == SearchType.RELATIONSHIP:
                return self._relationship(query)
            if stype == SearchType.GRAPH_TRAVERSAL:
                return self._graph_traversal(query)
            if stype == SearchType.HYBRID:
                return self._hybrid(query)
            if stype == SearchType.SEMANTIC:
                return self._semantic(query)
            # Unknown type → keyword fallback
            return self._keyword(query)
        except Exception as exc:
            raise SearchExecutionError(
                f"Execution failed for search_type={stype}: {exc}",
                code="QE-001",
            ) from exc

    # ── Search strategies ─────────────────────────────────────────────────────

    def _id_lookup(
        self, query: UnifiedSearchQuery,
    ) -> tuple[list[UnifiedSearchResult], list[str]]:
        item_id = query.text.strip()
        r = self._idx.search_by_id(item_id)
        if r is None:
            return [], [SearchIndexType.PRIMARY.value]
        result = self._clone_with_score(r, 1.0)
        if not self._passes_filter(result, query):
            return [], [SearchIndexType.PRIMARY.value]
        return [result], [SearchIndexType.PRIMARY.value]

    def _exact_match(
        self, query: UnifiedSearchQuery,
    ) -> tuple[list[UnifiedSearchResult], list[str]]:
        text = query.text.strip().lower()
        results: list[UnifiedSearchResult] = []
        for r in self._idx.all_items():
            if r.title.lower() == text:
                if self._passes_filter(self._clone_with_score(r, 1.0), query):
                    results.append(self._clone_with_score(r, 1.0))
        return results, [SearchIndexType.KEYWORD.value]

    def _keyword(
        self, query: UnifiedSearchQuery,
    ) -> tuple[list[UnifiedSearchResult], list[str]]:
        from .query_parser import get_query_parser
        pq    = get_query_parser().parse(query.text)
        tokens = pq.effective_tokens

        if not tokens:
            # No tokens → return all items that pass filters
            return self._all_filtered(query), [SearchIndexType.KEYWORD.value]

        op     = "AND" if pq.operator.value == "and" else "OR"
        scores = self._idx.search_keyword(
            tokens, operator=op, fuzzy=query.fuzzy, fuzzy_threshold=query.fuzzy_threshold,
        )
        results: list[UnifiedSearchResult] = []
        for item_id, score in scores.items():
            r = self._idx.get_item(item_id)
            if r is None:
                continue
            result = self._clone_with_score(r, score)
            if not self._passes_filter(result, query):
                continue
            # Add tag boost
            if query.tags:
                tag_overlap = len(set(result.tags) & {t.lower() for t in query.tags})
                if tag_overlap:
                    result = self._clone_with_score(result, result.score + 0.5 * tag_overlap)
            results.append(result)
        return results, [SearchIndexType.KEYWORD.value]

    def _tag(
        self, query: UnifiedSearchQuery,
    ) -> tuple[list[UnifiedSearchResult], list[str]]:
        ids = self._idx.search_by_tags(query.tags, match_all=query.tags_match_all)
        results: list[UnifiedSearchResult] = []
        for item_id in ids:
            r = self._idx.get_item(item_id)
            if r is None:
                continue
            overlap = len(set(r.tags) & {t.lower() for t in query.tags})
            score   = overlap / max(len(query.tags), 1)
            result  = self._clone_with_score(r, score)
            if self._passes_filter(result, query):
                results.append(result)
        return results, [SearchIndexType.TAG.value]

    def _metadata(
        self, query: UnifiedSearchQuery,
    ) -> tuple[list[UnifiedSearchResult], list[str]]:
        ids = self._idx.search_by_metadata(query.filters)
        results: list[UnifiedSearchResult] = []
        for item_id in ids:
            r = self._idx.get_item(item_id)
            if r is None:
                continue
            match_count = sum(
                1 for k, v in query.filters.items()
                if str(r.metadata.get(k, "")).lower() == str(v).lower()
            )
            score  = match_count / max(len(query.filters), 1)
            result = self._clone_with_score(r, score)
            if self._passes_filter(result, query):
                results.append(result)
        return results, [SearchIndexType.METADATA.value]

    def _ontology(
        self, query: UnifiedSearchQuery,
    ) -> tuple[list[UnifiedSearchResult], list[str]]:
        # Build ontology key list from knowledge_types + node_types + text
        keys: list[str] = []
        for kt in query.knowledge_types:
            keys.append(kt.lower() if ":" in kt else f"knowledge_type:{kt.lower()}")
        for nt in query.node_types:
            keys.append(nt.lower() if ":" in nt else f"node_type:{nt.lower()}")
        if not keys and query.text:
            keys.append(query.text.lower() if ":" in query.text else f"knowledge_type:{query.text.lower()}")

        ids = self._idx.search_by_ontology(keys)
        results: list[UnifiedSearchResult] = []
        for item_id in ids:
            r = self._idx.get_item(item_id)
            if r is None:
                continue
            result = self._clone_with_score(r, 1.0)
            if self._passes_filter(result, query):
                results.append(result)
        return results, [SearchIndexType.ONTOLOGY.value]

    def _relationship(
        self, query: UnifiedSearchQuery,
    ) -> tuple[list[UnifiedSearchResult], list[str]]:
        """Find knowledge items related to a given item (via graph edges)."""
        item_id = query.text.strip()
        related_ids: list[str] = []
        try:
            from ..graph.storage.graph_repository import get_graph_repository
            repo = get_graph_repository()
            node_result = self._idx.search_by_id(item_id)
            if node_result:
                edges_from = repo.get_edges_from(item_id)
                edges_to   = repo.get_edges_to(item_id)
                for e in edges_from:
                    related_ids.append(e.target_id)
                for e in edges_to:
                    related_ids.append(e.source_id)
        except Exception:
            pass

        results: list[UnifiedSearchResult] = []
        for rid in related_ids:
            r = self._idx.get_item(rid)
            if r and self._passes_filter(self._clone_with_score(r, 0.8), query):
                results.append(self._clone_with_score(r, 0.8))
        return results, [SearchIndexType.GRAPH.value]

    def _graph_traversal(
        self, query: UnifiedSearchQuery,
    ) -> tuple[list[UnifiedSearchResult], list[str]]:
        """BFS traversal from start_node_id, returning all reachable graph nodes."""
        if not query.start_node_id:
            return [], [SearchIndexType.GRAPH.value]

        node_ids: list[str] = []
        try:
            from ..graph.graph_engine import get_graph_engine
            engine   = get_graph_engine()
            node_ids = engine.bfs(query.start_node_id, max_depth=query.traversal_depth)
        except Exception:
            pass

        results: list[UnifiedSearchResult] = []
        for nid in node_ids:
            r = self._idx.get_item(nid)
            if r is None:
                continue
            # Score based on distance from start (closer = higher score)
            hop = node_ids.index(nid)
            score  = max(0.1, 1.0 - hop * 0.1)
            result = self._clone_with_score(r, score)
            if self._passes_filter(result, query):
                results.append(result)
        return results, [SearchIndexType.GRAPH.value]

    def _hybrid(
        self, query: UnifiedSearchQuery,
    ) -> tuple[list[UnifiedSearchResult], list[str]]:
        """Merge keyword + tag + metadata results."""
        seen: dict[str, UnifiedSearchResult] = {}
        indexes: list[str] = []

        # Keyword search
        if query.text.strip():
            kq = self._clone_query(query, search_type=SearchType.KEYWORD)
            kw_results, ki = self._keyword(kq)
            indexes.extend(ki)
            for r in kw_results:
                seen[r.item_id] = r

        # Tag search
        if query.tags:
            tq = self._clone_query(query, search_type=SearchType.TAG)
            tag_results, ti = self._tag(tq)
            indexes.extend(ti)
            for r in tag_results:
                if r.item_id in seen:
                    # Boost score for items matching both keyword and tags
                    existing = seen[r.item_id]
                    seen[r.item_id] = self._clone_with_score(
                        existing, existing.score + r.score * 0.5,
                    )
                else:
                    seen[r.item_id] = self._clone_with_score(r, r.score * 0.6)

        # Metadata search
        if query.filters:
            mq = self._clone_query(query, search_type=SearchType.METADATA)
            meta_results, mi = self._metadata(mq)
            indexes.extend(mi)
            for r in meta_results:
                if r.item_id in seen:
                    existing = seen[r.item_id]
                    seen[r.item_id] = self._clone_with_score(
                        existing, existing.score + r.score * 0.3,
                    )
                else:
                    seen[r.item_id] = self._clone_with_score(r, r.score * 0.4)

        return list(seen.values()), list(dict.fromkeys(indexes))

    def _semantic(
        self, query: UnifiedSearchQuery,
    ) -> tuple[list[UnifiedSearchResult], list[str]]:
        """
        Semantic search interface — falls back to hybrid search.
        Production extension point for embedding-based retrieval.
        """
        q = self._clone_query(query, search_type=SearchType.HYBRID)
        return self._hybrid(q)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _all_filtered(
        self, query: UnifiedSearchQuery,
    ) -> list[UnifiedSearchResult]:
        results = []
        for r in self._idx.all_items():
            result = self._clone_with_score(r, 1.0)
            if self._passes_filter(result, query):
                results.append(result)
        return results

    def _passes_filter(
        self, result: UnifiedSearchResult, query: UnifiedSearchQuery,
    ) -> bool:
        """Return True if the result satisfies all query filter conditions."""
        # Deleted / archived
        if not query.include_deleted and result.metadata.get("status", "") in ("deleted",):
            return False
        if not query.include_archived and result.metadata.get("status", "") == "archived":
            return False
        # Confidence
        if result.confidence < query.min_confidence:
            return False
        # Score gate (applied later but catch obvious zeros)
        if result.score < query.min_score:
            return False
        # Item type filter
        if query.item_types and result.item_type not in query.item_types:
            return False
        return True

    @staticmethod
    def _clone_with_score(
        r: UnifiedSearchResult, score: float,
    ) -> UnifiedSearchResult:
        from dataclasses import replace
        return replace(r, score=score)

    @staticmethod
    def _clone_query(
        q: UnifiedSearchQuery, **changes: Any,
    ) -> UnifiedSearchQuery:
        from dataclasses import replace
        return replace(q, **changes)


def get_query_executor() -> QueryExecutor:
    global _exec
    with _lock:
        if _exec is None:
            _exec = QueryExecutor()
        return _exec


def reset_query_executor() -> None:
    global _exec
    with _lock:
        _exec = None
