"""
iios/knowledge/graph/graph_manager.py
=======================================
High-level service façade for the Knowledge Graph Engine.
Primary entry-point for all graph operations.
"""
from __future__ import annotations

import logging
import threading
from typing import Any, Optional

from .graph_constants import (
    GraphEdgeType, GraphNodeType, NodeStatus,
    DEFAULT_EDGE_WEIGHT, DEFAULT_EDGE_CONFIDENCE, SYSTEM_GRAPH_ACTOR,
)
from .graph_exceptions import GraphNodeNotFoundError, GraphMergeError
from .models.graph_node       import GraphNode
from .models.graph_edge       import GraphEdge
from .models.graph_path       import GraphPath
from .models.graph_cluster    import GraphCluster
from .models.graph_subgraph   import GraphSubgraph
from .models.graph_statistics import GraphStatistics, NodeStatistics, ImpactResult
from .storage.graph_repository import GraphRepository, get_graph_repository
from .storage.graph_query      import (
    NodeFilter, EdgeFilter, NodeQuery, EdgeQuery, GraphPageResult,
)
from .graph_engine  import GraphEngine,  get_graph_engine
from .graph_factory import GraphFactory, get_graph_factory

__all__ = ["GraphManager", "get_graph_manager", "reset_graph_manager"]

_LOG  = logging.getLogger("iios.knowledge.graph.manager")
_lock = threading.Lock()
_manager: Optional["GraphManager"] = None


class GraphManager:
    """
    Unified façade for the Knowledge Graph Engine.

    Orchestrates GraphRepository (CRUD), GraphEngine (traversal + analytics),
    and GraphFactory (object construction).

    Usage::

        gm     = get_graph_manager()
        nifty  = gm.create_node("NIFTY 50",        GraphNodeType.MARKET)
        signal = gm.create_node("Bullish Momentum", GraphNodeType.SIGNAL)
        gm.connect(nifty.node_id, signal.node_id, GraphEdgeType.TRIGGERS, weight=0.9)
        path   = gm.shortest_path(nifty.node_id, signal.node_id)
        impact = gm.impact_analysis(nifty.node_id)
        print(gm.statistics().to_dict())
    """

    def __init__(
        self,
        repository: Optional[GraphRepository] = None,
        engine:     Optional[GraphEngine]     = None,
        factory:    Optional[GraphFactory]    = None,
    ) -> None:
        self._lock    = threading.RLock()
        self._repo    = repository or get_graph_repository()
        self._engine  = engine     or get_graph_engine()
        self._factory = factory    or get_graph_factory()

    # ── Node operations ───────────────────────────────────────────────────────

    def create_node(
        self,
        label:        str,
        node_type:    GraphNodeType            = GraphNodeType.ENTITY,
        properties:   Optional[dict[str, Any]] = None,
        weight:       float                    = 1.0,
        confidence:   float                    = 1.0,
        knowledge_id: Optional[str]            = None,
        tags:         Optional[list[str]]      = None,
        description:  str                      = "",
        actor:        str                      = SYSTEM_GRAPH_ACTOR,
    ) -> GraphNode:
        node = self._factory.create_node(
            label=label, node_type=node_type, properties=properties,
            weight=weight, confidence=confidence, knowledge_id=knowledge_id,
            tags=tags, description=description, actor=actor,
        )
        return self._repo.add_node(node)

    def get_node(self, node_id: str) -> GraphNode:
        return self._repo.get_node(node_id)

    def get_node_optional(self, node_id: str) -> Optional[GraphNode]:
        return self._repo.get_node_optional(node_id)

    def update_node(self, node: GraphNode) -> GraphNode:
        return self._repo.update_node(node)

    def delete_node(self, node_id: str, hard: bool = False) -> bool:
        return self._repo.delete_node(node_id, hard=hard)

    def node_exists(self, node_id: str) -> bool:
        return self._repo.node_exists(node_id)

    def node_count(self) -> int:
        return self._repo.node_count()

    def find_nodes_by_type(self, node_type: GraphNodeType) -> list[GraphNode]:
        result = self._repo.query_nodes(NodeQuery(filter=NodeFilter(node_types=[node_type])))
        return result.items

    def find_node_by_knowledge_id(self, knowledge_id: str) -> Optional[GraphNode]:
        from .storage.graph_index import get_graph_index
        nid = get_graph_index().node_by_knowledge_id(knowledge_id)
        return self._repo.get_node_optional(nid) if nid else None

    # ── Edge operations ───────────────────────────────────────────────────────

    def connect(
        self,
        source_id:  str,
        target_id:  str,
        edge_type:  GraphEdgeType              = GraphEdgeType.RELATED_TO,
        weight:     float                      = DEFAULT_EDGE_WEIGHT,
        confidence: float                      = DEFAULT_EDGE_CONFIDENCE,
        properties: Optional[dict[str, Any]]   = None,
        actor:      str                        = SYSTEM_GRAPH_ACTOR,
    ) -> GraphEdge:
        edge = self._factory.create_edge(
            source_id=source_id, target_id=target_id, edge_type=edge_type,
            weight=weight, confidence=confidence, properties=properties, actor=actor,
        )
        return self._repo.add_edge(edge)

    def disconnect(
        self,
        source_id: str,
        target_id: str,
        edge_type: Optional[GraphEdgeType] = None,
    ) -> int:
        """Remove edges from source→target, optionally filtered by type."""
        edges = [
            e for e in self._repo.get_edges_from(source_id)
            if e.target_id == target_id
            and (edge_type is None or e.edge_type == edge_type)
        ]
        removed = 0
        for e in edges:
            if self._repo.delete_edge(e.edge_id, hard=True):
                removed += 1
        return removed

    def get_edge(self, edge_id: str) -> GraphEdge:
        return self._repo.get_edge(edge_id)

    def update_edge(self, edge: GraphEdge) -> GraphEdge:
        return self._repo.update_edge(edge)

    def delete_edge(self, edge_id: str, hard: bool = False) -> bool:
        return self._repo.delete_edge(edge_id, hard=hard)

    def edge_count(self) -> int:
        return self._repo.edge_count()

    # ── Query ─────────────────────────────────────────────────────────────────

    def query_nodes(self, query: Optional[NodeQuery] = None) -> GraphPageResult:
        return self._repo.query_nodes(query)

    def query_edges(self, query: Optional[EdgeQuery] = None) -> GraphPageResult:
        return self._repo.query_edges(query)

    # ── Bulk operations ───────────────────────────────────────────────────────

    def bulk_create_nodes(self, nodes: list[GraphNode]) -> int:
        return self._repo.bulk_add_nodes(nodes)

    def bulk_create_edges(self, edges: list[GraphEdge]) -> int:
        return self._repo.bulk_add_edges(edges)

    # ── Advanced node operations ──────────────────────────────────────────────

    def merge_nodes(
        self,
        source_ids:   list[str],
        merged_label: str,
        merged_type:  Optional[GraphNodeType] = None,
        actor:        str                     = SYSTEM_GRAPH_ACTOR,
    ) -> GraphNode:
        """Merge N nodes into one. All edges are re-routed to the merged node."""
        if not source_ids:
            raise GraphMergeError("source_ids must not be empty", code="GM-001")

        first = self._repo.get_node(source_ids[0])
        ntype = merged_type or first.node_type

        merged = self._factory.create_node(label=merged_label, node_type=ntype, actor=actor)
        self._repo.add_node(merged)

        source_set = set(source_ids)
        for sid in source_ids:
            for e in self._repo.get_edges_from(sid):
                if e.target_id not in source_set:
                    ne = self._factory.create_edge(
                        merged.node_id, e.target_id, e.edge_type, weight=e.weight, actor=actor,
                    )
                    try:
                        self._repo.add_edge(ne)
                    except Exception:
                        pass
            for e in self._repo.get_edges_to(sid):
                if e.source_id not in source_set:
                    ne = self._factory.create_edge(
                        e.source_id, merged.node_id, e.edge_type, weight=e.weight, actor=actor,
                    )
                    try:
                        self._repo.add_edge(ne)
                    except Exception:
                        pass
            n = self._repo.get_node(sid)
            n.merge()
            self._repo.update_node(n)

        return merged

    def split_node(
        self,
        node_id: str,
        labels:  list[str],
        actor:   str = SYSTEM_GRAPH_ACTOR,
    ) -> list[GraphNode]:
        """Split a node into N new nodes with the same type (no edges re-routed)."""
        original = self._repo.get_node(node_id)
        new_nodes: list[GraphNode] = []
        for label in labels:
            n = self._factory.create_node(
                label=label, node_type=original.node_type,
                weight=original.weight, confidence=original.confidence,
                actor=actor,
            )
            self._repo.add_node(n)
            new_nodes.append(n)
        return new_nodes

    def clone_subgraph(
        self, root_id: str, depth: int = 3, actor: str = SYSTEM_GRAPH_ACTOR,
    ) -> GraphSubgraph:
        """Clone a subgraph rooted at root_id (new node IDs)."""
        original = self._engine.dependency_graph(root_id, depth=depth)
        id_map: dict[str, str] = {}
        sg = GraphSubgraph.new(label=f"clone:{root_id}", root_id=None)

        for orig_id, orig_node in original.nodes.items():
            n = self._factory.create_node(
                label=f"[clone] {orig_node.label}", node_type=orig_node.node_type,
                properties=dict(orig_node.properties), weight=orig_node.weight,
                confidence=orig_node.confidence, actor=actor,
            )
            id_map[orig_id] = n.node_id
            sg.add_node(n)

        if root_id in id_map:
            sg.root_id = id_map[root_id]

        for orig_edge in original.edges.values():
            new_src = id_map.get(orig_edge.source_id)
            new_tgt = id_map.get(orig_edge.target_id)
            if new_src and new_tgt:
                e = self._factory.create_edge(
                    source_id=new_src, target_id=new_tgt,
                    edge_type=orig_edge.edge_type, weight=orig_edge.weight, actor=actor,
                )
                sg.add_edge(e)

        return sg

    def extract_subgraph(self, node_ids: "list[str] | set[str]") -> GraphSubgraph:
        return self._engine.extract_subgraph(set(node_ids))

    # ── Traversal ─────────────────────────────────────────────────────────────

    def bfs(
        self, start_id: str, max_depth: int = 10,
        edge_types: Optional[list[GraphEdgeType]] = None,
    ) -> list[str]:
        return self._engine.bfs(start_id, max_depth=max_depth, edge_types=edge_types)

    def dfs(
        self, start_id: str, max_depth: int = 10,
        edge_types: Optional[list[GraphEdgeType]] = None,
    ) -> list[str]:
        return self._engine.dfs(start_id, max_depth=max_depth, edge_types=edge_types)

    def shortest_path(self, source_id: str, target_id: str) -> Optional[GraphPath]:
        return self._engine.shortest_path(source_id, target_id)

    def weighted_shortest_path(self, source_id: str, target_id: str) -> Optional[GraphPath]:
        return self._engine.weighted_shortest_path(source_id, target_id)

    def multi_hop(
        self, start_id: str, hops: int = 2,
        edge_types: Optional[list[GraphEdgeType]] = None,
    ) -> dict[int, list[str]]:
        return self._engine.multi_hop(start_id, hops=hops, edge_types=edge_types)

    def neighborhood(self, node_id: str, radius: int = 1) -> set[str]:
        return self._engine.neighborhood(node_id, radius=radius)

    def reachable(self, source_id: str, target_id: str) -> bool:
        return self._engine.reachable(source_id, target_id)

    def has_cycle(self) -> bool:
        return self._engine.has_cycle()

    def dependency_traversal(self, node_id: str, depth: Optional[int] = None) -> list[str]:
        return self._engine.dependency_traversal(node_id, depth=depth)

    # ── Analytics ─────────────────────────────────────────────────────────────

    def degree_centrality(self) -> dict[str, float]:
        return self._engine.degree_centrality()

    def connected_components(self) -> list[set[str]]:
        return self._engine.connected_components()

    def influence_scores(self) -> dict[str, float]:
        return self._engine.influence_scores()

    def impact_analysis(self, node_id: str) -> ImpactResult:
        return self._engine.impact_analysis(node_id)

    def dependency_graph(self, node_id: str, depth: int = 5) -> GraphSubgraph:
        return self._engine.dependency_graph(node_id, depth=depth)

    def statistics(self) -> GraphStatistics:
        return self._engine.compute_statistics()

    def node_statistics(self, node_id: str) -> NodeStatistics:
        return self._engine.node_statistics(node_id)

    # ── Validation ────────────────────────────────────────────────────────────

    def validate_graph(self) -> dict[str, Any]:
        issues: list[str] = []
        for edge in self._repo.all_edges():
            if not self._repo.node_exists(edge.source_id):
                issues.append(f"Edge {edge.edge_id}: dangling source '{edge.source_id}'")
            if not self._repo.node_exists(edge.target_id):
                issues.append(f"Edge {edge.edge_id}: dangling target '{edge.target_id}'")
        return {
            "valid":       len(issues) == 0,
            "issues":      issues,
            "has_cycle":   self._engine.has_cycle(),
            "node_count":  self._repo.node_count(),
            "edge_count":  self._repo.edge_count(),
        }

    def status(self) -> dict[str, Any]:
        return {
            "status":      "running",
            "node_count":  self._repo.node_count(),
            "edge_count":  self._repo.edge_count(),
        }


# ── Singleton ─────────────────────────────────────────────────────────────────

def get_graph_manager() -> GraphManager:
    global _manager
    with _lock:
        if _manager is None:
            _manager = GraphManager()
        return _manager


def reset_graph_manager() -> None:
    global _manager
    with _lock:
        _manager = None
