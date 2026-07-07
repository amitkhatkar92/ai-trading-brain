"""
iios/knowledge/graph/storage/graph_repository.py
==================================================
Central CRUD + query interface:  storage + cache + index in one place.
"""
from __future__ import annotations

import logging
import threading
from typing import Optional

from ..graph_constants import GraphSortOrder
from ..graph_exceptions import (
    GraphNodeNotFoundError,
    GraphEdgeNotFoundError,
    GraphNodeAlreadyExistsError,
    GraphEdgeAlreadyExistsError,
)
from ..models.graph_node import GraphNode
from ..models.graph_edge import GraphEdge
from .graph_storage    import GraphStorage,   get_graph_storage
from .graph_cache      import GraphCache,     get_graph_cache
from .graph_index      import GraphIndex,     get_graph_index
from .graph_query      import (
    NodeFilter, EdgeFilter, NodeQuery, EdgeQuery, GraphPageResult, PageRequest,
)

__all__ = ["GraphRepository", "get_graph_repository", "reset_graph_repository"]

_LOG  = logging.getLogger("iios.knowledge.graph.repository")
_lock = threading.Lock()
_repo: Optional["GraphRepository"] = None


class GraphRepository:
    """Unified CRUD + query interface for graph nodes and edges."""

    def __init__(
        self,
        storage: Optional[GraphStorage] = None,
        cache:   Optional[GraphCache]   = None,
        index:   Optional[GraphIndex]   = None,
    ) -> None:
        self._lock    = threading.RLock()
        self._storage = storage or get_graph_storage()
        self._cache   = cache   or get_graph_cache()
        self._index   = index   or get_graph_index()

    # ── Node CRUD ─────────────────────────────────────────────────────────────

    def add_node(self, node: GraphNode) -> GraphNode:
        if self._storage.node_exists(node.node_id):
            raise GraphNodeAlreadyExistsError(f"Node '{node.node_id}' already exists", code="GR-001")
        self._storage.put_node(node, allow_overwrite=False)
        self._index.index_node(node)
        self._cache.set_node(node)
        return node

    def update_node(self, node: GraphNode) -> GraphNode:
        if not self._storage.node_exists(node.node_id):
            raise GraphNodeNotFoundError(f"Node '{node.node_id}' not found", code="GR-002")
        self._storage.put_node(node, allow_overwrite=True)
        self._index.deindex_node(node.node_id)
        self._index.index_node(node)
        self._cache.set_node(node)
        return node

    def upsert_node(self, node: GraphNode) -> GraphNode:
        if self._storage.node_exists(node.node_id):
            return self.update_node(node)
        return self.add_node(node)

    def get_node(self, node_id: str) -> GraphNode:
        cached = self._cache.get_node(node_id)
        if cached is not None and not cached.is_deleted:
            return cached
        n = self._storage.get_node(node_id)
        if n.is_deleted:
            raise GraphNodeNotFoundError(f"Node '{node_id}' is soft-deleted", code="GR-003")
        self._cache.set_node(n)
        return n

    def get_node_optional(self, node_id: str) -> Optional[GraphNode]:
        try:
            return self.get_node(node_id)
        except GraphNodeNotFoundError:
            return None

    def delete_node(self, node_id: str, hard: bool = False) -> bool:
        ok = self._storage.delete_node(node_id, hard=hard)
        if ok:
            self._cache.delete_node(node_id)
            if hard:
                self._index.deindex_node(node_id)
        return ok

    def node_exists(self, node_id: str) -> bool:
        cached = self._cache.get_node(node_id)
        if cached is not None:
            return not cached.is_deleted
        return self._storage.node_exists(node_id)

    def all_nodes(self, include_deleted: bool = False) -> list[GraphNode]:
        return self._storage.all_nodes(include_deleted)

    def all_node_ids(self, include_deleted: bool = False) -> list[str]:
        return self._storage.all_node_ids(include_deleted)

    def node_count(self, include_deleted: bool = False) -> int:
        return self._storage.node_count(include_deleted)

    # ── Edge CRUD ─────────────────────────────────────────────────────────────

    def add_edge(self, edge: GraphEdge) -> GraphEdge:
        if not self._storage.node_exists(edge.source_id):
            raise GraphNodeNotFoundError(f"Source node '{edge.source_id}' not found", code="GR-004")
        if not self._storage.node_exists(edge.target_id):
            raise GraphNodeNotFoundError(f"Target node '{edge.target_id}' not found", code="GR-005")
        self._storage.put_edge(edge, allow_overwrite=False)
        self._index.index_edge(edge)
        self._cache.set_edge(edge)
        return edge

    def update_edge(self, edge: GraphEdge) -> GraphEdge:
        if not self._storage.get_edge_optional(edge.edge_id):
            raise GraphEdgeNotFoundError(f"Edge '{edge.edge_id}' not found", code="GR-006")
        self._storage.put_edge(edge, allow_overwrite=True)
        self._index.deindex_edge(edge.edge_id)
        self._index.index_edge(edge)
        self._cache.set_edge(edge)
        return edge

    def get_edge(self, edge_id: str) -> GraphEdge:
        cached = self._cache.get_edge(edge_id)
        if cached is not None and not cached.is_deleted:
            return cached
        e = self._storage.get_edge(edge_id)
        if e.is_deleted:
            raise GraphEdgeNotFoundError(f"Edge '{edge_id}' is soft-deleted", code="GR-007")
        self._cache.set_edge(e)
        return e

    def get_edge_optional(self, edge_id: str) -> Optional[GraphEdge]:
        try:
            return self.get_edge(edge_id)
        except GraphEdgeNotFoundError:
            return None

    def delete_edge(self, edge_id: str, hard: bool = False) -> bool:
        ok = self._storage.delete_edge(edge_id, hard=hard)
        if ok:
            self._cache.delete_edge(edge_id)
            if hard:
                self._index.deindex_edge(edge_id)
        return ok

    def edge_exists(self, edge_id: str) -> bool:
        cached = self._cache.get_edge(edge_id)
        if cached is not None:
            return not cached.is_deleted
        return self._storage.get_edge_optional(edge_id) is not None

    def get_edges_from(self, node_id: str) -> list[GraphEdge]:
        return self._storage.get_edges_from(node_id)

    def get_edges_to(self, node_id: str) -> list[GraphEdge]:
        return self._storage.get_edges_to(node_id)

    def all_edges(self, include_deleted: bool = False) -> list[GraphEdge]:
        return self._storage.all_edges(include_deleted)

    def edge_count(self, include_deleted: bool = False) -> int:
        return self._storage.edge_count(include_deleted)

    # ── Query ─────────────────────────────────────────────────────────────────

    def query_nodes(self, query: Optional[NodeQuery] = None) -> GraphPageResult:
        q    = query or NodeQuery()
        filt = q.filter
        page = q.pagination

        if filt.node_types:
            ids: set[str] = set()
            for t in filt.node_types:
                ids |= self._index.nodes_by_type(t)
        elif filt.tags:
            ids = set()
            for tag in filt.tags:
                ids |= self._index.nodes_by_tag(tag)
        elif filt.label_contains:
            ids = self._index.nodes_by_keyword(filt.label_contains)
        else:
            ids = self._index.all_node_ids()

        nodes = []
        for nid in ids:
            n = self._storage.get_node_optional(nid)
            if n is None:
                continue
            if not filt.include_deleted and n.is_deleted:
                continue
            if filt.statuses and n.status not in filt.statuses:
                continue
            if filt.labels and n.label not in filt.labels:
                continue
            if filt.knowledge_ids and n.knowledge_id not in filt.knowledge_ids:
                continue
            if filt.min_weight is not None and n.weight < filt.min_weight:
                continue
            if filt.max_weight is not None and n.weight > filt.max_weight:
                continue
            if filt.min_confidence is not None and n.confidence < filt.min_confidence:
                continue
            nodes.append(n)

        nodes.sort(
            key=lambda nd: nd.metadata.created_at,
            reverse=(page.sort_order == GraphSortOrder.DESC),
        )
        total = len(nodes)
        start = page.offset
        return GraphPageResult.build(nodes[start:start + page.page_size], total, page)

    def query_edges(self, query: Optional[EdgeQuery] = None) -> GraphPageResult:
        q    = query or EdgeQuery()
        filt = q.filter
        page = q.pagination

        if filt.edge_types:
            ids: set[str] = set()
            for t in filt.edge_types:
                ids |= self._index.edges_by_type(t)
        else:
            ids = self._index.all_edge_ids()

        edges = []
        for eid in ids:
            e = self._storage.get_edge_optional(eid)
            if e is None:
                continue
            if not filt.include_deleted and e.is_deleted:
                continue
            if not filt.include_expired and e.is_expired:
                continue
            if filt.source_ids and e.source_id not in filt.source_ids:
                continue
            if filt.target_ids and e.target_id not in filt.target_ids:
                continue
            if filt.min_weight is not None and e.weight < filt.min_weight:
                continue
            if filt.max_weight is not None and e.weight > filt.max_weight:
                continue
            edges.append(e)

        edges.sort(
            key=lambda ed: ed.metadata.created_at,
            reverse=(page.sort_order == GraphSortOrder.DESC),
        )
        total = len(edges)
        start = page.offset
        return GraphPageResult.build(edges[start:start + page.page_size], total, page)

    # ── Bulk ──────────────────────────────────────────────────────────────────

    def bulk_add_nodes(self, nodes: list[GraphNode]) -> int:
        added = 0
        for node in nodes:
            try:
                self.add_node(node)
                added += 1
            except GraphNodeAlreadyExistsError:
                pass
        return added

    def bulk_add_edges(self, edges: list[GraphEdge]) -> int:
        added = 0
        for edge in edges:
            try:
                self.add_edge(edge)
                added += 1
            except (GraphEdgeAlreadyExistsError, GraphNodeNotFoundError):
                pass
        return added

    def reset(self) -> None:
        self._storage.clear()
        self._index.reset()
        self._cache.clear()


# ── Singleton ─────────────────────────────────────────────────────────────────

def get_graph_repository() -> GraphRepository:
    global _repo
    with _lock:
        if _repo is None:
            _repo = GraphRepository()
        return _repo


def reset_graph_repository() -> None:
    global _repo
    with _lock:
        _repo = None
