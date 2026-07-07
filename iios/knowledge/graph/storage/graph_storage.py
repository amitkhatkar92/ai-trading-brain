"""
iios/knowledge/graph/storage/graph_storage.py
===============================================
Thread-safe in-memory storage backend for graph nodes and edges.
Maintains forward + reverse adjacency lists for O(1) neighbourhood queries.
"""
from __future__ import annotations

import logging
import threading
from collections import defaultdict
from typing import Optional

from ..graph_exceptions import (
    GraphNodeNotFoundError,
    GraphEdgeNotFoundError,
    GraphNodeAlreadyExistsError,
    GraphEdgeAlreadyExistsError,
)
from ..models.graph_node import GraphNode
from ..models.graph_edge import GraphEdge

__all__ = ["GraphStorage", "get_graph_storage", "reset_graph_storage"]

_LOG  = logging.getLogger("iios.knowledge.graph.storage")
_lock = threading.Lock()
_storage: Optional["GraphStorage"] = None


class GraphStorage:
    """Primary in-memory store for GraphNode and GraphEdge objects."""

    def __init__(self) -> None:
        self._lock    = threading.RLock()
        self._nodes:   dict[str, GraphNode] = {}
        self._edges:   dict[str, GraphEdge] = {}
        # node_id → set of edge_ids leaving / arriving
        self._forward: dict[str, set[str]]  = defaultdict(set)
        self._reverse: dict[str, set[str]]  = defaultdict(set)

    # ── Node CRUD ─────────────────────────────────────────────────────────────

    def put_node(self, node: GraphNode, allow_overwrite: bool = True) -> None:
        with self._lock:
            if not allow_overwrite and node.node_id in self._nodes:
                raise GraphNodeAlreadyExistsError(
                    f"Node '{node.node_id}' already exists", code="GS-001",
                )
            self._nodes[node.node_id] = node
            self._forward.setdefault(node.node_id, set())
            self._reverse.setdefault(node.node_id, set())

    def get_node(self, node_id: str) -> GraphNode:
        with self._lock:
            n = self._nodes.get(node_id)
        if n is None:
            raise GraphNodeNotFoundError(f"Node '{node_id}' not found", code="GS-002")
        return n

    def get_node_optional(self, node_id: str) -> Optional[GraphNode]:
        with self._lock:
            return self._nodes.get(node_id)

    def node_exists(self, node_id: str) -> bool:
        with self._lock:
            return node_id in self._nodes

    def delete_node(self, node_id: str, hard: bool = False) -> bool:
        with self._lock:
            n = self._nodes.get(node_id)
            if n is None:
                return False
            if hard:
                for eid in list(self._forward.get(node_id, set())):
                    e = self._edges.pop(eid, None)
                    if e:
                        self._reverse[e.target_id].discard(eid)
                for eid in list(self._reverse.get(node_id, set())):
                    e = self._edges.pop(eid, None)
                    if e:
                        self._forward[e.source_id].discard(eid)
                self._forward.pop(node_id, None)
                self._reverse.pop(node_id, None)
                del self._nodes[node_id]
            else:
                n.is_deleted = True
                n.metadata.touch()
        return True

    def all_nodes(self, include_deleted: bool = False) -> list[GraphNode]:
        with self._lock:
            nodes = list(self._nodes.values())
        return nodes if include_deleted else [n for n in nodes if not n.is_deleted]

    def all_node_ids(self, include_deleted: bool = False) -> list[str]:
        with self._lock:
            if include_deleted:
                return list(self._nodes.keys())
            return [nid for nid, n in self._nodes.items() if not n.is_deleted]

    def node_count(self, include_deleted: bool = False) -> int:
        return len(self.all_node_ids(include_deleted))

    # ── Edge CRUD ─────────────────────────────────────────────────────────────

    def put_edge(self, edge: GraphEdge, allow_overwrite: bool = True) -> None:
        with self._lock:
            if not allow_overwrite and edge.edge_id in self._edges:
                raise GraphEdgeAlreadyExistsError(
                    f"Edge '{edge.edge_id}' already exists", code="GS-003",
                )
            self._edges[edge.edge_id] = edge
            self._forward[edge.source_id].add(edge.edge_id)
            self._reverse[edge.target_id].add(edge.edge_id)

    def get_edge(self, edge_id: str) -> GraphEdge:
        with self._lock:
            e = self._edges.get(edge_id)
        if e is None:
            raise GraphEdgeNotFoundError(f"Edge '{edge_id}' not found", code="GS-004")
        return e

    def get_edge_optional(self, edge_id: str) -> Optional[GraphEdge]:
        with self._lock:
            return self._edges.get(edge_id)

    def delete_edge(self, edge_id: str, hard: bool = False) -> bool:
        with self._lock:
            e = self._edges.get(edge_id)
            if e is None:
                return False
            if hard:
                self._forward[e.source_id].discard(edge_id)
                self._reverse[e.target_id].discard(edge_id)
                del self._edges[edge_id]
            else:
                e.is_deleted = True
                e.metadata.touch()
        return True

    def get_edges_from(self, node_id: str, include_deleted: bool = False) -> list[GraphEdge]:
        with self._lock:
            eids = set(self._forward.get(node_id, set()))
        result = []
        for eid in eids:
            e = self._edges.get(eid)
            if e and (include_deleted or not e.is_deleted):
                result.append(e)
        return result

    def get_edges_to(self, node_id: str, include_deleted: bool = False) -> list[GraphEdge]:
        with self._lock:
            eids = set(self._reverse.get(node_id, set()))
        result = []
        for eid in eids:
            e = self._edges.get(eid)
            if e and (include_deleted or not e.is_deleted):
                result.append(e)
        return result

    def all_edges(self, include_deleted: bool = False) -> list[GraphEdge]:
        with self._lock:
            edges = list(self._edges.values())
        return edges if include_deleted else [e for e in edges if not e.is_deleted]

    def all_edge_ids(self, include_deleted: bool = False) -> list[str]:
        with self._lock:
            if include_deleted:
                return list(self._edges.keys())
            return [eid for eid, e in self._edges.items() if not e.is_deleted]

    def edge_count(self, include_deleted: bool = False) -> int:
        return len(self.all_edge_ids(include_deleted))

    def clear(self) -> None:
        with self._lock:
            self._nodes.clear()
            self._edges.clear()
            self._forward.clear()
            self._reverse.clear()

    def reset(self) -> None:
        self.clear()


# ── Singleton ─────────────────────────────────────────────────────────────────

def get_graph_storage() -> GraphStorage:
    global _storage
    with _lock:
        if _storage is None:
            _storage = GraphStorage()
        return _storage


def reset_graph_storage() -> None:
    global _storage
    with _lock:
        _storage = None
