"""
iios/knowledge/graph/graph_engine.py
======================================
Traversal and analytics engine for the Knowledge Graph.

Implements:
  BFS / DFS / Dijkstra (weighted shortest path)
  Multi-hop traversal / neighbourhood search
  Cycle detection / dependency traversal
  Degree centrality / PageRank-like influence
  Connected components / impact analysis
  Subgraph extraction
"""
from __future__ import annotations

import heapq
import logging
import threading
from collections import deque, defaultdict
from typing import Optional

from .graph_constants import (
    GraphEdgeType, MAX_TRAVERSAL_DEPTH,
    DEFAULT_PAGERANK_DAMPING, DEFAULT_PAGERANK_ITERATIONS,
)
from .graph_exceptions import GraphNodeNotFoundError, GraphTraversalError
from .models.graph_node       import GraphNode
from .models.graph_edge       import GraphEdge
from .models.graph_path       import GraphPath, PathStep
from .models.graph_subgraph   import GraphSubgraph
from .models.graph_statistics import GraphStatistics, NodeStatistics, ImpactResult
from .storage.graph_repository import GraphRepository, get_graph_repository

__all__ = ["GraphEngine", "get_graph_engine", "reset_graph_engine"]

_LOG  = logging.getLogger("iios.knowledge.graph.engine")
_lock = threading.Lock()
_engine: Optional["GraphEngine"] = None


class GraphEngine:
    """
    Stateless traversal + analytics engine.

    All state lives in the injected GraphRepository.
    Thread-safe: each public method acquires no instance-level lock
    (the repository's RLock handles concurrency).

    Usage::

        engine = get_graph_engine()
        engine.bfs("iios.graph/some-uuid", max_depth=5)
        path   = engine.shortest_path("a", "b")
        impact = engine.impact_analysis("iios.graph/some-uuid")
    """

    def __init__(self, repository: Optional[GraphRepository] = None) -> None:
        self._repo = repository or get_graph_repository()

    # ── Traversal ─────────────────────────────────────────────────────────────

    def bfs(
        self,
        start_id:      str,
        max_depth:     int                         = MAX_TRAVERSAL_DEPTH,
        edge_types:    Optional[list[GraphEdgeType]] = None,
        include_start: bool                        = True,
    ) -> list[str]:
        """Breadth-first search. Returns node IDs in visit order."""
        if not self._repo.node_exists(start_id):
            raise GraphNodeNotFoundError(f"Start node '{start_id}' not found", code="GE-001")

        visited: set[str]              = {start_id}
        queue:   deque[tuple[str,int]] = deque([(start_id, 0)])
        result:  list[str]             = []

        while queue:
            node_id, depth = queue.popleft()
            if include_start or depth > 0:
                result.append(node_id)
            if depth >= max_depth:
                continue
            for edge in self._repo.get_edges_from(node_id):
                if not edge.is_active:
                    continue
                if edge_types and edge.edge_type not in edge_types:
                    continue
                if edge.target_id not in visited:
                    visited.add(edge.target_id)
                    queue.append((edge.target_id, depth + 1))

        return result

    def dfs(
        self,
        start_id:      str,
        max_depth:     int                         = MAX_TRAVERSAL_DEPTH,
        edge_types:    Optional[list[GraphEdgeType]] = None,
        include_start: bool                        = True,
    ) -> list[str]:
        """Iterative depth-first search. Returns node IDs in DFS order."""
        if not self._repo.node_exists(start_id):
            raise GraphNodeNotFoundError(f"Start node '{start_id}' not found", code="GE-002")

        visited: set[str]               = set()
        # Stack: (node_id, depth)
        stack:   list[tuple[str, int]]  = [(start_id, 0)]
        result:  list[str]              = []

        while stack:
            node_id, depth = stack.pop()
            if node_id in visited:
                continue
            visited.add(node_id)
            if include_start or depth > 0:
                result.append(node_id)
            if depth >= max_depth:
                continue
            for edge in reversed(self._repo.get_edges_from(node_id)):
                if not edge.is_active:
                    continue
                if edge_types and edge.edge_type not in edge_types:
                    continue
                if edge.target_id not in visited:
                    stack.append((edge.target_id, depth + 1))

        return result

    def shortest_path(self, source_id: str, target_id: str) -> Optional[GraphPath]:
        """BFS unweighted shortest path."""
        if source_id == target_id:
            return GraphPath(
                source_id=source_id, target_id=target_id,
                steps=[PathStep(node_id=source_id, depth=0)],
                total_cost=0.0, algorithm="bfs",
            )

        if not self._repo.node_exists(source_id):
            raise GraphNodeNotFoundError(f"Source '{source_id}' not found", code="GE-003")
        if not self._repo.node_exists(target_id):
            raise GraphNodeNotFoundError(f"Target '{target_id}' not found", code="GE-004")

        visited: set[str] = {source_id}
        queue:   deque[tuple[str, list[PathStep]]] = deque([
            (source_id, [PathStep(node_id=source_id, depth=0)])
        ])

        while queue:
            node_id, path = queue.popleft()
            for edge in self._repo.get_edges_from(node_id):
                if not edge.is_active:
                    continue
                nb = edge.target_id
                step = PathStep(
                    node_id=nb, edge_id=edge.edge_id, depth=len(path),
                    edge_type=edge.edge_type.value, edge_weight=edge.weight,
                )
                if nb == target_id:
                    steps = path + [step]
                    return GraphPath(
                        source_id=source_id, target_id=target_id,
                        steps=steps, total_cost=float(len(steps) - 1),
                        algorithm="bfs",
                    )
                if nb not in visited:
                    visited.add(nb)
                    queue.append((nb, path + [step]))

        return None

    def weighted_shortest_path(self, source_id: str, target_id: str) -> Optional[GraphPath]:
        """Dijkstra algorithm: cost = (1 - edge.weight)."""
        if source_id == target_id:
            return GraphPath(
                source_id=source_id, target_id=target_id,
                steps=[PathStep(node_id=source_id, depth=0)],
                total_cost=0.0, algorithm="dijkstra",
            )

        if not self._repo.node_exists(source_id):
            raise GraphNodeNotFoundError(f"Source '{source_id}' not found", code="GE-005")

        dist:    dict[str, float]                          = {source_id: 0.0}
        prev:    dict[str, tuple[str, str, str, float]]    = {}  # node → (parent, eid, etype, ew)
        pq:      list[tuple[float, str]]                   = [(0.0, source_id)]
        visited: set[str]                                  = set()

        while pq:
            cost, u = heapq.heappop(pq)
            if u in visited:
                continue
            visited.add(u)
            if u == target_id:
                break
            for edge in self._repo.get_edges_from(u):
                if not edge.is_active:
                    continue
                v        = edge.target_id
                ecost    = max(0.001, 1.0 - edge.weight)
                new_cost = cost + ecost
                if new_cost < dist.get(v, float("inf")):
                    dist[v] = new_cost
                    prev[v] = (u, edge.edge_id, edge.edge_type.value, edge.weight)
                    heapq.heappush(pq, (new_cost, v))

        if target_id not in dist:
            return None

        # Reconstruct path (reverse order)
        steps: list[PathStep] = []
        node = target_id
        while node != source_id:
            parent, eid, etype, ew = prev[node]
            steps.append(PathStep(node_id=node, edge_id=eid, depth=0, edge_type=etype, edge_weight=ew))
            node = parent
        steps.append(PathStep(node_id=source_id, depth=0))
        steps.reverse()
        for i, s in enumerate(steps):
            s.depth = i

        return GraphPath(
            source_id=source_id, target_id=target_id,
            steps=steps, total_cost=dist[target_id], algorithm="dijkstra",
        )

    def multi_hop(
        self,
        start_id:   str,
        hops:       int                           = 2,
        edge_types: Optional[list[GraphEdgeType]] = None,
    ) -> dict[int, list[str]]:
        """Return nodes reachable at each exact hop count (1..hops)."""
        if not self._repo.node_exists(start_id):
            raise GraphNodeNotFoundError(f"Node '{start_id}' not found", code="GE-006")

        result:   dict[int, list[str]] = {}
        frontier: set[str]             = {start_id}
        visited:  set[str]             = {start_id}

        for hop in range(1, hops + 1):
            next_frontier: set[str] = set()
            for nid in frontier:
                for edge in self._repo.get_edges_from(nid):
                    if not edge.is_active:
                        continue
                    if edge_types and edge.edge_type not in edge_types:
                        continue
                    if edge.target_id not in visited:
                        visited.add(edge.target_id)
                        next_frontier.add(edge.target_id)
            result[hop] = sorted(next_frontier)
            frontier = next_frontier
            if not frontier:
                break

        return result

    def neighborhood(self, node_id: str, radius: int = 1) -> set[str]:
        """All nodes within *radius* hops in either direction."""
        if not self._repo.node_exists(node_id):
            raise GraphNodeNotFoundError(f"Node '{node_id}' not found", code="GE-007")

        result:   set[str] = set()
        frontier: set[str] = {node_id}
        visited:  set[str] = {node_id}

        for _ in range(radius):
            next_f: set[str] = set()
            for nid in frontier:
                for edge in self._repo.get_edges_from(nid):
                    if edge.is_active and edge.target_id not in visited:
                        visited.add(edge.target_id)
                        next_f.add(edge.target_id)
                        result.add(edge.target_id)
                for edge in self._repo.get_edges_to(nid):
                    if edge.is_active and edge.source_id not in visited:
                        visited.add(edge.source_id)
                        next_f.add(edge.source_id)
                        result.add(edge.source_id)
            frontier = next_f

        return result

    def reachable(self, source_id: str, target_id: str) -> bool:
        """Return True if *target_id* is reachable from *source_id*."""
        if source_id == target_id:
            return True
        visited: set[str]  = {source_id}
        queue:   deque[str] = deque([source_id])
        while queue:
            n = queue.popleft()
            for edge in self._repo.get_edges_from(n):
                if not edge.is_active:
                    continue
                if edge.target_id == target_id:
                    return True
                if edge.target_id not in visited:
                    visited.add(edge.target_id)
                    queue.append(edge.target_id)
        return False

    def has_cycle(self) -> bool:
        """Return True if the graph contains any directed cycle (iterative DFS)."""
        node_ids = self._repo.all_node_ids()
        visited:  set[str] = set()
        in_stack: set[str] = set()
        parent:   dict[str, Optional[str]] = {}

        def _dfs(start: str) -> bool:
            stack = [(start, False)]
            while stack:
                n, leaving = stack.pop()
                if leaving:
                    in_stack.discard(n)
                    continue
                if n in in_stack:
                    return True
                if n in visited:
                    continue
                visited.add(n)
                in_stack.add(n)
                stack.append((n, True))  # mark as "leaving" for cleanup
                for edge in self._repo.get_edges_from(n):
                    if not edge.is_active:
                        continue
                    if edge.target_id in in_stack:
                        return True
                    if edge.target_id not in visited:
                        stack.append((edge.target_id, False))
            return False

        for nid in node_ids:
            if nid not in visited:
                if _dfs(nid):
                    return True
        return False

    def dependency_traversal(
        self,
        node_id:    str,
        depth:      Optional[int]               = None,
        edge_types: Optional[list[GraphEdgeType]] = None,
    ) -> list[str]:
        """Follow DEPENDS_ON edges to find all dependencies."""
        et = edge_types or [GraphEdgeType.DEPENDS_ON]
        return self.bfs(node_id, max_depth=depth or MAX_TRAVERSAL_DEPTH, edge_types=et, include_start=False)

    # ── Analytics ─────────────────────────────────────────────────────────────

    def in_degree(self, node_id: Optional[str] = None) -> "int | dict[str, int]":
        if node_id is not None:
            return len(self._repo.get_edges_to(node_id))
        return {nid: len(self._repo.get_edges_to(nid)) for nid in self._repo.all_node_ids()}

    def out_degree(self, node_id: Optional[str] = None) -> "int | dict[str, int]":
        if node_id is not None:
            return len(self._repo.get_edges_from(node_id))
        return {nid: len(self._repo.get_edges_from(nid)) for nid in self._repo.all_node_ids()}

    def degree_centrality(self) -> dict[str, float]:
        """Normalised degree centrality (in + out) / 2*(n-1)."""
        nodes = self._repo.all_node_ids()
        n = len(nodes)
        if n <= 1:
            return {nid: 0.0 for nid in nodes}
        norm = 2 * (n - 1)
        return {
            nid: (len(self._repo.get_edges_to(nid)) + len(self._repo.get_edges_from(nid))) / norm
            for nid in nodes
        }

    def connected_components(self) -> list[set[str]]:
        """Weakly connected components (ignoring edge direction)."""
        nodes   = set(self._repo.all_node_ids())
        visited: set[str]         = set()
        result:  list[set[str]]   = []

        for start in nodes:
            if start in visited:
                continue
            component: set[str] = set()
            queue: deque[str]   = deque([start])
            while queue:
                n = queue.popleft()
                if n in component:
                    continue
                component.add(n)
                visited.add(n)
                for edge in self._repo.get_edges_from(n):
                    if edge.is_active and edge.target_id not in component:
                        queue.append(edge.target_id)
                for edge in self._repo.get_edges_to(n):
                    if edge.is_active and edge.source_id not in component:
                        queue.append(edge.source_id)
            result.append(component)

        return result

    def influence_scores(
        self,
        iterations: int   = DEFAULT_PAGERANK_ITERATIONS,
        damping:    float = DEFAULT_PAGERANK_DAMPING,
    ) -> dict[str, float]:
        """PageRank-like influence scores for all nodes."""
        nodes = self._repo.all_node_ids()
        n = len(nodes)
        if n == 0:
            return {}

        scores: dict[str, float] = {nid: 1.0 / n for nid in nodes}
        base = (1.0 - damping) / n

        for _ in range(iterations):
            new_scores: dict[str, float] = {}
            for nid in nodes:
                incoming  = self._repo.get_edges_to(nid)
                rank_sum  = 0.0
                for edge in incoming:
                    if not edge.is_active:
                        continue
                    src      = edge.source_id
                    out_cnt  = sum(1 for e in self._repo.get_edges_from(src) if e.is_active)
                    if out_cnt > 0:
                        rank_sum += scores.get(src, 0.0) / out_cnt * edge.weight
                new_scores[nid] = base + damping * rank_sum
            scores = new_scores

        return scores

    def influence_score(self, node_id: str) -> float:
        return self.influence_scores().get(node_id, 0.0)

    def impact_analysis(self, node_id: str) -> ImpactResult:
        """Compute downstream impact using BFS distance map."""
        if not self._repo.node_exists(node_id):
            raise GraphNodeNotFoundError(f"Node '{node_id}' not found", code="GE-008")

        # BFS from node_id to get distances
        distances: dict[str, int] = {}
        visited:   set[str]       = {node_id}
        queue:     deque[tuple[str, int]] = deque([(node_id, 0)])

        while queue:
            nid, depth = queue.popleft()
            if nid != node_id:
                distances[nid] = depth
            for edge in self._repo.get_edges_from(nid):
                if edge.is_active and edge.target_id not in visited:
                    visited.add(edge.target_id)
                    queue.append((edge.target_id, depth + 1))

        direct_out = [e.target_id for e in self._repo.get_edges_from(node_id) if e.is_active]
        direct_in  = [e.source_id for e in self._repo.get_edges_to(node_id)   if e.is_active]
        transitive = list(distances.keys())
        max_depth  = max(distances.values(), default=0)
        impact_score = len(transitive) / max(1, self._repo.node_count())

        return ImpactResult(
            node_id               = node_id,
            direct_dependents     = direct_out,
            transitive_dependents = transitive,
            direct_predecessors   = direct_in,
            impact_score          = impact_score,
            max_depth             = max_depth,
        )

    def compute_statistics(self) -> GraphStatistics:
        """Compute aggregate graph statistics."""
        all_nodes   = self._repo.all_nodes(include_deleted=True)
        all_edges   = self._repo.all_edges(include_deleted=True)
        active_n    = [nd for nd in all_nodes if not nd.is_deleted]
        active_e    = [e  for e  in all_edges if not e.is_deleted]
        n           = len(active_n)

        in_d  = [len(self._repo.get_edges_to(nd.node_id))   for nd in active_n]
        out_d = [len(self._repo.get_edges_from(nd.node_id)) for nd in active_n]

        max_e   = n * (n - 1) if n > 1 else 1
        density = len(active_e) / max_e

        components = self.connected_components()
        isolated   = sum(1 for c in components if len(c) == 1)

        nodes_by_type: dict[str, int] = defaultdict(int)
        for nd in active_n:
            nodes_by_type[nd.node_type.value] += 1

        edges_by_type: dict[str, int] = defaultdict(int)
        for e in active_e:
            edges_by_type[e.edge_type.value] += 1

        return GraphStatistics(
            node_count          = len(all_nodes),
            edge_count          = len(all_edges),
            active_node_count   = n,
            active_edge_count   = len(active_e),
            deleted_node_count  = len(all_nodes) - n,
            deleted_edge_count  = len(all_edges) - len(active_e),
            avg_in_degree       = sum(in_d)  / n if n > 0 else 0.0,
            avg_out_degree      = sum(out_d) / n if n > 0 else 0.0,
            max_in_degree       = max(in_d,  default=0),
            max_out_degree      = max(out_d, default=0),
            density             = density,
            is_dag              = not self.has_cycle(),
            component_count     = len(components),
            isolated_node_count = isolated,
            nodes_by_type       = dict(nodes_by_type),
            edges_by_type       = dict(edges_by_type),
        )

    def node_statistics(self, node_id: str) -> NodeStatistics:
        in_d  = len(self._repo.get_edges_to(node_id))
        out_d = len(self._repo.get_edges_from(node_id))
        nbrs  = self.neighborhood(node_id, radius=1)
        return NodeStatistics(
            node_id        = node_id,
            in_degree      = in_d,
            out_degree     = out_d,
            neighbor_count = len(nbrs),
        )

    # ── Subgraph extraction ───────────────────────────────────────────────────

    def dependency_graph(self, node_id: str, depth: int = 5) -> GraphSubgraph:
        ids = set(self.bfs(node_id, max_depth=depth, include_start=True))
        return self._build_subgraph(ids, label=f"deps:{node_id}")

    def extract_subgraph(self, node_ids: "set[str] | list[str]") -> GraphSubgraph:
        return self._build_subgraph(set(node_ids), label="subgraph")

    def _build_subgraph(self, node_ids: set[str], label: str = "subgraph") -> GraphSubgraph:
        sg = GraphSubgraph.new(label=label)
        for nid in node_ids:
            n = self._repo.get_node_optional(nid)
            if n:
                sg.add_node(n)
        for nid in node_ids:
            for edge in self._repo.get_edges_from(nid):
                if edge.is_active and edge.target_id in node_ids:
                    sg.add_edge(edge)
        return sg


# ── Singleton ─────────────────────────────────────────────────────────────────

def get_graph_engine() -> GraphEngine:
    global _engine
    with _lock:
        if _engine is None:
            _engine = GraphEngine()
        return _engine


def reset_graph_engine() -> None:
    global _engine
    with _lock:
        _engine = None
