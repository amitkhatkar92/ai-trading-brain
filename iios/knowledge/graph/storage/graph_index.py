"""
iios/knowledge/graph/storage/graph_index.py
============================================
Multi-field inverted index for fast graph lookups.
"""
from __future__ import annotations

import logging
import re
import threading
from collections import defaultdict
from typing import Optional

from ..graph_constants import GraphNodeType, GraphEdgeType, NodeStatus, EdgeStatus
from ..models.graph_node import GraphNode
from ..models.graph_edge import GraphEdge

__all__ = ["GraphIndex", "get_graph_index", "reset_graph_index"]

_LOG  = logging.getLogger("iios.knowledge.graph.index")
_lock = threading.Lock()
_index: Optional["GraphIndex"] = None

_WORD_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return _WORD_RE.findall(text.lower())


class GraphIndex:
    """Inverted indexes for fast node/edge retrieval by type, status, tag, and label."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        # Node indexes
        self._by_node_type:     dict[GraphNodeType, set[str]] = defaultdict(set)
        self._by_node_status:   dict[NodeStatus,    set[str]] = defaultdict(set)
        self._by_node_keyword:  dict[str,           set[str]] = defaultdict(set)
        self._by_node_tag:      dict[str,           set[str]] = defaultdict(set)
        self._by_knowledge_id:  dict[str, str]                = {}  # knowledge_id → node_id
        self._all_node_ids:     set[str]                      = set()
        # Edge indexes
        self._by_edge_type:     dict[GraphEdgeType, set[str]] = defaultdict(set)
        self._by_edge_status:   dict[EdgeStatus,    set[str]] = defaultdict(set)
        self._all_edge_ids:     set[str]                      = set()

    # ── Node indexing ─────────────────────────────────────────────────────────

    def index_node(self, node: GraphNode) -> None:
        nid = node.node_id
        with self._lock:
            self._all_node_ids.add(nid)
            self._by_node_type[node.node_type].add(nid)
            self._by_node_status[node.status].add(nid)
            for token in _tokenize(node.label):
                self._by_node_keyword[token].add(nid)
            for tag in node.metadata.tags:
                self._by_node_tag[tag].add(nid)
            if node.knowledge_id:
                self._by_knowledge_id[node.knowledge_id] = nid

    def deindex_node(self, node_id: str) -> None:
        with self._lock:
            self._all_node_ids.discard(node_id)
            for s in self._by_node_type.values():
                s.discard(node_id)
            for s in self._by_node_status.values():
                s.discard(node_id)
            for s in self._by_node_keyword.values():
                s.discard(node_id)
            for s in self._by_node_tag.values():
                s.discard(node_id)
            stale = [k for k, v in self._by_knowledge_id.items() if v == node_id]
            for k in stale:
                del self._by_knowledge_id[k]

    def nodes_by_type(self, t: GraphNodeType) -> set[str]:
        with self._lock:
            return set(self._by_node_type.get(t, set()))

    def nodes_by_status(self, s: NodeStatus) -> set[str]:
        with self._lock:
            return set(self._by_node_status.get(s, set()))

    def nodes_by_keyword(self, text: str) -> set[str]:
        """AND intersection of tokens."""
        tokens = _tokenize(text)
        if not tokens:
            return set()
        with self._lock:
            result = set(self._by_node_keyword.get(tokens[0], set()))
            for t in tokens[1:]:
                result &= self._by_node_keyword.get(t, set())
        return result

    def nodes_by_tag(self, tag: str) -> set[str]:
        with self._lock:
            return set(self._by_node_tag.get(tag, set()))

    def node_by_knowledge_id(self, knowledge_id: str) -> Optional[str]:
        with self._lock:
            return self._by_knowledge_id.get(knowledge_id)

    def all_node_ids(self) -> set[str]:
        with self._lock:
            return set(self._all_node_ids)

    def node_count(self) -> int:
        with self._lock:
            return len(self._all_node_ids)

    # ── Edge indexing ─────────────────────────────────────────────────────────

    def index_edge(self, edge: GraphEdge) -> None:
        eid = edge.edge_id
        with self._lock:
            self._all_edge_ids.add(eid)
            self._by_edge_type[edge.edge_type].add(eid)
            self._by_edge_status[edge.status].add(eid)

    def deindex_edge(self, edge_id: str) -> None:
        with self._lock:
            self._all_edge_ids.discard(edge_id)
            for s in self._by_edge_type.values():
                s.discard(edge_id)
            for s in self._by_edge_status.values():
                s.discard(edge_id)

    def edges_by_type(self, t: GraphEdgeType) -> set[str]:
        with self._lock:
            return set(self._by_edge_type.get(t, set()))

    def all_edge_ids(self) -> set[str]:
        with self._lock:
            return set(self._all_edge_ids)

    def edge_count(self) -> int:
        with self._lock:
            return len(self._all_edge_ids)

    def reset(self) -> None:
        with self._lock:
            self._by_node_type.clear()
            self._by_node_status.clear()
            self._by_node_keyword.clear()
            self._by_node_tag.clear()
            self._by_knowledge_id.clear()
            self._all_node_ids.clear()
            self._by_edge_type.clear()
            self._by_edge_status.clear()
            self._all_edge_ids.clear()


# ── Singleton ─────────────────────────────────────────────────────────────────

def get_graph_index() -> GraphIndex:
    global _index
    with _lock:
        if _index is None:
            _index = GraphIndex()
        return _index


def reset_graph_index() -> None:
    global _index
    with _lock:
        _index = None
