"""
iios/knowledge/graph/knowledge_graph.py
========================================
In-memory directed knowledge graph.
Nodes are knowledge record IDs; edges are KnowledgeReferences.
Supports traversal, neighbourhood queries, cycle detection, and
shortest-path via BFS.
"""

from __future__ import annotations

import logging
import threading
from collections import defaultdict, deque
from typing import Optional

from ..knowledge_constants import RelationshipType
from ..knowledge_exceptions import (
    KnowledgeGraphError,
    KnowledgeRelationshipError,
    KnowledgeCycleError,
)
from ..models.knowledge_record import KnowledgeRecord
from ..models.knowledge_reference import KnowledgeReference

__all__ = [
    "KnowledgeGraph",
    "get_knowledge_graph",
    "reset_knowledge_graph",
]

_LOG = logging.getLogger("iios.knowledge.graph")
_lock = threading.Lock()
_graph: Optional["KnowledgeGraph"] = None


class KnowledgeGraph:
    """Directed graph of knowledge items connected by typed relationships.

    Graph is adjacency-list based.  Both forward (source→targets) and
    reverse (target→sources) adjacency lists are maintained for O(1)
    neighbourhood lookups.

    Usage::

        graph = get_knowledge_graph()
        graph.add_node(record.id)
        graph.add_edge(ref)
        neighbours = graph.successors("iios.knowledge/abc")
        path = graph.shortest_path("iios.knowledge/abc", "iios.knowledge/xyz")
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        # node_id → set of node_ids (forward edges)
        self._forward: dict[str, set[str]] = defaultdict(set)
        # node_id → set of node_ids (reverse edges)
        self._reverse: dict[str, set[str]] = defaultdict(set)
        # (source_id, target_id) → list[KnowledgeReference]
        self._edges: dict[tuple[str, str], list[KnowledgeReference]] = defaultdict(list)
        self._nodes: set[str] = set()

    # ── Node management ───────────────────────────────────────────────────────

    def add_node(self, node_id: str) -> None:
        with self._lock:
            self._nodes.add(node_id)
            if node_id not in self._forward:
                self._forward[node_id] = set()
            if node_id not in self._reverse:
                self._reverse[node_id] = set()

    def remove_node(self, node_id: str) -> None:
        with self._lock:
            self._nodes.discard(node_id)
            # Remove all edges referencing this node
            for target in set(self._forward.get(node_id, set())):
                self._reverse[target].discard(node_id)
                self._edges.pop((node_id, target), None)
            for source in set(self._reverse.get(node_id, set())):
                self._forward[source].discard(node_id)
                self._edges.pop((source, node_id), None)
            self._forward.pop(node_id, None)
            self._reverse.pop(node_id, None)

    def has_node(self, node_id: str) -> bool:
        with self._lock:
            return node_id in self._nodes

    def node_count(self) -> int:
        with self._lock:
            return len(self._nodes)

    # ── Edge management ───────────────────────────────────────────────────────

    def add_edge(self, ref: KnowledgeReference) -> None:
        """Add an edge. Auto-creates nodes if missing."""
        with self._lock:
            self._nodes.add(ref.source_id)
            self._nodes.add(ref.target_id)
            self._forward[ref.source_id].add(ref.target_id)
            self._reverse[ref.target_id].add(ref.source_id)
            self._edges[(ref.source_id, ref.target_id)].append(ref)

    def remove_edge(self, source_id: str, target_id: str, ref_id: Optional[str] = None) -> bool:
        with self._lock:
            key = (source_id, target_id)
            if key not in self._edges:
                return False
            if ref_id:
                before = len(self._edges[key])
                self._edges[key] = [r for r in self._edges[key] if r.ref_id != ref_id]
                removed = len(self._edges[key]) < before
            else:
                self._edges.pop(key, None)
                removed = True
            # If no refs remain, remove adjacency entries
            if not self._edges.get(key):
                self._edges.pop(key, None)
                self._forward[source_id].discard(target_id)
                self._reverse[target_id].discard(source_id)
            return removed

    def get_edges(self, source_id: str, target_id: str) -> list[KnowledgeReference]:
        with self._lock:
            return list(self._edges.get((source_id, target_id), []))

    def edge_count(self) -> int:
        with self._lock:
            return sum(len(refs) for refs in self._edges.values())

    # ── Traversal ─────────────────────────────────────────────────────────────

    def successors(self, node_id: str) -> set[str]:
        """Return direct successors of *node_id*."""
        with self._lock:
            return set(self._forward.get(node_id, set()))

    def predecessors(self, node_id: str) -> set[str]:
        """Return direct predecessors of *node_id*."""
        with self._lock:
            return set(self._reverse.get(node_id, set()))

    def descendants(self, node_id: str) -> set[str]:
        """BFS: all reachable nodes from *node_id* (forward)."""
        return self._bfs(node_id, forward=True)

    def ancestors(self, node_id: str) -> set[str]:
        """BFS: all nodes that can reach *node_id* (reverse)."""
        return self._bfs(node_id, forward=False)

    def _bfs(self, start: str, forward: bool) -> set[str]:
        visited: set[str] = set()
        queue = deque([start])
        with self._lock:
            adj = self._forward if forward else self._reverse
            while queue:
                node = queue.popleft()
                for neighbour in adj.get(node, set()):
                    if neighbour not in visited:
                        visited.add(neighbour)
                        queue.append(neighbour)
        return visited

    def shortest_path(self, source: str, target: str) -> list[str]:
        """BFS shortest path from *source* to *target*. Returns [] if none."""
        if source == target:
            return [source]
        visited: set[str] = {source}
        queue: deque[list[str]] = deque([[source]])
        with self._lock:
            while queue:
                path = queue.popleft()
                node = path[-1]
                for neighbour in self._forward.get(node, set()):
                    if neighbour == target:
                        return path + [neighbour]
                    if neighbour not in visited:
                        visited.add(neighbour)
                        queue.append(path + [neighbour])
        return []

    # ── Cycle detection ───────────────────────────────────────────────────────

    def has_cycle(self) -> bool:
        """Return True if the graph contains any cycle (DFS)."""
        with self._lock:
            nodes = set(self._nodes)
        visited: set[str] = set()
        in_stack: set[str] = set()

        def dfs(n: str) -> bool:
            visited.add(n)
            in_stack.add(n)
            with self._lock:
                neighbours = set(self._forward.get(n, set()))
            for nb in neighbours:
                if nb not in visited:
                    if dfs(nb):
                        return True
                elif nb in in_stack:
                    return True
            in_stack.discard(n)
            return False

        for node in nodes:
            if node not in visited:
                if dfs(node):
                    return True
        return False

    def cycle_raises(self) -> None:
        if self.has_cycle():
            raise KnowledgeCycleError("Cycle detected in knowledge graph", code="KG-001")

    # ── Neighbourhood helpers ─────────────────────────────────────────────────

    def related_by_type(self, node_id: str, rel_type: RelationshipType) -> list[str]:
        """Return targets of edges from *node_id* with a given relationship type."""
        result = []
        with self._lock:
            for target_id in self._forward.get(node_id, set()):
                refs = self._edges.get((node_id, target_id), [])
                for ref in refs:
                    if ref.relationship_type == rel_type and ref.is_active:
                        result.append(target_id)
                        break
        return result

    def sync_from_record(self, record: KnowledgeRecord) -> None:
        """Synchronize all references in *record* into the graph."""
        self.add_node(record.id)
        for ref in record.references:
            if ref.is_active:
                self.add_edge(ref)

    def all_nodes(self) -> set[str]:
        with self._lock:
            return set(self._nodes)

    def reset(self) -> None:
        with self._lock:
            self._nodes.clear()
            self._forward.clear()
            self._reverse.clear()
            self._edges.clear()


# ── Singleton ─────────────────────────────────────────────────────────────────

def get_knowledge_graph() -> KnowledgeGraph:
    global _graph
    with _lock:
        if _graph is None:
            _graph = KnowledgeGraph()
        return _graph


def reset_knowledge_graph() -> None:
    global _graph
    with _lock:
        if _graph is not None:
            _graph.reset()
        _graph = None
