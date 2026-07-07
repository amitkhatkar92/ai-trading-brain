"""
iios/knowledge/models/knowledge_query.py
=========================================
Query and filter objects used by the repository and search layers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from ..knowledge_constants import (
    KnowledgeDomain,
    KnowledgeStatus,
    KnowledgeType,
    QueryOperator,
    SearchMode,
    SortOrder,
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
)

__all__ = [
    "FilterCondition",
    "KnowledgeFilter",
    "KnowledgeQuery",
    "SearchQuery",
    "PageRequest",
    "PageResult",
]


@dataclass
class FilterCondition:
    """A single field-level filter expression."""
    field:    str
    operator: QueryOperator
    value:    Any

    def to_dict(self) -> dict[str, Any]:
        return {
            "field":    self.field,
            "operator": self.operator.value,
            "value":    self.value,
        }


@dataclass
class KnowledgeFilter:
    """Structured filter for knowledge queries."""
    knowledge_types:    list[KnowledgeType]    = field(default_factory=list)
    statuses:           list[KnowledgeStatus]  = field(default_factory=list)
    domains:            list[KnowledgeDomain]  = field(default_factory=list)
    owner_ids:          list[str]              = field(default_factory=list)
    tags:               list[str]              = field(default_factory=list)
    created_after:      Optional[float]        = None
    created_before:     Optional[float]        = None
    updated_after:      Optional[float]        = None
    min_confidence:     Optional[float]        = None
    max_confidence:     Optional[float]        = None
    conditions:         list[FilterCondition]  = field(default_factory=list)
    include_deleted:    bool                   = False
    include_expired:    bool                   = False

    def add_condition(self, field: str, op: QueryOperator, value: Any) -> None:
        self.conditions.append(FilterCondition(field, op, value))


@dataclass
class PageRequest:
    """Pagination parameters."""
    page:      int = 1
    page_size: int = DEFAULT_PAGE_SIZE
    sort_by:   str = "created_at"
    sort_order: SortOrder = SortOrder.DESC

    def __post_init__(self) -> None:
        self.page = max(1, self.page)
        self.page_size = max(1, min(self.page_size, MAX_PAGE_SIZE))

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


@dataclass
class KnowledgeQuery:
    """Complete query specification (filter + pagination)."""
    filter:      KnowledgeFilter = field(default_factory=KnowledgeFilter)
    pagination:  PageRequest     = field(default_factory=PageRequest)


@dataclass
class SearchQuery:
    """Full-text or hybrid search query."""
    text:        str              = ""
    mode:        SearchMode       = SearchMode.KEYWORD
    filter:      KnowledgeFilter  = field(default_factory=KnowledgeFilter)
    pagination:  PageRequest      = field(default_factory=PageRequest)
    boost_tags:  list[str]        = field(default_factory=list)
    min_score:   float            = 0.0


@dataclass
class PageResult:
    """Paginated result set."""
    items:       list[Any]   = field(default_factory=list)
    total:       int         = 0
    page:        int         = 1
    page_size:   int         = DEFAULT_PAGE_SIZE
    has_next:    bool        = False
    has_prev:    bool        = False

    @classmethod
    def build(cls, items: list[Any], total: int, req: PageRequest) -> "PageResult":
        return cls(
            items     = items,
            total     = total,
            page      = req.page,
            page_size = req.page_size,
            has_next  = (req.page * req.page_size) < total,
            has_prev  = req.page > 1,
        )
