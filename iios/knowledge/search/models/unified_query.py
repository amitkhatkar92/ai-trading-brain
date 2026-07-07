"""
iios/knowledge/search/models/unified_query.py
"""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from ..search_constants import (
    SearchType, RankingStrategy, SearchSortOrder, SearchQueryOp, ItemType,
    DEFAULT_SEARCH_PAGE_SIZE, DEFAULT_MAX_RESULTS, DEFAULT_FUZZY_THRESHOLD,
    SYSTEM_SEARCH_ACTOR,
)

__all__ = ["UnifiedSearchQuery"]


@dataclass
class UnifiedSearchQuery:
    """Unified, engine-agnostic search query.

    Covers every search type: keyword, tag, metadata, ontology, ID lookup,
    graph traversal, and hybrid combinations.

    Usage::

        q = UnifiedSearchQuery(
            text="NIFTY 50 trend analysis",
            search_type=SearchType.HYBRID,
            tags=["equity", "index"],
            min_confidence=0.8,
            page_size=20,
        )
    """

    # ── Identity ──────────────────────────────────────────────────────────────
    query_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # ── Search intent ─────────────────────────────────────────────────────────
    search_type:    SearchType      = SearchType.KEYWORD
    text:           str             = ""

    # ── Filters ───────────────────────────────────────────────────────────────
    filters:        dict[str, Any]  = field(default_factory=dict)
    tags:           list[str]       = field(default_factory=list)
    tags_match_all: bool            = False     # True → AND, False → OR
    item_types:     list[str]       = field(default_factory=list)   # ItemType values
    knowledge_types: list[str]      = field(default_factory=list)
    node_types:     list[str]       = field(default_factory=list)
    min_confidence: float           = 0.0
    min_score:      float           = 0.0
    include_archived: bool          = False
    include_deleted:  bool          = False

    # ── Graph traversal ───────────────────────────────────────────────────────
    start_node_id:   Optional[str] = None
    traversal_depth: int           = 3

    # ── Multi-token operator ──────────────────────────────────────────────────
    operator: SearchQueryOp = SearchQueryOp.OR

    # ── Fuzzy matching ────────────────────────────────────────────────────────
    fuzzy:           bool  = False
    fuzzy_threshold: float = DEFAULT_FUZZY_THRESHOLD

    # ── Ranking & sorting ─────────────────────────────────────────────────────
    ranking_strategy: RankingStrategy = RankingStrategy.HYBRID
    sort_by:          str             = "score"
    sort_order:       SearchSortOrder = SearchSortOrder.DESC
    boost_fields:     dict[str, float] = field(default_factory=dict)

    # ── Pagination ────────────────────────────────────────────────────────────
    page:        int = 1
    page_size:   int = DEFAULT_SEARCH_PAGE_SIZE
    max_results: int = DEFAULT_MAX_RESULTS

    # ── Context ───────────────────────────────────────────────────────────────
    actor:      str   = SYSTEM_SEARCH_ACTOR
    created_at: float = field(default_factory=time.time)

    # ── Metadata ──────────────────────────────────────────────────────────────
    explain:    bool  = False   # include scoring explanation in results

    # ── Internal ─────────────────────────────────────────────────────────────
    _normalized_text: Optional[str] = field(default=None, repr=False, compare=False)

    @property
    def offset(self) -> int:
        return max(0, (self.page - 1)) * self.page_size

    @property
    def normalized_text(self) -> str:
        if self._normalized_text is None:
            self._normalized_text = self.text.strip().lower()
        return self._normalized_text

    def cache_key(self) -> str:
        """Deterministic cache key (MD5 of stable fields)."""
        payload = {
            "type":            self.search_type.value,
            "text":            self.normalized_text,
            "tags":            sorted(self.tags),
            "tags_match_all":  self.tags_match_all,
            "filters":         sorted((str(k), str(v)) for k, v in self.filters.items()),
            "item_types":      sorted(self.item_types),
            "knowledge_types": sorted(self.knowledge_types),
            "node_types":      sorted(self.node_types),
            "min_confidence":  self.min_confidence,
            "min_score":       self.min_score,
            "include_archived": self.include_archived,
            "include_deleted": self.include_deleted,
            "start_node_id":   self.start_node_id or "",
            "traversal_depth": self.traversal_depth,
            "operator":        self.operator.value,
            "fuzzy":           self.fuzzy,
            "fuzzy_threshold": self.fuzzy_threshold,
            "ranking":         self.ranking_strategy.value,
            "sort_by":         self.sort_by,
            "sort_order":      self.sort_order.value,
            "page":            self.page,
            "page_size":       self.page_size,
        }
        digest = hashlib.md5(
            json.dumps(payload, sort_keys=True).encode("utf-8"), usedforsecurity=False,
        ).hexdigest()
        return f"sq:{digest}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "query_id":        self.query_id,
            "search_type":     self.search_type.value,
            "text":            self.text,
            "filters":         self.filters,
            "tags":            self.tags,
            "tags_match_all":  self.tags_match_all,
            "item_types":      self.item_types,
            "knowledge_types": self.knowledge_types,
            "node_types":      self.node_types,
            "min_confidence":  self.min_confidence,
            "min_score":       self.min_score,
            "include_archived": self.include_archived,
            "include_deleted": self.include_deleted,
            "start_node_id":   self.start_node_id,
            "traversal_depth": self.traversal_depth,
            "operator":        self.operator.value,
            "fuzzy":           self.fuzzy,
            "fuzzy_threshold": self.fuzzy_threshold,
            "ranking_strategy": self.ranking_strategy.value,
            "sort_by":         self.sort_by,
            "sort_order":      self.sort_order.value,
            "boost_fields":    self.boost_fields,
            "page":            self.page,
            "page_size":       self.page_size,
            "max_results":     self.max_results,
            "actor":           self.actor,
            "created_at":      self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UnifiedSearchQuery":
        return cls(
            query_id         = data.get("query_id", str(uuid.uuid4())),
            search_type      = SearchType(data.get("search_type", SearchType.KEYWORD)),
            text             = data.get("text", ""),
            filters          = data.get("filters", {}),
            tags             = data.get("tags", []),
            tags_match_all   = data.get("tags_match_all", False),
            item_types       = data.get("item_types", []),
            knowledge_types  = data.get("knowledge_types", []),
            node_types       = data.get("node_types", []),
            min_confidence   = float(data.get("min_confidence", 0.0)),
            min_score        = float(data.get("min_score", 0.0)),
            include_archived = data.get("include_archived", False),
            include_deleted  = data.get("include_deleted", False),
            start_node_id    = data.get("start_node_id"),
            traversal_depth  = int(data.get("traversal_depth", 3)),
            operator         = SearchQueryOp(data.get("operator", SearchQueryOp.OR)),
            fuzzy            = data.get("fuzzy", False),
            fuzzy_threshold  = float(data.get("fuzzy_threshold", DEFAULT_FUZZY_THRESHOLD)),
            ranking_strategy = RankingStrategy(data.get("ranking_strategy", RankingStrategy.HYBRID)),
            sort_by          = data.get("sort_by", "score"),
            sort_order       = SearchSortOrder(data.get("sort_order", SearchSortOrder.DESC)),
            boost_fields     = data.get("boost_fields", {}),
            page             = int(data.get("page", 1)),
            page_size        = int(data.get("page_size", DEFAULT_SEARCH_PAGE_SIZE)),
            max_results      = int(data.get("max_results", DEFAULT_MAX_RESULTS)),
            actor            = data.get("actor", SYSTEM_SEARCH_ACTOR),
        )
