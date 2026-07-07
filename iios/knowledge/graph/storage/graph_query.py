"""
iios/knowledge/graph/storage/graph_query.py
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from ..graph_constants import (
    GraphNodeType,
    GraphEdgeType,
    NodeStatus,
    EdgeStatus,
    GraphSortOrder,
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
)

__all__ = [
    "NodeFilter",
    "EdgeFilter",
    "PageRequest",
    "NodeQuery",
    "EdgeQuery",
    "GraphPageResult",
]


@dataclass
class NodeFilter:
    node_types:      list[GraphNodeType]  = field(default_factory=list)
    statuses:        list[NodeStatus]     = field(default_factory=list)
    labels:          list[str]            = field(default_factory=list)
    label_contains:  str                  = ""
    knowledge_ids:   list[str]            = field(default_factory=list)
    tags:            list[str]            = field(default_factory=list)
    min_weight:      Optional[float]      = None
    max_weight:      Optional[float]      = None
    min_confidence:  Optional[float]      = None
    properties:      dict[str, Any]       = field(default_factory=dict)
    include_deleted: bool                 = False


@dataclass
class EdgeFilter:
    edge_types:      list[GraphEdgeType]  = field(default_factory=list)
    statuses:        list[EdgeStatus]     = field(default_factory=list)
    source_ids:      list[str]            = field(default_factory=list)
    target_ids:      list[str]            = field(default_factory=list)
    min_weight:      Optional[float]      = None
    max_weight:      Optional[float]      = None
    include_deleted: bool                 = False
    include_expired: bool                 = False


@dataclass
class PageRequest:
    page:       int            = 1
    page_size:  int            = DEFAULT_PAGE_SIZE
    sort_by:    str            = "metadata.created_at"
    sort_order: GraphSortOrder = GraphSortOrder.DESC

    def __post_init__(self) -> None:
        self.page      = max(1, self.page)
        self.page_size = max(1, min(self.page_size, MAX_PAGE_SIZE))

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


@dataclass
class NodeQuery:
    filter:     NodeFilter  = field(default_factory=NodeFilter)
    pagination: PageRequest = field(default_factory=PageRequest)


@dataclass
class EdgeQuery:
    filter:     EdgeFilter  = field(default_factory=EdgeFilter)
    pagination: PageRequest = field(default_factory=PageRequest)


@dataclass
class GraphPageResult:
    items:     list[Any] = field(default_factory=list)
    total:     int       = 0
    page:      int       = 1
    page_size: int       = DEFAULT_PAGE_SIZE
    has_next:  bool      = False
    has_prev:  bool      = False

    @classmethod
    def build(cls, items: list[Any], total: int, req: PageRequest) -> GraphPageResult:
        return cls(
            items     = items,
            total     = total,
            page      = req.page,
            page_size = req.page_size,
            has_next  = (req.page * req.page_size) < total,
            has_prev  = req.page > 1,
        )
