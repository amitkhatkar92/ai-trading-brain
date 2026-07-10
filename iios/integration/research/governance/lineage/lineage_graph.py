"""lineage/lineage_graph.py — Directed acyclic graph for artifact and experiment lineage."""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from iios.integration.research.governance.governance_constants import (
    DEFAULT_MAX_LINEAGE_NODES,
    LineageEdgeType,
    LineageNodeType,
)
from iios.integration.research.governance.governance_exceptions import (
    LineageCapacityError,
    LineageCycleError,
    LineageNodeNotFoundError,
)


@dataclass
class LineageNode:
    """A vertex in the lineage graph."""
    node_id:    str
    node_type:  LineageNodeType
    entity_id:  str            # ID of the entity this node represents
    label:      str
    version:    Optional[str]
    created_at: float
    metadata:   dict[str, Any]

    @classmethod
    def create(
        cls,
        entity_id:  str,
        node_type:  LineageNodeType,
        label:      str,
        *,
        node_id:    Optional[str] = None,
        version:    Optional[str] = None,
        metadata:   Optional[dict] = None,
    ) -> "LineageNode":
        return cls(
            node_id    = node_id or f"ln_{uuid.uuid4().hex[:10]}",
            node_type  = node_type,
            entity_id  = entity_id,
            label      = label,
            version    = version,
            created_at = time.time(),
            metadata   = metadata or {},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id":    self.node_id,
            "node_type":  self.node_type.value,
            "entity_id":  self.entity_id,
            "label":      self.label,
            "version":    self.version,
            "created_at": self.created_at,
        }


@dataclass
class LineageEdge:
    """A directed edge in the lineage graph."""
    edge_id:    str
    from_node:  str
    to_node:    str
    edge_type:  LineageEdgeType
    label:      Optional[str]
    created_at: float
    metadata:   dict[str, Any]

    @classmethod
    def create(
        cls,
        from_node:  str,
        to_node:    str,
        edge_type:  LineageEdgeType,
        *,
        edge_id:    Optional[str] = None,
        label:      Optional[str] = None,
        metadata:   Optional[dict] = None,
    ) -> "LineageEdge":
        return cls(
            edge_id    = edge_id or f"le_{uuid.uuid4().hex[:10]}",
            from_node  = from_node,
            to_node    = to_node,
            edge_type  = edge_type,
            label      = label,
            created_at = time.time(),
            metadata   = metadata or {},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "edge_id":    self.edge_id,
            "from_node":  self.from_node,
            "to_node":    self.to_node,
            "edge_type":  self.edge_type.value,
            "label":      self.label,
            "created_at": self.created_at,
        }


class LineageGraph:
    """
    Thread-safe directed acyclic graph for lineage tracking.

    Nodes represent research entities (datasets, models, experiments, artifacts).
    Directed edges represent derivation / training / evaluation relationships.

    Cycle detection is performed on every edge insertion to maintain the DAG invariant.
    """

    def __init__(self, max_nodes: int = DEFAULT_MAX_LINEAGE_NODES) -> None:
        self._nodes:     dict[str, LineageNode]        = {}
        self._edges:     dict[str, LineageEdge]        = {}
        self._adj_out:   dict[str, set[str]]           = {}  # node_id → {child node_ids}
        self._adj_in:    dict[str, set[str]]           = {}  # node_id → {parent node_ids}
        self._max        = max_nodes
        self._lock       = threading.RLock()

    # ── Node management ───────────────────────────────────────────────────────

    def add_node(self, node: LineageNode) -> None:
        with self._lock:
            if len(self._nodes) >= self._max:
                raise LineageCapacityError(f"Lineage graph capacity ({self._max}) reached")
            self._nodes[node.node_id]    = node
            self._adj_out[node.node_id]  = set()
            self._adj_in[node.node_id]   = set()

    def get_node(self, node_id: str) -> LineageNode:
        with self._lock:
            node = self._nodes.get(node_id)
        if node is None:
            raise LineageNodeNotFoundError(f"Lineage node '{node_id}' not found")
        return node

    def find_by_entity(self, entity_id: str) -> list[LineageNode]:
        with self._lock:
            return [n for n in self._nodes.values() if n.entity_id == entity_id]

    # ── Edge management ───────────────────────────────────────────────────────

    def add_edge(self, edge: LineageEdge) -> None:
        """Add a directed edge from ``edge.from_node`` → ``edge.to_node``.

        Raises ``LineageCycleError`` if the edge would introduce a cycle.
        """
        with self._lock:
            if edge.from_node not in self._nodes:
                raise LineageNodeNotFoundError(f"Source node '{edge.from_node}' not found")
            if edge.to_node not in self._nodes:
                raise LineageNodeNotFoundError(f"Target node '{edge.to_node}' not found")
            # Cycle detection: DFS from to_node; if from_node is reachable → cycle
            if self._is_reachable(edge.to_node, edge.from_node):
                raise LineageCycleError(
                    f"Adding edge {edge.from_node}→{edge.to_node} would create a cycle"
                )
            self._edges[edge.edge_id]           = edge
            self._adj_out[edge.from_node].add(edge.to_node)
            self._adj_in[edge.to_node].add(edge.from_node)

    def _is_reachable(self, start: str, target: str) -> bool:
        """BFS reachability check (already holding the lock)."""
        if start == target:
            return True
        visited = {start}
        queue   = [start]
        while queue:
            current = queue.pop(0)
            for child in self._adj_out.get(current, set()):
                if child == target:
                    return True
                if child not in visited:
                    visited.add(child)
                    queue.append(child)
        return False

    # ── Traversal ─────────────────────────────────────────────────────────────

    def ancestors(self, node_id: str) -> list[LineageNode]:
        """Return all ancestor nodes (upstream lineage)."""
        with self._lock:
            result = []
            visited: set[str] = set()
            queue = list(self._adj_in.get(node_id, set()))
            while queue:
                nid = queue.pop(0)
                if nid in visited:
                    continue
                visited.add(nid)
                if nid in self._nodes:
                    result.append(self._nodes[nid])
                queue.extend(self._adj_in.get(nid, set()))
            return result

    def descendants(self, node_id: str) -> list[LineageNode]:
        """Return all descendant nodes (downstream impact)."""
        with self._lock:
            result = []
            visited: set[str] = set()
            queue = list(self._adj_out.get(node_id, set()))
            while queue:
                nid = queue.pop(0)
                if nid in visited:
                    continue
                visited.add(nid)
                if nid in self._nodes:
                    result.append(self._nodes[nid])
                queue.extend(self._adj_out.get(nid, set()))
            return result

    def parents(self, node_id: str) -> list[LineageNode]:
        with self._lock:
            return [self._nodes[n] for n in self._adj_in.get(node_id, set())
                    if n in self._nodes]

    def children(self, node_id: str) -> list[LineageNode]:
        with self._lock:
            return [self._nodes[n] for n in self._adj_out.get(node_id, set())
                    if n in self._nodes]

    # ── Stats ─────────────────────────────────────────────────────────────────

    def node_count(self) -> int:
        with self._lock:
            return len(self._nodes)

    def edge_count(self) -> int:
        with self._lock:
            return len(self._edges)

    def stats(self) -> dict[str, Any]:
        with self._lock:
            by_type: dict[str, int] = {}
            for n in self._nodes.values():
                k = n.node_type.value
                by_type[k] = by_type.get(k, 0) + 1
            return {
                "nodes":       len(self._nodes),
                "edges":       len(self._edges),
                "by_type":     by_type,
                "capacity":    self._max,
            }
