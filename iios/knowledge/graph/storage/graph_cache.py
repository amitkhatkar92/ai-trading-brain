"""
iios/knowledge/graph/storage/graph_cache.py
"""
from __future__ import annotations

import logging
import threading
from typing import Any, Optional

from ..graph_constants import DEFAULT_CACHE_TTL
from ..models.graph_node import GraphNode
from ..models.graph_edge import GraphEdge

__all__ = ["GraphCache", "get_graph_cache", "reset_graph_cache"]

_LOG  = logging.getLogger("iios.knowledge.graph.cache")
_lock = threading.Lock()
_cache: Optional["GraphCache"] = None
_MAX_SIZE = 10_000


class GraphCache:
    """LRU dict-based cache for graph nodes and edges."""

    def __init__(self, max_size: int = _MAX_SIZE, ttl: float = DEFAULT_CACHE_TTL) -> None:
        self._lock        = threading.RLock()
        self._nodes:       dict[str, GraphNode] = {}
        self._edges:       dict[str, GraphEdge] = {}
        self._max_size    = max_size
        self._node_hits   = 0
        self._node_misses = 0
        self._edge_hits   = 0
        self._edge_misses = 0

    def _evict_nodes(self) -> None:
        if len(self._nodes) >= self._max_size:
            oldest = next(iter(self._nodes))
            del self._nodes[oldest]

    def _evict_edges(self) -> None:
        if len(self._edges) >= self._max_size:
            oldest = next(iter(self._edges))
            del self._edges[oldest]

    # ── Nodes ─────────────────────────────────────────────────────────────────

    def get_node(self, node_id: str) -> Optional[GraphNode]:
        with self._lock:
            n = self._nodes.get(node_id)
        if n is not None:
            self._node_hits += 1
        else:
            self._node_misses += 1
        return n

    def set_node(self, node: GraphNode) -> None:
        with self._lock:
            self._evict_nodes()
            self._nodes[node.node_id] = node

    def delete_node(self, node_id: str) -> None:
        with self._lock:
            self._nodes.pop(node_id, None)

    # ── Edges ─────────────────────────────────────────────────────────────────

    def get_edge(self, edge_id: str) -> Optional[GraphEdge]:
        with self._lock:
            e = self._edges.get(edge_id)
        if e is not None:
            self._edge_hits += 1
        else:
            self._edge_misses += 1
        return e

    def set_edge(self, edge: GraphEdge) -> None:
        with self._lock:
            self._evict_edges()
            self._edges[edge.edge_id] = edge

    def delete_edge(self, edge_id: str) -> None:
        with self._lock:
            self._edges.pop(edge_id, None)

    # ── Stats / control ───────────────────────────────────────────────────────

    @property
    def node_hit_ratio(self) -> float:
        total = self._node_hits + self._node_misses
        return self._node_hits / total if total > 0 else 0.0

    def stats(self) -> dict[str, Any]:
        return {
            "node_hits":      self._node_hits,
            "node_misses":    self._node_misses,
            "edge_hits":      self._edge_hits,
            "edge_misses":    self._edge_misses,
            "node_hit_ratio": self.node_hit_ratio,
            "cached_nodes":   len(self._nodes),
            "cached_edges":   len(self._edges),
        }

    def clear(self) -> None:
        with self._lock:
            self._nodes.clear()
            self._edges.clear()

    def reset(self) -> None:
        self.clear()
        self._node_hits = self._node_misses = 0
        self._edge_hits = self._edge_misses = 0


# ── Singleton ─────────────────────────────────────────────────────────────────

def get_graph_cache() -> GraphCache:
    global _cache
    with _lock:
        if _cache is None:
            _cache = GraphCache()
        return _cache


def reset_graph_cache() -> None:
    global _cache
    with _lock:
        _cache = None
