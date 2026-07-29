"""
knowledge_graph.py -- iios.ai.memory_knowledge.graph
=====================================================
:class:`KnowledgeGraph` — mutable, thread-safe in-memory knowledge graph.

Supports
--------
* Node and relationship CRUD
* Breadth-first traversal
* Neighbour enumeration (incoming / outgoing)
* Path retrieval between two nodes (BFS shortest path)
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Dict, FrozenSet, List, Optional, Set, Tuple

from ..events.event_bus          import MemoryEventBus
from ..events.memory_events      import GraphTraversedEvent
from .knowledge_node             import KnowledgeNode
from .knowledge_path             import KnowledgePath
from .knowledge_relationship     import KnowledgeRelationship

SYSTEM_ID = "iios:ai:memory_knowledge:knowledge_graph"


class KnowledgeGraph:
    """
    Thread-safe in-memory knowledge graph.

    Nodes are vertices; relationships are directed edges.
    """

    def __init__(self, event_bus: Optional[MemoryEventBus] = None) -> None:
        self._nodes:     Dict[str, KnowledgeNode]           = {}
        self._rels:      Dict[str, KnowledgeRelationship]   = {}
        # adjacency: source_id -> list of rel_ids
        self._adj_out:   Dict[str, List[str]]               = {}
        # reverse adjacency: target_id -> list of rel_ids
        self._adj_in:    Dict[str, List[str]]               = {}
        self._lock:      threading.RLock                    = threading.RLock()
        self._event_bus: MemoryEventBus                     = event_bus or MemoryEventBus()

    # ── Nodes ─────────────────────────────────────────────────────────────────

    def add_node(self, node: KnowledgeNode) -> None:
        with self._lock:
            self._nodes[node.node_id] = node
            self._adj_out.setdefault(node.node_id, [])
            self._adj_in.setdefault(node.node_id, [])

    def remove_node(self, node_id: str) -> bool:
        with self._lock:
            if node_id not in self._nodes:
                return False
            # remove all relationships touching this node
            rel_ids_to_remove = (
                self._adj_out.get(node_id, []) +
                self._adj_in.get(node_id, [])
            )
            for rid in set(rel_ids_to_remove):
                self._remove_rel_unlocked(rid)
            del self._nodes[node_id]
            self._adj_out.pop(node_id, None)
            self._adj_in.pop(node_id, None)
            return True

    def get_node(self, node_id: str) -> Optional[KnowledgeNode]:
        with self._lock:
            return self._nodes.get(node_id)

    def list_nodes(self) -> List[KnowledgeNode]:
        with self._lock:
            return list(self._nodes.values())

    # ── Relationships ─────────────────────────────────────────────────────────

    def add_relationship(self, rel: KnowledgeRelationship) -> None:
        with self._lock:
            self._rels[rel.rel_id] = rel
            self._adj_out.setdefault(rel.source_id, []).append(rel.rel_id)
            self._adj_in.setdefault(rel.target_id, []).append(rel.rel_id)

    def remove_relationship(self, rel_id: str) -> bool:
        with self._lock:
            return self._remove_rel_unlocked(rel_id)

    def get_relationship(self, rel_id: str) -> Optional[KnowledgeRelationship]:
        with self._lock:
            return self._rels.get(rel_id)

    def list_relationships(self) -> List[KnowledgeRelationship]:
        with self._lock:
            return list(self._rels.values())

    # ── Traversal ─────────────────────────────────────────────────────────────

    def neighbours_out(self, node_id: str) -> List[KnowledgeNode]:
        """Return nodes reachable from ``node_id`` via outgoing edges."""
        with self._lock:
            return [
                self._nodes[self._rels[rid].target_id]
                for rid in self._adj_out.get(node_id, [])
                if rid in self._rels and self._rels[rid].target_id in self._nodes
            ]

    def neighbours_in(self, node_id: str) -> List[KnowledgeNode]:
        """Return nodes that point to ``node_id``."""
        with self._lock:
            return [
                self._nodes[self._rels[rid].source_id]
                for rid in self._adj_in.get(node_id, [])
                if rid in self._rels and self._rels[rid].source_id in self._nodes
            ]

    def shortest_path(
        self, start_id: str, end_id: str
    ) -> Optional[KnowledgePath]:
        """
        BFS shortest path from ``start_id`` to ``end_id``.
        Returns None if no path exists or nodes are absent.
        """
        with self._lock:
            if start_id not in self._nodes or end_id not in self._nodes:
                return None
            if start_id == end_id:
                return KnowledgePath.create(
                    (self._nodes[start_id],), ()
                )

            visited: Set[str] = {start_id}
            # queue items: (current_node_id, node_path, rel_path)
            queue: deque = deque()
            queue.append(
                (start_id, [self._nodes[start_id]], [])
            )

            while queue:
                current_id, node_path, rel_path = queue.popleft()
                for rid in self._adj_out.get(current_id, []):
                    rel   = self._rels.get(rid)
                    if not rel:
                        continue
                    nid = rel.target_id
                    if nid not in self._nodes:
                        continue
                    if nid in visited:
                        continue
                    new_node_path = node_path + [self._nodes[nid]]
                    new_rel_path  = rel_path  + [rel]
                    if nid == end_id:
                        path = KnowledgePath.create(
                            tuple(new_node_path),
                            tuple(new_rel_path),
                        )
                        return path
                    visited.add(nid)
                    queue.append((nid, new_node_path, new_rel_path))
            return None

    def traverse_bfs(
        self, start_id: str, max_depth: int = 3
    ) -> List[KnowledgeNode]:
        """Return all nodes reachable from ``start_id`` within ``max_depth`` hops."""
        with self._lock:
            if start_id not in self._nodes:
                return []
            visited: Set[str] = {start_id}
            result:  List[KnowledgeNode] = [self._nodes[start_id]]
            queue:   deque = deque([(start_id, 0)])

            while queue:
                nid, depth = queue.popleft()
                if depth >= max_depth:
                    continue
                for rid in self._adj_out.get(nid, []):
                    rel = self._rels.get(rid)
                    if not rel:
                        continue
                    tid = rel.target_id
                    if tid in visited or tid not in self._nodes:
                        continue
                    visited.add(tid)
                    result.append(self._nodes[tid])
                    queue.append((tid, depth + 1))

        self._event_bus.publish(
            GraphTraversedEvent.create(start_id, len(result) - 1)
        )
        return result

    # ── Stats ─────────────────────────────────────────────────────────────────

    def node_count(self) -> int:
        with self._lock:
            return len(self._nodes)

    def relationship_count(self) -> int:
        with self._lock:
            return len(self._rels)

    # ── Internals ─────────────────────────────────────────────────────────────

    def _remove_rel_unlocked(self, rel_id: str) -> bool:
        rel = self._rels.pop(rel_id, None)
        if rel is None:
            return False
        out_list = self._adj_out.get(rel.source_id, [])
        if rel_id in out_list:
            out_list.remove(rel_id)
        in_list = self._adj_in.get(rel.target_id, [])
        if rel_id in in_list:
            in_list.remove(rel_id)
        return True
