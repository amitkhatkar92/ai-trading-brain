"""
iios/knowledge/search/models/search_response.py
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional, TYPE_CHECKING

from ..search_constants import SearchType

if TYPE_CHECKING:
    from .unified_query  import UnifiedSearchQuery
    from .unified_result import UnifiedSearchResult

__all__ = ["SearchResponse"]


@dataclass
class SearchResponse:
    """Paginated search response returned by SearchEngine and SearchManager."""

    response_id:      str
    query_id:         str
    results:          list["UnifiedSearchResult"]
    total:            int
    page:             int
    page_size:        int
    has_next:         bool
    has_prev:         bool
    search_type:      SearchType
    execution_time_ms: float              = 0.0
    cache_hit:        bool                = False
    indexes_used:     list[str]          = field(default_factory=list)
    warnings:         list[str]          = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.results)

    @property
    def total_pages(self) -> int:
        if self.page_size <= 0:
            return 1
        return max(1, -(-self.total // self.page_size))  # ceiling division

    def to_dict(self) -> dict[str, Any]:
        return {
            "response_id":       self.response_id,
            "query_id":          self.query_id,
            "results":           [r.to_dict() for r in self.results],
            "total":             self.total,
            "count":             self.count,
            "page":              self.page,
            "page_size":         self.page_size,
            "total_pages":       self.total_pages,
            "has_next":          self.has_next,
            "has_prev":          self.has_prev,
            "search_type":       self.search_type.value,
            "execution_time_ms": round(self.execution_time_ms, 3),
            "cache_hit":         self.cache_hit,
            "indexes_used":      self.indexes_used,
            "warnings":          self.warnings,
        }

    @classmethod
    def build(
        cls,
        query:            "UnifiedSearchQuery",
        ranked_results:   "list[UnifiedSearchResult]",
        total:            int,
        execution_time_ms: float,
        cache_hit:        bool              = False,
        indexes_used:     list[str]         = (),  # type: ignore[assignment]
        warnings:         list[str]         = (),  # type: ignore[assignment]
    ) -> "SearchResponse":
        """Paginate and assemble a SearchResponse from ranked results."""
        offset   = query.offset
        page_end = offset + query.page_size
        page_results = ranked_results[offset:page_end]

        # Assign rank to each result
        for i, r in enumerate(page_results, start=offset + 1):
            r.rank = i

        return cls(
            response_id       = str(uuid.uuid4()),
            query_id          = query.query_id,
            results           = page_results,
            total             = total,
            page              = query.page,
            page_size         = query.page_size,
            has_next          = page_end < total,
            has_prev          = query.page > 1,
            search_type       = query.search_type,
            execution_time_ms = execution_time_ms,
            cache_hit         = cache_hit,
            indexes_used      = list(indexes_used),
            warnings          = list(warnings),
        )

    @classmethod
    def empty(
        cls,
        query:            "UnifiedSearchQuery",
        execution_time_ms: float = 0.0,
    ) -> "SearchResponse":
        return cls(
            response_id       = str(uuid.uuid4()),
            query_id          = query.query_id,
            results           = [],
            total             = 0,
            page              = query.page,
            page_size         = query.page_size,
            has_next          = False,
            has_prev          = query.page > 1,
            search_type       = query.search_type,
            execution_time_ms = execution_time_ms,
        )
